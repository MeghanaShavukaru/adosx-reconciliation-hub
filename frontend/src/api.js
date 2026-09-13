const API_BASE = '/api';

async function request(path, query = {}) {
  const params = new URLSearchParams(query);
  const response = await fetch(`${API_BASE}${path}?${params.toString()}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Request failed');
  }
  return response.json();
}

export function fetchOrganizations() {
  return request('/organizations/');
}

export function fetchLocations(params) {
  return request('/locations/', params);
}

export function fetchDiscrepancies(params) {
  return request('/discrepancies/', params);
}

export function fetchImportSummary(params) {
  return request('/import-summary/', params);
}
