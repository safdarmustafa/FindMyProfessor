# Frontend Architecture

> Part of the [FindMyProfessor Architecture Documentation](../ARCHITECTURE.md).

## 1. Stack

React `18.3.1`, `react-router-dom 6.26.0`, `@supabase/supabase-js 2.45.0`, built with **Vite 5.4**, tested with **Vitest 2.1.9** + Testing Library (`frontend/package.json`). No CSS framework — hand-written CSS + inline styles. `frontend/vite.config.js` proxies backend path prefixes (`/api`, `/profile`, `/cv`, `/matching`, `/professors`, `/universities`, `/outreach/drafts`, `/outreach/cv-versions`, `/gmail/*`) to `http://localhost:8000` in dev.

## 2. Route table

Defined in `frontend/src/App.jsx:20-35` (`BrowserRouter`).

| Path | Component | Gated? |
|---|---|---|
| `/` | `Home` | No |
| `/team` | `Team` | No |
| `/login` | `Login` | No |
| `/onboarding` | `Onboarding` | Soft — needs `fmp_profile_id` in `localStorage` |
| `/matches` | `Matches` | Soft — shows `EmptyState` if no `profileId` |
| `/matches/:id` | `ProfessorDetail` | No explicit gate |
| `/outreach/compose/:professorId` | `EmailCompose` | Soft — needs `profileId` + confirmed profile |
| `/outreach/history` | `OutreachHistory` | Soft — needs `profileId` |
| `/outreach/gmail-connected` | `GmailConnected` | No |
| `/outreach/gmail-callback-error`, `/gmail-error` | `GmailError` | No |
| `/privacy` | `Privacy` | No |
| `/terms` | `Terms` | No |
| `*` | redirect to `/` | N/A |

**Important finding: there is no hard route guard anywhere.** No page uses `useAuth()` to redirect an unauthenticated visitor to `/login`. "Gating" is entirely a soft, presence-based check on a `localStorage` value that has nothing to do with whether a Supabase session exists — a user could, in principle, clear their Supabase session but keep `fmp_profile_id` in `localStorage` and continue using pages that only check for the latter. `useAuth()` is otherwise consumed only by `AppShell` (`frontend/src/components/AppShell/AppShell.jsx:78`) to render the account menu.

## 3. Authentication on the frontend

**Google OAuth via Supabase Auth, exclusively** — no email/password, no magic link.

```js
// frontend/src/pages/Login.jsx:64-67
supabase.auth.signInWithOAuth({
  provider: 'google',
  options: { redirectTo: (VITE_SITE_URL || 'http://localhost:5173') + '/login' }
})
```

`Login.jsx:41-58` checks `getSession()` on mount and subscribes to `onAuthStateChange`, navigating to `/onboarding` on `SIGNED_IN`. `useAuth.js` is a general-purpose session hook wrapping the same two calls; its `signOut()` also clears `fmp_profile_id` from `localStorage` (`useAuth.js:32-36`).

**Minor finding:** the Supabase client (`frontend/src/lib/supabase.js:3-6`) is constructed with a **hardcoded URL and anon key directly in source**, not read from `import.meta.env` — unusual, since the Supabase anon key is meant to be safely public, but it does mean the frontend build doesn't actually need Supabase-related env vars at all; only `VITE_API_URL` and `VITE_SITE_URL` are read from the environment anywhere in the frontend.

## 4. How identity reaches the backend

Every backend call goes through one helper, and this is the single most important fact about the frontend/backend boundary:

```js
// frontend/src/services/api.js:23-51 (apiFetch)
export async function apiFetch(url, options = {}) {
  const profileId = getProfileId();               // localStorage['fmp_profile_id']
  const headers = { ...options.headers };
  if (profileId) headers['X-Profile-Id'] = profileId;

  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (token) headers['Authorization'] = `Bearer ${token}`;

  return fetch(apiUrl(url), { ...options, headers });
}
```

**Both headers are attached on every single request, unconditionally when available.** The Supabase session token is re-fetched fresh from `getSession()` on every call (not cached client-side), so it's always current. See [Auth vs Authorization](auth-and-authorization.md) for exactly how the backend reconciles these two signals.

## 5. Gmail connection state

`useGmailStatus.js` (`frontend/src/hooks/useGmailStatus.js:1-25`) does a **one-time fetch on mount** — no polling, no shared context/cache. `AppShell`, `GmailWidget`, and `EmailCompose` each mount their own independent instance of this hook, so the connect status is fetched multiple times per page load. Freshness after a connect/disconnect action depends on an explicit `refetch()` call or a full page remount — there's no global state store keeping this in sync automatically.

## 6. Page-by-page walkthrough

- **`Onboarding.jsx`** — 3-step CV flow: (1) drag/drop upload → `uploadCV()` → `POST /cv/upload` as `FormData`, stores the returned `profile_id`; (2) review/edit the extracted profile → `updateProfile()` → `PUT /profile`; (3) confirm → `confirmProfile()` → `POST /profile/confirm`.
- **`Matches.jsx`** — filter UI (university, min score, email-only, opportunity type/status, mode) maps directly to `fetchMatches()` query params against `GET /matching/professors`; a separate client-side text search further narrows the already-fetched result set without another backend call.
- **`ProfessorDetail.jsx`** — fetches `GET /professors/{id}` for the detail view, plus a non-blocking `GET /matching/professors?limit=100` purely to locate this professor's score/evidence object client-side — there is no single-professor match endpoint on the backend.
- **`EmailCompose.jsx`** (966 lines, the most complex page) — on mount: restores a pending draft (from an OAuth-return intent, or `listDrafts()`), fetches the student profile, the target professor, and (non-blocking) the match list; once a draft exists, also lists CV versions. Generate → `POST /outreach/drafts/generate`. Save → `PATCH /outreach/drafts/{id}`. Attach CV → `POST /outreach/drafts/{id}/attach-cv`. Connect Gmail → auto-saves the draft, then does a full-page redirect to `GET /gmail/connect`. Preview → auto-saves if needed, then `GET /outreach/drafts/{id}/preview`. Send → `POST /outreach/drafts/{id}/send`.
- **`OutreachHistory.jsx`** — lists past drafts/sends for the profile.
- **`GmailConnected.jsx` / `GmailError.jsx`** — receive the backend's OAuth redirect; see [Gmail OAuth §10](gmail-oauth.md#10-frontend-callback-handling).

## 7. API-call inventory (cross-referenced against backend routers)

Every frontend service call was cross-checked path-for-path against `backend/app/routers/*.py` and the router registration in `backend/app/main.py:59-67` — **no orphaned frontend calls were found.** One asymmetry worth noting: `backend/app/routers/departments.py` and `labs.py` exist and are registered, but no frontend service calls their endpoints directly — the frontend reaches labs/departments only indirectly, through the professor/university endpoints. **NOT VERIFIED** whether this is simply unused-for-now surface area or reserved for a future drill-down UI.

See the [API Map](api-map.md) for the full endpoint reference.

## 8. Frontend build in production

Root `.gitignore` excludes `backend/app/static/react/`, implying the intended production setup copies the frontend's Vite build output into that path for FastAPI to serve directly — but no CI/build script performing that copy exists in this repository, so the actual production build/deploy mechanism is **NOT VERIFIED FROM CURRENT CODEBASE**. See [Deployment](deployment.md).
