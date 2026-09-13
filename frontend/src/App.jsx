import { useEffect, useMemo, useState } from 'react';
import './App.css';
import { fetchDiscrepancies, fetchImportSummary, fetchLocations, fetchOrganizations } from './api';

const REASON_LABELS = {
  MISSING_IN_SYSTEM_B: 'Missing in System B',
  ORPHAN_IN_SYSTEM_B: 'Orphan in System B',
  DUPLICATE_IN_SYSTEM_B: 'Duplicate in System B',
  VALUE_MISMATCH: 'Value Mismatch',
};

const REASON_OPTIONS = [
  { value: 'ALL', label: 'All reasons' },
  { value: 'MISSING_IN_SYSTEM_B', label: 'Missing in System B' },
  { value: 'ORPHAN_IN_SYSTEM_B', label: 'Orphan in System B' },
  { value: 'DUPLICATE_IN_SYSTEM_B', label: 'Duplicate in System B' },
  { value: 'VALUE_MISMATCH', label: 'Value Mismatch' },
];

function formatNumeric(value) {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return number.toLocaleString('en-US', { maximumFractionDigits: 4 });
}

function formatRaw(value) {
  return value === null || value === undefined || value === '' ? '—' : value;
}

function valueForTable(value) {
  return value?.parsed_value === null || value?.parsed_value === undefined
    ? '—'
    : formatNumeric(value.parsed_value);
}

function sideEntries(side) {
  if (!side) return [];
  return side.entries || [side];
}

function sourceFields(value) {
  if (!value?.raw_source_row?.fields) return '—';
  return JSON.stringify(value.raw_source_row.fields);
}

function DetailSide({ title, side }) {
  const entries = sideEntries(side);
  return (
    <section className="detail-side">
      <h3>{title}</h3>
      {entries.length === 0 ? <p className="muted">No source entry.</p> : entries.map((entry, index) => (
        <div className="source-entry" key={`${entry.raw_reference || title}-${index}`}>
          {entries.length > 1 && <h4>Entry {index + 1}</h4>}
          <dl className="detail-list">
            <div><dt>Raw reference</dt><dd>{formatRaw(entry.raw_reference)}</dd></div>
            <div><dt>Normalized reference</dt><dd>{formatRaw(entry.normalized_reference)}</dd></div>
            <div><dt>Raw value</dt><dd>{formatRaw(entry.raw_value)}</dd></div>
            <div><dt>Parsed value</dt><dd>{formatRaw(entry.parsed_value)}</dd></div>
            <div><dt>Parse status</dt><dd>{formatRaw(entry.parse_status)}</dd></div>
            <div><dt>Source row</dt><dd>{formatRaw(entry.source_row_number)}</dd></div>
            <div><dt>Malformed row</dt><dd>{entry.malformed_row ? 'Yes' : 'No'}</dd></div>
          </dl>
          <div className="raw-source">
            <span>Preserved source fields</span>
            <code>{sourceFields(entry)}</code>
          </div>
          {entry.import_warning && <p className="warning"><strong>Import warning:</strong> {entry.import_warning}</p>}
        </div>
      ))}
    </section>
  );
}

