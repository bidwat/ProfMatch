-- Milestone 3 durable scan job schema. Apply in Supabase before running workers in production.
CREATE TABLE IF NOT EXISTS scan_jobs (
  id SERIAL PRIMARY KEY,
  created_by_user_id INTEGER REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'queued',
  job_type TEXT NOT NULL DEFAULT 'agentic_onboarding',
  source TEXT NOT NULL DEFAULT 'admin',
  input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  settings JSONB NOT NULL DEFAULT '{}'::jsonb,
  total_tasks INTEGER NOT NULL DEFAULT 0,
  queued_tasks INTEGER NOT NULL DEFAULT 0,
  running_tasks INTEGER NOT NULL DEFAULT 0,
  succeeded_tasks INTEGER NOT NULL DEFAULT 0,
  failed_tasks INTEGER NOT NULL DEFAULT 0,
  canceled_tasks INTEGER NOT NULL DEFAULT 0,
  progress_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  heartbeat_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_scan_jobs_status_created ON scan_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS ix_scan_jobs_type_status ON scan_jobs(job_type, status);

CREATE TABLE IF NOT EXISTS scan_tasks (
  id SERIAL PRIMARY KEY,
  scan_job_id INTEGER NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'queued',
  task_type TEXT NOT NULL DEFAULT 'department_agentic_scan',
  university TEXT NOT NULL,
  department TEXT NOT NULL,
  faculty_url TEXT NOT NULL,
  input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  priority INTEGER NOT NULL DEFAULT 0,
  locked_by TEXT,
  locked_until TIMESTAMP,
  last_error TEXT,
  result_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  started_at TIMESTAMP,
  finished_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_scan_tasks_job_status ON scan_tasks(scan_job_id, status);
CREATE INDEX IF NOT EXISTS ix_scan_tasks_status_lock ON scan_tasks(status, locked_until);
CREATE INDEX IF NOT EXISTS ix_scan_tasks_priority_created ON scan_tasks(priority, created_at);

CREATE TABLE IF NOT EXISTS scan_results (
  id SERIAL PRIMARY KEY,
  scan_job_id INTEGER NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
  scan_task_id INTEGER REFERENCES scan_tasks(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'candidate',
  dedupe_key TEXT,
  professor_name TEXT NOT NULL,
  university TEXT NOT NULL,
  department TEXT NOT NULL,
  title TEXT,
  email TEXT,
  profile_url TEXT,
  homepage_url TEXT,
  google_scholar_url TEXT,
  research_summary TEXT,
  research_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  recruiting_signal TEXT NOT NULL DEFAULT 'unknown',
  source_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  source_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
  professor_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  publications_payload JSONB NOT NULL DEFAULT '[]'::jsonb,
  qa_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
  import_status TEXT NOT NULL DEFAULT 'not_imported',
  imported_professor_id INTEGER,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_scan_results_job_status ON scan_results(scan_job_id, status);
CREATE INDEX IF NOT EXISTS ix_scan_results_task_status ON scan_results(scan_task_id, status);
CREATE INDEX IF NOT EXISTS ix_scan_results_dedupe ON scan_results(dedupe_key);
CREATE INDEX IF NOT EXISTS ix_scan_results_import ON scan_results(import_status);

CREATE TABLE IF NOT EXISTS scan_logs (
  id SERIAL PRIMARY KEY,
  scan_job_id INTEGER NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
  scan_task_id INTEGER REFERENCES scan_tasks(id) ON DELETE SET NULL,
  level TEXT NOT NULL DEFAULT 'info',
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_scan_logs_job_created ON scan_logs(scan_job_id, created_at);
CREATE INDEX IF NOT EXISTS ix_scan_logs_task_created ON scan_logs(scan_task_id, created_at);
CREATE INDEX IF NOT EXISTS ix_scan_logs_level_created ON scan_logs(level, created_at);
