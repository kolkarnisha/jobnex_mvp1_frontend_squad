import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import demo_server


class DemoServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), demo_server.DemoRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_analyze_persists_only_result_fields(self):
        status, result = self.request(
            "/api/analyze",
            {
                "resume_text": "Python developer with SQL, React, FastAPI, and Docker.",
                "jd_text": "Looking for Python, SQL, React, FastAPI, and Docker skills.",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("Analysis_Id", result)
        self.assertEqual(result["matched_score"], 100.0)

        history_status, history = self.request("/api/analyses")
        self.assertEqual(history_status, 200)
        self.assertEqual(history["analyses"][0]["Analysis_id"], result["Analysis_Id"])
        self.assertNotIn("resume_text", history["analyses"][0])

    def test_job_search_and_application_queue_cycle(self):
        status, result = self.request("/api/jobs/search?keyword=python%20developer")
        self.assertEqual(status, 200)
        self.assertEqual(result["jobs"][0]["title"], "Python Developer")

        application_status, application = self.request(
            "/api/applications",
            {
                "resume_text": "Python developer with SQL, React, FastAPI, and Docker.",
                "job_title": "Demo Test Engineer",
                "company": "Demo Test Company",
                "job_description": "Python SQL React FastAPI Docker",
                "job_url": "https://example.test/demo-test",
            },
        )
        self.assertEqual(application_status, 201)
        self.assertEqual(application["status"], "queued_demo")
        self.assertEqual(application["match_score"], 100.0)
        self.assertIn("no email was sent", application["status_message"])

        duplicate_status, duplicate = self.request(
            "/api/applications",
            {
                "resume_text": "Python developer with SQL, React, FastAPI, and Docker.",
                "job_title": "Demo Test Engineer",
                "company": "Demo Test Company",
                "job_description": "Python SQL React FastAPI Docker",
            },
        )
        self.assertEqual(duplicate_status, 409)
        self.assertIn("already exists", duplicate["detail"])

        list_status, listed = self.request("/api/applications")
        self.assertEqual(list_status, 200)
        self.assertEqual(listed["applications"][0]["application_id"], application["application_id"])

    def test_blank_analyzer_input_is_rejected(self):
        status, result = self.request(
            "/api/analyze",
            {"resume_text": " ", "jd_text": "Python developer"},
        )
        self.assertEqual(status, 422)
        self.assertIn("resume_text", result["detail"])

    def test_frontend_is_served_by_the_demo_server(self):
        status, page = self.request_text("/analyzer.html")
        self.assertEqual(status, 200)
        self.assertIn('src="api.js"', page)
        self.assertIn('src="common.js"', page)

    def request_text(self, path):
        with urlopen(self.base_url + path, timeout=3) as response:
            return response.status, response.read().decode("utf-8")


if __name__ == "__main__":
    unittest.main()
