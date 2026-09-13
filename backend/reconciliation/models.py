from django.db import models


class ImportRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now=True)
    system_a_rows_read = models.PositiveIntegerField(default=0)
    system_a_rows_saved = models.PositiveIntegerField(default=0)
    system_b_rows_read = models.PositiveIntegerField(default=0)
    system_b_rows_saved = models.PositiveIntegerField(default=0)
    location_rows_read = models.PositiveIntegerField(default=0)
    location_rows_saved = models.PositiveIntegerField(default=0)
    warnings_count = models.PositiveIntegerField(default=0)
    invalid_values_count = models.PositiveIntegerField(default=0)
    system_a_invalid_values = models.PositiveIntegerField(default=0)
    system_a_blank_values = models.PositiveIntegerField(default=0)
    system_a_malformed_rows = models.PositiveIntegerField(default=0)
    system_b_invalid_values = models.PositiveIntegerField(default=0)
    system_b_blank_values = models.PositiveIntegerField(default=0)
    system_b_malformed_rows = models.PositiveIntegerField(default=0)
    locations_malformed_rows = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"ImportRun {self.pk}"


class Location(models.Model):
    location_id = models.CharField(max_length=255, unique=True)
    organization_id = models.CharField(max_length=255)
    organization_name = models.CharField(max_length=255, blank=True, default="")
    raw_row = models.JSONField(default=dict, blank=True)
    malformed_row = models.BooleanField(default=False)
    import_warning = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location_id} -> {self.organization_id}"


class SystemARecord(models.Model):
    record_id_raw = models.CharField(max_length=255)
    record_id_normalized = models.CharField(max_length=255, db_index=True)
    location_id = models.CharField(max_length=255, blank=True, default="")
    value_raw = models.TextField(blank=True, default="")
    value_parsed = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    value_parse_status = models.CharField(max_length=32, default="UNKNOWN")
    source_row_number = models.PositiveIntegerField(default=0)
    import_warning = models.TextField(blank=True, default="")
    raw_source_row = models.JSONField(default=dict, blank=True)
    malformed_row = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["record_id_normalized", "location_id"])]

    def __str__(self):
        return f"A:{self.record_id_normalized}"


class SystemBEntry(models.Model):
    record_ref_raw = models.CharField(max_length=255)
    record_ref_normalized = models.CharField(max_length=255, db_index=True)
    location_id = models.CharField(max_length=255, blank=True, default="")
    value_raw = models.TextField(blank=True, default="")
    value_parsed = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    value_parse_status = models.CharField(max_length=32, default="UNKNOWN")
    source_row_number = models.PositiveIntegerField(default=0)
    import_warning = models.TextField(blank=True, default="")
    raw_source_row = models.JSONField(default=dict, blank=True)
    malformed_row = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["record_ref_normalized", "location_id"])]

    def __str__(self):
        return f"B:{self.record_ref_normalized}"
