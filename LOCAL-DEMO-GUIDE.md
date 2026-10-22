# JOBNEX local integration demo

This demo proves a full browser → FastAPI → response cycle without MySQL, external job services, credentials, or email. It uses the real `backend\Astra\analyzer.py` function, fixed sample job data, and an in-memory SQLite database. The production FastAPI app and its routes are unchanged.

## Start

Install the backend requirements if they are not already installed, then from the project root run:

```powershell
python -m pip install -r backend\Astra\requirements.txt
python -m uvicorn demo_fastapi:app --app-dir backend\Astra --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000/>. The root redirects to `login.html`; enter any valid email and a password of at least eight characters to enter the frontend demo. This is only the existing client-side demo session, not backend authentication.

The FastAPI demo uses the backend's declared FastAPI/Uvicorn dependencies and the project-owned `analyzer.py`. It uses SQLite in-memory storage; no MySQL server, API keys, or email account are needed. Keep the server terminal open while testing; press Ctrl+C to stop it. Demo records are in memory and reset when the process stops. The optional `demo_server.py` is a standard-library HTTP fallback, but it is not the FastAPI integration verified here.

## Request → response walkthrough

### 1. Analyze a resume

Open **Resume Analyzer**, submit the following sample values, and observe the JSON response rendered on the page:

```text
Resume: Python developer with SQL, React, FastAPI, and Docker.
Job description: Looking for Python, SQL, React, FastAPI, and Docker skills.
```

Browser request:

```http
POST /api/analyze
Content-Type: application/json

{"resume_text":"Python developer with SQL, React, FastAPI, and Docker.","jd_text":"Looking for Python, SQL, React, FastAPI, and Docker skills."}
```

The page adapter in `frontend\index.html\api.js` maps the form's camelCase values to the backend's snake_case request fields. The demo server calls `analyzer.analyze_resume`, stores the score and skill arrays in SQLite, and responds with:

```json
{
  "Analysis_Id": 1,
  "matched_skills": ["python", "sql", "react", "fastapi", "docker"],
  "missing_skills": [],
  "suggestions": [],
  "matched_score": 100.0
}
```

`GET /api/analyses` returns the recent demo analysis records. The demo database deliberately does not retain the submitted resume or job-description text.

### 2. Search jobs and queue a demo application

Open **Find Jobs**, search for `Python Developer`, and click **Queue application** on the Python role. The page starts with a clearly labelled sample resume that you can edit. Search sends:

```http
GET /api/jobs/search?keyword=Python+Developer&limit=10
```

Queue sends:

```http
POST /api/applications
Content-Type: application/json

{
  "resume_text": "Python developer with experience in SQL, React, FastAPI, and Docker.",
  "job_title": "Python Developer",
  "company": "Brightpath Systems",
  "job_description": "Develop Python APIs with FastAPI, SQL, Docker, and automated tests.",
  "job_url": "https://example.test/jobs/brightpath-python"
}
```

The response includes an `application_id`, a match score, `status: "queued_demo"`, and a message that no email was sent. Open **Applications** to read the same record through `GET /api/applications`.

The sample jobs, URLs, and companies are fictitious. Queueing never sends an email or contacts an employer. Duplicate role/company submissions return HTTP 409; invalid form data returns HTTP 422 with a visible error message.

### 3. Verify the API from PowerShell

With the server running in one terminal, use another:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health

$body = @{
  resume_text = "Python, SQL, React, FastAPI, Docker"
  jd_text = "Python, SQL, React, FastAPI, Docker"
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/analyze -Method Post -ContentType "application/json" -Body $body

Invoke-RestMethod "http://127.0.0.1:8000/api/jobs/search?keyword=Python%20Developer"
Invoke-RestMethod http://127.0.0.1:8000/api/applications
```

## Validate

From the project root:

```powershell
python -m unittest discover -s backend\Astra -p test_demo_server.py -v
```

The tests cover the FastAPI analysis/history and job-search/application queue/list endpoints, validation errors, and serving HTML/CSS/JS files. Run the tests in the same environment where backend requirements are installed.

## Demo boundaries and remaining integration work

- The local FastAPI demo app is separate from the production FastAPI app and serves the frontend plus demo `/api` routes on one origin.
- The production `/api/analyze` and application routes use MySQL and the production job-search path uses an external jobs provider. Those are not exercised by this offline demo.
- The existing analyzer uses a small fixed skill list and is deterministic; it is not an AI resume evaluator.
- The demo has no auth endpoint, dashboard summary API, chat adapter, interview-resource UI, learning-resource API integration, privacy controls backed by API, daily-match interface, recruiter-screening interface, or referral-mailer UI.
- The application tracker displays queued demo records, while status changes and removal are not connected to backend routes. The production dashboard API also has a separate contract and requires an `X-User-Id` header.
- Use `GET /api/health` to confirm the local demo server is available. Do not use this in-memory server as a production backend.
