# API Map

> Part of the [FindMyProfessor Architecture Documentation](../ARCHITECTURE.md). Every row is grounded in a specific router file. Where a detail wasn't directly confirmed during this research pass, it's marked NOT VERIFIED rather than guessed.

## Universities

| | |
|---|---|
| **GET** `/universities` | List all universities. **Input:** none. **Auth:** none. **Service:** `services/universities.py::list_universities`. **Output:** `UniversityListResponse`. |
| **GET** `/universities/{university_id}` | Get one university. **Auth:** none. **Service:** `get_university`. **Errors:** 404 if not found. |
| **GET** `/universities/{university_id}/departments` | List a university's departments. **Auth:** none. **Service:** `list_departments_for_university`. **Errors:** 404 if university not found. |

_Router: `backend/app/routers/universities.py`._

## Departments

| | |
|---|---|
| **GET** `/departments/{department_id}` | Get one department. **Auth:** none. **Errors:** 404. |
| **GET** `/departments/{department_id}/labs` | List a department's labs. **Auth:** none. **Errors:** 404 if department not found. |

_Router: `backend/app/routers/departments.py`. Confirmed not called directly by the frontend service layer — see [Frontend §7](frontend.md#7-api-call-inventory-cross-referenced-against-backend-routers)._

## Labs

| | |
|---|---|
| **GET** `/labs/{lab_id}` | Get one lab. **Auth:** none. **Errors:** 404. |
| **GET** `/labs/{lab_id}/professors` | List professors in a lab. **Auth:** none. **Errors:** 404 if lab not found. |

_Router: `backend/app/routers/labs.py`. Same "not called directly by frontend" note as Departments._

## Professors

| | |
|---|---|
| **GET** `/professors/search` | Search/filter professors. **Input (query params):** `q, research_area, country, university_id, department_id, recruiting, internship, ra, masters, phd, limit (1-100, default 50)`. **Auth:** none. **Service:** `services/professors.py::search_professors`. **Output:** `ProfessorSearchResponse`. |
| **GET** `/professors/{professor_id}` | Full professor detail (with lab/department/university/research areas joined). **Auth:** none. **Errors:** 404. |
| **GET** `/professors/{professor_id}/research-areas` | List a professor's tagged research areas. **Auth:** none. **Errors:** 404 if professor not found. |

_Router: `backend/app/routers/professors.py`._

## CV

| | |
|---|---|
| **POST** `/cv/upload` | Upload a CV file, triggering validation, storage, and extraction. **Input:** multipart file + optional existing `profile_id`. **Auth:** `auth.resolve_identity` — can create a new profile if none exists. **Service:** `services/cv.py::upload_and_parse`. **Output:** `CvUploadResponse`. **Errors:** 413 (too large), 415 (unsupported type). |
| **GET** `/cv/{cv_id}` | Fetch one CV version's metadata + extracted profile. **Auth:** optional `profile_id` scoping. **Errors:** 404. |
| **POST** `/cv/{cv_id}/parse` | Re-run extraction on an already-stored file without re-uploading. **Service:** `services/cv.py::parse_cv`. **Errors:** 400 if the stored file is missing. |

_Router: `backend/app/routers/cv.py`. Full pipeline detail: [CV Pipeline](cv-pipeline.md)._

## Profile

| | |
|---|---|
| **GET** `/profile` | Get the current profile's active CV + extracted data. **Auth:** `auth.require_profile_id` (401 if none, 404 if authenticated with no profile yet). **Service:** `cv_service.get_active_profile`. |
| **PUT** `/profile` | Update the extracted-profile fields before confirming. **Body:** `StudentProfileUpdate`. **Auth:** `require_profile_id`. **Service:** `cv_service.update_extracted_profile`. |
| **POST** `/profile/confirm` | Lock in the extracted profile, normalizing it into `profiles`/`student_projects`/`student_publications`/`student_research_areas`. **Auth:** `require_profile_id`. **Service:** `cv_service.confirm_profile`. **Errors:** 400 if no CV or if the active CV's last parse failed. |

_Router: `backend/app/routers/profile.py`._

## Matching

| | |
|---|---|
| **GET** `/matching/professors` | Rank professors by research fit and/or opportunity fit. **Input (query):** `mode (research\|opportunity\|both), limit (1-100, default 25), university_id, min_score (0-100), email_only, opportunity_type, opportunity_status`. **Auth:** `require_profile_id`. **Errors:** 400 if the profile's CV isn't confirmed. **Full detail:** [Matching Engine](matching-engine.md). |

_Router: `backend/app/routers/matching.py`._

## Outreach

| | |
|---|---|
| **POST** `/outreach/drafts/generate` | Generate a new email draft for a professor. **Body:** `professor_id, email_type, opportunity_id?`. **Auth:** `require_profile_id`. **Errors:** 400 (CV not confirmed / opportunity closed), 404 (professor not found). |
| **PATCH** `/outreach/drafts/{draft_id}` | Edit subject/body and/or set status. **Body:** `SaveDraftRequest{subject, body, status}`. **Auth:** ownership-checked against `profile_id`. |
| **GET** `/outreach/drafts/{draft_id}/preview` | Preview the rendered send (validates sendability without sending). |
| **POST** `/outreach/drafts/{draft_id}/attach-cv` | Attach a specific `cv_version_id` to the draft. **Errors:** validates CV ownership + file existence. |
| **GET** `/outreach/cv-versions` | List the profile's CV versions (for the attach-CV picker). |
| **POST** `/outreach/drafts/{draft_id}/send` | Send the draft via Gmail. **Body:** `SendDraftRequest{confirmed: bool}` (required). **Errors:** 400 (not confirmed / validation failure), 409 (already sending — CAS conflict), 401 (Gmail not connected/token invalid), 502 (Gmail API error). **Full detail:** [Gmail Send](gmail-send.md). |
| **GET** `/outreach/history` | List past drafts/sends for the profile. |

_Router: `backend/app/routers/outreach.py`. Full detail: [Email Generation](email-generation.md)._

## Gmail

| | |
|---|---|
| **GET** `/gmail/connect` | Begin the OAuth handshake. **Input:** `profile_id` (header or query — see [Gmail OAuth §1](gmail-oauth.md#1-connect-endpoint)), optional `return_to`. **Auth:** cannot use a verified session (full-page navigation); accepts `X-Profile-Id`/query directly. **Response:** 302 to Google. |
| **GET** `/gmail/callback` | OAuth redirect target. **Input:** `code`, `state` (or `error`). **Response:** 302 to a frontend SPA route with success or `?reason=...` on failure. |
| **GET** `/gmail/status` | Connection status for the current profile. **Auth:** `require_profile_id`. **Output:** `{connected, email}` only — never tokens (`backend/app/routers/gmail.py:231-237`). |
| **POST** `/gmail/disconnect` | Disconnect Gmail: best-effort token revocation with Google, clears stored tokens, preserves historical sent-draft records (`backend/app/routers/gmail.py:244-255`). **Auth:** `require_profile_id`. **Output:** `{disconnected: true, message}`. |

_Router: `backend/app/routers/gmail.py`. Full OAuth detail: [Gmail OAuth](gmail-oauth.md)._

## Health/root

| | |
|---|---|
| **GET** `/` | API identity — links to `/docs` and `/health`. |
| **GET** `/health` | Pings the `universities` table via Supabase. **Errors:** 503 if the database is unreachable. |

_`backend/app/main.py`._
