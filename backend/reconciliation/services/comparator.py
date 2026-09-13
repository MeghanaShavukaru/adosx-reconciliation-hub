from decimal import Decimal


MISSING_IN_SYSTEM_B = "MISSING_IN_SYSTEM_B"
ORPHAN_IN_SYSTEM_B = "ORPHAN_IN_SYSTEM_B"
DUPLICATE_IN_SYSTEM_B = "DUPLICATE_IN_SYSTEM_B"
VALUE_MISMATCH = "VALUE_MISMATCH"


def compare_values(a_raw, a_parsed, a_status, b_raw, b_parsed, b_status):
    if a_status == "VALID" and b_status == "VALID":
        if a_parsed == b_parsed:
            return False, None, ""
        return (
            True,
            b_parsed - a_parsed,
            f"System A reported {a_parsed} while System B reported {b_parsed}.",
        )

    if a_status == "BLANK" and b_status == "BLANK":
        return False, None, ""

    if a_status == "INVALID" and b_status == "INVALID":
        return (
            True,
            None,
            "Both systems contain an unparseable value; numeric equality "
            "could not be established.",
        )

    return (
        True,
        None,
        "One value was blank or invalid while the other was populated.",
    )


def _value_details(record):
    parsed = record.get("value_parsed")
    return {
        "raw_reference": record.get("record_id_raw", record.get("record_ref_raw")),
        "normalized_reference": record.get("record_id_normalized", record.get("record_ref_normalized")),
        "raw_value": record.get("value_raw"),
        "parsed_value": str(parsed) if parsed is not None else None,
        "parse_status": record.get("value_parse_status"),
        "raw_source_row": record.get("raw_source_row", {}),
        "import_warning": record.get("import_warning", ""),
        "malformed_row": record.get("malformed_row", False),
        "source_row_number": record.get("source_row_number"),
    }


def compare_systems(system_a_records, system_b_entries, location_map):
    discrepancies = []
    b_by_ref = {}
    for entry in system_b_entries:
        ref = entry["record_ref_normalized"]
        b_by_ref.setdefault(ref, []).append(entry)

    a_by_ref = {item["record_id_normalized"]: item for item in system_a_records}
    duplicate_refs = {
        ref for ref, entries in b_by_ref.items() if len(entries) > 1
    }
    emitted_duplicate_refs = set()

    for a in system_a_records:
        ref = a["record_id_normalized"]
        a_org = location_map.get(a.get("location_id"), {}).get("organization_id")
        b_entries = b_by_ref.get(ref, [])
        if not b_entries:
            discrepancies.append({
                "record_id": a["record_id_raw"],
                "location": a.get("location_id"),
                "org_id": a_org,
                "reason": MISSING_IN_SYSTEM_B,
                "system_a": _value_details(a),
                "system_b": {"raw_value": None, "parsed_value": None},
                "difference": None,
                "explanation": "No System B entry resolves to this System A record.",
            })
            continue

        if ref in duplicate_refs and ref not in emitted_duplicate_refs:
            emitted_duplicate_refs.add(ref)
            duplicates = [
                {
                    "raw_reference": item["record_ref_raw"],
                    "normalized_reference": item["record_ref_normalized"],
                    "raw_value": item.get("value_raw"),
                    "parsed_value": str(item.get("value_parsed")) if item.get("value_parsed") is not None else None,
                    "parse_status": item.get("value_parse_status"),
                    "source_row_number": item.get("source_row_number"),
                    "raw_source_row": item.get("raw_source_row", {}),
                    "import_warning": item.get("import_warning", ""),
                    "malformed_row": item.get("malformed_row", False),
                }
                for item in b_entries
            ]
            discrepancies.append({
                "record_id": a["record_id_raw"],
                "location": a.get("location_id"),
                "org_id": a_org,
                "reason": DUPLICATE_IN_SYSTEM_B,
                "system_a": _value_details(a),
                "system_b": {"entries": duplicates},
                "parent_exists": True,
                "difference": None,
                "explanation": f"{len(b_entries)} System B entries resolve to the same System A record.",
            })
            continue

        b_entry = b_entries[0]
        a_raw = a.get("value_raw")
        b_raw = b_entry.get("value_raw")
        mismatch, diff, explanation = compare_values(
            a_raw,
            a.get("value_parsed"),
            a.get("value_parse_status"),
            b_raw,
            b_entry.get("value_parsed"),
            b_entry.get("value_parse_status"),
        )
        if mismatch:
            discrepancies.append({
                "record_id": a["record_id_raw"],
                "location": a.get("location_id"),
                "org_id": a_org,
                "reason": VALUE_MISMATCH,
                "system_a": _value_details(a),
                "system_b": _value_details(b_entry),
                "difference": str(diff) if diff is not None else None,
                "explanation": explanation,
            })

    for ref, entries in b_by_ref.items():
        if ref in a_by_ref or ref in duplicate_refs:
            continue
        for entry in entries:
            org_id = location_map.get(entry.get("location_id"), {}).get("organization_id")
            discrepancies.append({
                "record_id": entry["record_ref_raw"],
                "location": entry.get("location_id"),
                "org_id": org_id,
                "reason": ORPHAN_IN_SYSTEM_B,
                "system_a": {"raw_value": None, "parsed_value": None},
                "system_b": _value_details(entry),
                "parent_exists": False,
                "difference": None,
                "explanation": "This System B entry references a record that does not exist in System A.",
            })

    for ref in duplicate_refs - set(a_by_ref):
        entries = b_by_ref[ref]
        first_entry = entries[0]
        org_id = location_map.get(first_entry.get("location_id"), {}).get("organization_id")
        duplicates = [
            {
                "raw_reference": item["record_ref_raw"],
                "normalized_reference": item["record_ref_normalized"],
                "raw_value": item.get("value_raw"),
                "parsed_value": str(item.get("value_parsed")) if item.get("value_parsed") is not None else None,
                "parse_status": item.get("value_parse_status"),
                "source_row_number": item.get("source_row_number"),
                "raw_source_row": item.get("raw_source_row", {}),
                "import_warning": item.get("import_warning", ""),
                "malformed_row": item.get("malformed_row", False),
            }
            for item in entries
        ]
        discrepancies.append({
            "record_id": first_entry["record_ref_raw"],
            "location": first_entry.get("location_id"),
            "org_id": org_id,
            "reason": DUPLICATE_IN_SYSTEM_B,
            "system_a": {"raw_value": None, "parsed_value": None},
            "system_b": {"entries": duplicates},
            "parent_exists": False,
            "difference": None,
            "explanation": (
                f"{len(entries)} System B entries resolve to "
                f"{first_entry['record_ref_raw']}, which also has no System A record."
            ),
        })

    return discrepancies
