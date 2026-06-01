import type { AdminScanDetail, AgenticJobGroups, AuthResponse, ExplorerStatsResponse, GetProfessorResponse, IndexedDepartment, ListAdminScansResponse, ListProfessorsResponse, ListUniversitiesResponse, MatchResponse, ProfessorFacetsResponse, ScanJob, ScanLog, ScanResult, ScanTask, StudentProfile, UserStateResponse } from './types';

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

function friendlyError(code: string | undefined, message: string, status: number) {
  if (code === 'rate_limit_exceeded') return 'Too many requests. Please wait a moment, then try again.';
  if (status === 401) return 'Please sign in to continue.';
  if (status === 403) return 'You do not have permission to do that.';
  if (code === 'validation_error') return message || 'Please check the highlighted fields and try again.';
  return message || `Request failed: ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    cache: 'no-store',
    credentials: 'include',
  });
  if (!res.ok) {
    const raw = await res.text();
    let message = raw;
    let code: string | undefined;
    try {
      const parsed = raw ? JSON.parse(raw) : null;
      code = parsed?.error?.code;
      message = parsed?.error?.message || parsed?.detail || raw;
    } catch {
      // Keep raw text fallback.
    }
    throw new ApiError(friendlyError(code, message, res.status), res.status, code);
  }
  return res.json() as Promise<T>;
}

export function getStats() {
  return request<ExplorerStatsResponse>('/api/stats');
}

export function getUniversities() {
  return request<ListUniversitiesResponse>('/api/universities');
}

export function listProfessors(params: Record<string, string | number | string[] | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.filter(Boolean).forEach(item => qs.append(key, item));
    } else if (value !== undefined && value !== '') qs.set(key, String(value));
  });
  return request<ListProfessorsResponse>(`/api/professors?${qs.toString()}`);
}

export function getProfessorFacets() {
  return request<ProfessorFacetsResponse>('/api/professors/facets');
}

export function getProfessor(id: string | number) {
  return request<GetProfessorResponse>(`/api/professors/${id}`);
}

export function findMatches(
  student: StudentProfile,
  options?: { threshold_percent?: number; minimum_results?: number }
) {
  return request<MatchResponse>('/api/match', {
    method: 'POST',
    body: JSON.stringify({
      ...student,
      threshold_percent: options?.threshold_percent ?? 40,
      minimum_results: options?.minimum_results ?? 10,
    }),
  });
}

export function registerUser(payload: { email: string; password: string; display_name: string }) {
  return request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function loginUser(payload: { email: string; password: string }) {
  return request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function logoutUser() {
  return request<{ status: string }>('/api/auth/logout', { method: 'POST' });
}

export function deleteAccount() {
  return request<{ status: string }>('/api/auth/account', { method: 'DELETE' });
}

export function getCurrentUser() {
  return request<AuthResponse>('/api/auth/me');
}

export function getUserState() {
  return request<UserStateResponse>('/api/auth/state');
}

export function patchUserState(payload: Partial<UserStateResponse>) {
  return request<UserStateResponse>('/api/auth/state', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function createScanJob(payload: { items: Array<{ university: string; department: string; faculty_url: string }>; settings?: Record<string, any> }) {
  return request<{ job_id: number; status: string; total_tasks: number; job: ScanJob }>('/api/admin/scan-jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listScanJobs(params: { status?: string; limit?: number; offset?: number } = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') qs.set(key, String(value));
  });
  return request<{ jobs: ScanJob[] }>(`/api/admin/scan-jobs${qs.toString() ? `?${qs.toString()}` : ''}`);
}

export function getScanJob(id: number | string) {
  return request<{ job: ScanJob }>(`/api/admin/scan-jobs/${encodeURIComponent(String(id))}`);
}

export function cancelScanJob(id: number | string) {
  return request<{ job: ScanJob }>(`/api/admin/scan-jobs/${encodeURIComponent(String(id))}/cancel`, { method: 'POST' });
}

export function listScanJobTasks(id: number | string) {
  return request<{ tasks: ScanTask[] }>(`/api/admin/scan-jobs/${encodeURIComponent(String(id))}/tasks`);
}

export function listScanJobResults(id: number | string) {
  return request<{ results: ScanResult[] }>(`/api/admin/scan-jobs/${encodeURIComponent(String(id))}/results`);
}

export function listScanJobLogs(id: number | string) {
  return request<{ logs: ScanLog[] }>(`/api/admin/scan-jobs/${encodeURIComponent(String(id))}/logs`);
}

export function approveScanResult(id: number | string) {
  return request<{ result: ScanResult }>(`/api/admin/scan-results/${encodeURIComponent(String(id))}/approve`, { method: 'POST' });
}

export function rejectScanResult(id: number | string) {
  return request<{ result: ScanResult }>(`/api/admin/scan-results/${encodeURIComponent(String(id))}/reject`, { method: 'POST' });
}

export function importScanResult(id: number | string) {
  return request<{ result: ScanResult }>(`/api/admin/scan-results/${encodeURIComponent(String(id))}/import`, { method: 'POST' });
}

export function fetchScanJobPublications(id: number | string, payload: { max_publications?: number; use_llm_verification?: boolean } = {}) {
  return request<{ summary: Record<string, any> }>(`/api/admin/scan-jobs/${encodeURIComponent(String(id))}/fetch-publications`, {
    method: 'POST',
    body: JSON.stringify({ max_publications: payload.max_publications ?? 10, use_llm_verification: payload.use_llm_verification ?? false }),
  });
}

export function reviseScanJobPublications(id: number | string, payload: { max_publications?: number; use_llm_verification?: boolean } = {}) {
  return fetchScanJobPublications(id, payload);
}

export function importApprovedScanResults(id: number | string) {
  return request<{ imported_count: number; results: ScanResult[] }>(`/api/admin/scan-jobs/${encodeURIComponent(String(id))}/import-approved`, { method: 'POST' });
}

export function listAdminScans() {
  return request<ListAdminScansResponse>('/api/admin/scans');
}

export function getAdminScan(id: string) {
  return request<AdminScanDetail>(`/api/admin/scans/${encodeURIComponent(id)}`);
}

export function importAdminScan(id: string) {
  return request<any>(`/api/admin/scans/${encodeURIComponent(id)}/import`, { method: 'POST' });
}

export function listAdapters() {
  return request<{ adapters: string[] }>('/api/admin/adapters');
}

export function runAdminScan(payload: { adapter: string; enrich_profiles?: boolean; enrich_publications?: boolean }) {
  return request<{ status: string; adapter: string }>('/api/admin/scans/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function onboardUniversity(payload: { url: string; university: string; department: string; automatic?: boolean }) {
  return request<{ status: string; job_id: string; message: string }>('/api/admin/agentic/onboard', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listAgenticJobs() {
  return request<{ jobs: any[] }>('/api/admin/agentic/jobs');
}

export function listAgenticJobGroups() {
  return request<AgenticJobGroups>('/api/admin/agentic/jobs/grouped');
}

export function getAgenticJob(id: string) {
  return request<any>(`/api/admin/agentic/job/${encodeURIComponent(id)}`);
}

export function enrichAgenticHomepage(id: string) {
  return request<{ status: string; message: string }>(`/api/admin/agentic/job/${encodeURIComponent(id)}/enrich-homepage`, { method: 'POST' });
}

export function fetchAgenticPublications(id: string) {
  return request<{ status: string; message: string }>(`/api/admin/agentic/job/${encodeURIComponent(id)}/fetch-publications`, { method: 'POST' });
}

export function generateAgenticSummary(id: string) {
  return request<{ status: string; message: string }>(`/api/admin/agentic/job/${encodeURIComponent(id)}/generate-summary`, { method: 'POST' });
}

export function publishAgenticJob(id: string) {
  return request<{ status: string; message: string }>(`/api/admin/agentic/job/${encodeURIComponent(id)}/publish`, { method: 'POST' });
}

export function stopAgenticJob(id: string) {
  return request<{ status: string; message: string }>(`/api/admin/agentic/job/${encodeURIComponent(id)}/stop`, { method: 'POST' });
}

export function deleteAgenticJob(id: string) {
  return request<{ status: string }>(`/api/admin/agentic/job/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export function getScanStatus() {
  return request<{ status: string; message: string }>('/api/admin/scans/status');
}

export function listIndexedDepartments() {
  return request<{ groups: IndexedDepartment[] }>('/api/admin/indexed-departments');
}

export function refreshIndexedDepartment(payload: { university: string; department: string; faculty_page_url: string; automatic?: boolean }) {
  return request<{ status: string; job_id: string; message: string }>('/api/admin/indexed-departments/refresh', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function refreshIndexedDepartmentPublications(payload: { university: string; department: string; max_publications?: number; max_professors?: number }) {
  return request<{ status: string; message: string }>('/api/admin/indexed-departments/fetch-publications', {
    method: 'POST',
    body: JSON.stringify({
      max_publications: 10,
      max_professors: 250,
      ...payload,
      regenerate_summaries: false,
    }),
  });
}

export function enrichIndexedDepartmentProfiles(payload: { university: string; department: string; max_professors?: number }) {
  return request<{ status: string; message: string }>('/api/admin/indexed-departments/enrich-profiles', {
    method: 'POST',
    body: JSON.stringify({ max_professors: 250, ...payload }),
  });
}

export function deleteIndexedDepartment(payload: { university: string; department: string; confirm: boolean }) {
  return request<{ status: string; professors_deleted: number; publications_deleted: number }>('/api/admin/indexed-departments', {
    method: 'DELETE',
    body: JSON.stringify(payload),
  });
}

export function submitRecommendation(payload: { university: string; department: string; faculty_page_url: string }) {
  return request<{ status: string; id: string; message: string }>('/api/recommendations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listRecommendationRequests() {
  return request<{ requests: any[] }>('/api/admin/recommendations');
}
