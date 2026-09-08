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

  function renderOpportunity(item) {
    if (!item) return "";
    const specific = item.not_professor_specific === false;
    return (
      '<div class="opp">' +
        "<strong>University opportunity</strong>" +
        "<p>" + escapeHtml(item.title || "Untitled") + "</p>" +
        (item.type ? "<p class=\"meta\">" + escapeHtml(item.type) + "</p>" : "") +
        (item.status ? "<p class=\"meta\">Status: " + escapeHtml(item.status) + "</p>" : "") +
        (item.official_url ? '<p class="meta"><a href="' + escapeHtml(item.official_url) + '">Official page</a></p>' : "") +
        (specific ? "" : '<p class="note">This opportunity is offered by the university, not specifically by this professor.</p>') +
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
    const fit = match.university_opportunity_fit;
    const whyHtml = renderWhy(match);
    const whyBlock = opts.showWhy
      ? whyHtml
      : (
        '<button type="button" class="linkish js-toggle-why" data-target="' + whyId + '">Why am I a match?</button> ' +
        (opts.detailHref
          ? '<a href="' + escapeHtml(opts.detailHref) + '">View professor</a>'
          : "") +
        '<div id="' + whyId + '" class="hidden">' + whyHtml + "</div>"
      );
    return (
      '<article class="card" data-professor-id="' + escapeHtml(professorId) + '">' +
        "<h2>" + escapeHtml(professor.name || "Professor") + "</h2>" +
        (professor.title ? "<p class=\"meta\">" + escapeHtml(professor.title) + "</p>" : "") +
        affiliationLines(professor) +
        '<p class="score">' + escapeHtml(score) + "/100</p>" +
        '<p><span class="priority">' + escapeHtml(displayPriority(research.priority)) + "</span></p>" +
        overlapChips(match.research_overlap) +
        (signals ? "<p class=\"muted\">" + signals + " research signal" + (signals === 1 ? "" : "s") + "</p>" : "") +
        "<p class=\"meta\">" + emailLabel(professor) + "</p>" +
        whyBlock +
        (typeof fit === "number"
          ? "<p class=\"note\">University opportunity fit: " + escapeHtml(fit) + "</p>"
          : "") +
        (opportunities.length
          ? "<h3>University opportunities</h3>" + opportunities.map(renderOpportunity).join("")
          : "") +
      "</article>"
    );
  }

  root.FMPMatchingUi = {
    escapeHtml: escapeHtml,
    displayPriority: displayPriority,
    emailLabel: emailLabel,
    renderProfessorCard: renderProfessorCard,
    renderWhy: renderWhy,
    renderOpportunity: renderOpportunity,
    overlapChips: overlapChips
  };
})(typeof window !== "undefined" ? window : globalThis);
