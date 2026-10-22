import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from demo_fastapi import app


class DemoFastAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_and_frontend_assets(self):
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["mode"], "demo")

        page = self.client.get("/analyzer.html")
        self.assertEqual(page.status_code, 200)
        self.assertIn('src="api.js"', page.text)

        stylesheet = self.client.get("/common.css")
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("text/css", stylesheet.headers["content-type"])

        adapter = self.client.get("/api.js")
        self.assertEqual(adapter.status_code, 200)
        self.assertIn("fetch(path", adapter.text)

    def test_analyze_and_history_endpoints(self):
        response = self.client.post(
            "/api/analyze",
            json={
                "resume_text": "Python developer with SQL, React, FastAPI, and Docker.",
                "jd_text": "Looking for Python, SQL, React, FastAPI, and Docker skills.",
            },
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["matched_score"], 100.0)
        self.assertEqual(
            set(result),
            {"Analysis_Id", "matched_skills", "missing_skills", "suggestions", "matched_score"},
        )

        history = self.client.get("/api/analyses")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(
            history.json()["analyses"][0]["Analysis_id"],
            result["Analysis_Id"],
        )

    def test_validation_and_job_queue_flow(self):
        invalid = self.client.post(
            "/api/analyze",
            json={"resume_text": " ", "jd_text": "Python developer"},
        )
        self.assertEqual(invalid.status_code, 422)

        search = self.client.get(
            "/api/jobs/search",
            params={"keyword": "Python Developer"},
        )
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.json()["jobs"][0]["title"], "Python Developer")

        role = f"Demo Test Engineer {uuid4()}"
        payload = {
            "resume_text": "Python developer with SQL, React, FastAPI, and Docker.",
            "job_title": role,
            "company": "FastAPI Demo",
            "job_description": "Python SQL React FastAPI Docker",
        }
        queued = self.client.post("/api/applications", json=payload)
        self.assertEqual(queued.status_code, 201)
        self.assertEqual(queued.json()["status"], "queued_demo")
        self.assertIn("no email was sent", queued.json()["status_message"])

        applications = self.client.get("/api/applications")
        self.assertEqual(applications.status_code, 200)
        self.assertEqual(
            applications.json()["applications"][0]["job_title"],
            role,
        )


if __name__ == "__main__":
    unittest.main()
