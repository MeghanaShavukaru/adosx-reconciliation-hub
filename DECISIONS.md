# Design Decisions

## 1. Preserve raw data and normalize separately
The importer stores raw values exactly as read from CSV. A second normalized field is used for matching and comparison logic. This prevents dirty data loss and allows audit review of the original source values.

## 2. Keep a conservative normalization policy
Reference normalization strips whitespace, lowercases, removes common separators, and preserves the record identity structure. It does not aggressively rewrite values beyond the observed dataset, because over-normalization can merge distinct records.

## 3. Treat invalid numeric values as invalid rather than equal
Numeric parsing is intentionally explicit: valid numbers are compared numerically; blanks are tracked separately; invalid strings remain invalid. This avoids false clean matches and makes the audit trail explainable.

When both systems contain invalid values, the comparator emits `VALUE_MISMATCH` because numeric equality cannot be established. Identical invalid strings are not treated as a valid numeric match.

## 3a. Preserve malformed CSV rows without repairing them
The importer stores the complete parsed field sequence, mapped fields, extra fields, and missing fields for every source row. Extra columns produce an import warning and malformed-row flag. The importer does not reconstruct `$1,200.00` from an unquoted `$1,200.00` row, because that would pretend malformed source data was valid.

The original row remains available for audit inspection, while comparison uses the value field that the CSV parser actually mapped.

## 3b. Detect duplicate System B references globally
System B references are grouped after normalization before matching to System A. A duplicate group is emitted once with `DUPLICATE_IN_SYSTEM_B`. If the parent is absent, the result includes `parent_exists: false` and explains both conditions.

## 3c. Fail closed for unknown locations
Rows with locations absent from `locations.csv` are preserved and have unresolved ownership. Organization-scoped endpoints only query known location IDs belonging to the requested organization, so unknown-location rows are not exposed to any tenant.

## 4. Do not trust UI filters for enforcement
The API enforces tenant boundaries and validates required query parameters. The frontend is display-only; all security-sensitive filtering must happen server-side.

## 5. Use SQLite for the assignment scope
SQLite keeps the project lightweight, easy to run locally, and deterministic in tests. The data size and assignment scope do not require a more complex database.

## 6. Keep the frontend simple and composable
The React UI is intentionally narrow: summary cards, filters, table, and modal. This keeps the product easy to understand and demonstrates the required behavior without overengineering the interface.

## 7. Structure the code to make testing straightforward
The normalization and comparator logic were separated into service functions and unit-tested independently. This makes it easier to validate the root cause and to keep a stable regression suite.

## 8. Feature completeness focused on assignment requirements
The tool includes no auth, no complex workflows, and no unrelated analytics; it stays focused on reconciliation quality, tenant scoping, and the required audit experience.
