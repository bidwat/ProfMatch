# UX Cleanup Plan — Professor Match

Status legend: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

This document is the working checklist for the complete UX cleanup requested on 2026-05-06. It is the source of truth while implementation proceeds and must be updated after each slice.

## Goals

- Separate unauthenticated marketing/auth pages from the authenticated product shell.
- Replace sidebar navigation with a top navigation bar for signed-in users.
- Make Profile the primary academic-profile and onboarding page.
- Re-run matching after login so results reflect the latest professor database.
- Standardize professor list rows across Matches, Discover, and Saved.
- Add a recommendation request flow for missing universities/departments.
- Consolidate admin tools into `/admin` for admin users only.

## Global Guardrails

- No technical implementation details are shown to end users.
- Frontend must not invent unsupported professor/recruiting fields.
- Recruiting status remains `recruiting`, `not recruiting`, or `unknown`, and positive/negative claims require evidence.
- Admin refresh/import workflows remain QA-gated; existing indexed data is not destructively replaced without explicit confirmation.
- SQLite remains the local development database.

---

## Implementation Slices

### Slice 1 — Public/Auth Shell and Navigation

Status: `DONE`

- [x] Landing page has no sidebar.
- [x] Login page has no sidebar.
- [x] Signup page has no sidebar.
- [x] Logged-in users visiting landing page redirect to Home.
- [x] Authenticated pages use a top nav:
  - Left: logo/name.
  - Middle: Home, Matches, Discover, Saved.
  - Right: FirstName LastName/Profile, Sign Out.
- [x] Remove sidebar from end-user flows.
- [x] Keep admin access available only to admin users.

Affected files expected:

- `apps/frontend/app/layout.tsx`
- `apps/frontend/components/AppShell.tsx`
- `apps/frontend/app/page.tsx`
- `apps/frontend/app/signin/page.tsx`
- `apps/frontend/app/signup/page.tsx`
- `apps/frontend/lib/api.ts`

### Slice 2 — Landing, Login, Signup UX Cleanup

Status: `DONE`

#### Landing Page

- [x] Does not list university names.
- [x] Removes “How it works” section.
- [x] Adds SVGs/images/animations.
- [x] Provides clean CTA paths to sign in/sign up.

#### Login / Signup

- [x] Remove technical copy such as HttpOnly/local backend/session implementation details.
- [x] Signup routes to Profile setup.
- [x] Login routes to Home if profile exists, otherwise Profile.
- [x] After login, always re-run match logic when a saved academic profile exists.

### Slice 3 — Profile Contract and Profile Page

Status: `DONE`

- [x] Add banner: “Don’t See Who You’re Looking for? Add Universities and Departments” linking to Recommend page.
- [x] Profile form supports:
  - [x] Name.
  - [x] Photo.
  - [x] Email.
  - [x] Target Degree.
  - [x] Department.
  - [x] Highest Degree Attained: degree, field, institution, year.
  - [x] Academic Background free text.
  - [x] Areas of Interest: tags + free text.
  - [x] Preferred Universities / Locations.
- [x] Update Profile and Match button is enabled only when form changed.
- [x] Update Profile and Match saves profile and reruns matching.
- [x] Delete Account button appears small at bottom and asks for confirmation.

Backend/API needs:

- [x] Validate expanded profile fields.
- [x] Add or update endpoint to save profile.
- [x] Add match rerun endpoint using saved profile.
- [x] Add account deletion endpoint.

### Slice 4 — Home Page

Status: `DONE`

- [x] Profile section displays Target Degree, Academic Background, and Interests.
- [x] Edit Academic Profile button links to Profile.
- [x] Desktop layout splits Matches and Saved panels side-by-side.
- [x] Matches panel shows:
  - [x] Number of professors matched.
  - [x] Limited card/list preview.
  - [x] “View All Matched Professors” button.
- [x] Saved panel shows:
  - [x] Number of professors saved.
  - [x] Limited preview or placeholder if none saved.
  - [x] “View All Saved Professors” button.

### Slice 5 — Shared Professor List Row

