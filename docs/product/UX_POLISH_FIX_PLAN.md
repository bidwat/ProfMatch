# UX Polish Fix Plan — 2026-05-06

Status legend: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

This checklist tracks the follow-up UX/auth/rate-limit issues reported after the main UX cleanup.

Overall status: `DONE` for this pass.

## Root Causes

- Rate-limit errors were caused by a strict per-IP `/api/*` limiter combined with admin/status HTTP polling and repeated Discover/filter requests from the same local browser/IP.
- Frontend errors displayed raw JSON because the API helper threw raw response text instead of parsing structured backend errors.
- Protected pages hydrated private data from `localStorage` before confirming an active backend session.
- Saved preview used the first professor page and then filtered locally, so saved IDs outside that page showed an empty preview despite a nonzero saved count.

## Checklist

### Profile photo upload
- [x] Replace Photo URL input with upload UI.
- [x] Validate JPG/JPEG/PNG only in frontend.
- [x] Resize/crop uploaded image to 256x256 before storing.
- [x] Store generated small image data in profile state/local backend state.
- [x] Remove user-facing photo URL copy.

### Common confirmation modals
- [x] Create reusable modal confirmation component with variants: default, warning, danger.
- [x] Replace Profile delete `window.confirm`.
- [x] Replace Admin delete `window.confirm`.
- [x] Replace Admin refresh `window.prompt` with a modal/text confirmation.
- [x] Replace remaining frontend `alert/confirm/prompt` usage.

### Rate limit and polling
- [x] Parse and display friendly API errors instead of raw JSON.
- [x] Raise local read/status rate-limit tolerance and exempt low-risk status reads.
- [x] Stop aggressive dashboard polling; use manual refresh/dashboard interval only when needed.
- [x] Pause residual scan-status polling when tab is hidden.
- [x] Add SSE-based agentic job status stream for `/admin/onboarding?job=...`.

### Auth/local storage safety
- [x] Add guarded authenticated routes in AppShell.
- [x] Clear private local state on auth failure/logout.
- [x] Prevent protected pages from rendering private localStorage data when unauthenticated.
- [x] Ensure backend-protected APIs still require valid sessions.

### Filters/search/sort components
- [x] Create reusable SearchBox.
- [x] Create reusable MultiSelectFilter with ellipsis and scrollable dropdown.
- [x] Create reusable FilterSortBar.
- [x] Create reusable Chip/ChipInput display.
- [x] Center/fix filter layout.

### Matches page polish
- [x] Make tag filter multi-select.
- [x] Add clear “Sort by” label.
- [x] Remove duplicate Update Profile button outside the profile card.
- [x] Always show tags as chips where tags are visible.

### Discover/Saved polish
- [x] Make tags multi-select.
- [x] Make universities multi-select.
- [x] Remove position filter.
- [x] Debounce search/filter calls.
- [x] Keep dropdown items ellipsized with max width and max height.

### Profile tag/multi-input polish
- [x] Areas of interest tags use chips and multi-select/free add.
- [x] Preferred universities use multi-input/free add.

### Admin requested items
- [x] Add admin endpoint to list recommendation requests.
- [x] Show requested universities/departments/faculty URLs in Admin Dashboard.

### Dashboard saved preview bug
- [x] Fetch saved preview by saved professor IDs instead of filtering the first directory page.

### Auth pages
- [x] Add Back to home on Sign in.
- [x] Add Back to home on Sign up.

### Professor detail sticky card
- [x] Add sticky/compact professor card/header behavior while scrolling.

### QA
- [x] Backend tests for recommendation listing and auth/rate limit behavior.
- [x] Frontend tests/build for auth guard/profile shell still pass.
- [x] Backend tests pass.
- [x] `make test` passes.
- [x] `make qa` passes or documented.

## Evidence

- Frontend Jest: `7 passed`.
- Frontend production build: PASS with existing warnings (`<img>` in admin onboarding, `fetchScans` hook dependency in admin scans).
- Backend pytest: `27 passed`.
- `make test`: PASS (`22` scraper tests and `27` backend tests).
- `make qa`: PASS (`22` scraper tests, `27` backend tests, `7` frontend Jest tests, frontend build, and `3` Playwright tests).

## Notes

- Profile photos are client-resized to a small 256×256 data URL and saved with the profile state. A binary authenticated upload endpoint can be added later if profile images need file storage instead of local-first state storage.
- Agentic job detail uses SSE. The older scan-artifact page keeps a low-frequency, hidden-tab-paused status check because it is a secondary admin artifact page.
