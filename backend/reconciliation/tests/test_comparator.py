from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.test import SimpleTestCase

from reconciliation.services.comparator import (
    DUPLICATE_IN_SYSTEM_B,
    MISSING_IN_SYSTEM_B,
    ORPHAN_IN_SYSTEM_B,
    VALUE_MISMATCH,
    compare_systems,
)
from reconciliation.management.commands.import_data import Command
from reconciliation.services.normalization import normalize_reference, parse_numeric_value


class ComparatorTests(SimpleTestCase):
    def setUp(self):
        self.location_map = {
            "LOC-A": {"organization_id": "ORG-A"},
            "LOC-B": {"organization_id": "ORG-B"},
        }

    def test_detects_missing_in_system_b(self):
        system_a = [{
            "record_id_raw": "REC-001",
            "record_id_normalized": "rec001",
            "location_id": "LOC-A",
            "value_raw": "$500.00",
            "value_parsed": Decimal("500.00"),
            "value_parse_status": "VALID",
        }]
        system_b = []

        discrepancies = compare_systems(system_a, system_b, self.location_map)
        self.assertTrue(any(item["reason"] == MISSING_IN_SYSTEM_B for item in discrepancies))

    def test_detects_orphan_in_system_b(self):
        system_a = []
        system_b = [{
            "record_ref_raw": "REC-999",
            "record_ref_normalized": "rec999",
            "location_id": "LOC-A",
            "value_raw": "400",
            "value_parsed": Decimal("400"),
            "value_parse_status": "VALID",
        }]

        discrepancies = compare_systems(system_a, system_b, self.location_map)
        self.assertTrue(any(item["reason"] == ORPHAN_IN_SYSTEM_B for item in discrepancies))

    def test_detects_duplicate_in_system_b(self):
        system_a = [{
            "record_id_raw": "REC-001",
            "record_id_normalized": "rec001",
            "location_id": "LOC-A",
            "value_raw": "$500.00",
            "value_parsed": Decimal("500.00"),
            "value_parse_status": "VALID",
        }]
        system_b = [
            {"record_ref_raw": "REC-001", "record_ref_normalized": "rec001", "location_id": "LOC-A", "value_raw": "500", "value_parsed": Decimal("500"), "value_parse_status": "VALID"},
            {"record_ref_raw": "REC_001", "record_ref_normalized": "rec001", "location_id": "LOC-A", "value_raw": "500", "value_parsed": Decimal("500"), "value_parse_status": "VALID"},
        ]

        discrepancies = compare_systems(system_a, system_b, self.location_map)
        self.assertTrue(any(item["reason"] == DUPLICATE_IN_SYSTEM_B for item in discrepancies))

    def test_detects_duplicate_orphan_reference(self):
        system_b = [
            {"record_ref_raw": "REC021", "record_ref_normalized": "rec021", "location_id": "LOC-A", "value_raw": "555", "value_parsed": Decimal("555"), "value_parse_status": "VALID"},
            {"record_ref_raw": "REC021", "record_ref_normalized": "rec021", "location_id": "LOC-A", "value_raw": "666", "value_parsed": Decimal("666"), "value_parse_status": "VALID"},
        ]

        discrepancies = compare_systems([], system_b, self.location_map)

        self.assertEqual(1, len(discrepancies))
        self.assertEqual(DUPLICATE_IN_SYSTEM_B, discrepancies[0]["reason"])
        self.assertFalse(discrepancies[0]["parent_exists"])
        self.assertEqual(2, len(discrepancies[0]["system_b"]["entries"]))

    def test_duplicate_detection_occurs_after_normalization(self):
        system_a = [{
            "record_id_raw": "REC021",
            "record_id_normalized": "rec021",
            "location_id": "LOC-A",
            "value_raw": "500",
            "value_parsed": Decimal("500"),
            "value_parse_status": "VALID",
        }]
        system_b = [
            {"record_ref_raw": "REC-021", "record_ref_normalized": "rec021", "location_id": "LOC-A", "value_raw": "555", "value_parsed": Decimal("555"), "value_parse_status": "VALID"},
            {"record_ref_raw": "REC_021", "record_ref_normalized": "rec021", "location_id": "LOC-A", "value_raw": "666", "value_parsed": Decimal("666"), "value_parse_status": "VALID"},
        ]

        discrepancies = compare_systems(system_a, system_b, self.location_map)

        self.assertEqual([DUPLICATE_IN_SYSTEM_B], [item["reason"] for item in discrepancies])

    def test_detects_value_mismatch(self):
        system_a = [{
            "record_id_raw": "REC-001",
            "record_id_normalized": "rec001",
            "location_id": "LOC-A",
            "value_raw": "$500.00",
            "value_parsed": Decimal("500.00"),
            "value_parse_status": "VALID",
        }]
        system_b = [{
            "record_ref_raw": "REC001",
            "record_ref_normalized": "rec001",
            "location_id": "LOC-A",
            "value_raw": "550",
            "value_parsed": Decimal("550"),
            "value_parse_status": "VALID",
        }]

        discrepancies = compare_systems(system_a, system_b, self.location_map)
        self.assertTrue(any(item["reason"] == VALUE_MISMATCH for item in discrepancies))

    def test_clean_matching_record_is_not_flagged(self):
        system_a = [{
            "record_id_raw": "REC-002",
            "record_id_normalized": "rec002",
            "location_id": "LOC-A",
            "value_raw": "$1,200.00",
            "value_parsed": Decimal("1200.00"),
            "value_parse_status": "VALID",
        }]
        system_b = [{
            "record_ref_raw": "REC_002",
            "record_ref_normalized": "rec002",
            "location_id": "LOC-A",
            "value_raw": "1200",
            "value_parsed": Decimal("1200"),
            "value_parse_status": "VALID",
        }]

        discrepancies = compare_systems(system_a, system_b, self.location_map)
        self.assertEqual([], discrepancies)

    def test_reference_variants_normalize_to_same_record(self):
        variants = ["REC-001", "rec_001", " REC001 "]
        normalized = {value: normalize_reference(value) for value in variants}
        self.assertTrue(all(normalized[value] == "rec001" for value in variants))

    def test_equivalent_numeric_formats_match(self):
        parsed_value, status, _ = parse_numeric_value("$1,200.00")
        self.assertEqual(status, "VALID")
        self.assertEqual(parsed_value, Decimal("1200.00"))

    def test_malformed_numeric_value_does_not_crash(self):
        parsed_value, status, warning = parse_numeric_value("not-a-number")
        self.assertIsNone(parsed_value)
        self.assertEqual(status, "INVALID")

    def test_identical_invalid_values_are_not_treated_as_valid_numeric_match(self):
        system_a = [{
            "record_id_raw": "REC005",
            "record_id_normalized": "rec005",
            "location_id": "LOC-A",
            "value_raw": "not-a-number",
            "value_parsed": None,
            "value_parse_status": "INVALID",
        }]
        system_b = [{
            "record_ref_raw": "REC005",
            "record_ref_normalized": "rec005",
            "location_id": "LOC-A",
            "value_raw": "not-a-number",
            "value_parsed": None,
            "value_parse_status": "INVALID",
        }]

        discrepancies = compare_systems(system_a, system_b, self.location_map)

        self.assertEqual(VALUE_MISMATCH, discrepancies[0]["reason"])
        self.assertIn("numeric equality could not be established", discrepancies[0]["explanation"])

    def test_different_invalid_values_are_mismatch(self):
        system_a = [{
            "record_id_raw": "REC005",
            "record_id_normalized": "rec005",
            "location_id": "LOC-A",
            "value_raw": "not-a-number",
            "value_parsed": None,
            "value_parse_status": "INVALID",
        }]
        system_b = [{
            "record_ref_raw": "REC005",
            "record_ref_normalized": "rec005",
            "location_id": "LOC-A",
            "value_raw": "unknown",
            "value_parsed": None,
            "value_parse_status": "INVALID",
        }]

        discrepancies = compare_systems(system_a, system_b, self.location_map)

        self.assertEqual(VALUE_MISMATCH, discrepancies[0]["reason"])

    def test_malformed_csv_extra_field_is_preserved(self):
        with NamedTemporaryFile(mode="w", newline="", suffix=".csv", delete=False) as handle:
            handle.write("record_id,location,value\nREC003,LOC-A,$1,200.00\n")
            path = Path(handle.name)

        try:
            rows = Command()._read_csv_rows(path)
            _, raw_source_row = rows[0]
            self.assertEqual(["REC003", "LOC-A", "$1", "200.00"], raw_source_row["fields"])
            self.assertEqual(["200.00"], raw_source_row["extra_fields"])
            self.assertIn("unexpected extra columns", Command()._row_warning(raw_source_row))
        finally:
            path.unlink()
