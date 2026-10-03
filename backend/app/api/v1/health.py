from io import BytesIO

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ServiceAuth
from app.models import BloodPressureReading, CycleDay, DailySummary, EcgRecording, User, VitalSample
from app.schemas.health import HealthIngest, HealthIngestResult
from app.schemas.user import HealthProfileFields, UserOut
from app.services import user_service
from app.statistics import analyze
from app.statistics.charts import render_pdf

router = APIRouter(prefix="/health", tags=["health"])
# Dla generatora danych: działa na dowolnym użytkowniku, chroniony nagłówkiem X-Service-Key
service_router = APIRouter(prefix="/health/service", tags=["health-service"], dependencies=[ServiceAuth])


def _insert_new(db: Session, model, user_id: int, items) -> int:
    """Wstawia wiersze, pomijając te o istniejącym kluczu (ingest jest idempotentny). Zwraca liczbę nowych."""
    rows = [{**item.model_dump(), "user_id": user_id} for item in items]
    if not rows:
        return 0
    # on_conflict_do_nothing jest per-dialekt: Postgres w produkcji, SQLite w testach
    insert = postgresql.insert if db.get_bind().dialect.name == "postgresql" else sqlite.insert
    # rowcount bywa -1 (psycopg), więc liczymy wiersze z RETURNING – zwraca tylko faktycznie wstawione
    pk = next(iter(model.__table__.primary_key.columns))
    return len(db.execute(insert(model).values(rows).on_conflict_do_nothing().returning(pk)).all())


def _ingest(db: Session, user: User, data: HealthIngest) -> HealthIngestResult:
    if data.cycle and user.sex != "F":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cycle data requires user sex 'F'")
    result = HealthIngestResult(
        samples=_insert_new(db, VitalSample, user.id, data.samples),
        daily=_insert_new(db, DailySummary, user.id, data.daily),
        blood_pressure=_insert_new(db, BloodPressureReading, user.id, data.blood_pressure),
        ecg=_insert_new(db, EcgRecording, user.id, data.ecg),
        cycle=_insert_new(db, CycleDay, user.id, data.cycle),
    )
    db.commit()
    return result


@router.post("/ingest", response_model=HealthIngestResult, status_code=status.HTTP_201_CREATED)
def ingest(data: HealthIngest, user: CurrentUser, db: DbSession):
    return _ingest(db, user, data)


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@service_router.get("/users", response_model=list[UserOut])
def list_users(db: DbSession):
    return db.scalars(select(User).where(User.is_active).order_by(User.id)).all()


@service_router.patch("/users/{user_id}/profile", response_model=UserOut)
def set_profile(user_id: int, data: HealthProfileFields, db: DbSession):
    return user_service.update_user(db, _get_user(db, user_id), data)


@service_router.post("/ingest/{user_id}", response_model=HealthIngestResult, status_code=status.HTTP_201_CREATED)
def ingest_for_user(user_id: int, data: HealthIngest, db: DbSession):
    return _ingest(db, _get_user(db, user_id), data)


@router.get("/report")
def report(user: CurrentUser, db: DbSession):
    result = analyze(db, user.id, include_series=True)
    if not any(m["status"] == "ok" for m in result["metrics"].values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Za mało danych do wygenerowania raportu")
    buffer = BytesIO()
    render_pdf(result, buffer)
    return Response(buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="raport.pdf"'})
