(function (root) {
  const PROFILE_STORAGE_KEY = "fmp_profile_id";

  function getProfileId() {
    try {
      return localStorage.getItem(PROFILE_STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  function profileHeaders(profileId) {
    const headers = {};
    if (profileId) headers["X-Profile-Id"] = profileId;
    return headers;
  }

  function buildMatchingUrl(options) {
    const opts = options || {};
    const params = new URLSearchParams();
    params.set("mode", opts.mode || "research");
    params.set("limit", String(opts.limit == null ? 25 : opts.limit));
    if (opts.universityId) params.set("university_id", opts.universityId);
    if (opts.minScore != null && opts.minScore !== "" && Number(opts.minScore) > 0) {
      params.set("min_score", String(opts.minScore));
    }
    if (opts.emailOnly) params.set("email_only", "true");
    return "/matching/professors?" + params.toString();
  }

  async function fetchJson(url, profileId) {
    const response = await fetch(url, { headers: profileHeaders(profileId) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = data.detail;
      const message = typeof detail === "string" ? detail : "Unable to load research matches.";
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function fetchProfile(profileId) {
    return fetchJson("/profile", profileId);
  }

  function fetchMatches(profileId, options) {
    return fetchJson(buildMatchingUrl(options), profileId);
  }

  function fetchUniversities() {
    return fetch("/universities").then(function (response) {
      if (!response.ok) return { universities: [] };
      return response.json();
    });
  }

  function fetchProfessor(professorId) {
    return fetch("/professors/" + encodeURIComponent(professorId)).then(function (response) {
      if (!response.ok) return null;
      return response.json();
    });
  }

  root.FMPMatchingApi = {
    PROFILE_STORAGE_KEY: PROFILE_STORAGE_KEY,
    getProfileId: getProfileId,
    profileHeaders: profileHeaders,
    buildMatchingUrl: buildMatchingUrl,
    fetchProfile: fetchProfile,
    fetchMatches: fetchMatches,
    fetchUniversities: fetchUniversities,
    fetchProfessor: fetchProfessor
  };
})(typeof window !== "undefined" ? window : globalThis);
