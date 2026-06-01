export interface ProfessorSummary {
  id: number;
  name: string;
  title?: string | null;
  university: string;
  department: string;
  research_summary?: string | null;
  recruiting_signal: 'positive' | 'negative' | 'unknown';
  source_confidence: number;
  publication_count: number;
  tags: string[];
  profile_display_status?: string | null;
  profile_text_source_url?: string | null;
  profile_text_confidence?: number | null;
  photo_url?: string | null;
  photo_source_url?: string | null;
  photo_confidence?: number | null;
}

export interface ListProfessorsResponse {
  professors: ProfessorSummary[];
  total: number;
  page: number;
  limit: number;
  next_cursor?: string | null;
}

export interface ProfessorFacetsResponse {
  tags: string[];
  universities: string[];
  departments: string[];
  titles: string[];
  recruiting_signals: string[];
}

export interface PublicationResponse {
  id: number;
  title: string;
  year: number | null;
  venue: string | null;
  abstract?: string | null;
  url?: string | null;
  source: string;
  source_author_id?: string | null;
  match_confidence: number;
}

export interface ProfessorDetail {
  id: number;
  name: string;
  normalized_name: string;
  title?: string | null;
  university: string;
  department: string;
  email?: string | null;
  faculty_profile_url?: string | null;
  homepage_url?: string | null;
  google_scholar_url?: string | null;
  openalex_id?: string | null;
  dblp_url?: string | null;
  semantic_scholar_id?: string | null;
  research_text?: string | null;
  research_summary?: string | null;
  recruiting_signal: 'positive' | 'negative' | 'unknown';
  recruiting_evidence_url?: string | null;
  recruiting_evidence_text?: string | null;
  source_confidence: number;
  photo_url?: string | null;
  photo_source_url?: string | null;
  photo_confidence?: number | null;
  photo_license_note?: string | null;
  created_at: string;
  updated_at: string;
  extra?: Record<string, any>;
}

export interface GetProfessorResponse {
  professor: ProfessorDetail;
  publications: PublicationResponse[];
}

export interface UniversityStat {
  university: string;
  professor_count: number;
  publication_count: number;
}

export interface ExplorerStatsResponse {
  database_path: string;
  professor_count: number;
  publication_count: number;
  university_count: number;
  professors_with_email: number;
  professors_with_homepage: number;
  professors_with_publications: number;
  universities: UniversityStat[];
}

export interface ListUniversitiesResponse {
  universities: string[];
}

export interface StudentProfile {
  name: string;
  photo_url?: string;
  email?: string;
  background?: string;
  academic_background?: string;
  research_interests: string;
  interest_tags?: string[];
  interests_free_text?: string;
  target_degree: string;
  target_department?: string;
  highest_degree?: {
    degree?: string;
    field?: string;
    institution?: string;
    year?: string | number;
  };
  preferred_departments?: string[];
  preferred_locations?: string[];
  preferred_universities?: string[];
  limit: number;
  shortlist_limit: number;
  threshold_percent?: number;
  minimum_results?: number;
  rerank: boolean;
  include_publication_evidence?: boolean;
  max_abstracts_per_professor?: number;
}

export interface MatchEvidence {
  matched_terms: string[];
  tags: string[];
  publications: Array<{
    id?: number | null;
    title: string;
    year?: number | null;
    url?: string | null;
    venue?: string | null;
    source?: string | null;
    match_confidence?: number | null;
    similarity_score?: number | null;
    matched_terms: string[];
    abstract?: string | null;
    abstract_snippet?: string | null;
  }>;
  recruiting_status: string;
  recruiting_evidence_url?: string | null;
  recruiting_evidence_text?: string | null;
  risks: string[];
}

export interface MatchScore {
  professor_id: number;
  professor_name: string;
  title?: string | null;
  university: string;
  department: string;
  research_summary?: string | null;
  professor_url?: string | null;
  photo_url?: string | null;
  photo_source_url?: string | null;
  photo_confidence?: number | null;
  total_score: number;
  research_text_similarity: number;
  recent_publication_similarity: number;
  recruiting_signal_score: number;
  department_title_relevance: number;
  location_preference_fit: number;
  fts_score: number;
  metadata_boost: number;
  explanation: string;
  evidence: MatchEvidence;
  llm_rerank_score?: number | null;
  llm_rerank_reason?: string | null;
  risks_uncertainties: string[];
  suggested_outreach_angle?: string | null;
  rerank_applied: boolean;
}

