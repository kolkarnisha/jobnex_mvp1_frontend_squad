# JOBNEX backend–frontend map

## Scope and current-state summary

The initial Python AST inventory covered the 37 project-owned backend files then present in `backend\Astra` (including tests), while excluding the `backend\algonex` virtual environment and installed packages. The local demos subsequently added `demo_server.py`, `demo_fastapi.py`, and their test modules; these are documented separately. Production route discovery includes decorators inside router factories. Tests and setup/data scripts are not treated as runtime API routes.

The main API entry point is `backend\Astra\main.py`. It mounts the privacy and filter routers directly, and mounts interview, chatbot, resources, and dashboard routers when their imports/configuration succeed. `backend\Astra\Automatic Job Referral Emails.py` creates a separate FastAPI app; it is not mounted by `main.py`.

The pages under `frontend\index.html` load `common.css` and `common.js`; `analyzer.html`, `jobs.html`, and `applications.html` also load `api.js`. That adapter connects those pages to `demo_fastapi.py`'s analyzer, job-search, queue, and application-list routes. These are deliberately isolated from the production FastAPI app and MySQL dependencies. Other mappings below remain recommendations, not active connections. In particular, the backend has no login/authentication endpoint.

The root-level `frontend\index1.html` is a separate combined prototype using `frontend\style.css` and `frontend\script.js`; it is not the same page set as `frontend\index.html\*.html`.

## Connection diagram

Open [backend-frontend-linkage.svg](./backend-frontend-linkage.svg) in Figma (File → Place image, or drag the SVG onto the canvas). The SVG is vector-based and labels shared CSS/JS assets, endpoint groups, unmatched routes, and demo-only status.

## Frontend pages → backend routes

Every page listed in the “Shared assets” column links to `frontend\index.html\common.css` and `frontend\index.html\common.js`. A frontend API adapter should translate the page-facing camelCase values into the backend’s snake_case JSON fields and normalize response names where needed.

| Frontend page | Best backend mapping | Inputs → outputs | Current status |
|---|---|---|---|
| `login.html` | No corresponding auth route exists in the main API. | UI collects `email`, `password`; no backend request/response contract is available. | Demo session flag only. Do not point this at an unrelated route. |
| `analyzer.html` | Demo FastAPI: `POST /api/analyze`, `GET /api/analyses`; production: `POST /api/analyze` (alias `/api/analyse`), `GET /api/analyses`; optionally `/api/resources`. | Analyze JSON: `resume_text`, `jd_text` → `Analysis_Id`, skill lists, suggestions, score. | Connected through `api.js` to local FastAPI demo with SQLite history. Production routes still require MySQL. |
| `jobs.html` | Demo FastAPI: `GET /api/jobs/search?keyword=...`, `POST /api/applications`; production additionally has `/api/applications/{application_id}/approve`. | Search query → `{jobs: [...]}`. Queue JSON: `resume_text`, `job_title`, `company`, `job_description`, optional `job_url` → queued demo record and match score. | Connected to deterministic sample jobs and in-memory SQLite. No email is sent; the page's filters operate on demo metadata. |
| `applications.html` | Demo FastAPI: `GET /api/applications`. Production: main API list (queued/sent) or `/dashboard/applications` CRUD/status/history. | Demo list → `{applications: [...]}`. Dashboard list uses a distinct paginated contract; writes accept `ApplicationCreate` or `StatusUpdate`. | Connected to demo queue records; status changes/removal remain local-only in fallback mode. Dashboard API requires `X-User-Id`. |
| `dashboard.html` | `GET /dashboard/summary`; `GET /dashboard/applications?page=1&page_size=5`. | Both require `X-User-Id`. Summary is a status-count object; list response is paginated `{items,total,page,page_size}`. | Page computes counts from local-storage sample records; no request is sent. |
| `chatbot.html` | `POST /api/chat`; `DELETE /api/chat/{session_id}`. | Request model: `message`, optional `session_id`, optional `analysis`, optional `use_ai` (default `true`) → `session_id`, `reply`, `intent`, `topic`, `source`, `resources`, `quick_replies`. Delete → `{status:"cleared"}`. | Optional hook sends `{message, history}` and expects a string or `{text}`. The backend expects `session_id`/`analysis`, returns `reply`, and does not accept `history`; an adapter is needed. Otherwise it uses scripted demo replies. |
| `courses.html` | `POST /api/resources` or `GET /api/resources/{analysis_id}`. | Skill list and options → learning-resource response (`suggestions` with per-skill resources, summary/overview, and AI/source metadata). | Courses are sample data. No API method is called. |
| `interveiw.html` | `POST /api/interview/resources`. | Optional JSON `resume_text`, `jd_text`, `role` (at least one required) → detected role and interview/coding resource links (site, URL, difficulty). | Built-in question set only; no API call. The shared navigation now points to the existing misspelled filename. |
| `privacy.html` | `POST /api/privacy/redact`; `DELETE /api/privacy/analysis/{analysis_id}`. | Redaction JSON `{resume_text}` → `{redacted_text}`. Delete ID → `{deleted: analysis_id}`. | Privacy preferences are local-storage only; page does not expose redaction or saved-analysis deletion controls. |

