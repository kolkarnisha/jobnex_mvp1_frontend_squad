"""Local, dependency-free demo API with in-memory SQLite storage.

Run from the project root with:
    python backend/Astra/demo_server.py
The server serves frontend/index.html and exposes demo routes under /api.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend" / "index.html"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from analyzer import analyze_resume


DATABASE = sqlite3.connect(":memory:", check_same_thread=False)
DATABASE.row_factory = sqlite3.Row
DATABASE.executescript(
    """
    CREATE TABLE analyses (
        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        matched_score REAL NOT NULL,
        matched_skills TEXT NOT NULL,
        missing_skills TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE applications (
        application_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_title TEXT NOT NULL,
        company TEXT NOT NULL,
        job_url TEXT,
        match_score REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(job_title, company)
    );
    """
)

SAMPLE_JOBS = [
    {
        "id": 1,
        "title": "Frontend Developer",
        "company": "Northwind Labs",
        "location": "Bengaluru, India",
        "region": "bengaluru",
        "experience": "junior",
        "certifications": [],
        "match": 86,
        "skills": "html css javascript react",
        "job_type": "Full-time",
        "url": "https://example.test/jobs/northwind-frontend",
        "description": "Build frontend applications with JavaScript, React, HTML, and CSS.",
    },
    {
        "id": 2,
        "title": "Python Developer",
        "company": "Brightpath Systems",
        "location": "Hyderabad, India",
        "region": "india",
        "experience": "mid",
        "certifications": ["aws"],
        "match": 78,
        "skills": "python fastapi docker sql",
        "job_type": "Full-time",
        "url": "https://example.test/jobs/brightpath-python",
        "description": "Develop Python APIs with FastAPI, SQL, Docker, and automated tests.",
    },
    {
        "id": 3,
        "title": "Data Analyst",
        "company": "Orbit Analytics",
        "location": "Remote",
        "region": "global",
        "experience": "fresher",
        "certifications": [],
        "match": 64,
        "skills": "sql python dashboards",
        "job_type": "Remote",
        "url": "https://example.test/jobs/orbit-analyst",
        "description": "Use SQL and Python to prepare datasets and build dashboards.",
    },
    {
        "id": 4,
        "title": "DevOps Engineer",
        "company": "Cobalt Works",
        "location": "Bengaluru, India",
        "region": "bengaluru",
        "experience": "mid",
        "certifications": ["azure", "aws"],
        "match": 59,
        "skills": "docker kubernetes ci cd",
        "job_type": "Full-time",
        "url": "https://example.test/jobs/cobalt-devops",
        "description": "Maintain Docker and Kubernetes infrastructure and CI/CD pipelines.",
    },
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_default(value):
    raise TypeError(f"Cannot serialize {type(value).__name__}")


class DemoRequestHandler(BaseHTTPRequestHandler):
    server_version = "JobNexDemo/1.0"

    def log_message(self, format_string, *args):
        print("%s - %s" % (self.address_string(), format_string % args))

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                return None, "Request body is too large"
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return None, "Request body must be valid JSON"
        if not isinstance(payload, dict):
            return None, "Request body must be a JSON object"
        return payload, None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self._send_json(
                200,
                {"status": "ok", "mode": "demo", "database": "in-memory SQLite"},
            )
        if parsed.path == "/api/jobs/search":
            return self._search_jobs(parse_qs(parsed.query))
        if parsed.path == "/api/applications":
            return self._list_applications()
        if parsed.path == "/api/analyses":
            return self._list_analyses()

        if parsed.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/login.html")
            self.end_headers()
            return
        return self._serve_frontend_file(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in ("/api/analyze", "/api/analyse", "/api/applications"):
            return self._send_json(404, {"detail": "Demo API route not found"})

        payload, error = self._read_json()
        if error:
            return self._send_json(400, {"detail": error})
        if parsed.path in ("/api/analyze", "/api/analyse"):
            return self._analyze(payload)
        return self._queue_application(payload)

    def _analyze(self, payload):
        resume_text = payload.get("resume_text")
        jd_text = payload.get("jd_text")
        if not isinstance(resume_text, str) or not resume_text.strip():
            return self._send_json(422, {"detail": "resume_text must not be blank"})
        if not isinstance(jd_text, str) or not jd_text.strip():
            return self._send_json(422, {"detail": "jd_text must not be blank"})

        result = analyze_resume(resume_text, jd_text)
        created_at = _timestamp()
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
                created_at,
            ),
        )
        DATABASE.commit()
        return self._send_json(
            200,
            {"Analysis_Id": cursor.lastrowid, **result},
        )

    def _list_analyses(self):
        rows = DATABASE.execute(
            """
            SELECT analysis_id, matched_score, matched_skills, missing_skills, created_at
            FROM analyses ORDER BY analysis_id DESC LIMIT 20
            """
        ).fetchall()
        return self._send_json(
            200,
            {
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
            },
        )

    def _search_jobs(self, query):
        keyword = query.get("keyword", [""])[0].strip()
        if len(keyword) < 2:
            return self._send_json(422, {"detail": "keyword must contain at least 2 characters"})
        try:
            limit = max(1, min(int(query.get("limit", ["10"])[0]), 25))
        except ValueError:
            return self._send_json(422, {"detail": "limit must be an integer"})

        words = keyword.casefold().split()
        jobs = [
            job for job in SAMPLE_JOBS
            if all(
                word in " ".join(
                    str(job.get(key, ""))
                    for key in ("title", "company", "location", "skills", "description")
                ).casefold()
                for word in words
            )
        ]
        return self._send_json(200, {"jobs": jobs[:limit], "mode": "sample"})

    def _queue_application(self, payload):
        required = ("resume_text", "job_title", "company", "job_description")
        if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in required):
            return self._send_json(
                422,
                {"detail": "resume_text, job_title, company, and job_description are required"},
            )

        result = analyze_resume(payload["resume_text"], payload["job_description"])
        created_at = _timestamp()
        try:
            cursor = DATABASE.execute(
                """
                INSERT INTO applications
                    (job_title, company, job_url, match_score, status, created_at)
                VALUES (?, ?, ?, ?, 'queued_demo', ?)
                """,
                (
                    payload["job_title"].strip(),
                    payload["company"].strip(),
                    payload.get("job_url"),
                    result["matched_score"],
                    created_at,
                ),
            )
        except sqlite3.IntegrityError:
            return self._send_json(
                409,
                {"detail": "A demo application already exists for this role and company"},
            )
        DATABASE.commit()
        return self._send_json(
            201,
            {
                "application_id": cursor.lastrowid,
                "job_title": payload["job_title"].strip(),
                "company": payload["company"].strip(),
                "job_url": payload.get("job_url"),
                "match_score": result["matched_score"],
                "status": "queued_demo",
                "status_message": "Stored in the local demo database; no email was sent.",
                "created_at": created_at,
            },
        )

    def _list_applications(self):
        rows = DATABASE.execute(
            """
            SELECT application_id, job_title, company, job_url, match_score, status, created_at
            FROM applications ORDER BY application_id DESC LIMIT 50
            """
        ).fetchall()
        return self._send_json(
            200,
            {
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
            },
        )

    def _serve_frontend_file(self, request_path):
        relative_path = unquote(request_path).lstrip("/")
        target = (FRONTEND_ROOT / relative_path).resolve()
        try:
            target.relative_to(FRONTEND_ROOT.resolve())
        except ValueError:
            return self._send_json(404, {"detail": "File not found"})
        if not target.is_file():
            return self._send_json(404, {"detail": "File not found"})

        content_type = {
            ".css": "text/css; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), DemoRequestHandler)
    print("JOBNEX demo is running at http://127.0.0.1:8000/")
    print("API health: http://127.0.0.1:8000/api/health")
    print("Stop with Ctrl+C. Demo records reset when the process stops.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping JOBNEX demo.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
