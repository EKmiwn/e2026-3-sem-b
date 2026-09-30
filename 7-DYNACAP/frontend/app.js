// DYNACAP Academy – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { user: null, lang: "da", menteeId: null };

// Alle skærmbilleder findes på dansk og engelsk (afsnit 16)
const TEXT = {
  da: {
    tagline: "Seks niveauer fra første dag til fuldt oplært – ens i Danmark og Norge", signedIn: "Logget ind som",
    tabMine: "Min oplæring", tabMentees: "Konsulenter", tabHr: "Forløb og indhold", tabReport: "Statusrapport",
    newConsultant: "Ny konsulent – opret forløb", name: "Navn", office: "Kontor", mentor: "Vejleder",
    startDate: "Startdato", language: "Sprog", createProgramme: "Opret forløb med seks niveauer", editLevel: "Ret niveau",
    save: "Gem", levels: "Niveauer", activities: "Aktiviteter", reportTitle: "Status pr. kontor",
    sendReport: "Send statusrapport nu", sentReports: "Sendte rapporter", level: "Niveau", yourLevel: "Du er på niveau",
    fullyTrained: "Fuldt oplært", onTrack: "Følger planen", behind: "Bagud i forhold til planen", expected: "forventet niveau",
    canAfter: "Du kan efter niveauet", weeks: "uger", locked: "Låst – låses op, når niveauet før er godkendt",
    approved: "Godkendt", current: "Aktuelt niveau", rejected: "Afvist", reviews: "Vurderinger", certifications: "Certificeringer",
    addCertification: "Registrér certificering", passed: "Bestået", readyForReview: "Klar til godkendelse",
    approve: "Godkend niveau", reject: "Afvis", comment: "Kommentar", consultant: "Konsulent", progress: "Fremdrift",
    status: "Status", awaiting: "Afventer godkendelse af niveau", open: "Åbn", consultants: "Konsulenter",
    avgLevel: "Gns. niveau", onProject: "På kundeprojekt", behindPlan: "Bagud", nextAuto: "Næste automatiske rapport",
    everyDays: "Sendes automatisk hver", days: "dage", done: "gennemført", missingCert: "Mangler certificering",
    requiresCert: "Kræver certificering",
  },
  en: {
    tagline: "Six levels from day one to fully trained – the same in Denmark and Norway", signedIn: "Signed in as",
    tabMine: "My training", tabMentees: "Consultants", tabHr: "Programmes and content", tabReport: "Status report",
    newConsultant: "New consultant – create programme", name: "Name", office: "Office", mentor: "Mentor",
    startDate: "Start date", language: "Language", createProgramme: "Create six-level programme", editLevel: "Edit level",
    save: "Save", levels: "Levels", activities: "Activities", reportTitle: "Status per office",
    sendReport: "Send status report now", sentReports: "Sent reports", level: "Level", yourLevel: "You are on level",
    fullyTrained: "Fully trained", onTrack: "On track", behind: "Behind plan", expected: "expected level",
    canAfter: "After this level you can", weeks: "weeks", locked: "Locked – unlocks when the previous level is approved",
    approved: "Approved", current: "Current level", rejected: "Rejected", reviews: "Reviews", certifications: "Certifications",
    addCertification: "Register certification", passed: "Passed", readyForReview: "Ready for approval",
    approve: "Approve level", reject: "Reject", comment: "Comment", consultant: "Consultant", progress: "Progress",
    status: "Status", awaiting: "Awaiting approval of level", open: "Open", consultants: "Consultants",
    avgLevel: "Avg. level", onProject: "On customer project", behindPlan: "Behind", nextAuto: "Next automatic report",
    everyDays: "Sent automatically every", days: "days", done: "done", missingCert: "Certification missing",
    requiresCert: "Requires certification",
  },
};

function t(key) {
  return TEXT[state.lang][key] ?? key;
}

function translatePage() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-lang]").forEach((b) => b.classList.toggle("secondary", b.dataset.lang !== state.lang));
}

// Alle kald sender den indloggede bruger med (simuleret login)
function userApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-User-Id": state.user.id } });
}

function withLang(path) {
  return `${path}${path.includes("?") ? "&" : "?"}lang=${state.lang}`;
}

