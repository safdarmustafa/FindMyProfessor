(function (root) {
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
    return '<div class="chips">' + labels.map(function (label) {
      return '<span class="chip">' + escapeHtml(label) + "</span>";
    }).join("") + "</div>";
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
    if (source === "signal") return "research signal";
    if (source === "project") return "project";
    if (source === "publication") return "publication";
    return source || "";
  }

  function renderEvidenceItem(item) {
    if (!item || !item.type) return "";
    if (item.type === "shared_research_area") {
      return (
        "<li><strong>" + escapeHtml(item.area_name) + "</strong> — from your " +
        escapeHtml(studentSourceLabel(item.student_source)) + ".</li>"
      );
    }
    if (item.type === "artifact_research_area") {
      const kind = item.student_source === "publication" ? "publication" : "project";
      return (
        "<li><strong>" + escapeHtml(item.area_name) + "</strong> — " + kind +
        (item.artifact_title ? ' “' + escapeHtml(item.artifact_title) + "”" : "") +
        ".</li>"
      );
    }
    if (item.type === "professor_summary_mentions_area") {
      return (
        "<li>Supporting evidence: the professor’s research summary mentions " +
        escapeHtml(item.area_name) +
        (item.excerpt ? " (“" + escapeHtml(item.excerpt) + "”)" : "") +
        ".</li>"
      );
    }
    if (item.type === "university_opportunity") {
      return (
        "<li>University opportunity context: " + escapeHtml(item.title || "Opportunity") +
        (item.not_professor_specific === false ? "" : " (not professor-specific)") +
        ".</li>"
      );
    }
    return "";
  }

  function renderWhy(match) {
    const why = (match.research_match && match.research_match.why) || [];
    const evidence = match.evidence || [];
    const whyItems = why.map(function (line) {
      return "<li>" + escapeHtml(line) + "</li>";
    }).join("");
    const evidenceItems = evidence.map(renderEvidenceItem).join("");
    return (
      '<div class="why">' +
        "<h3>Why you're a match</h3>" +
        (whyItems ? "<ul>" + whyItems + "</ul>" : "<p class=\"muted\">No explanation was returned.</p>") +
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
    if (key === "open") return "Open";
    if (key === "upcoming") return "Upcoming";
    if (key === "closed") return "Closed";
    return "Unknown";
  }

  function optionalField(label, value) {
    if (value == null || value === "") return "";
    return "<p class=\"meta\">" + escapeHtml(label) + ": " + escapeHtml(value) + "</p>";
  }

  function renderOpportunity(item) {
    if (!item) return "";
    const specific = item.not_professor_specific === false;
    const closed = String(item.status || "").toLowerCase() === "closed";
    return (
      '<div class="opp' + (closed ? " opp-closed" : "") + '">' +
        "<strong>" + (specific ? "Opportunity" : "University opportunity") + "</strong>" +
        "<p>" + escapeHtml(item.title || "Untitled") + "</p>" +
        (item.type ? "<p class=\"meta\">" + escapeHtml(item.type) + "</p>" : "") +
        "<p class=\"meta\">Status: " + escapeHtml(statusLabel(item.status)) + "</p>" +
        optionalField("Deadline", item.application_deadline) +
        optionalField("Start date", item.start_date) +
        optionalField("Funding", item.funding_type) +
        optionalField("Stipend", item.stipend_amount) +
        optionalField("Tuition coverage", item.tuition_coverage) +
        optionalField("Accommodation", item.accommodation_coverage) +
        optionalField("Travel", item.travel_coverage) +
        (item.official_url ? '<p class="meta"><a href="' + escapeHtml(item.official_url) + '">Official page</a></p>' : "") +
        (specific ? "" : '<p class="note">This opportunity is offered by the university, not specifically by this professor.</p>') +
      "</div>"
    );
  }

  function renderFitBlock(match, options) {
    const opts = options || {};
    const fit = fitObject(match.university_opportunity_fit);
    if (!fit || typeof fit.score !== "number") return "";
    const prominent = opts.mode === "both" || opts.mode === "opportunity";
    const why = (fit.why || []).map(function (line) {
      return "<li>" + escapeHtml(line) + "</li>";
    }).join("");
    return (
      '<div class="' + (prominent ? "fit-block" : "note") + '">' +
        (prominent
          ? "<p class=\"score secondary\">University Opportunity Fit<br>" + escapeHtml(fit.score) + "/100</p>"
          : "<p class=\"note\">University opportunity fit: " + escapeHtml(fit.score) + "</p>") +
        (prominent && why ? "<ul>" + why + "</ul>" : "") +
      "</div>"
    );
  }

  function signalCount(match) {
    const evidence = match.evidence || [];
    return evidence.filter(function (item) {
      return item && item.student_source === "signal";
    }).length;
  }

  function renderProfessorCard(match, options) {
    const opts = options || {};
    const professor = match.professor || {};
    const research = match.research_match || {};
    const score = research.score;
    const professorId = professor.id;
    const whyId = "why-" + professorId;
    const signals = signalCount(match);
    const opportunities = match.university_opportunities || [];
    const active = opportunities.filter(function (item) {
      return String(item.status || "").toLowerCase() !== "closed";
    });
    const closed = opportunities.filter(function (item) {
      return String(item.status || "").toLowerCase() === "closed";
    });
    const whyHtml = renderWhy(match);
    const researchScore =
      '<p class="score">Research Match<br>' + escapeHtml(score) + "/100</p>" +
      '<p><span class="priority">' + escapeHtml(displayPriority(research.priority)) + "</span></p>";
    const composeHref = "/outreach/compose/" + encodeURIComponent(professorId);
    const whyBlock = opts.showWhy
      ? whyHtml
      : (
        '<button type="button" class="linkish js-toggle-why" data-target="' + whyId + '">Why am I a match?</button> ' +
        (opts.detailHref
          ? '<a href="' + escapeHtml(opts.detailHref) + '">View professor</a>'
          : "") +
        ' <a href="' + escapeHtml(composeHref) + '">Generate Email</a>' +
        '<div id="' + whyId + '" class="hidden">' + whyHtml + "</div>"
      );
    return (
      '<article class="card" data-professor-id="' + escapeHtml(professorId) + '">' +
        "<h2>" + escapeHtml(professor.name || "Professor") + "</h2>" +
        (professor.title ? "<p class=\"meta\">" + escapeHtml(professor.title) + "</p>" : "") +
        affiliationLines(professor) +
        researchScore +
        (opts.hideFit ? "" : (opts.mode === "both" || opts.mode === "opportunity" ? renderFitBlock(match, opts) : renderFitBlock(match, { mode: "research" }))) +
        overlapChips(match.research_overlap) +
        (signals ? "<p class=\"muted\">" + signals + " research signal" + (signals === 1 ? "" : "s") + "</p>" : "") +
        "<p class=\"meta\">" + emailLabel(professor) + "</p>" +
        whyBlock +
        (opts.hideOpportunities ? "" : (
          (active.length ? "<h3>University opportunities</h3>" + active.map(renderOpportunity).join("") : "") +
          (closed.length && opts.mode !== "research" ? "<h4>Closed</h4>" + closed.map(renderOpportunity).join("") : "")
        )) +
      "</article>"
    );
  }

  function renderOpportunityFirst(matches, options) {
    const groups = [];
    const index = {};
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
      const name = group.university && group.university.name ? group.university.name : "University";
      const score = group.fit && group.fit.score != null ? group.fit.score : 0;
      const why = ((group.fit && group.fit.why) || []).map(function (line) {
        return "<li>" + escapeHtml(line) + "</li>";
      }).join("");
      const active = [];
      const seen = {};
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
          "<h2>" + escapeHtml(name) + "</h2>" +
          '<p class="score">University Opportunity Fit<br>' + escapeHtml(score) + "/100</p>" +
          (why ? "<ul>" + why + "</ul>" : "") +
          (active.length ? "<h3>University opportunities</h3>" + active.map(renderOpportunity).join("") : "") +
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
    const id = match.professor && match.professor.id;
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

  root.FMPMatchingUi = {
    escapeHtml: escapeHtml,
    displayPriority: displayPriority,
    emailLabel: emailLabel,
    fitScore: fitScore,
    renderProfessorCard: renderProfessorCard,
    renderWhy: renderWhy,
    renderOpportunity: renderOpportunity,
    renderMatchList: renderMatchList,
    overlapChips: overlapChips
  };
})(typeof window !== "undefined" ? window : globalThis);
