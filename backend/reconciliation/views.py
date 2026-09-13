import csv
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view

from .models import ImportRun, Location, SystemARecord, SystemBEntry
from .services.comparator import compare_systems
from .services.normalization import normalize_reference, parse_numeric_value


ALLOWED_REASONS = {
    "MISSING_IN_SYSTEM_B",
    "ORPHAN_IN_SYSTEM_B",
    "DUPLICATE_IN_SYSTEM_B",
    "VALUE_MISMATCH",
}


@api_view(["GET"])
def organizations(request):
    orgs = Location.objects.values_list("organization_id", flat=True).distinct()
    return JsonResponse({"organizations": list(orgs)})


@api_view(["GET"])
def locations(request):
    org_id = request.GET.get("org_id")
    if not org_id:
        return JsonResponse({"detail": "org_id is required."}, status=400)
    location_ids = Location.objects.filter(
        organization_id=org_id,
    ).values_list("location_id", flat=True)
    return JsonResponse({"locations": list(location_ids)})


@api_view(["GET"])
def discrepancies(request):
    org_id = request.GET.get("org_id")
    if not org_id:
        return JsonResponse({"detail": "org_id is required."}, status=400)

    reason = request.GET.get("reason")
    sort = request.GET.get("sort", "value_desc")
    search = request.GET.get("search", "").strip()
    location = request.GET.get("location", "")

    if reason and reason not in ALLOWED_REASONS:
        return JsonResponse({"detail": "Unsupported reason filter."}, status=400)
    if sort not in {"value_asc", "value_desc"}:
        return JsonResponse({"detail": "Unsupported sort option."}, status=400)

    allowed_location_ids = list(Location.objects.filter(organization_id=org_id).values_list("location_id", flat=True))
    records_a = list(SystemARecord.objects.filter(location_id__in=allowed_location_ids))
    entries_b = list(SystemBEntry.objects.filter(location_id__in=allowed_location_ids))

    location_map = {}
    for location_obj in Location.objects.filter(organization_id=org_id):
        location_map[location_obj.location_id] = {"organization_id": location_obj.organization_id}

    data = compare_systems(
        [
            {
                "record_id_raw": record.record_id_raw,
                "record_id_normalized": record.record_id_normalized,
                "record_id_raw": record.record_id_raw,
                "location_id": record.location_id,
                "value_raw": record.value_raw,
                "value_parsed": record.value_parsed,
                "value_parse_status": record.value_parse_status,
                "raw_source_row": record.raw_source_row,
                "import_warning": record.import_warning,
                "malformed_row": record.malformed_row,
                "source_row_number": record.source_row_number,
            }
            for record in records_a
        ],
        [
            {
                "record_ref_raw": entry.record_ref_raw,
                "record_ref_normalized": entry.record_ref_normalized,
                "record_ref_raw": entry.record_ref_raw,
                "location_id": entry.location_id,
                "value_raw": entry.value_raw,
                "value_parsed": entry.value_parsed,
                "value_parse_status": entry.value_parse_status,
                "raw_source_row": entry.raw_source_row,
                "import_warning": entry.import_warning,
                "malformed_row": entry.malformed_row,
                "source_row_number": entry.source_row_number,
            }
            for entry in entries_b
        ],
        location_map,
    )

    filtered = []
    for item in data:
        if reason and item["reason"] != reason:
            continue
        if search:
            if search.lower() not in str(item["record_id"]).lower() and search.lower() not in str(item.get("location") or "").lower():
                continue
        if location and str(item.get("location") or "") != str(location):
            continue
        filtered.append(item)

    def value_sort_key(item):
        value_candidates = []
        if item.get("system_a") and item["system_a"].get("parsed_value") is not None:
            value_candidates.append(Decimal(str(item["system_a"]["parsed_value"])))
        if item.get("system_b"):
            if isinstance(item["system_b"], dict) and item["system_b"].get("parsed_value") is not None:
                value_candidates.append(Decimal(str(item["system_b"]["parsed_value"])))
            elif isinstance(item["system_b"], dict) and item["system_b"].get("entries"):
                values = []
                for entry in item["system_b"]["entries"]:
                    if entry.get("parsed_value") is not None:
                        values.append(Decimal(str(entry["parsed_value"])))
                if values:
                    value_candidates.append(max(values))
        if not value_candidates:
            return Decimal("0")
        return max(value_candidates)

    filtered.sort(key=value_sort_key, reverse=(sort == "value_desc"))

    return JsonResponse({"discrepancies": filtered})


@api_view(["GET"])
def import_summary(request):
    org_id = request.GET.get("org_id")
    if not org_id:
        return JsonResponse({"detail": "org_id is required."}, status=400)

    latest = ImportRun.objects.order_by("-started_at").first()
    if latest is None:
        return JsonResponse({"system_a": {"rows_read": 0, "rows_stored": 0, "invalid_values": 0}, "system_b": {"rows_read": 0, "rows_stored": 0, "invalid_values": 0}, "locations": {"rows_read": 0, "organizations_found": 0}})

    return JsonResponse({
        "system_a": {
            "rows_read": latest.system_a_rows_read,
            "rows_stored": latest.system_a_rows_saved,
            "invalid_values": latest.system_a_invalid_values,
            "blank_values": latest.system_a_blank_values,
            "malformed_csv_rows": latest.system_a_malformed_rows,
        },
        "system_b": {
            "rows_read": latest.system_b_rows_read,
            "rows_stored": latest.system_b_rows_saved,
            "invalid_values": latest.system_b_invalid_values,
            "blank_values": latest.system_b_blank_values,
            "malformed_csv_rows": latest.system_b_malformed_rows,
        },
        "locations": {
            "rows_read": latest.location_rows_read,
            "rows_stored": latest.location_rows_saved,
            "malformed_csv_rows": latest.locations_malformed_rows,
            "organizations_found": Location.objects.values("organization_id").distinct().count(),
        },
    })


def _read_csv_rows(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


@api_view(["POST"])
def import_data(request):
    # Allows the management command to run via HTTP if desired.
    from django.core.management import call_command
    call_command("import_data")
    return JsonResponse({"status": "ok"})
