from decimal import Decimal

from django.test import TestCase

from reconciliation.models import Location, SystemARecord, SystemBEntry


class TenantApiTests(TestCase):
    def setUp(self):
        self.location_a = Location.objects.create(location_id="LOC-A", organization_id="ORG-A", organization_name="Org A")
        self.location_b = Location.objects.create(location_id="LOC-B", organization_id="ORG-B", organization_name="Org B")

        SystemARecord.objects.create(
            record_id_raw="REC-001",
            record_id_normalized="rec001",
            location_id="LOC-A",
            value_raw="500",
            value_parsed=Decimal("500"),
            value_parse_status="VALID",
        )
        SystemBEntry.objects.create(
            record_ref_raw="REC001",
            record_ref_normalized="rec001",
            location_id="LOC-A",
            value_raw="550",
            value_parsed=Decimal("550"),
            value_parse_status="VALID",
        )

        SystemARecord.objects.create(
            record_id_raw="REC-900",
            record_id_normalized="rec900",
            location_id="LOC-B",
            value_raw="400",
            value_parsed=Decimal("400"),
            value_parse_status="VALID",
        )
        SystemBEntry.objects.create(
            record_ref_raw="REC-900",
            record_ref_normalized="rec900",
            location_id="LOC-B",
            value_raw="400",
            value_parsed=Decimal("400"),
            value_parse_status="VALID",
        )

    def test_tenant_a_cannot_receive_tenant_b_discrepancies(self):
        response = self.client.get("/api/discrepancies/?org_id=ORG-A")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(item["record_id"] == "REC-001" for item in payload["discrepancies"]))
        self.assertFalse(any(item["org_id"] == "ORG-B" for item in payload["discrepancies"]))

    def test_missing_org_id_returns_400(self):
        response = self.client.get("/api/discrepancies/")
        self.assertEqual(response.status_code, 400)

    def test_unknown_location_is_not_exposed_to_any_tenant(self):
        SystemBEntry.objects.create(
            record_ref_raw="REC-ZONE",
            record_ref_normalized="reczone",
            location_id="LOC-Z",
            value_raw="100",
            value_parsed=Decimal("100"),
            value_parse_status="VALID",
        )

        for organization_id in ("ORG-A", "ORG-B"):
            response = self.client.get(f"/api/discrepancies/?org_id={organization_id}")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(any(
                item["record_id"] == "REC-ZONE"
                for item in response.json()["discrepancies"]
            ))

        locations_response = self.client.get("/api/locations/?org_id=ORG-A")
        self.assertEqual(locations_response.status_code, 200)
        self.assertEqual(["LOC-A"], locations_response.json()["locations"])
