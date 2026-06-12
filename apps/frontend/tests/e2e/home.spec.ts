import { test, expect } from '@playwright/test'

test('homepage shows ProfMatch landing', async ({ page }) => {
  await page.route('**/api/auth/me', async route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) }))
  await page.route('**/api/auth/state', async route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) }))
  await page.route('**/api/stats', async route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ professor_count: 890, publication_count: 4094, university_count: 9, professors_with_email: 382, professors_with_homepage: 608, professors_with_publications: 844, universities: [] }),
  }))
  await page.goto('/')

  await expect(page).toHaveTitle(/ProfMatch/)
  await expect(page.locator('h1')).toContainText('Find professors whose recent work matches')
  await expect(page.getByPlaceholder(/Search by professor, university, department/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Search professors' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Get started →' }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()
})

test('anonymous visitors can browse professors from the landing search', async ({ page }) => {
  await page.route('**/api/auth/me', async route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) }))
  await page.route('**/api/auth/state', async route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) }))
  await page.route('**/api/stats', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ professor_count: 1, publication_count: 1, university_count: 1, professors_with_email: 1, professors_with_homepage: 1, professors_with_publications: 1, universities: [] }) }))
  await page.route('**/api/professors/facets', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tags: ['Robotics'], universities: ['Example University'], departments: ['Computer Science'], titles: [], recruiting_signals: ['unknown'] }) }))
  await page.route('**/api/professors?**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 1, page: 1, limit: 24, next_cursor: null, professors: [{ id: 1, name: 'Grace Hopper', title: 'Professor', university: 'Example University', department: 'Computer Science', research_summary: 'Compilers and systems.', recruiting_signal: 'unknown', source_confidence: 0.9, publication_count: 4, tags: ['Robotics'], photo_url: null }] }) }))

  await page.goto('/')
  await page.getByPlaceholder(/Search by professor, university, department/).fill('robotics')
  await page.getByRole('button', { name: 'Search professors' }).click()

  await expect(page).toHaveURL(/\/professors\?q=robotics/)
  await expect(page.getByRole('heading', { name: 'Discover' })).toBeVisible()
  await expect(page.getByText('Grace Hopper')).toBeVisible()
  // Signed-out shell shows public navigation, not the authenticated tabs.
  await expect(page.getByRole('link', { name: 'Sign up' })).toBeVisible()
})

test('local signup leads to intake flow', async ({ page }) => {
  let registered = false;
  await page.route('**/api/auth/me', async route => route.fulfill(registered
    ? { status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 1, email: 'test@example.com', display_name: 'Test Applicant', role: 'student', is_active: true, created_at: '2026-04-30T00:00:00', last_login_at: null } }) }
    : { status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) }
  ))
  await page.route('**/api/auth/state', async route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) }))
  await page.route('**/api/auth/register', async route => {
    registered = true;
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ user: { id: 1, email: 'test@example.com', display_name: 'Test Applicant', role: 'student', is_active: true, created_at: '2026-04-30T00:00:00', last_login_at: null } }),
    });
  })
  await page.goto('/signup')
  await page.getByPlaceholder('Jordan Lee').fill('Test Applicant')
  await page.getByPlaceholder('you@university.edu').fill('test@example.com')
  await page.getByPlaceholder('At least 8 characters').fill('strongpass123')
  await page.getByRole('button', { name: 'Continue to profile →' }).click()
  await expect(page).toHaveURL(/\/profile/)
  await expect(page.getByRole('heading', { name: 'Academic Profile' })).toBeVisible()
})