// ---------------------------------------------------------------- Login og roller
async function loadBase() {
  const people = await api("/people");
  const select = $("#user-select");
  const previous = state.user?.id;
  fillSelect(select, people, (p) => `${p.name} · ${p.role.toLowerCase()} · ${p.office}`);
  if (previous) select.value = previous;
  await signIn(Number(select.value));
}

async function signIn(userId) {
  state.user = await api("/me", { headers: { "X-User-Id": userId } });
  state.lang = state.user.language;
  state.menteeId = null;
  translatePage();
  // Vis kun faneblade, som rollen har adgang til
  const buttons = [...document.querySelectorAll(".tabs button")];
  buttons.forEach((b) => { b.hidden = !b.dataset.roles.split(" ").includes(state.user.role); });
  buttons.find((b) => !b.hidden).click();
}

$("#user-select").addEventListener("change", (event) => signIn(Number(event.target.value)));

document.querySelectorAll("[data-lang]").forEach((button) => button.addEventListener("click", () => {
  state.lang = button.dataset.lang;
  translatePage();
  reloadActiveTab();
}));

function reloadActiveTab() {
  const tab = document.querySelector(".tabs button.active")?.dataset.tab;
  ({ mine: loadMine, mentees: loadMentees, hr: loadHr, report: loadReport })[tab]?.();
}

// ---------------------------------------------------------------- Fremdrift (F2): niveaubar, næste skridt og tjekliste
function renderProgress(p, { canTick, canReview }) {
  const levelBar = h("div", { class: "levelbar" }, p.levels.map((lv) => h("div", { class: lv.status },
    `${lv.number}`, h("small", {}, lv.title))));
  const header = h("div", { class: "card highlight" },
    h("h2", {}, p.consultant.name, " · ", p.fully_trained ? t("fullyTrained") : `${t("yourLevel")} ${p.current_level}`),
    levelBar,
    h("p", { class: "next" }, p.next_step),
    h("div", { class: "progress" }, h("span", { style: `width:${p.percent}%` })),
    h("p", { class: "muted" }, `${p.percent} % ${t("done")} · `,
      p.on_track ? badge(t("onTrack"), "ok") : badge(t("behind"), "warn"), ` (${t("expected")} ${p.expected_level})`));
  const levels = p.levels.map((lv) => h("div", { class: `card level ${lv.status}` },
    h("h3", {}, `${t("level")} ${lv.number}: ${lv.title} `,
      lv.status === "GODKENDT" ? badge(t("approved"), "ok") : lv.status === "AKTUEL" ? badge(t("current")) : badge("🔒", "muted"),
      lv.ready_for_review ? badge(t("readyForReview"), "warn") : null),
    h("p", {}, `${t("canAfter")}: `, h("em", {}, lv.goal)),
    h("p", { class: "muted" }, `${lv.learning_form} · ${lv.estimate} ${t("weeks")}`,
      lv.requires_certification ? ` · ${t("requiresCert")}: ${lv.requires_certification}` : ""),
    lv.status === "LÅST" ? h("p", { class: "empty" }, t("locked")) : h("div", {}, lv.activities.map((a) => h("label", { class: `check ${a.completed_at ? "done" : ""}` },
      h("input", { type: "checkbox", checked: !!a.completed_at, disabled: !(canTick && lv.status === "AKTUEL"), onchange: () => toggle(p.consultant.id, a.id) }),
      h("span", {}, a.title), badge(a.type, "muted"),
      a.link ? h("a", { href: a.link, target: "_blank", rel: "noopener" }, "↗") : null))),
    lv.certification_missing && lv.status === "AKTUEL" ? h("p", {}, badge(t("missingCert"), "warn")) : null,
    lv.reviews.length ? h("ul", { class: "list" }, lv.reviews.map((r) => h("li", {},
      badge(r.decision === "GODKENDT" ? t("approved") : t("rejected"), r.decision === "GODKENDT" ? "ok" : "danger"),
      ` ${formatDate(r.reviewed_at)} · ${r.mentor_name}`, r.comment ? `: "${r.comment}"` : ""))) : null,
    canReview && lv.status === "AKTUEL" ? reviewForm(p.consultant.id, lv) : null));
  const certForm = h("form", { class: "toolbar" },
    h("label", {}, "Certificering", h("input", { name: "name", value: "Salesforce Administrator", required: true })),
    h("label", {}, t("passed"), h("input", { type: "date", name: "passed_at", required: true })),
    h("button", {}, t("addCertification")));
  certForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const updated = await run(() => userApi(withLang(`/consultants/${p.consultant.id}/certifications`), { method: "POST", body: formToJson(certForm) }), "✓");
    rerender(updated);
  });
  const certs = h("div", { class: "card" }, h("h3", {}, t("certifications")),
    p.certifications.length ? h("ul", { class: "list" }, p.certifications.map((c) => h("li", {}, `🎓 ${c.name} · ${c.passed_at}`)))
      : h("p", { class: "empty" }, "–"),
    state.user.role !== "LEDELSE" ? certForm : null);
  return [header, ...levels, certs];
}