Status: `DONE`

Create one reusable row/card component for Matches, Discover, and Saved.

Common behavior:

- [x] One professor per row.
- [x] Image, name, and expand button can expand/open details.
- [x] Save button works consistently.
- [x] Name/photo links preserve navigation origin for detail page back button.

Match variant:

- [x] Image, name, position, university.
- [x] Match reason / why matched.
- [x] Number of matched papers.
- [x] No visible tags.

Discover/Saved variant:

- [x] Image, name, position, university.
- [x] Tags.
- [x] AI summary excerpt only.
- [x] `X papers indexed`.
- [x] Save button.

### Slice 6 — Matches Page

Status: `DONE`

- [x] Empty if profile not set.
- [x] Empty state prompts user to update profile.
- [x] Small profile section with update profile button.
- [x] Sticky controls:
  - [x] Sort by Name asc/desc.
  - [x] Sort by Match asc/desc.
  - [x] Filter by Tags dropdown.
  - [x] Search all properties.
- [x] Lazy loading instead of pagination.
- [x] Uses shared professor list row in Match variant.

Backend/API needs:

- [x] Authenticated match list endpoint or state hydration supports sorting/filtering/search/lazy loading.
- [x] Match rows hydrate latest professor data.

### Slice 7 — Discover Page

Status: `DONE`

- [x] Sticky filter section.
- [x] Filter by tags dropdown with search.
- [x] Filter by universities dropdown with search.
- [x] Filter by position dropdown with search.
- [x] Filter by department dropdown with search.
- [x] Filter by recruiting status: recruiting, not recruiting, unknown.
- [x] Search works on all fields.
- [x] Sort by name, university name, recruiting status; asc/desc.
- [x] Lazy loading instead of pagination.
- [x] Uses shared professor list row in Discover variant.

Backend/API needs:

- [x] Professor list filters/sorts/lazy loading.
- [x] Filter facets endpoint or equivalent values from existing data.

### Slice 8 — Saved Professors Page

Status: `DONE`

- [x] Same filters as Discover.
- [x] Additional sort by Recently Saved asc/desc.
- [x] Uses shared professor list row in Saved variant.
- [x] Helpful empty state.

Backend/API needs:

- [x] Saved professor timestamps or compatible saved order.
- [x] Save/unsave/list endpoints or robust auth state wrappers.

### Slice 9 — Recommend University/Professor Page

Status: `DONE`

- [x] New recommendation page.
- [x] Short prompt asking user to recommend university and department.
- [x] Form fields:
  - [x] University.
  - [x] Department.
  - [x] Faculty Page URL.
- [x] Frontend validation for all fields, especially URL.
- [x] Backend validation for all fields, especially URL.
- [x] After submit, show thanks state and “make another request”.

Backend/API needs:

- [x] Recommendation request model/storage.
- [x] `POST /api/recommendations` endpoint.
- [x] SSRF-safe URL validation.

### Slice 10 — Professor Detail Cleanup

Status: `DONE`

- [x] Keep current useful information.
- [x] Back button returns to originating page/context.
- [x] Remove evidence tab from student UI.
- [x] Keep source/evidence data in backend for audit/admin needs.

### Slice 11 — Admin Dashboard `/admin`

Status: `DONE`

- [x] `/admin` is available to admin users only.
- [x] Lists indexed universities/departments with professor counts.
- [x] Admin can update indexed university/department.
- [x] Update triggers agentic flow.
- [x] Old information is deleted/replaced only after confirmation inside agentic workflow.
- [x] Admin can delete indexed university/department with confirmation.
- [x] Shows ongoing workflow list.
- [x] Includes agentic scan dashboard.
- [x] Completed agents/runs appear in separate tab.
- [x] Shows ongoing and ready-to-publish agentic runs.
- [x] Remove old “runs” and “QA artifact detail” pages from primary admin UX.

Backend/API needs:

- [x] Indexed department/group counts endpoint.
- [x] Agentic jobs grouped by running/ready-to-publish/completed.
- [x] Refresh/update endpoint that stages replacement.
- [x] Delete endpoint with admin-only access.

