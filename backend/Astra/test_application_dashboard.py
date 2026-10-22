"""
Tests for application_dashboard.py (MySQL version)

Files needed in the same folder:
    application_dashboard.py, schema.sql, queries.sql, test_application_dashboard.py

Install : uv add fastapi httpx pytest mysql-connector-python
Run     : uv run pytest -v   (run inside the same folder as the files)

IMPORTANT: tests use a SEPARATE database called  jobnext_test  (created automatically)
so your real JobNext data is never touched. The test DB name must end with "_test".
If MySQL is not running / wrong password, the DB tests are SKIPPED (not failed).
Set MYSQL_USER / MYSQL_PASSWORD (env or .env) the same way as for the app.
"""
import os

import mysql.connector
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application_dashboard import (
    ALLOWED_TRANSITIONS,
    Q,  # queries loaded from queries.sql
    ApplicationStatus,
    build_summary,
    create_router,
    get_db_config,
)

TEST_DB = os.getenv("MYSQL_TEST_DATABASE", "jobnext_test")
USER = {"X-User-Id": "user-1"}
OTHER_USER = {"X-User-Id": "user-2"}


@pytest.fixture
def client():
    assert TEST_DB.endswith("_test"), "Safety: test database name must end with '_test'"
    config = get_db_config(database=TEST_DB)
    try:
        router = create_router(config)  # creates test DB + tables (schema.sql) if missing
    except mysql.connector.Error as e:
        pytest.skip(f"MySQL not available for tests: {e}")

    # start every test with empty tables (queries come from queries.sql)
    conn = mysql.connector.connect(**config)
    try:
        cur = conn.cursor()
        cur.execute(Q["clear_history"])
        cur.execute(Q["clear_applications"])
        conn.commit()
    finally:
        conn.close()

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def make_job(n=1, **overrides):
    data = {
        "job_title": f"Python Developer {n}",
        "company": f"Company {n}",
        "job_url": f"https://jobs.example.com/{n}",
    }
    data.update(overrides)
    return data


def add(client, n=1, headers=USER, **overrides):
    return client.post("/dashboard/applications", json=make_job(n, **overrides), headers=headers)


# ---------------- create ----------------
def test_create_application_success(client):
    r = add(client)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "APPLIED"
    assert body["company"] == "Company 1"
    assert body["id"] > 0


def test_create_writes_first_history_entry(client):
    app_id = add(client).json()["id"]
    hist = client.get(f"/dashboard/applications/{app_id}/history", headers=USER).json()["history"]
    assert len(hist) == 1
    assert hist[0]["from_status"] is None
    assert hist[0]["to_status"] == "APPLIED"


def test_data_is_really_stored_in_mysql(client):
    add(client)
    conn = mysql.connector.connect(**get_db_config(database=TEST_DB))
    try:
        cur = conn.cursor(dictionary=True)
        # same query the app uses: user, status, status, company, company (None = no filter)
        cur.execute(Q["count_applications"], ("user-1", None, None, None, None))
        assert cur.fetchone()["n"] == 1
    finally:
        conn.close()


def test_duplicate_job_url_rejected(client):
    assert add(client).status_code == 201
    assert add(client).status_code == 409


def test_same_url_allowed_for_different_users(client):
    assert add(client, headers=USER).status_code == 201
    assert add(client, headers=OTHER_USER).status_code == 201


def test_create_validation_error(client):
    r = client.post("/dashboard/applications", json={"job_title": "", "company": "X", "job_url": "u"}, headers=USER)
    assert r.status_code == 422


def test_missing_user_header_returns_401(client):
    assert client.get("/dashboard/applications").status_code == 401
    assert client.get("/dashboard/summary").status_code == 401


# ---------------- read / list ----------------
def test_get_single_application(client):
    app_id = add(client).json()["id"]
    r = client.get(f"/dashboard/applications/{app_id}", headers=USER)
    assert r.status_code == 200
    assert r.json()["id"] == app_id


def test_get_unknown_application_404(client):
    assert client.get("/dashboard/applications/999999", headers=USER).status_code == 404


def test_user_cannot_see_other_users_application(client):
    app_id = add(client, headers=USER).json()["id"]
    assert client.get(f"/dashboard/applications/{app_id}", headers=OTHER_USER).status_code == 404
    listing = client.get("/dashboard/applications", headers=OTHER_USER).json()
    assert listing["total"] == 0


def test_list_filter_by_status_and_company(client):
    a = add(client, 1).json()["id"]
    add(client, 2)
    client.patch(f"/dashboard/applications/{a}/status", json={"status": "UNDER_REVIEW"}, headers=USER)

    by_status = client.get("/dashboard/applications?status=UNDER_REVIEW", headers=USER).json()
    assert by_status["total"] == 1

    by_company = client.get("/dashboard/applications?company=company 2", headers=USER).json()
    assert by_company["total"] == 1
    assert by_company["items"][0]["company"] == "Company 2"