export interface MatchThresholdSettings {
  threshold_percent: number;
  minimum_results: number;
}

export interface MatchMetadata {
  threshold_percent: number;
  minimum_results: number;
  total_candidates: number;
  above_threshold_count: number;
  returned_count: number;
  fallback_top_results_used: boolean;
}

export interface MatchResponse {
  student: StudentProfile;
  matches: MatchScore[];
  shortlist_size: number;
  rerank_applied: boolean;
  rerank_model?: string | null;
  notes: string[];
  metadata?: MatchMetadata | null;
}

export interface LocalUser {
  name: string;
  email: string;
  createdAt: string;
  role?: string;
  photo_url?: string;
}

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  user: AuthUser;
}

export interface UserStateResponse {
  student_profile?: StudentProfile | null;
  last_match_response?: MatchResponse | null;
  saved_professor_ids: number[];
  tracker_rows: any[];
}

export interface IndexedDepartment {
  university: string;
  department: string;
  professor_count: number;
  publication_count: number;
}

export interface AgenticJobGroups {
  ongoing: any[];
  ready_to_publish: any[];
  completed: any[];
}

export interface ScanJob {
  id: number;
  status: string;
  job_type: string;
  source: string;
  input_payload: { items?: Array<Record<string, any>> };
  settings: Record<string, any>;
  total_tasks: number;
  queued_tasks: number;
  running_tasks: number;
  succeeded_tasks: number;
  failed_tasks: number;
  canceled_tasks: number;
  progress_percent: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  heartbeat_at?: string | null;
}

export interface ScanTask {
  id: number;
  scan_job_id: number;
  status: string;
  task_type: string;
  university: string;
  department: string;
  faculty_url: string;
  attempt_count: number;
  max_attempts: number;
  locked_by?: string | null;
  locked_until?: string | null;
  last_error?: string | null;
  result_summary: Record<string, any>;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface ScanResult {
  id: number;
  scan_job_id: number;
  scan_task_id?: number | null;
  status: string;
  professor_name: string;
  university: string;
  department: string;
  title?: string | null;
  email?: string | null;
  profile_url?: string | null;
  homepage_url?: string | null;
  research_summary?: string | null;
  source_confidence: number;
  source_urls: string[];
  publications_payload: Array<Record<string, any>>;
  qa_issues: Array<Record<string, any>>;
  import_status: string;
  imported_professor_id?: number | null;
}

export interface ScanLog {
  id: number;
  scan_job_id: number;
  scan_task_id?: number | null;
  level: string;
  event_type: string;
  message: string;
  payload: Record<string, any>;
  created_at: string;
}

export interface AdminScanPaths {
  validation?: string | null;
  scan_manifest?: string | null;
  openrouter_audit?: string | null;
  raw?: string | null;
  raw_manifest?: string | null;
  processed_professors?: string | null;
  processed_publications?: string | null;
}

export interface AdminScanIssueBreakdown {
  by_severity?: Record<string, number>;
  by_code?: Record<string, number>;
  by_field?: Record<string, number>;
  by_record_type?: Record<string, number>;
  missing_required_fields?: Record<string, number>;
}

export interface AdminScanSummary {
  id: string;
  date?: string | null;
  school_slug: string;
  university: string;
  department?: string | null;
  adapter_name?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  run_status?: string | null;
  qa_status?: string | null;
  db_import_allowed: boolean;
  professors: number;
  publications: number;
  duplicates: number;
  errors: number;
  warnings: number;
  total_issues: number;
  openrouter_status?: string | null;
  openrouter_model?: string | null;
  issue_breakdown: AdminScanIssueBreakdown;
  issues_preview: Array<Record<string, any>>;
  duplicate_candidates: Array<Record<string, any>>;
  validation_filename: string;
  manifest_filename: string;
  openrouter_audit_filename: string;
  paths: AdminScanPaths;
}

export interface AdminScanDetail extends AdminScanSummary {
  validation?: Record<string, any> | null;
  scan_manifest?: Record<string, any> | null;
  openrouter_audit?: Record<string, any> | null;
  professors_preview?: Array<Record<string, any>>;
  publications_preview?: Array<Record<string, any>>;
}

export interface ListAdminScansResponse {
  scans: AdminScanSummary[];
}
