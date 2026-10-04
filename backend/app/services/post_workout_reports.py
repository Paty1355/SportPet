from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import openai
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.post_workout.llm import PostWorkoutLLM, PostWorkoutModelError
from app.models import PostWorkoutCheckIn, PostWorkoutReport
from app.schemas.post_workout import ReportResponse, ReportStatistics, Support
from app.services.post_workout import payload_hash
from app.statistics.post_workout import (
    ANALYSIS_VERSION,
    calendar_period,
    compare_checkins,
    observations_for,
    period_bounds,
    utc,
)


def ensure_report(db: Session, user_id: int, period: str, timezone: str, anchor) -> PostWorkoutReport:
    now = datetime.now(UTC)
    if anchor > now.astimezone(ZoneInfo(timezone)).date():
        raise HTTPException(422, "anchorDate cannot be in the future")
    start, end = calendar_period(period, anchor)
    previous_start, previous_end = calendar_period(period, start - timedelta(days=1))
    lo, hi = period_bounds(start, end, timezone)
    previous_lo, previous_hi = period_bounds(previous_start, previous_end, timezone)

    def rows_in(lower, upper):
        return list(
            db.scalars(
                select(PostWorkoutCheckIn)
                .where(
                    PostWorkoutCheckIn.user_id == user_id,
                    PostWorkoutCheckIn.status == "completed",
                    PostWorkoutCheckIn.workout_ended_at >= lower,
                    PostWorkoutCheckIn.workout_ended_at < upper,
                )
                .order_by(PostWorkoutCheckIn.workout_ended_at, PostWorkoutCheckIn.id)
            )
        )

    current, previous = rows_in(lo, hi), rows_in(previous_lo, previous_hi)
    fields = (
        "id",
        "fatigue_level",
        "feeling_change",
        "mood_level",
        "motivation_level",
        "perceived_exertion_rating",
        "pain_experienced",
        "pain_intensity",
    )
    snapshot = {
        "version": ANALYSIS_VERSION,
        "current": [{key: getattr(row, key) for key in fields} for row in current],
        "previous": [{key: getattr(row, key) for key in fields} for row in previous],
        "is_partial": now < hi,
    }
    fingerprint = payload_hash(snapshot)
    condition = (
        PostWorkoutReport.user_id == user_id,
        PostWorkoutReport.period == period,
        PostWorkoutReport.timezone == timezone,
        PostWorkoutReport.period_start == start,
        PostWorkoutReport.snapshot_hash == fingerprint,
    )
    existing = db.scalar(select(PostWorkoutReport).where(*condition))
    if existing is not None:
        return existing
    report = PostWorkoutReport(
        user_id=user_id,
        period=period,
        timezone=timezone,
        period_start=start,
        period_end=end,
        is_partial=now < hi,
        snapshot_hash=fingerprint,
        analysis_version=ANALYSIS_VERSION,
        statistics=compare_checkins(current, previous).model_dump(mode="json", by_alias=True),
    )
    try:
        with db.begin_nested():
            db.add(report)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(PostWorkoutReport).where(*condition))
        if existing is None:
            raise
        return existing
    return report


def report_response(report: PostWorkoutReport) -> ReportResponse:
    statistics = ReportStatistics.model_validate(report.statistics)
    return ReportResponse(
        id=report.id,
        period=report.period,
        timezone=report.timezone,
        period_start=report.period_start,
        period_end=report.period_end,
        is_partial=report.is_partial,
        computed_at=utc(report.computed_at),
        analysis_version=report.analysis_version,
        statistics=statistics,
        observations=observations_for(statistics),
        support=Support.model_validate(report.support) if report.support else None,
    )


def selected_support(result, observations) -> Support:
    available = {observation.id: observation.text for observation in observations}
    if any(key not in available for key in result.observation_ids):
        raise PostWorkoutModelError("Azure selected an observation that was not computed by the backend")
    if any(character.isdigit() for character in result.message):
        raise PostWorkoutModelError("Azure included numeric claims in the support message")
    return Support(
        status="available",
        message=result.message,
        observations=[available[key] for key in dict.fromkeys(result.observation_ids)],
    )


async def describe_report(
    db: Session, user_id: int, report_id: str, llm: PostWorkoutLLM, profile: dict, regenerate: bool = False
) -> ReportResponse:
    row = db.scalar(
        select(PostWorkoutReport)
        .where(
            PostWorkoutReport.id == report_id,
            PostWorkoutReport.user_id == user_id,
        )
        .with_for_update()
    )
    if row is None:
        raise HTTPException(404, "Post-workout report not found")
    response = report_response(row)
    if response.support and response.support.status == "available" and not regenerate:
        db.commit()
        return response
    if (
        response.support
        and response.support.status == "pending"
        and response.support.started_at
        and (datetime.now(UTC) - utc(response.support.started_at) < timedelta(minutes=2))
    ):
        db.commit()
        return response
    pending = Support(
        status="pending", message="Your report is saved. A comment is being generated.", started_at=datetime.now(UTC)
    )
    row.support = pending.model_dump(mode="json", by_alias=True)
    db.commit()
    context = {
        "profile": profile,
        "statistics": response.statistics.model_dump(mode="json", by_alias=True),
        "available_observations": [item.model_dump() for item in response.observations],
        "safety_notice": None,
    }
    try:
        result = await llm.support(context)
        support = selected_support(result, response.observations)
    except (openai.APIError, PostWorkoutModelError, HTTPException):
        support = Support(
            status="unavailable", message="Your report is saved. A personalised comment is unavailable right now."
        )
    result = db.execute(
        update(PostWorkoutReport)
        .where(
            PostWorkoutReport.id == report_id,
            PostWorkoutReport.user_id == user_id,
            PostWorkoutReport.support["startedAt"].as_string()
            == pending.model_dump(mode="json", by_alias=True)["startedAt"],
        )
        .values(support=support.model_dump(mode="json", by_alias=True))
        .execution_options(synchronize_session=False)
    )
    db.commit()
    if result.rowcount != 1:
        db.expire_all()
        return report_response(db.get(PostWorkoutReport, report_id))
    response.support = support
    return response
