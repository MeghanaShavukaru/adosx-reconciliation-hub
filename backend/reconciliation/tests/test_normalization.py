from decimal import Decimal

from django.test import SimpleTestCase

from reconciliation.services.normalization import normalize_reference, parse_numeric_value


class NormalizationTests(SimpleTestCase):
    def test_reference_variants_normalize_to_same_record(self):
        variants = ["REC-001", "rec_001", " REC001 "]
        self.assertTrue(all(normalize_reference(v) == "rec001" for v in variants))

    def test_equivalent_numeric_formats_match(self):
        parsed, status, _ = parse_numeric_value("$1,200.00")
        self.assertEqual(status, "VALID")
        self.assertEqual(parsed, Decimal("1200.00"))

    def test_invalid_numeric_value_preserves_status(self):
        parsed, status, warning = parse_numeric_value("not-a-number")
        self.assertIsNone(parsed)
        self.assertEqual(status, "INVALID")
        self.assertIn("Could not parse", warning)