function reviewForm(consultantId, level) {
  const form = h("form", {},
    h("label", {}, t("comment"), h("textarea", { name: "comment" })),
    h("div", { class: "actions" },
      h("button", { type: "button", disabled: !level.ready_for_review, onclick: () => review("GODKENDT") }, t("approve")),
      h("button", { type: "button", class: "danger", onclick: () => review("AFVIST") }, t("reject"))));
  async function review(decision) {
    const updated = await run(() => userApi(withLang(`/consultants/${consultantId}/levels/${level.id}/review`), {
      method: "POST", body: { decision, ...formToJson(form) },
    }), decision === "GODKENDT" ? t("approved") : t("rejected"));
    rerender(updated);
    loadMentees();
  }
  return h("div", { class: "card", style: "background:var(--brand-soft)" }, form);
}

async function toggle(consultantId, activityId) {
  const updated = await run(() => userApi(withLang(`/consultants/${consultantId}/activities/${activityId}/toggle`), { method: "POST" }));
  rerender(updated);
}

function rerender(p) {
  if (p.consultant.id === state.user.id) {
    $("#my-progress").replaceChildren(...renderProgress(p, { canTick: true, canReview: false }));
  } else {
    $("#mentee-progress").replaceChildren(...renderProgress(p, {
      canTick: false, canReview: state.user.role === "VEJLEDER" && p.consultant.mentor_id === state.user.id,
    }));
  }
}

// ---------------------------------------------------------------- Konsulent
async function loadMine() {
  rerender(await userApi(withLang(`/consultants/${state.user.id}/progress`)));
}

// ---------------------------------------------------------------- Vejleder, HR og ledelse: konsulenter
async function loadMentees() {
  const rows = await userApi("/consultants");
  renderTable($("#consultant-table"), rows, [
    { label: t("consultant"), key: "name" },
    { label: t("office"), key: "office" },
    { label: t("mentor"), key: "mentor" },
    { label: t("level"), class: "num", render: (c) => (c.fully_trained ? "✓ 6" : c.current_level) },
    { label: t("progress"), class: "num", render: (c) => `${c.percent} %` },
    { label: t("status"), render: (c) => h("span", {}, c.on_track ? badge(t("onTrack"), "ok") : badge(t("behind"), "warn"),
      c.awaiting_review ? badge(`${t("awaiting")} ${c.awaiting_review}`) : null) },
    { label: "", render: (c) => h("button", { class: "small secondary", onclick: () => openMentee(c.id) }, t("open")) },
  ]);
  if (state.menteeId) openMentee(state.menteeId, false);
}

async function openMentee(id, scroll = true) {
  state.menteeId = id;
  rerender(await userApi(withLang(`/consultants/${id}/progress`)));
  if (scroll) $("#mentee-progress").scrollIntoView({ behavior: "smooth" });
}