### Additional backend routes without a matching page

| Backend route group | Functionality and contract | Suggested future frontend |
|---|---|---|
| `/api/daily/settings` GET/PUT, `/api/daily/run` POST, `/api/daily/jobs` GET | Settings GET/PUT exchanges resume text, keywords, match threshold, schedule hour/minute, enabled flag, and last/next run values. Run returns the daily job result. Jobs query accepts optional `min_score` and `day`; response is `{date,min_score,count,hidden_below_min,jobs}`. | Add a dedicated daily-matches/settings page; current pages do not provide these controls. |
| `/api/filters/check` POST | `CheckRequest(resume_text,jd_text)` (both at least 50 chars) → `Check_Id`, experience requirement result, certification result, and `overall_match`; stores a redacted resume. | `jobs.html` only if it is explicitly expanded to support recruiter screening; otherwise add a dedicated screening page. |
| `/api/filters/filter` POST | `FilterRequest(resumes:[{id,resume_text}], min_experience_years?, required_certifications[])` → filtered match details/counts/IDs; resume text is not persisted by this endpoint. | Dedicated recruiter screening page; not an exact match for the current personal job-search filters. |
| Separate referral app: `/candidates`, `/jobs`, `/referrals`, `/run-matching`, `/email-logs`, `/email-templates`, plus unsubscribe/close/matches routes | Pydantic request/response models include `CandidateIn/Out`, `JobIn/Out`, `ReferralIn`, `EmailLogOut`, `EmailTemplateOut`. Creates return one model; list endpoints return arrays; matching/log endpoints return match/log data. | No matching page found. These paths belong to the separate app in `Automatic Job Referral Emails.py`; they are not served by the main app unless deployed separately. |
| `/`, `/favicon.ico`, `/favicon.png` | Main API health message or empty 204 favicon responses. | Infrastructure/browser metadata, not product pages. |

## Backend request/response models

Models found by AST and source inspection:

| Model | Fields |
|---|---|
| `AnalyzeRequest` | `resume_text: str`, `jd_text: str` (non-empty and non-blank) |
| `queueApplicationRequest` | `resume_text`, `job_title`, `company`, `job_description`; optional `job_url`, `apply_email` |
| `DailySettingsRequest` | `resume_text` (min 20), `keywords` (min 2), `min_score` (0–100, default 60), `run_hour` (0–23, default 9), `run_minute` (0–59, default 0), `enabled` (default true) |
| `RedactRequest` | `resume_text` |
| `CheckRequest` | `resume_text`, `jd_text` (each min 50) |
| `ResumeItem` / `FilterRequest` | Resume `{id,resume_text}`; request has 1–100 resumes, optional minimum years, required-certification list |
| `InterviewRequest` | Optional `resume_text`, `jd_text`, `role`; at least one is required |
| `ChatRequest` (declared in router factory) | `message` (1–max length), optional `session_id`, optional `analysis`, `use_ai` (default true) |
| `ResourceRequest` (declared in router factory) | `missing_skills[]`, `max_per_skill`, `use_ai` |
| `ApplicationCreate` / `StatusUpdate` | Application title/company/URL/source/status/notes; status update plus optional note |
| Referral app models | `CandidateIn/Out`, `JobIn/Out`, `ReferralIn`, `EmailLogOut`, `EmailTemplateOut`; see the standalone route group above. |

