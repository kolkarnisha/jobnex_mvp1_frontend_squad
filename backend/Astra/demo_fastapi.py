"""FastAPI-backed local demo with in-memory SQLite storage.

Run from the project root:
    python -m uvicorn demo_fastapi:app --app-dir backend/Astra --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from analyzer import analyze_resume
from demo_server import DATABASE, SAMPLE_JOBS

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend" / "index.html"
DATABASE_LOCK = threading.Lock()

app = FastAPI(title="JOBNEX Local Demo", version="1.0.0")


class AnalyzeRequest(BaseModel):
    resume_text: str = Field(min_length=1)
    jd_text: str = Field(min_length=1)

    @field_validator("resume_text", "jd_text")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value


class QueueApplicationRequest(BaseModel):
    resume_text: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    job_description: str = Field(min_length=1)
    job_url: str | None = None

    @field_validator("resume_text", "job_title", "company", "job_description")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "demo", "database": "in-memory SQLite"}


@app.post("/api/analyze")
@app.post("/api/analyse")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    result = analyze_resume(request.resume_text, request.jd_text)
    with DATABASE_LOCK:
        cursor = DATABASE.execute(
            """
            INSERT INTO analyses
                (matched_score, matched_skills, missing_skills, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                result["matched_score"],
                json.dumps(result["matched_skills"]),
                json.dumps(result["missing_skills"]),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        DATABASE.commit()
        analysis_id = cursor.lastrowid
    return {"Analysis_Id": analysis_id, **result}


@app.get("/api/analyses")
def list_analyses() -> dict[str, list[dict[str, Any]]]:
    with DATABASE_LOCK:
        rows = DATABASE.execute(
            """
            SELECT analysis_id, matched_score, matched_skills, missing_skills, created_at
            FROM analyses ORDER BY analysis_id DESC LIMIT 20
            """
        ).fetchall()
    return {
        "analyses": [
            {
                "Analysis_id": row["analysis_id"],
                "matched_score": row["matched_score"],
                "matched_skills": json.loads(row["matched_skills"]),
                "missing_skills": json.loads(row["missing_skills"]),
                "created_At": row["created_at"],
            }
            for row in rows
        ]
    }


@app.get("/api/jobs/search")
def search_jobs(
    keyword: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=25),
) -> dict[str, Any]:
    words = keyword.casefold().split()
    jobs = [
        job
        for job in SAMPLE_JOBS
        if all(
            word
            in " ".join(
                str(job.get(key, ""))
                for key in ("title", "company", "location", "skills", "description")
            ).casefold()
            for word in words
        )
    ]
    return {"jobs": jobs[:limit], "mode": "sample"}


@app.post("/api/applications", status_code=201)
def queue_application(request: QueueApplicationRequest) -> dict[str, Any]:
    result = analyze_resume(request.resume_text, request.job_description)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with DATABASE_LOCK:
            cursor = DATABASE.execute(
                """
                INSERT INTO applications
                    (job_title, company, job_url, match_score, status, created_at)
                VALUES (?, ?, ?, ?, 'queued_demo', ?)
                """,
                (
                    request.job_title.strip(),
                    request.company.strip(),
                    request.job_url,
                    result["matched_score"],
                    created_at,
                ),
            )
            DATABASE.commit()
            application_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="A demo application already exists for this role and company",
        ) from error

    return {
        "application_id": application_id,
        "job_title": request.job_title.strip(),
        "company": request.company.strip(),
        "job_url": request.job_url,
        "match_score": result["matched_score"],
        "status": "queued_demo",
        "status_message": "Stored in the local demo database; no email was sent.",
        "created_at": created_at,
    }


@app.get("/api/applications")
def list_applications() -> dict[str, list[dict[str, Any]]]:
    with DATABASE_LOCK:
        rows = DATABASE.execute(
            """
            SELECT application_id, job_title, company, job_url, match_score, status, created_at
            FROM applications ORDER BY application_id DESC LIMIT 50
            """
        ).fetchall()
    return {
        "applications": [
            {
                "application_id": row["application_id"],
                "job_title": row["job_title"],
                "company": row["company"],
                "job_url": row["job_url"],
                "match_score": row["match_score"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def frontend_home() -> RedirectResponse:
    return RedirectResponse("/login.html")


@app.get("/{page_name}.html", include_in_schema=False)
def frontend_page(page_name: str) -> FileResponse:
    page_path = (FRONTEND_ROOT / f"{page_name}.html").resolve()
    try:
        page_path.relative_to(FRONTEND_ROOT.resolve())
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Page not found") from error
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(page_path, media_type="text/html")


app.mount("/", StaticFiles(directory=FRONTEND_ROOT), name="frontend-assets")