// ---------------------------------------------------------------- HR: forløb og indhold (F1, afsnit 14)
async function loadHr() {
  const [offices, people, levels, activities] = await Promise.all([api("/offices"), api("/people"), api("/levels"), api("/activities")]);
  fillSelect($("#consultant-form [name=office_id]"), offices, (o) => `${o.name} (${o.country})`);
  fillSelect($("#consultant-form [name=mentor_id]"), people.filter((p) => p.role === "VEJLEDER"), (p) => `${p.name} · ${p.office}`);
  fillSelect($("#activity-form [name=level_id]"), levels, (l) => `${l.number}. ${l.title_da}`);
  renderTable($("#level-table"), levels, [
    { label: "Nr.", key: "number" },
    { label: "Titel", render: (l) => `${l.title_da} / ${l.title_en}` },
    { label: "Mål", render: (l) => (state.lang === "en" ? l.goal_en : l.goal_da) },
    { label: "Uger", render: (l) => `${l.estimate_weeks_min}–${l.estimate_weeks_max}` },
    { label: "", render: (l) => h("button", { class: "small secondary", onclick: () => fillForm($("#level-form"), l) }, "Redigér") },
  ]);
  renderTable($("#activity-table"), activities, [
    { label: t("level"), render: (a) => levels.find((l) => l.id === a.level_id)?.number },
    { label: "Titel", render: (a) => (state.lang === "en" ? a.title_en : a.title_da) },
    { label: "Type", render: (a) => badge(a.type, "muted") },
    { label: "", render: (a) => hrButtons("activities", $("#activity-form"), a, loadHr) },
  ]);
}

$("#consultant-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const p = await run(() => userApi("/consultants", { method: "POST", body: formToJson(event.target) }), "Forløb oprettet");
  event.target.reset();
  await loadBase();
  toast(`${p.consultant.name}: ${p.next_step}`);
});

// Niveauer og aktiviteter ændres af HR (backenden kræver rollen HR)
function bindHrForm(form, resource) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const { id, ...data } = formToJson(form);
    await run(() => userApi(id ? `/${resource}/${id}` : `/${resource}`, { method: id ? "PUT" : "POST", body: data }), "Gemt");
    form.reset();
    form.elements.id.value = "";
    loadHr();
  });
}
bindHrForm($("#level-form"), "levels");
bindHrForm($("#activity-form"), "activities");
$("#activity-form [data-reset]").addEventListener("click", () => { $("#activity-form").reset(); $("#activity-form").elements.id.value = ""; });

// Som crudButtons() i api.js, men sletningen sender HR-brugeren med i X-User-Id
function hrButtons(resource, form, row, reload) {
  return h("div", { class: "actions" },
    h("button", { class: "small secondary", onclick: () => fillForm(form, row) }, "Redigér"),
    h("button", {
      class: "small danger",
      onclick: async () => {
        if (!confirm("Vil du slette denne post?")) return;
        await run(() => userApi(`/${resource}/${row.id}`, { method: "DELETE" }), "Slettet");
        reload();
      },
    }, "Slet"));
}

// ---------------------------------------------------------------- Ledelse: statusrapport pr. kontor (F7)
async function loadReport() {
  const r = await userApi("/reports/status");
  renderTable($("#report-table"), r.offices, [
    { label: t("office"), render: (o) => `${o.office} (${o.country})` },
    { label: t("consultants"), class: "num", key: "consultants" },
    { label: t("avgLevel"), class: "num", key: "average_level" },
    ...[1, 2, 3, 4, 5, 6].map((n) => ({ label: `${t("level")} ${n}`, class: "num", render: (o) => o.levels[n] || "–" })),
    { label: t("fullyTrained"), class: "num", key: "fully_trained" },
    { label: t("onProject"), class: "num", key: "on_project" },
    { label: t("behindPlan"), class: "num", key: "behind_plan" },
  ]);
  $("#report-info").textContent = `${t("everyDays")} ${r.interval_days} ${t("days")} · ${t("nextAuto")}: ${r.next_automatic}`;
  renderTable($("#report-log"), r.sent, [
    { label: "Tid", render: (s) => formatDate(s.sent_at) },
    { label: "Til", key: "sent_to" },
    { label: "", render: (s) => badge(s.trigger_type.toLowerCase(), "muted") },
  ], "–");
}

$("#send-report").addEventListener("click", async () => {
  await run(() => userApi("/reports/send", { method: "POST" }), (r) => `Sendt til ${r.sent_to}`);
  loadReport();
});

// ---------------------------------------------------------------- Start
setupTabs(() => reloadActiveTab());
loadBase().catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
