from django.test import TestCase

from telemetry_app.models import Wayline


class WaylineSelectAllTests(TestCase):
    def test_select_all_returns_full_list_without_pagination_envelope(self):
        for i in range(120):
            Wayline.objects.create(
                wayline_id=f"wl_{i}",
                name=f"Wayline {i:03d}",
                status="ARCHIVED" if i % 2 == 0 else "ACTIVE",
                detect_type="rail",
            )

        resp = self.client.get("/api/v1/waylines/select-all/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 120)
        self.assertIn("id", data[0])
        self.assertIn("wayline_id", data[0])
        self.assertIn("name", data[0])
        self.assertIn("status", data[0])
        self.assertIn("detect_type", data[0])
        self.assertIn("updated_at", data[0])