test('design refresh covers match intake and discover filters', async ({ page }) => {
  await page.route('**/api/auth/me', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 1, email: 'test@example.com', display_name: 'Test Applicant', role: 'student', is_active: true, created_at: '2026-04-30T00:00:00', last_login_at: null } }) }))
  await page.route('**/api/auth/state', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ saved_professor_ids: [], tracker_rows: [], student_profile: null, last_match_response: null }) }))
  await page.route('**/api/professors/facets', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tags: ['Machine Learning', 'Robotics'], universities: ['Example University'], departments: ['Computer Science'], titles: ['Assistant Professor'], recruiting_signals: ['unknown'] }) }))
  await page.route('**/api/professors?**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 1, page: 1, limit: 24, next_cursor: null, professors: [{ id: 1, name: 'Ada Lovelace', title: 'Assistant Professor', university: 'Example University', department: 'Computer Science', research_summary: 'Works on machine learning for robotics.', recruiting_signal: 'unknown', source_confidence: 0.82, publication_count: 12, tags: ['Machine Learning', 'Robotics'], photo_url: null }] }) }))

  await page.goto('/match')
  await expect(page.getByRole('heading', { name: 'No academic profile yet' })).toBeVisible()
  await page.screenshot({ path: 'test-results/design-match-intake.png', fullPage: true })

  await page.goto('/professors')
  await expect(page.getByRole('heading', { name: 'Discover' })).toBeVisible()
  await expect(page.getByText('Ada Lovelace')).toBeVisible()
  await expect(page.getByText('Machine Learning', { exact: true })).toBeVisible()
  await page.screenshot({ path: 'test-results/design-discover.png', fullPage: true })
})

test('admin scan dashboard shows QA details and captures evidence screenshot', async ({ page }) => {
  const scan = {
    id: '2026-05-01_stanford-university',
    date: '2026-05-01',
    school_slug: 'stanford-university',
    university: 'Stanford University',
    department: 'Computer Science',
    adapter_name: 'stanford',
    started_at: '2026-05-01T00:00:00+00:00',
    completed_at: '2026-05-01T00:01:00+00:00',
    run_status: 'success',
    qa_status: 'ready_for_review',
    db_import_allowed: false,
    professors: 2,
    publications: 0,
    duplicates: 1,
    errors: 1,
    warnings: 1,
    total_issues: 2,
    openrouter_status: 'disabled',
    openrouter_model: null,
    issue_breakdown: {
      by_severity: { error: 1, warning: 1 },
      by_code: { missing_required_field: 1, missing_research_provenance: 1 },
      by_field: { faculty_profile_url: 1, research_text: 1 },
      by_record_type: { professor: 2 },
      missing_required_fields: { 'professor.faculty_profile_url': 1 },
    },
    issues_preview: [{ severity: 'error', code: 'missing_required_field', field_name: 'faculty_profile_url', record_type: 'professor', record_index: 0, message: 'Missing required professor field: faculty_profile_url' }],
    duplicate_candidates: [{ left_index: 0, right_index: 1, confidence: 0.91, reason: 'same profile URL' }],
    validation_filename: '2026-05-01_stanford-university_validation.json',
    manifest_filename: '2026-05-01_stanford-university_scan_manifest.json',
    openrouter_audit_filename: '2026-05-01_stanford-university_openrouter_audit.json',
    paths: { validation: 'data/qa/scraper_runs/2026-05-01_stanford-university_validation.json', scan_manifest: 'data/qa/scraper_runs/2026-05-01_stanford-university_scan_manifest.json', openrouter_audit: 'data/qa/scraper_runs/2026-05-01_stanford-university_openrouter_audit.json', raw: 'data/raw/university_scans/2026-05-01/stanford-university/roster.html', processed_professors: 'data/processed/university_scans/2026-05-01/stanford-university_professors.jsonl', processed_publications: 'data/processed/university_scans/2026-05-01/stanford-university_publications.jsonl' },
  }
  await page.route('**/api/auth/me', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 1, email: 'admin@example.edu', display_name: 'Admin User', role: 'admin', is_active: true, created_at: '2026-04-30T00:00:00', last_login_at: null } }) }))
  await page.route('**/api/admin/scans', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ scans: [scan] }) }))
  await page.route('**/api/admin/scans/*', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...scan, validation: { status: 'ready_for_review' }, scan_manifest: { import_policy: 'No SQLite import' }, openrouter_audit: { status: 'disabled' } }) }))
  await page.route('**/api/admin/adapters', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ adapters: ['stanford', 'mit'] }) }))

  await page.goto('/admin/scrapes')
  await expect(page.getByRole('heading', { name: 'University Scan Dashboard' })).toBeVisible()
  await expect(page.getByText('missing_required_field', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('professor.faculty_profile_url', { exact: true })).toBeVisible()
  await expect(page.getByText('same profile URL', { exact: true }).first()).toBeVisible()
  await page.screenshot({ path: 'test-results/admin-scans-dashboard.png', fullPage: true })
})
