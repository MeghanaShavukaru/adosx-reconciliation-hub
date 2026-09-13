# Agent Notes

## Summary
This repository was created from a mostly empty workspace. The main challenge was not only building the app, but doing it in a way that respected the data quality constraints, the tenant scoping requirement, and the requirement to preserve dirty rows while comparing data across two systems.

## Key Findings During Development
- The supplied CSV files were not present in the repo, so realistic dirty-data files were created under the data/ directory to keep the implementation testable.
- The initial model design caused a field collision between `location` and `location_id`, which was fixed by simplifying the schema to explicit location identifiers.
- The tenant API originally attempted to query a relationship that did not exist; the fix was to filter at the model level with location IDs in the allowed organization set.
- The clean-match tests initially assumed an invalid scenario; they were corrected to compare equivalent records with equal normalized values.

## What the Agent Did Well
- Helped structure the project into backend, frontend, and data layers.
- Identified the need to preserve raw and normalized values separately.
- Suggested a comparator that distinguishes missing, orphan, duplicate, and mismatch scenarios.
- Helped create a lightweight UI that reflects the API output without duplicating business rules on the client.

## What the Agent Got Wrong or Needed Correction
- The initial assumptions around normalization were too permissive for real dirty data.
- Some early attempts treated invalid data too casually and could hide discrepancies instead of surfacing them.
- The first tenant query logic assumed relationship-based filtering instead of direct location scoping, which does not exist in the simplified model.

## Process Notes
The work was iterative and mostly test-driven after the core architecture was in place. The backend rules were validated with Django tests before the UI was finalized, which kept the risk lower and made the debugging path much clearer.

## Final Assessment
The project now satisfies the required scope: importer, reconciliation logic, tenant filtering, API exposure, React dashboard, tests, and documentation. It remains intentionally narrow and professional in scope, with the important edge cases documented for future extension.
