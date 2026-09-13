# AdosX Reconciliation Hub

## Overview
This project is a small reconciliation tool for comparing two dirty data sources and making tenant-safe disagreement checks visible in a simple UI. The goal is to preserve raw CSV values, normalize references and numbers carefully, and highlight mismatches without losing the original source data.

## Tech Stack
- Django
- Django REST Framework
- SQLite
- React
- Vite

## Architecture
CSV data flows through the importer into SQLite, where raw values and normalized values are stored separately. The comparison logic then groups records, detects discrepancy types, and exposes tenant-scoped data through a Django API. The frontend requests only the selected organization’s data and renders it in a dashboard.

## Project Structure
```text
adosx-reconciliation-hub/
├── backend/
│   ├── config/
│   ├── reconciliation/
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── locations.csv
│   ├── system_a.csv
│   └── system_b.csv
├── README.md
├── DECISIONS.md
├── AGENT_NOTES.md
├── .gitignore
└── .venv (optional local virtual environment)
```

## Setup From Clean Clone
```bash
cd adosx-reconciliation-hub

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py import_data
python manage.py test
python manage.py runserver 127.0.0.1:8000
```

Then in a second terminal:
```bash
cd adosx-reconciliation-hub/frontend
npm install
npm run dev
```

## Backend Setup
The backend uses SQLite for simplicity and deterministic local testing. After activation, install dependencies, run migrations, and import the CSV files using the management command. The import command preserves dirty rows and stores both raw and normalized values.

## Frontend Setup
The frontend is a Vite React app. It calls the backend API at http://127.0.0.1:8000 and presents the tenant-scoped reconciliation dashboard. Run `npm run dev` and open the local Vite URL.

## Running Tests
```bash
cd backend
python manage.py test reconciliation.tests
```

## Data Import Behavior
Every imported row remains visible in the database. Values are parsed into a normalized decimal when possible, but the raw source value stays alongside the parsed value. This prevents dirty data from silently disappearing and makes the results explainable in audit scenarios.

Malformed CSV rows are also preserved as complete field sequences with their extra or missing fields and an import warning. The importer does not silently repair an unquoted numeric comma. Unknown locations remain stored with unresolved ownership and are excluded from organization-scoped API responses.

## Reconciliation Rules
The comparator detects four required disagreement types:
- Missing in System B
- Orphan in System B
- Duplicate in System B
- Value Mismatch

A clean match is excluded from the discrepancy table when the normalized record identity matches and both values are valid and equal, or both values are explicitly blank. Invalid values remain discrepancies because numeric equality cannot be established.

## Tenant Isolation
Tenant isolation happens on the backend before serialization. The API requires `org_id` and only returns rows for that organization. Authentication was intentionally omitted because the assignment explicitly says that auth is outside scope; the organization selector is a demonstration of correct scoping rather than production-grade authorization.

## Additional Features
- Organization selector with tenant-scoped data requests
- Summary cards
- Organization-scoped search and reason filtering
- Location filtering
- Value sorting
- Detail modal with preserved source-row metadata
- Import quality summary
- Tenant-scoped locations endpoint

## What I Built
- Django app with CSV import command
- SQLite data models for location, System A, System B, and import tracking
- Normalization and numeric parsing utilities
- Reconciliation engine and tenant-scoped API
- React dashboard with filters, summary cards, and detail view
- Automated tests for normalization, comparison, and tenant isolation

## What I Deliberately Did Not Build
- Authentication or user accounts
- JWT or OIDC
- microservices or Docker
- an LLM-backed reconciliation feature
- complex caching or analytics features
- CSV export (left as a second-day improvement)

## How I Worked With the Agent
I used an AI coding agent to help inspect the problem, propose architecture, flag edge cases, and generate draft implementations. I treated the generated code as a starting point rather than as ground truth, checked behavior against the CSVs and tests, and changed assumptions when they did not match the data or the security requirements.

## Mandatory Reflection Questions
### A. Name one thing the AI agent got wrong. How did you notice?
The agent initially suggested a pattern that treated invalid numeric parsing as an equivalent null-like state and could accidentally hide real errors. I noticed this while writing the comparator tests because a malformed value should stay invalid rather than being silently treated as equal to another invalid value.

### B. Which part of your submission are you least confident about, and why?
I am least confident about widening the reference normalization rules beyond the observed dataset. The project intentionally keeps normalization conservative so it does not merge genuinely different IDs, but future CSVs could require a wider set of sanitization rules.

### C. If you had a second day, what would you fix first?
I would add stronger import validation and richer data-quality reporting, especially for unresolved tenant ownership and invalid-location edge cases. That would make the tool better for operational audits without changing the core reconciliation logic.

## Limitations
- No authentication has been implemented by design.
- SQLite is used intentionally for a small local dataset.
- Reference normalization is deliberately conservative and based on the observed data patterns.
- The app is designed for the supplied dataset and does not include large-file streaming or pagination.