### Slice 12 — QA and Documentation

Status: `DONE`

- [x] Frontend tests for public pages without sidebar.
- [x] Frontend tests for authenticated top nav.
- [x] Frontend tests for profile dirty-state update button.
- [x] Backend tests for match rerun after login.
- [x] Backend tests for recommendation validation.
- [x] Backend tests for saved professor timestamps/sorting if implemented.
- [x] Admin access tests.
- [x] Playwright screenshots for core pages.
- [x] `make test` passes or documented.
- [x] Frontend Jest/build passes or documented.
- [x] `make qa` passes or documented.
- [ ] Update `docs/qa-reports/latest.md` with PASS/PARTIAL/FAIL.

---

## Open Questions / Decisions

1. Should user-facing Matches route be `/matches` with `/results` redirected, or should `/results` remain internal only?
2. Should account deletion be hard delete or soft deactivate?
3. For student photo, is a URL field sufficient for MVP, or is upload required later?
4. Should recommendation requests also allow optional professor name, even though the requested form only requires university/department/faculty URL?
5. Should exact Recently Saved sorting migrate to a normalized `saved_professors` table now, or use saved order in `user_states` as an MVP compromise?

---

## Progress Log

- 2026-05-06: Created UX cleanup plan from user requirements.
- 2026-05-06: Started Slice 1 and Slice 2. Refactored `AppShell` to public/no-shell and authenticated top-nav modes; cleaned landing/signin/signup copy; removed landing university list and “How it works”; added animated SVG landing visual; signup now routes to `/profile`; login reruns matching when a saved profile exists.
- 2026-05-06: Frontend Jest tests pass (`2` suites, `4` tests). Frontend production build passes with existing warnings in admin pages (`no-img-element`, `fetchScans` hook dependency).
- 2026-05-06: Implemented Profile page cleanup with expanded academic profile form, recommendation banner, dirty-state “Update Profile and Match”, account delete confirmation, and backend soft-delete endpoint.
- 2026-05-06: Implemented Home page cleanup with profile summary plus desktop split Matches/Saved panels and limited previews.
- 2026-05-06: Implemented `/recommend` page plus `POST /api/recommendations` backend endpoint with URL validation and JSONL storage under `data/qa/recommendation_requests.jsonl`.
- 2026-05-06: Validation: frontend Jest and production build pass; backend auth tests pass (`2 passed`).
- 2026-05-06: Converted `ProfessorCard` into the shared one-row list component for Matches, Discover, and Saved. Match cards hide tags and show match reason/paper count; Discover/Saved cards show tags, summary excerpt, and indexed paper count.
- 2026-05-06: Implemented Matches sticky controls, profile summary, empty state, sorting, tag filtering, full-property search, and lazy “load more”.
- 2026-05-06: Implemented Discover and Saved sticky filters/sorts and lazy/list-row UX. Backend still needs full server-side facet/filter/cursor support for large-corpus exactness.
- 2026-05-06: Cleaned Professor Detail page: origin-aware back link via `from`, removed Evidence tab from student UI, retained compact source-backed indicators in Overview.
- 2026-05-06: Frontend production build passes after Professor Detail cleanup.
- 2026-05-06: Added backend professor facets, filters, sorting, and cursor-style lazy loading. Discover now calls server-side filters/facets.
- 2026-05-06: Added `/admin` consolidated dashboard, indexed department counts, grouped agentic jobs, staged refresh, and confirmed indexed-group deletion.
- 2026-05-06: Added backend tests for recommendation validation/storage, account deletion, professor facets/cursors, and admin indexed-department access/delete.
- 2026-05-06: Validation: `make qa` PASS. Includes scraper tests `22 passed`, backend pytest `26 passed`, frontend Jest `7 passed`, frontend production build PASS, and Playwright `3 passed`. Existing warnings: ReactDOMTestUtils act deprecation in Jest output, Next `<img>` warning in admin onboarding, missing `fetchScans` hook dependency in admin scans, and `npm audit` reports 5 vulnerabilities.
