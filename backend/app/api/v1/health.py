from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.core.deps import CurrentUser, DbSession
from app.statistics.charts import analyze, render_pdf

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/report")
def report(user: CurrentUser, db: DbSession, limit: Annotated[int, Query(ge=1, le=1000)] = 200):
    result = analyze(db, user.id, limit=limit)
    buffer = BytesIO()
    render_pdf(result, buffer)
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="raport.pdf"'},
    )
