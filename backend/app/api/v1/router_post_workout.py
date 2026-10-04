from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.agents.post_workout.agent import PostWorkoutAgent, get_post_workout_agent
from app.agents.post_workout.llm import PostWorkoutModelError
from app.core.deps import CurrentUser, DbSession
from app.models import Message, PostWorkoutCheckIn, PostWorkoutReport
from app.schemas.post_workout import (
    ChatTurn,
    CheckInMessage,
    CheckInResponse,
    Period,
    ReportRequest,
    ReportResponse,
    StartCheckIn,
)
from app.services import post_workout as store
from app.services.post_workout_reports import describe_report, ensure_report, report_response
from app.statistics.post_workout import utc

router = APIRouter(prefix="/agents/post-workout", tags=["post-workout agent"])
Agent = Annotated[PostWorkoutAgent, Depends(get_post_workout_agent)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0)]


@router.post("/sessions", response_model=CheckInResponse)
def start(data: StartCheckIn, user: CurrentUser, db: DbSession):
    return store.response_for(store.create_checkin(db, user.id, data))


@router.get("/sessions/{session_id}", response_model=CheckInResponse)
def session(session_id: str, user: CurrentUser, db: DbSession):
    return store.response_for(store.get_checkin(db, user.id, session_id))


@router.post("/sessions/{session_id}/chat", response_model=CheckInResponse)
async def chat(session_id: str, data: ChatTurn, user: CurrentUser, db: DbSession, agent: Agent):
    try:
        return await agent.run(db, user.id, session_id, data)
    except PostWorkoutModelError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/sessions/{session_id}/history", response_model=list[CheckInMessage])
def history(session_id: str, user: CurrentUser, db: DbSession, limit: PageLimit = 50, offset: PageOffset = 0):
    store.get_checkin(db, user.id, session_id)
    rows = db.scalars(
        select(Message)
        .where(
            Message.user_id == user.id,
            Message.agent == "post_workout",
            Message.post_workout_checkin_id == session_id,
        )
        .order_by(Message.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [CheckInMessage(role=row.role, content=row.content, created_at=utc(row.created_at)) for row in rows]


@router.get("/feedback", response_model=list[CheckInResponse])
def feedback(user: CurrentUser, db: DbSession, limit: PageLimit = 50, offset: PageOffset = 0):
    rows = db.scalars(
        select(PostWorkoutCheckIn)
        .where(
            PostWorkoutCheckIn.user_id == user.id,
            PostWorkoutCheckIn.status == "completed",
        )
        .order_by(PostWorkoutCheckIn.workout_ended_at.desc(), PostWorkoutCheckIn.id)
        .offset(offset)
        .limit(limit)
    )
    return [store.response_for(row) for row in rows]


@router.post("/reports", response_model=ReportResponse)
async def generate_report(data: ReportRequest, user: CurrentUser, db: DbSession, agent: Agent):
    user_id = user.id
    profile = store.user_context(db, user_id)
    period = data.period or profile["reporting_frequency"]
    anchor = data.anchor_date or datetime.now(ZoneInfo(profile["timezone"])).date()
    report = ensure_report(db, user_id, period, profile["timezone"], anchor)
    report_id = report.id
    db.commit()  # Persist calculations even when Azure cannot produce the comment.
    return await describe_report(db, user_id, report_id, agent.llm, profile, data.regenerate_comment)


@router.get("/reports", response_model=list[ReportResponse])
def reports(
    user: CurrentUser,
    db: DbSession,
    period: Period | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: PageLimit = 50,
    offset: PageOffset = 0,
):
    if start and end and start > end:
        raise HTTPException(422, "start must not be after end")
    query = select(PostWorkoutReport).where(PostWorkoutReport.user_id == user.id)
    if period:
        query = query.where(PostWorkoutReport.period == period)
    if start:
        query = query.where(PostWorkoutReport.period_end >= start)
    if end:
        query = query.where(PostWorkoutReport.period_start <= end)
    rows = db.scalars(
        query.order_by(PostWorkoutReport.computed_at.desc(), PostWorkoutReport.id).offset(offset).limit(limit)
    )
    return [report_response(row) for row in rows]
