(function (root) {

  /* ── Utilities ─────────────────────────────────────────────────── */
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function displayPriority(priority) {
    if (!priority) return "";
    return String(priority);
  }

  function overlapChips(overlap) {
    const labels = Array.isArray(overlap) ? overlap : [];
    if (!labels.length) return "";
    return (
      '<div class="chips">' +
      labels.map(function (label) {
        return '<span class="chip">' + escapeHtml(label) + "</span>";
      }).join("") +
      "</div>"
    );
  }

  function affiliationLines(professor) {
    const lines = [];
    const university = professor && professor.university;
    const department = professor && professor.department;
    const lab = professor && professor.lab;
    if (university && university.name) lines.push(escapeHtml(university.name));
    if (department && department.name) lines.push(escapeHtml(department.name));
    if (lab && lab.name) lines.push(escapeHtml(lab.name));
    return lines.map(function (line) {
      return '<p class="meta">' + line + "</p>";
    }).join("");
  }

  function emailLabel(professor) {
    if (professor && professor.email_available) return "Outreach-ready";
    return "Discovery only";
  }

  function studentSourceLabel(source) {
    if (source === "interest") return "explicit research interest";
    if (source === "signal")   return "research signal";
    if (source === "project")  return "project";
    if (source === "publication") return "publication";
    return source || "";
  }

  function renderEvidenceItem(item) {
    if (!item || !item.type) return "";
    if (item.type === "shared_research_area") {
      return (
        "<li><strong>" + escapeHtml(item.area_name) + "</strong> \u2014 from your " +
        escapeHtml(studentSourceLabel(item.student_source)) + ".</li>"
      );
    }
    if (item.type === "artifact_research_area") {
      const kind = item.student_source === "publication" ? "publication" : "project";
      return (
        "<li><strong>" + escapeHtml(item.area_name) + "</strong> \u2014 " + kind +
        (item.artifact_title ? " \u201c" + escapeHtml(item.artifact_title) + "\u201d" : "") +
        ".</li>"
      );
    }
    if (item.type === "professor_summary_mentions_area") {
      return (
        "<li>Supporting evidence: professor\u2019s research mentions " +
        escapeHtml(item.area_name) +
        (item.excerpt ? " (\u201c" + escapeHtml(item.excerpt) + "\u201d)" : "") +
        ".</li>"
      );
    }
    if (item.type === "university_opportunity") {
      return (
        "<li>University opportunity: " + escapeHtml(item.title || "Opportunity") +
        (item.not_professor_specific === false ? "" : " (university-wide)") +
        ".</li>"
      );
    }
    return "";
  }

  function renderWhy(match) {
    const why      = (match.research_match && match.research_match.why) || [];
    const evidence = match.evidence || [];
    const whyItems      = why.map(function (l) { return "<li>" + escapeHtml(l) + "</li>"; }).join("");
    const evidenceItems = evidence.map(renderEvidenceItem).join("");
    return (
      '<div class="why">' +
        "<h3>Why you\u2019re a match</h3>" +
        (whyItems
          ? "<ul>" + whyItems + "</ul>"
          : '<p class="muted">No explanation was returned.</p>') +
        (evidenceItems ? "<h4>Evidence</h4><ul>" + evidenceItems + "</ul>" : "") +
      "</div>"
    );
  }

  function fitObject(fit) {
    if (fit == null) return null;
    if (typeof fit === "number") return { score: fit, why: [] };
    return fit;
  }

  function fitScore(match) {
    const fit = fitObject(match && match.university_opportunity_fit);
    return fit && typeof fit.score === "number" ? fit.score : null;
  }

  function statusLabel(status) {
    const key = String(status || "unknown").toLowerCase();
    if (key === "open")     return "Open";
    if (key === "upcoming") return "Upcoming";
    if (key === "closed")   return "Closed";
    return "Unknown";
  }

  function optionalField(label, value) {
    if (value == null || value === "") return "";
    return '<p class="meta">' + escapeHtml(label) + ": " + escapeHtml(value) + "</p>";
  }

  function renderOpportunity(item) {
    if (!item) return "";
    const specific = item.not_professor_specific === false;
    const closed   = String(item.status || "").toLowerCase() === "closed";
    return (
      '<div class="opp' + (closed ? " opp-closed" : "") + '">' +
        "<strong>" + (specific ? "Opportunity" : "University opportunity") + "</strong>" +
        "<p>" + escapeHtml(item.title || "Untitled") + "</p>" +
        (item.type ? '<p class="meta">' + escapeHtml(item.type) + "</p>" : "") +
        '<p class="meta">Status: ' + escapeHtml(statusLabel(item.status)) + "</p>" +
        optionalField("Deadline", item.application_deadline) +
        optionalField("Start date", item.start_date) +
        optionalField("Funding", item.funding_type) +
        optionalField("Stipend", item.stipend_amount) +
        optionalField("Tuition coverage", item.tuition_coverage) +
        optionalField("Accommodation", item.accommodation_coverage) +
        optionalField("Travel", item.travel_coverage) +
        (item.official_url
          ? '<p class="meta"><a href="' + escapeHtml(item.official_url) + '" target="_blank" rel="noopener">Official page</a></p>'
          : "") +
        (specific ? "" : '<p class="note">This opportunity is offered by the university, not specifically by this professor.</p>') +
      "</div>"
    );
  }

  function renderFitBlock(match, options) {
    const opts = options || {};
    const fit  = fitObject(match.university_opportunity_fit);
    if (!fit || typeof fit.score !== "number") return "";
    const prominent = opts.mode === "both" || opts.mode === "opportunity";
    const why = (fit.why || []).map(function (l) { return "<li>" + escapeHtml(l) + "</li>"; }).join("");
    return (
      '<div class="' + (prominent ? "fit-block" : "note") + '">' +
        (prominent
          ? '<p class="score secondary">University Opportunity Fit<br>' + escapeHtml(fit.score) + "/100</p>"
          : '<p class="note">University opportunity fit: ' + escapeHtml(fit.score) + "</p>") +
        (prominent && why ? "<ul>" + why + "</ul>" : "") +
      "</div>"
    );
  }

  function signalCount(match) {
    return (match.evidence || []).filter(function (item) {
      return item && item.student_source === "signal";
    }).length;
  }

  /* ── Score helpers ─────────────────────────────────────────────── */
  function scoreClass(score) {
    if (typeof score !== "number") return "pc-moderate";
    if (score >= 80) return "pc-strong";
    if (score >= 60) return "pc-good";
    return "pc-moderate";
  }

  function scoreAlignmentLabel(score, priority) {
    if (priority) {
      const p = String(priority).toLowerCase();
      if (p === "high")   return "Strong match";
      if (p === "medium") return "Good match";
      if (p === "low")    return "Potential match";
    }
    if (typeof score === "number") {
      if (score >= 80) return "Strong match";
      if (score >= 60) return "Good match";
      return "Potential match";
    }
    return "Match";
  }

  /* SVGs ──────────────────────────────────────────────────────────── */
  var CHECK_SM =
    '<svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">' +
    '<circle cx="5" cy="5" r="5" fill="#dcfce7"/>' +
    '<path d="M2.5 5l1.8 1.8 3-3" stroke="#16a34a" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>' +
    '</svg>';

  var INFO_SM =
    '<svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="currentColor" ' +
    'stroke-width="1.5" stroke-linecap="round" aria-hidden="true">' +
    '<circle cx="5.5" cy="5.5" r="4.5"/>' +
    '<line x1="5.5" y1="4.5" x2="5.5" y2="5.5"/>' +
    '<circle cx="5.5" cy="7.5" r=".4" fill="currentColor"/>' +
    '</svg>';

  var ARROW_SM =
    '<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" ' +
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M2 5h6M6 3l2 2-2 2"/></svg>';

  /* ── renderProfessorCard ───────────────────────────────────────── *
   *                                                                  *
   * Faculty-directory style card.                                    *
   *                                                                  *
   * HTML structure:                                                  *
   *   .pc  (article[data-professor-id])                              *
   *     .pc-head                                                     *
   *       .pc-identity  h2.pc-name, p.pc-role, p.pc-uni             *
   *       .pc-score     .pc-score-num + .pc-score-unit               *
   *                     span.pc-score-label  (Strong/Good/Potential) *
   *     .pc-areas  (research areas as dot-separated text)            *
   *     .pc-why    (hidden why block + toggle button)                *
   *     .pc-footer                                                   *
   *       .pc-status    (email badge, signals, opportunity count)    *
   *       .pc-actions   (why toggle, view link, draft link)          *
   *                                                                  *
   * Preserved attributes for event wiring:                           *
   *   .js-toggle-why  +  data-target="why-{id}"                     *
   *   id="why-{id}"                                                  *
   * ──────────────────────────────────────────────────────────────── */
  function renderProfessorCard(match, options) {
    const opts        = options || {};
    const professor   = match.professor || {};
    const research    = match.research_match || {};
    const score       = research.score;
    const professorId = professor.id;
    const whyId       = "why-" + professorId;
    const signals     = signalCount(match);
    const opportunities = match.university_opportunities || [];
    const active = opportunities.filter(function (item) {
      return String(item.status || "").toLowerCase() !== "closed";
    });
    const closed = opportunities.filter(function (item) {
      return String(item.status || "").toLowerCase() === "closed";
    });
    const whyHtml     = renderWhy(match);
    const composeHref = "/outreach/compose/" + encodeURIComponent(professorId);

    /* Build role / affiliation line */
    const uni  = professor.university  && professor.university.name  ? professor.university.name  : "";
    const dept = professor.department  && professor.department.name  ? professor.department.name  : "";
    const lab  = professor.lab         && professor.lab.name         ? professor.lab.name         : "";
    const role = [professor.title, dept].filter(Boolean).join(" \u00b7 ");
    const uniLine = [uni, lab].filter(Boolean).join(" \u00b7 ");

    /* Research areas: dot-separated from research_overlap */
    const areas = Array.isArray(match.research_overlap) ? match.research_overlap : [];
    const areasText = areas.length
      ? '<div class="pc-areas"><span class="pc-areas-label">Research</span>' +
          areas.map(function (a) { return escapeHtml(a); }).join(" \u00b7 ") +
        "</div>"
      : "";

    /* Score */
    const cls    = scoreClass(score);
    const clsMap = { "pc-strong": "Strong", "pc-good": "Good", "pc-moderate": "Potential" };
    const alignLabel = scoreAlignmentLabel(score, research.priority);
    const scoreHtml = (
      '<div class="pc-score">' +
        '<div>' +
          (typeof score === "number"
            ? '<span class="pc-score-num">' + escapeHtml(score) + '</span>' +
              '<span class="pc-score-unit">%</span>'
            : '<span class="pc-score-num" style="font-size:1.1rem;color:var(--muted)">\u2014</span>') +
        "</div>" +
        '<span class="pc-score-label ' + cls + '">' + escapeHtml(clsMap[cls] || "Match") + "</span>" +
      "</div>"
    );

    /* Why block */
    const whyBlock = opts.showWhy
      ? whyHtml
      : (
        '<div class="pc-why">' +
          '<div id="' + whyId + '" class="hidden">' + whyHtml + "</div>" +
        "</div>"
      );

    /* Outreach / discovery status */
    const emailBadge = professor.email_available
      ? '<span class="pc-email-ok">' + CHECK_SM + " Email available</span>"
      : '<span class="pc-discovery">Discovery only</span>';

    /* Active opportunity count */
    const oppPill = active.length
      ? '<span class="pc-opp-pill">' + active.length + " opp.</span>"
      : "";

    /* Signals indicator */
    const signalsTxt = signals
      ? '<span class="pc-signals">' + signals + " signal" + (signals > 1 ? "s" : "") + "</span>"
      : "";

    /* Actions */
    const actionsHtml = opts.showWhy ? "" : (
      '<div class="pc-actions">' +
        '<button type="button" class="why-toggle js-toggle-why" data-target="' + whyId + '">' +
          INFO_SM + " Why this match" +
        "</button>" +
        (opts.detailHref
          ? '<a href="' + escapeHtml(opts.detailHref) + '" class="pc-view-link">View profile</a>'
          : "") +
        (professor.email_available
          ? '<a href="' + escapeHtml(composeHref) + '" class="pc-draft-link">' +
              'Draft email\u00a0' + ARROW_SM +
            "</a>"
          : "") +
      "</div>"
    );

    /* Opportunity blocks (university-wide, semantic separation preserved) */
    const oppBlocks = opts.hideOpportunities ? "" : (
      (active.length
        ? '<div style="margin-top:.7rem"><p style="font-size:.68rem;font-weight:700;' +
            'text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:.35rem">' +
            'University opportunities</p>' +
            active.map(renderOpportunity).join("") + "</div>"
        : "") +
      (closed.length && opts.mode !== "research"
        ? '<div style="margin-top:.5rem"><p style="font-size:.68rem;font-weight:700;' +
            'text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:.25rem">' +
            'Closed</p>' +
            closed.map(renderOpportunity).join("") + "</div>"
        : "")
    );

    /* Fit block */
    const fitBlock = opts.hideFit ? "" : (
      opts.mode === "both" || opts.mode === "opportunity"
        ? renderFitBlock(match, opts)
        : renderFitBlock(match, { mode: "research" })
    );

    return (
      '<article class="pc" data-professor-id="' + escapeHtml(professorId) + '">' +

        /* ── Head: identity + score ── */
        '<div class="pc-head">' +
          '<div class="pc-identity">' +
            '<h2 class="pc-name">' + escapeHtml(professor.name || "Professor") + "</h2>" +
            (role    ? '<p class="pc-role">' + role    + "</p>" : "") +
            (uniLine ? '<p class="pc-uni">'  + uniLine + "</p>" : "") +
          "</div>" +
          scoreHtml +
        "</div>" +

        /* ── Research areas ── */
        areasText +

        /* ── Fit block (opportunity mode) ── */
        fitBlock +

        /* ── Why block ── */
        whyBlock +

        /* ── Opportunities ── */
        oppBlocks +

        /* ── Footer: status + actions ── */
        (opts.showWhy ? "" :
          '<div class="pc-footer">' +
            '<div class="pc-status">' +
              emailBadge + signalsTxt + oppPill +
            "</div>" +
            actionsHtml +
          "</div>"
        ) +

      "</article>"
    );
  }

  /* ── Opportunity-first grouped view ────────────────────────────── */
  function renderOpportunityFirst(matches, options) {
    const groups = [];
    const index  = {};
    (matches || []).forEach(function (match) {
      const uni = match.professor && match.professor.university;
      const key = (uni && uni.id) ? String(uni.id) : "unknown";
      if (!index[key]) {
        index[key] = { university: uni, fit: fitObject(match.university_opportunity_fit), matches: [] };
        groups.push(index[key]);
      }
      index[key].matches.push(match);
    });
    return groups.map(function (group) {
      const name  = group.university && group.university.name ? group.university.name : "University";
      const score = group.fit && group.fit.score != null ? group.fit.score : 0;
      const why   = ((group.fit && group.fit.why) || []).map(function (l) {
        return "<li>" + escapeHtml(l) + "</li>";
      }).join("");
      const active = [];
      const seen   = {};
      group.matches.forEach(function (match) {
        (match.university_opportunities || []).forEach(function (item) {
          if (!item || String(item.status || "").toLowerCase() === "closed") return;
          const id = String(item.id || item.title);
          if (seen[id]) return;
          seen[id] = true;
          active.push(item);
        });
      });
      return (
        '<section class="university-group">' +
          '<h2>' + escapeHtml(name) + '</h2>' +
          '<p class="score">University Opportunity Fit<br>' + escapeHtml(score) + "/100</p>" +
          (why ? "<ul>" + why + "</ul>" : "") +
          (active.length
            ? '<div style="margin:.6rem 0">' +
                '<p style="font-size:.68rem;font-weight:700;text-transform:uppercase;' +
                'letter-spacing:.07em;color:var(--muted);margin-bottom:.35rem">Opportunities</p>' +
                active.map(renderOpportunity).join("") +
              "</div>"
            : "") +
          group.matches.map(function (match) {
            return renderProfessorCard(match, cardOptions(match, Object.assign({}, options, {
              mode: "opportunity",
              hideOpportunities: true,
              hideFit: true
            })));
          }).join("") +
        "</section>"
      );
    }).join("");
  }

  function cardOptions(match, options) {
    const opts = Object.assign({}, options || {});
    const id   = match.professor && match.professor.id;
    if (id && !opts.detailHref) {
      opts.detailHref = "/matches/" + encodeURIComponent(id);
    }
    return opts;
  }

  function renderMatchList(matches, options) {
    const opts = options || {};
    if (opts.mode === "opportunity") return renderOpportunityFirst(matches, opts);
    return (matches || []).map(function (match) {
      return renderProfessorCard(match, cardOptions(match, opts));
    }).join("");
  }

  /* ── Public API ─────────────────────────────────────────────────── */
  root.FMPMatchingUi = {
    escapeHtml:          escapeHtml,
    displayPriority:     displayPriority,
    emailLabel:          emailLabel,
    fitScore:            fitScore,
    affiliationLines:    affiliationLines,
    renderProfessorCard: renderProfessorCard,
    renderWhy:           renderWhy,
    renderOpportunity:   renderOpportunity,
    renderMatchList:     renderMatchList,
    overlapChips:        overlapChips
  };

})(typeof window !== "undefined" ? window : globalThis);