function App() {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [reason, setReason] = useState('ALL');
  const [sort, setSort] = useState('value_desc');
  const [search, setSearch] = useState('');
  const [location, setLocation] = useState('ALL');
  const [rows, setRows] = useState([]);
  const [organizationRows, setOrganizationRows] = useState([]);
  const [organizationLocations, setOrganizationLocations] = useState([]);
  const [importSummary, setImportSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [organizationError, setOrganizationError] = useState('');
  const [error, setError] = useState('');
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState(null);

  useEffect(() => {
    fetchOrganizations()
      .then((payload) => {
        const orgs = payload.organizations || [];
        setOrganizations(orgs);
        setSelectedOrg((current) => current || orgs[0] || '');
      })
      .catch(() => setOrganizationError('Unable to load organization list.'));
  }, []);

  useEffect(() => {
    if (!selectedOrg) return;
    setOrganizationLocations([]);

    fetchDiscrepancies({ org_id: selectedOrg, sort: 'value_desc' })
      .then((payload) => setOrganizationRows(payload.discrepancies || []))
      .catch(() => setOrganizationRows([]));

    fetchImportSummary({ org_id: selectedOrg })
      .then((payload) => setImportSummary(payload))
      .catch(() => setImportSummary(null));

    fetchLocations({ org_id: selectedOrg })
      .then((payload) => setOrganizationLocations(payload.locations || []))
      .catch(() => setOrganizationLocations([]));
  }, [selectedOrg]);

  useEffect(() => {
    if (!selectedOrg) return;
    setLoading(true);
    setError('');

    const query = {
      org_id: selectedOrg,
      ...(reason !== 'ALL' ? { reason } : {}),
      sort,
      ...(search ? { search } : {}),
      ...(location !== 'ALL' ? { location } : {}),
    };

    fetchDiscrepancies(query)
      .then((payload) => setRows(payload.discrepancies || []))
      .catch((err) => {
        setError(err.message || 'Unable to load reconciliation data.');
        setRows([]);
      })
      .finally(() => setLoading(false));
  }, [selectedOrg, reason, sort, search, location]);

  const summary = useMemo(() => {
    const counts = {
      total: organizationRows.length,
      MISSING_IN_SYSTEM_B: 0,
      ORPHAN_IN_SYSTEM_B: 0,
      DUPLICATE_IN_SYSTEM_B: 0,
      VALUE_MISMATCH: 0,
    };
    organizationRows.forEach((row) => {
      counts[row.reason] = (counts[row.reason] || 0) + 1;
    });
    return counts;
  }, [organizationRows]);

  const availableLocations = useMemo(
    () => [...new Set(organizationLocations.filter(Boolean))],
    [organizationLocations],
  );

  const changeOrganization = (nextOrganization) => {
    setSelectedDiscrepancy(null);
    setRows([]);
    setLocation('ALL');
    setSelectedOrg(nextOrganization);
  };

  const resetFilters = () => {
    setReason('ALL');
    setSort('value_desc');
    setSearch('');
    setLocation('ALL');
  };

  const tableEmptyMessage = organizationRows.length === 0
    ? 'No disagreements found for this organization.'
    : 'No disagreements match the current filters.';

  return (
    <div className="page-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">AdosX Reconciliation Hub</p>
          <h1>Cross-System Discrepancy Monitor</h1>
        </div>
        <label className="org-picker">
          <span>Organization</span>
          <select value={selectedOrg} onChange={(e) => changeOrganization(e.target.value)} disabled={!organizations.length}>
            {!organizations.length && <option value="">Loading organizations...</option>}
            {organizations.map((org) => <option key={org} value={org}>{org}</option>)}
          </select>
          {organizationError && <small className="error-text">{organizationError}</small>}
        </label>
      </header>

      <section className="summary-grid" aria-label="Organization issue summary">
        <div className="stat-card"><strong>{summary.total}</strong><span>Total Issues</span></div>
        <div className="stat-card"><strong>{summary.MISSING_IN_SYSTEM_B}</strong><span>Missing</span></div>
        <div className="stat-card"><strong>{summary.VALUE_MISMATCH}</strong><span>Mismatches</span></div>
        <div className="stat-card"><strong>{summary.DUPLICATE_IN_SYSTEM_B}</strong><span>Duplicates</span></div>
        <div className="stat-card"><strong>{summary.ORPHAN_IN_SYSTEM_B}</strong><span>Orphans</span></div>
      </section>

      <section className="toolbar" aria-label="Discrepancy filters">
        <label className="filter-field search-field">
          <span>Search</span>
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search record or location..." />
        </label>
        <label className="filter-field">
          <span>Reason</span>
          <select value={reason} onChange={(e) => setReason(e.target.value)}>
            {REASON_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.value === 'ALL' ? 'All Reasons' : option.label}</option>)}
          </select>
        </label>
        <label className="filter-field">
          <span>Location</span>
          <select value={availableLocations.includes(location) ? location : 'ALL'} onChange={(e) => setLocation(e.target.value)}>
            <option value="ALL">All Locations</option>
            {availableLocations.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="filter-field">
          <span>Sort</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="value_desc">Value: High → Low</option>
            <option value="value_asc">Value: Low → High</option>
          </select>
        </label>
        <button type="button" className="reset-button" onClick={resetFilters}>Reset Filters</button>
      </section>

      <section className="table-wrap">
        {loading ? <p className="empty-message">Loading discrepancies...</p> : error ? <p className="empty-message">{error}</p> : rows.length === 0 ? <p className="empty-message">{tableEmptyMessage}</p> : (
          <table>
            <thead>
              <tr><th>Record</th><th>Location</th><th>Reason</th><th>System A Value</th><th>System B Value</th><th>Difference</th><th>Details</th></tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${row.record_id}-${row.reason}-${row.location}-${index}`}>
                  <td>{row.record_id}</td>
                  <td>{row.location || '—'}</td>
                  <td><span className="badge">{REASON_LABELS[row.reason] || row.reason}</span></td>
                  <td>{valueForTable(row.system_a)}</td>
                  <td>{row.system_b?.entries ? row.system_b.entries.map((entry) => formatNumeric(entry.parsed_value)).join(', ') : valueForTable(row.system_b)}</td>
                  <td>{formatNumeric(row.difference)}</td>
                  <td><button type="button" className="view-button" onClick={() => setSelectedDiscrepancy(row)}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {importSummary && (
        <section className="import-box">
          <h2>Import Quality</h2>
          <div className="import-grid">
            <div className="import-source"><strong>System A</strong><span>Rows: {importSummary.system_a.rows_read} / {importSummary.system_a.rows_stored} preserved</span><span>Invalid values: {importSummary.system_a.invalid_values}</span><span>Blank values: {importSummary.system_a.blank_values}</span><span>Malformed CSV rows: {importSummary.system_a.malformed_csv_rows}</span></div>
            <div className="import-source"><strong>System B</strong><span>Rows: {importSummary.system_b.rows_read} / {importSummary.system_b.rows_stored} preserved</span><span>Invalid values: {importSummary.system_b.invalid_values}</span><span>Blank values: {importSummary.system_b.blank_values}</span><span>Malformed CSV rows: {importSummary.system_b.malformed_csv_rows}</span></div>
            <div className="import-source"><strong>Locations</strong><span>Rows: {importSummary.locations.rows_read} / {importSummary.locations.rows_stored} preserved</span><span>Malformed CSV rows: {importSummary.locations.malformed_csv_rows}</span></div>
          </div>
        </section>
      )}

      {selectedDiscrepancy && (
        <div className="modal-backdrop" onClick={() => setSelectedDiscrepancy(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header"><div><p className="eyebrow">Audit record</p><h2>Discrepancy Details</h2></div><button type="button" className="close-icon" aria-label="Close details" onClick={() => setSelectedDiscrepancy(null)}>×</button></div>
            <dl className="record-summary">
              <div><dt>Record</dt><dd>{selectedDiscrepancy.record_id}</dd></div>
              <div><dt>Location</dt><dd>{selectedDiscrepancy.location || '—'}</dd></div>
              <div><dt>Organization</dt><dd>{selectedDiscrepancy.org_id || 'Unresolved'}</dd></div>
              <div><dt>Reason</dt><dd><span className="badge">{REASON_LABELS[selectedDiscrepancy.reason] || selectedDiscrepancy.reason}</span></dd></div>
            </dl>
            <p className="explanation"><strong>Why flagged</strong>{selectedDiscrepancy.explanation}</p>
            <div className="detail-columns"><DetailSide title="System A" side={selectedDiscrepancy.system_a} /><DetailSide title="System B" side={selectedDiscrepancy.system_b} /></div>
            <button type="button" className="close-button" onClick={() => setSelectedDiscrepancy(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
