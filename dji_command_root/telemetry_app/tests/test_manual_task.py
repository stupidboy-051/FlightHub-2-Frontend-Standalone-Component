import json

from django.test import TestCase
from django.urls import reverse


class StartManualTaskTests(TestCase):
    def test_start_manual_task_method_not_allowed(self):
        resp = self.client.get("/api/v1/start_manual_task")
        self.assertEqual(resp.status_code, 405)

    def test_start_manual_task_invalid_json(self):
        resp = self.client.post(
            "/api/v1/start_manual_task",
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data.get("code"), 400)

    def test_start_manual_task_missing_folder_path(self):
        resp = self.client.post(
            "/api/v1/start_manual_task",
            data=json.dumps({"source": "web_manual"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data.get("code"), 400)

    def test_start_manual_task_success_returns_task_id(self):
        resp = self.client.post(
            "/api/v1/start_manual_task",
            data=json.dumps(
                {
                    "source": "web_manual",
                    "folder_path": "fh_sync/20250101_demo/media/fake_uuid/",
                    "detect_type": "unknown",
                    "task_name": "demo",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("code"), 0)
        self.assertIsNotNone(data.get("task_id"))
        self.assertIn("new_images_count", data)
