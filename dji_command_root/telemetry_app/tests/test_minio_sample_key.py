from django.test import SimpleTestCase

from telemetry_app.views import is_algorithm_output_image_key


class MinioSampleKeyTests(SimpleTestCase):
    def test_is_algorithm_output_image_key_detected_prefix(self):
        self.assertTrue(
            is_algorithm_output_image_key(
                "fh_sync/x/media/f4dd2ace/detected_DJI_20260227133621_0014_V.jpeg"
            )
        )

    def test_is_algorithm_output_image_key_result_substring(self):
        self.assertTrue(
            is_algorithm_output_image_key(
                "fh_sync/x/media/f4dd2ace/foo_result_001.jpeg"
            )
        )

    def test_is_algorithm_output_image_key_source_image(self):
        self.assertFalse(
            is_algorithm_output_image_key(
                "fh_sync/x/media/f4dd2ace/DJI_20260227133621_0014.jpeg"
            )
        )