def test_list_pagination(client):
    for i in range(5):
        add(client, i + 1)
    page1 = client.get("/dashboard/applications?page=1&page_size=2", headers=USER).json()
    page3 = client.get("/dashboard/applications?page=3&page_size=2", headers=USER).json()
    assert page1["total"] == 5
    assert len(page1["items"]) == 2
    assert len(page3["items"]) == 1


def test_invalid_page_size_rejected(client):
    assert client.get("/dashboard/applications?page_size=500", headers=USER).status_code == 422


# ---------------- status updates ----------------
def test_valid_status_update_adds_history(client):
    app_id = add(client).json()["id"]
    r = client.patch(
        f"/dashboard/applications/{app_id}/status",
        json={"status": "SHORTLISTED", "note": "HR called"},
        headers=USER,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SHORTLISTED"

    hist = client.get(f"/dashboard/applications/{app_id}/history", headers=USER).json()["history"]
    assert [h["to_status"] for h in hist] == ["APPLIED", "SHORTLISTED"]
    assert hist[-1]["from_status"] == "APPLIED"
    assert hist[-1]["note"] == "HR called"


def test_invalid_transition_returns_409(client):
    app_id = add(client).json()["id"]
    r = client.patch(f"/dashboard/applications/{app_id}/status", json={"status": "OFFER"}, headers=USER)
    assert r.status_code == 409
    # status must stay unchanged
    assert client.get(f"/dashboard/applications/{app_id}", headers=USER).json()["status"] == "APPLIED"


def test_final_status_cannot_change(client):
    app_id = add(client).json()["id"]
    client.patch(f"/dashboard/applications/{app_id}/status", json={"status": "REJECTED"}, headers=USER)
    r = client.patch(f"/dashboard/applications/{app_id}/status", json={"status": "APPLIED"}, headers=USER)
    assert r.status_code == 409


def test_failed_application_can_be_retried(client):
    app_id = add(client, status="FAILED").json()["id"]
    r = client.patch(f"/dashboard/applications/{app_id}/status", json={"status": "APPLIED"}, headers=USER)
    assert r.status_code == 200


def test_update_unknown_application_404(client):
    r = client.patch("/dashboard/applications/999999/status", json={"status": "REJECTED"}, headers=USER)
    assert r.status_code == 404


def test_other_user_cannot_update_status(client):
    app_id = add(client, headers=USER).json()["id"]
    r = client.patch(f"/dashboard/applications/{app_id}/status", json={"status": "REJECTED"}, headers=OTHER_USER)
    assert r.status_code == 404


def test_invalid_status_value_422(client):
    app_id = add(client).json()["id"]
    r = client.patch(f"/dashboard/applications/{app_id}/status", json={"status": "HIRED_LOL"}, headers=USER)
    assert r.status_code == 422


def test_full_happy_path_to_offer(client):
    app_id = add(client).json()["id"]
    for st in ["UNDER_REVIEW", "SHORTLISTED", "INTERVIEW_SCHEDULED", "OFFER"]:
        r = client.patch(f"/dashboard/applications/{app_id}/status", json={"status": st}, headers=USER)
        assert r.status_code == 200, st


# ---------------- summary ----------------
def test_summary_empty(client):
    s = client.get("/dashboard/summary", headers=USER).json()
    assert s["total"] == 0
    assert s["response_rate_percent"] == 0.0
    assert s["by_status"]["APPLIED"] == 0


def test_summary_counts_and_response_rate(client):
    ids = [add(client, i + 1).json()["id"] for i in range(4)]
    client.patch(f"/dashboard/applications/{ids[0]}/status", json={"status": "SHORTLISTED"}, headers=USER)
    client.patch(f"/dashboard/applications/{ids[1]}/status", json={"status": "REJECTED"}, headers=USER)
    s = client.get("/dashboard/summary", headers=USER).json()
    assert s["total"] == 4
    assert s["by_status"]["APPLIED"] == 2
    assert s["by_status"]["SHORTLISTED"] == 1
    assert s["by_status"]["REJECTED"] == 1
    assert s["response_rate_percent"] == 50.0
    assert s["active"] == 3  # 2 applied + 1 shortlisted


# ---------------- pure unit tests (no DB needed) ----------------
def test_build_summary_unit():
    s = build_summary({"APPLIED": 1, "OFFER": 1})
    assert s["total"] == 2
    assert s["response_rate_percent"] == 50.0


def test_every_status_has_transition_rule():
    assert set(ALLOWED_TRANSITIONS) == set(ApplicationStatus)


def test_all_queries_loaded_from_sql_file():
    expected = {
        "create_database", "insert_application", "insert_history",
        "lock_application_status", "update_status", "get_application",
        "count_applications", "list_applications", "get_history",
        "counts_by_status", "clear_history", "clear_applications",
    }
    assert expected <= set(Q)