## AST definition inventory

The following production modules contain top-level functions/classes and were parsed; route factories also contain nested route handlers. This inventory separates feature logic from persistence and scheduling helpers.

- `main.py`: lifespan, health/favicon, analyze/history, search/queue/list/approve applications, daily settings/run/jobs; request models `AnalyzeRequest`, `queueApplicationRequest`, `DailySettingsRequest`.
- `analyzer.py`, `ai_analyzer.py`: `analyze_resume`, AI client and resume analysis helpers.
- `database.py`, `dashboard_db.py`, `apply_db.py`, `daily_db.py`, `resource_db.py`: connection/configuration, schema, CRUD and persistence functions.
- `auto_apply.py`, `job_fetcher.py`, `daily_jobs.py`, `daily_scheduler.py`: matching/scoring, queue/send, job collection, scheduled daily execution.
- `application_dashboard.py`: SQL/schema helpers, `ApplicationRepository`, summary builder, dashboard router factory and request models.
- `filter_logic.py`: experience/certification parsing, resume filtering, `/check` and `/filter` routes, request models.
- `resume_privacy.py`: redaction helper and privacy routes.
- `interview_prep.py`: role detection, resource link generation, interview request model/route.
- `chatbot_assistant.py`: conversation store, chatbot rules/resource helpers and chat router factory.
- `suggestions_resources.py`: skill normalization, course/resource generation and resource router factory.
- `Automatic Job Referral Emails.py`: matching/email helpers, SQLAlchemy entities/models and separate app routes.
- `setup_mysql.py`, `insert_db.py`, `text_analyzer.py`, `update_schema.py`: setup, sample/test scripts, and schema/update helpers; not frontend API entry points.

## Step-by-step wiring notes

1. Keep page URLs and files explicit: `frontend\index.html\*.html` all use `common.css` and `common.js`. The root prototype `frontend\index1.html` uses root-level `style.css` and `script.js`; do not mix the asset sets.
2. Add a single `window.JOBNEX_API` adapter loaded before `common.js`. It should call the base URL for the FastAPI service, set JSON content type, surface non-2xx errors, and normalize endpoint response names.
3. Implement `analyzeResume({resumeText,jdText})` as `POST /api/analyze` with `{resume_text,jd_text}`. Return the backend object unchanged or adapt it consistently; `common.js` renders either a string or JSON.
4. Implement `chat({message,...})` against `POST /api/chat` using a `session_id` and optional `analysis`; display `reply` and preserve `session_id`. Do not send the page’s current `history` field directly as the backend does not define it.
5. Bind jobs search, queue, approve, dashboard, and application-list/status flows to their separate routes. Confirm which application store is authoritative: `/api/applications` (auto-apply queue) and `/dashboard/applications` (user application tracker) have different request/response contracts.
6. Add matching request forms and result states for interview resources, courses, and privacy redaction/deletion. Add a separate page before exposing daily matching, recruiter filters, or the referral-email app.
7. Fix the `interveiw.html` filename/nav mismatch before relying on the interview link. Keep login marked demo-only until a real auth endpoint and session contract are designed.
8. In Figma, import `backend-frontend-linkage.svg` as a vector reference. Solid route names describe backend definitions; amber dashed links are suggested page mappings, not active HTTP calls.
