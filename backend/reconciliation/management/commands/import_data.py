import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from reconciliation.models import ImportRun, Location, SystemARecord, SystemBEntry
from reconciliation.services.normalization import normalize_reference, parse_numeric_value


class Command(BaseCommand):
    help = "Import system data and preserve raw rows for reconciliation."

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[4]
        data_dir = base_dir / "data"
        location_path = data_dir / "locations.csv"
        system_a_path = data_dir / "system_a.csv"
        system_b_path = data_dir / "system_b.csv"

        if not location_path.exists() or not system_a_path.exists() or not system_b_path.exists():
            self.stdout.write(self.style.ERROR("Required CSV files are missing from data/."))
            return

        with transaction.atomic():
            Location.objects.all().delete()
            SystemARecord.objects.all().delete()
            SystemBEntry.objects.all().delete()

            import_run = ImportRun.objects.create(
                system_a_rows_read=0,
                system_b_rows_read=0,
                location_rows_read=0,
                location_rows_saved=0,
                system_a_rows_saved=0,
                system_b_rows_saved=0,
                warnings_count=0,
                invalid_values_count=0,
            )

            location_rows = self._read_csv_rows(location_path)
            for idx, (row, raw_source_row) in enumerate(location_rows, start=1):
                normalized = {
                    "location_id": (row.get("location_id") or row.get("location") or row.get("location_identifier") or "").strip(),
                    "organization_id": (row.get("organization_id") or row.get("org_id") or row.get("organization") or "").strip(),
                    "organization_name": (row.get("organization_name") or row.get("org_name") or row.get("organization") or "").strip(),
                }
                import_warning = self._row_warning(raw_source_row)
                Location.objects.create(
                    location_id=normalized["location_id"],
                    organization_id=normalized["organization_id"],
                    organization_name=normalized["organization_name"],
                    raw_row=raw_source_row,
                    malformed_row=bool(import_warning),
                    import_warning=import_warning,
                )
            import_run.location_rows_read = len(location_rows)
            import_run.location_rows_saved = len(location_rows)
            import_run.locations_malformed_rows = sum(
                bool(self._row_warning(raw_source_row))
                for _, raw_source_row in location_rows
            )

            system_a_rows = self._read_csv_rows(system_a_path)
            for idx, (row, raw_source_row) in enumerate(system_a_rows, start=1):
                record_id_raw = (row.get("record_id") or row.get("record_ref") or row.get("id") or "").strip()
                location_id = (row.get("location") or row.get("location_id") or row.get("location_identifier") or "").strip()
                value_raw = row.get("value") or row.get("amount") or row.get("total") or ""
                parsed, status, warning = parse_numeric_value(value_raw)
                if status == "INVALID":
                    import_run.invalid_values_count += 1
                    import_run.warnings_count += 1
                    import_run.system_a_invalid_values += 1
                elif status == "BLANK":
                    import_run.system_a_blank_values += 1
                row_warning = self._row_warning(raw_source_row)
                if row_warning:
                    warning = "; ".join(filter(None, [warning, row_warning]))
                    import_run.warnings_count += 1
                    import_run.system_a_malformed_rows += 1
                SystemARecord.objects.create(
                    record_id_raw=record_id_raw,
                    record_id_normalized=normalize_reference(record_id_raw),
                    location_id=location_id,
                    value_raw=str(value_raw),
                    value_parsed=parsed,
                    value_parse_status=status,
                    source_row_number=idx,
                    import_warning=warning,
                    raw_source_row=raw_source_row,
                    malformed_row=bool(row_warning),
                )
            import_run.system_a_rows_read = len(system_a_rows)
            import_run.system_a_rows_saved = len(system_a_rows)

            system_b_rows = self._read_csv_rows(system_b_path)
            for idx, (row, raw_source_row) in enumerate(system_b_rows, start=1):
                record_ref_raw = (row.get("record_id") or row.get("record_ref") or row.get("id") or "").strip()
                location_id = (row.get("location") or row.get("location_id") or row.get("location_identifier") or "").strip()
                value_raw = row.get("value") or row.get("amount") or row.get("total") or ""
                parsed, status, warning = parse_numeric_value(value_raw)
                if status == "INVALID":
                    import_run.invalid_values_count += 1
                    import_run.warnings_count += 1
                    import_run.system_b_invalid_values += 1
                elif status == "BLANK":
                    import_run.system_b_blank_values += 1
                row_warning = self._row_warning(raw_source_row)
                if row_warning:
                    warning = "; ".join(filter(None, [warning, row_warning]))
                    import_run.warnings_count += 1
                    import_run.system_b_malformed_rows += 1
                SystemBEntry.objects.create(
                    record_ref_raw=record_ref_raw,
                    record_ref_normalized=normalize_reference(record_ref_raw),
                    location_id=location_id,
                    value_raw=str(value_raw),
                    value_parsed=parsed,
                    value_parse_status=status,
                    source_row_number=idx,
                    import_warning=warning,
                    raw_source_row=raw_source_row,
                    malformed_row=bool(row_warning),
                )
            import_run.system_b_rows_read = len(system_b_rows)
            import_run.system_b_rows_saved = len(system_b_rows)
            import_run.save()

        self.stdout.write(self.style.SUCCESS(
            "Import completed.\n"
            f"Locations: {len(location_rows)} rows read, {len(location_rows)} rows stored\n"
            f"System A: {len(system_a_rows)} rows read, {len(system_a_rows)} rows stored\n"
            f"System B: {len(system_b_rows)} rows read, {len(system_b_rows)} rows stored"
        ))

    def _read_csv_rows(self, path):
        with open(path, newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            rows = []
            for row in reader:
                extra_fields = row.get(None) or []
                missing_fields = [
                    field for field in fieldnames if row.get(field) is None
                ]
                rows.append((
                    row,
                    {
                        "header": fieldnames,
                        "fields": [
                            row.get(field) for field in fieldnames
                        ] + extra_fields,
                        "mapped_fields": {
                            field: row.get(field) for field in fieldnames
                        },
                        "extra_fields": extra_fields,
                        "missing_fields": missing_fields,
                    },
                ))
            return rows

    def _row_warning(self, raw_source_row):
        warnings = []
        if raw_source_row["extra_fields"]:
            warnings.append(
                "Malformed CSV row: unexpected extra columns were preserved."
            )
        if raw_source_row["missing_fields"]:
            warnings.append(
                "Malformed CSV row: expected columns are missing values."
            )
        return " ".join(warnings)
