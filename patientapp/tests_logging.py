from django.test import SimpleTestCase
import logging
from chaviprom.logging_filters import PHIMaskingFilter


class PHIMaskingFilterTests(SimpleTestCase):
    def _run(self, msg, *args):
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=args, exc_info=None,
        )
        PHIMaskingFilter().filter(record)
        return record.getMessage()

    def test_uuid_is_masked(self):
        out = self._run("Found patient UUID: 80722ef0-ebf1-4e65-a2e8-e73aadff050d")
        self.assertNotIn("80722ef0-ebf1-4e65-a2e8-e73aadff050d", out)
        self.assertIn("80722ef0", out)  # keeps prefix for correlation

    def test_patient_name_after_from_patient_masked(self):
        out = self._run("New questionnaire submission registered: abc from patient Test Patient 0")
        self.assertNotIn("Test Patient 0", out)
        self.assertIn("patient [REDACTED]", out)

    def test_patient_name_after_patient_colon_masked(self):
        out = self._run("Patient: PAT5")
        self.assertNotIn("PAT5", out)
        self.assertIn("Patient: [REDACTED]", out)

    def test_patient_id_label_masked(self):
        out = self._run("PRO Review view called for patient ID: 80722ef0-ebf1-4e65-a2e8-e73aadff050d, print_mode=False")
        self.assertNotIn("80722ef0-ebf1-4e65-a2e8-e73aadff050d", out)

    def test_patient_name_and_id_in_parens_masked(self):
        out = self._run("Patient portal accessed by: John Doe (ID: 80722ef0-ebf1-4e65-a2e8-e73aadff050d)")
        self.assertNotIn("John Doe", out)
        self.assertNotIn("80722ef0-ebf1-4e65-a2e8-e73aadff050d", out)

    def test_clean_message_passes_through(self):
        out = self._run("Completed parallel aggregation for construct Test Construct 6")
        self.assertEqual(out, "Completed parallel aggregation for construct Test Construct 6")

    def test_dict_arg_patient_name_masked(self):
        out = self._run("metadata: %s", {"patient_name": "PAT6", "patient_id": "PAT6"})
        self.assertNotIn("PAT6", out)
