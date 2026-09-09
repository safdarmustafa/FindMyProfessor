(function (root) {
  const PROFILE_STORAGE_KEY = "fmp_profile_id";

  function getProfileId() {
    try { return localStorage.getItem(PROFILE_STORAGE_KEY); } catch (e) { return null; }
  }

  function headers(profileId, extra) {
    const h = Object.assign({ "Content-Type": "application/json" }, extra || {});
    if (profileId) h["X-Profile-Id"] = profileId;
    return h;
  }

  async function fetchJson(url, opts) {
    const response = await fetch(url, opts);
    const data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      const detail = data.detail;
      const msg = typeof detail === "string" ? detail : "Request failed.";
      const err = new Error(msg);
      err.status = response.status;
      throw err;
    }
    return data;
  }

  // ── Phase 5 ────────────────────────────────────────────────────────────
  function generateDraft(profileId, professorId, emailType, opportunityId) {
    return fetchJson("/outreach/drafts/generate", {
      method: "POST",
      headers: headers(profileId),
      body: JSON.stringify({
        professor_id: professorId,
        email_type: emailType || "research",
        opportunity_id: opportunityId || null
      })
    });
  }

  function saveDraft(profileId, draftId, subject, body, status) {
    return fetchJson("/outreach/drafts/" + encodeURIComponent(draftId), {
      method: "PATCH",
      headers: headers(profileId),
      body: JSON.stringify({ subject: subject, body: body, status: status || "ready" })
    });
  }

  function getDraft(profileId, draftId) {
    return fetchJson("/outreach/drafts/" + encodeURIComponent(draftId), {
      headers: headers(profileId, { "Content-Type": undefined })
    });
  }

  // ── Phase 6 — CV ───────────────────────────────────────────────────────
  function listCvVersions(profileId) {
    return fetchJson("/outreach/cv-versions", {
      headers: headers(profileId, { "Content-Type": undefined })
    });
  }

  function attachCv(profileId, draftId, cvVersionId) {
    return fetchJson("/outreach/drafts/" + encodeURIComponent(draftId) + "/attach-cv", {
      method: "POST",
      headers: headers(profileId),
      body: JSON.stringify({ cv_version_id: cvVersionId })
    });
  }

  // ── Phase 6 — Gmail status ─────────────────────────────────────────────
  function getGmailStatus(profileId) {
    return fetchJson("/gmail/status", {
      headers: headers(profileId, { "Content-Type": undefined })
    });
  }

  function disconnectGmail(profileId) {
    return fetchJson("/gmail/disconnect", {
      method: "POST",
      headers: headers(profileId)
    });
  }

  function gmailConnectUrl(profileId) {
    return "/gmail/connect?profile_id=" + encodeURIComponent(profileId || "");
  }

  // ── Phase 6 — Preview & Send ───────────────────────────────────────────
  function getSendPreview(profileId, draftId) {
    return fetchJson("/outreach/drafts/" + encodeURIComponent(draftId) + "/preview", {
      headers: headers(profileId, { "Content-Type": undefined })
    });
  }

  function sendDraft(profileId, draftId) {
    return fetchJson("/outreach/drafts/" + encodeURIComponent(draftId) + "/send", {
      method: "POST",
      headers: headers(profileId),
      body: JSON.stringify({ confirmed: true })
    });
  }

  // ── Phase 6 — History ─────────────────────────────────────────────────
  function listHistory(profileId) {
    return fetchJson("/outreach/history", {
      headers: headers(profileId, { "Content-Type": undefined })
    });
  }

  root.FMPOutreachApi = {
    getProfileId: getProfileId,
    // Phase 5
    generateDraft: generateDraft,
    saveDraft: saveDraft,
    getDraft: getDraft,
    // Phase 6 — CV
    listCvVersions: listCvVersions,
    attachCv: attachCv,
    // Phase 6 — Gmail
    getGmailStatus: getGmailStatus,
    disconnectGmail: disconnectGmail,
    gmailConnectUrl: gmailConnectUrl,
    // Phase 6 — Preview & Send
    getSendPreview: getSendPreview,
    sendDraft: sendDraft,
    // Phase 6 — History
    listHistory: listHistory
  };
})(typeof window !== "undefined" ? window : globalThis);
