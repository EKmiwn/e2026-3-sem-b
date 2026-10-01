// Bispebjerg Akutmodtagelse – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { userId: null, staff: [], examTypes: [], departments: [], lang: "da", patient: null, birthDate: null,
  selectedId: null, startedAt: null };

const STATUS_ORDER = ["REGISTRERET", "VENTER_PÅ_SYGEPLEJERSKE", "UNDERSØGELSE_BESTILT", "VENTER_PÅ_LÆGE", "AFSLUTTET"];
const STATUS_BADGE = { REGISTRERET: "muted", VENTER_PÅ_SYGEPLEJERSKE: "warn", UNDERSØGELSE_BESTILT: "", VENTER_PÅ_LÆGE: "warn", AFSLUTTET: "ok" };
const INJURY_TYPES = ["SYGDOM", "FALD", "BRUD", "FORSTUVNING", "SÅR", "FORBRÆNDING", "HOVEDSKADE", "ANDET"];
const TRIAGE = { RØD: "red", ORANGE: "orange", GUL: "yellow", GRØN: "green", BLÅ: "blue" };
const TRIAGE_TEXT = { RØD: "Rød – livstruende", ORANGE: "Orange – haster", GUL: "Gul – haster mindre", GRØN: "Grøn – ikke hastende", BLÅ: "Blå – let tilskadekomst" };

// Patientsiderne findes på dansk og engelsk (afsnit 11 og 16). Personalesiderne er på dansk.
const TEXT = {
  da: {
    registerTitle: "Fortæl os, hvorfor du er her",
    registerIntro: "Det tager højst 5 minutter. Sygeplejersken og lægen kan se dine svar, før de taler med dig, så du ikke skal fortælle det hele flere gange.",
    name: "Dit fulde navn", birthDate: "Fødselsdato", where: "Hvor er du nu?",
    whereHere: "Jeg er på akutmodtagelsen", whereHome: "Jeg er hjemme eller på vej",
    symptoms: "Hvad er der sket, og hvad er dine symptomer?", symptomsHint: "Fx: Faldt på cyklen og har ondt i håndleddet",
    injuryType: "Type af skade eller sygdom", pain: "Hvor ondt gør det? (0 = ingen smerte, 10 = værst tænkelige)",
    medication: "Medicin, du tager", allergies: "Allergier", noneHint: "Lad feltet stå tomt, hvis ingen",
    consent: "Jeg giver samtykke til, at Bispebjerg Akutmodtagelse behandler mine helbredsoplysninger i forbindelse med mit besøg.",
    submit: "Send registrering", statusTitle: "Se status på dit forløb", regNumber: "Registreringsnummer", lookup: "Vis min status",
    lookupHint: "Du fik registreringsnummeret, da du sendte din registrering.",
    yourNumber: "Dit registreringsnummer", saveNumber: "Gem nummeret. Du skal bruge det sammen med din fødselsdato for at se din status eller rette dine oplysninger.",
    seeStatus: "Se min status", hello: "Hej", arriveText: "Tryk her, når du er ankommet til akutmodtagelsen.",
    arrive: "Jeg er ankommet", waited: "Ventet", minutes: "min.", examinations: "Undersøgelser", ordered: "bestilt", done: "udført",
    timeline: "Forløb", yourInfo: "Dine oplysninger", saveChanges: "Gem ændringer", closedInfo: "Forløbet er afsluttet og kan ikke ændres.",
    refresh: "Opdatér status", saved: "Dine oplysninger er opdateret", arrived: "Din ankomst er registreret", registered: "Din registrering er modtaget",
    none: "Ingen oplyst",
    status: { REGISTRERET: "Registreret", VENTER_PÅ_SYGEPLEJERSKE: "Venter på sygeplejerske", UNDERSØGELSE_BESTILT: "Undersøgelse bestilt", VENTER_PÅ_LÆGE: "Venter på læge", AFSLUTTET: "Afsluttet" },
    injury: { SYGDOM: "Sygdom", FALD: "Fald", BRUD: "Mistanke om brud", FORSTUVNING: "Forstuvning", SÅR: "Sår eller snit", FORBRÆNDING: "Forbrænding", HOVEDSKADE: "Slag mod hovedet", ANDET: "Andet" },
  },
  en: {
    registerTitle: "Tell us why you are here",
    registerIntro: "It takes no more than 5 minutes. The nurse and doctor can read your answers before they talk to you, so you do not have to repeat everything.",
    name: "Your full name", birthDate: "Date of birth", where: "Where are you now?",
    whereHere: "I am at the emergency department", whereHome: "I am at home or on my way",
    symptoms: "What happened, and what are your symptoms?", symptomsHint: "E.g. Fell off my bike and my wrist hurts",
    injuryType: "Type of injury or illness", pain: "How much does it hurt? (0 = no pain, 10 = worst imaginable)",
    medication: "Medication you take", allergies: "Allergies", noneHint: "Leave empty if none",
    consent: "I consent to Bispebjerg Emergency Department processing my health information in connection with my visit.",
    submit: "Send registration", statusTitle: "See the status of your visit", regNumber: "Registration number", lookup: "Show my status",
    lookupHint: "You received the registration number when you sent your registration.",
    yourNumber: "Your registration number", saveNumber: "Keep this number. You need it together with your date of birth to see your status or change your information.",
    seeStatus: "See my status", hello: "Hello", arriveText: "Press here when you have arrived at the emergency department.",
    arrive: "I have arrived", waited: "Waited", minutes: "min.", examinations: "Examinations", ordered: "ordered", done: "done",
    timeline: "Timeline", yourInfo: "Your information", saveChanges: "Save changes", closedInfo: "The visit is closed and cannot be changed.",
    refresh: "Refresh status", saved: "Your information has been updated", arrived: "Your arrival has been registered", registered: "Your registration has been received",
    none: "None stated",
    status: { REGISTRERET: "Registered", VENTER_PÅ_SYGEPLEJERSKE: "Waiting for nurse", UNDERSØGELSE_BESTILT: "Examination ordered", VENTER_PÅ_LÆGE: "Waiting for doctor", AFSLUTTET: "Closed" },
    injury: { SYGDOM: "Illness", FALD: "Fall", BRUD: "Suspected fracture", FORSTUVNING: "Sprain", SÅR: "Wound or cut", FORBRÆNDING: "Burn", HOVEDSKADE: "Blow to the head", ANDET: "Other" },
  },
};

function t(key) {
  return TEXT[state.lang][key];
}

// Alle personalekald sender den valgte medarbejder med (simuleret login)
function userApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-User-Id": state.userId } });
}

function currentUser() {
  return state.staff.find((s) => s.id === state.userId);
}

function isClinical() {
  return ["SYGEPLEJERSKE", "LÆGE"].includes(currentUser()?.role);
}

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

function triageBadge(level) {
  return h("span", { class: `triage ${TRIAGE[level] ?? "none"}` }, level ?? "Ikke vurderet");
}

function statusBadge(status) {
  return badge(TEXT.da.status[status], STATUS_BADGE[status]);
}

function injurySelect(name, value) {
  const select = h("select", { name }, INJURY_TYPES.map((type) => h("option", { value: type }, t("injury")[type])));
  if (value) select.value = value;
  return select;
}

// Som replaceChildren(), men springer null over og folder lister ud – ligesom h()
function show(container, ...children) {
  container.replaceChildren(...h("div", {}, children).childNodes);
}

function openTab(name) {
  document.querySelector(`.tabs button[data-tab="${name}"]`).click();
}

// ---------------------------------------------------------------- Sprog (dansk/engelsk på patientsiderne)
function applyLanguage() {
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder)));
  document.querySelectorAll("[data-lang]").forEach((b) => b.classList.toggle("secondary", b.dataset.lang !== state.lang));
  const select = $("#injury-select");
  const previous = select.value;
  select.replaceChildren(...injurySelect("injury_type").children);
  if (previous) select.value = previous;
  if (state.patient) renderPatientStatus(state.patient);
}

document.querySelectorAll("[data-lang]").forEach((button) => button.addEventListener("click", () => {
  state.lang = button.dataset.lang;
  applyLanguage();
}));

// ---------------------------------------------------------------- Patient: registrering (FR1, FR2)
const registerForm = $("#register-form");
registerForm.addEventListener("input", () => (state.startedAt ??= Date.now()));   // måler udfyldelsestiden
registerForm.elements.pain_level.addEventListener("input", (event) => ($("#pain-output").textContent = event.target.value));

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = {
    ...formToJson(registerForm),
    language: state.lang,
    fill_seconds: Math.max(1, Math.round((Date.now() - (state.startedAt ?? Date.now())) / 1000)),
  };
  const view = await run(() => api("/patient/registrations", { method: "POST", body }), t("registered"));
  state.startedAt = null;
  registerForm.reset();
  $("#pain-output").textContent = registerForm.elements.pain_level.value;
  const box = $("#register-result");
  box.hidden = false;
  box.replaceChildren(
    h("p", { class: "muted" }, t("yourNumber")),
    h("div", { class: "reg-number" }, view.reg_number),
    h("p", {}, t("saveNumber")),
    h("button", { class: "big", onclick: () => { showPatient(view, view.birth_date); openTab("status"); } }, t("seeStatus")),
  );
  box.scrollIntoView({ behavior: "smooth", block: "center" });
  loadStaffViews();
});

// ---------------------------------------------------------------- Patient: status og opdatering (FR8, FR9)
const lookupForm = $("#lookup-form");
lookupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const { reg_number: regNumber, birth_date: birthDate } = formToJson(lookupForm);
  await loadPatient(regNumber, birthDate);
});

async function loadPatient(regNumber, birthDate) {
  const view = await run(() => api(`/patient/registrations/${encodeURIComponent(regNumber.trim())}?birth_date=${birthDate}`));
  showPatient(view, birthDate);
}

function showPatient(view, birthDate) {
  state.patient = view;
  state.birthDate = birthDate;
  lookupForm.elements.reg_number.value = view.reg_number;
  lookupForm.elements.birth_date.value = birthDate;
  renderPatientStatus(view);
}

function renderPatientStatus(p) {
  const reached = new Set(p.timeline.map((e) => e.status));
  const current = STATUS_ORDER.indexOf(p.status);
  const closed = p.status === "AFSLUTTET";
  const path = `/patient/registrations/${p.reg_number}`;

  const form = h("form", {},
    h("label", {}, t("symptoms"), h("textarea", { name: "symptoms", required: true }, p.symptoms)),
    h("label", {}, t("injuryType"), injurySelect("injury_type", p.injury_type)),
    h("label", {}, t("pain"), h("span", { class: "pain" },
      h("input", { name: "pain_level", type: "range", min: 0, max: 10, value: p.pain_level,
        oninput: (event) => (event.target.nextSibling.textContent = event.target.value) }),
      h("output", {}, p.pain_level))),
    h("label", {}, t("medication"), h("input", { name: "medication", value: p.medication, placeholder: t("noneHint") })),
    h("label", {}, t("allergies"), h("input", { name: "allergies", value: p.allergies, placeholder: t("noneHint") })),
    h("button", { class: "big" }, t("saveChanges")));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const f = form.elements;
    // Tomme felter sendes med, så patienten også kan fjerne fx medicin igen
    const body = { birth_date: state.birthDate, symptoms: f.symptoms.value, injury_type: f.injury_type.value,
      pain_level: Number(f.pain_level.value), medication: f.medication.value, allergies: f.allergies.value };
    showPatient(await run(() => api(path, { method: "PUT", body }), t("saved")), state.birthDate);
    loadStaffViews();
  });

  show($("#patient-status"),
    h("div", { class: "card highlight" },
      h("p", { class: "muted" }, `${t("hello")} ${p.name}`),
      h("div", { class: "reg-number" }, p.reg_number),
      h("ol", { class: "steps" }, STATUS_ORDER.map((status, i) =>
        h("li", { class: i === current ? "current" : i < current && reached.has(status) ? "done" : "" }, t("status")[status]))),
      p.waited_minutes !== null ? h("p", {}, `${t("waited")}: `, h("strong", {}, `${p.waited_minutes} ${t("minutes")}`)) : null,
      p.status === "REGISTRERET" ? h("p", {}, t("arriveText")) : null,
      h("div", { class: "actions" },
        p.status === "REGISTRERET" ? h("button", {
          class: "big",
          onclick: async () => {
            showPatient(await run(() => api(`${path}/arrive`, { method: "POST", body: { birth_date: state.birthDate } }), t("arrived")), state.birthDate);
            loadStaffViews();
          },
        }, t("arrive")) : null,
        h("button", { class: "big secondary", onclick: () => loadPatient(p.reg_number, state.birthDate) }, t("refresh")))),
    p.examinations.length ? h("div", { class: "card" },
      h("h2", {}, t("examinations")),
      h("ul", { class: "list" }, p.examinations.map((e) =>
        h("li", {}, `${e.exam_name} `, badge(e.status === "UDFØRT" ? t("done") : t("ordered"), e.status === "UDFØRT" ? "ok" : "warn"))))) : null,
    h("div", { class: "card" },
      h("h2", {}, t("timeline")),
      h("ul", { class: "list" }, p.timeline.map((e) => h("li", {}, `${formatDate(e.created_at)} · ${t("status")[e.status]}`)))),
    h("div", { class: "card" },
      h("h2", {}, t("yourInfo")),
      closed ? h("p", { class: "muted" }, t("closedInfo")) : form),
  );
}

// ---------------------------------------------------------------- Personale: patientkø (FR3, FR4)
async function loadQueue() {
  if (!isClinical()) {
    $("#queue-count").textContent = "";
    $("#queue-table").replaceChildren(h("p", { class: "empty" }, "Patientkøen kan kun ses af sygeplejersker og læger."));
    $("#patient-detail").replaceChildren(h("p", { class: "empty" }, "Ingen adgang med denne rolle."));
    return;
  }
  const rows = await userApi("/registrations");
  $("#queue-count").textContent = rows.length ? `(${rows.length})` : "";
  renderTable($("#queue-table"), rows, [
    { label: "Triage", render: (r) => triageBadge(r.status === "REGISTRERET" ? null : r.triage_level) },
    { label: "Patient", render: (r) => h("span", {}, h("strong", {}, r.name), h("br"), h("small", { class: "muted" }, `${r.reg_number} · f. ${r.birth_date}`)) },
    { label: "Skade", render: (r) => TEXT.da.injury[r.injury_type] },
    { label: "Smerte", class: "num", render: (r) => `${r.pain_level}/10` },
    { label: "Status", render: (r) => h("span", {}, statusBadge(r.status),
      r.open_examinations ? h("small", { class: "muted" }, ` ${r.open_examinations} åben`) : null,
      r.updated_since_triage ? h("div", {}, badge("opdateret af patient", "danger")) : null) },
    { label: "Ventet", class: "num", render: (r) => (r.waited_minutes === null ? "ikke ankommet" : `${r.waited_minutes} min.`) },
    { label: "", render: (r) => h("button", { class: `small ${r.id === state.selectedId ? "" : "secondary"}`, onclick: () => openPatient(r.id) }, "Åbn") },
  ], "Ingen patienter i kø");
}

async function openPatient(id) {
  state.selectedId = id;
  const d = await run(() => userApi(`/registrations/${id}`));
  renderDetail(d);
  loadQueue();
}

async function staffAction(path, body, message) {
  await run(() => userApi(path, { method: "POST", body }), message);
  await Promise.all([loadQueue(), loadExams(), loadOverview()]);
  if (state.selectedId && isClinical()) renderDetail(await userApi(`/registrations/${state.selectedId}`));
}

function renderDetail({ registration: r, timeline, examinations, history }) {
  const arrived = r.status !== "REGISTRERET";
  const closed = r.status === "AFSLUTTET";
  const base = `/registrations/${r.id}`;
  // Rød markering, indtil personalet har vurderet patienten igen efter ændringen
  const updatedSinceTriage = r.patient_updated_at && (!r.triaged_at || r.patient_updated_at > r.triaged_at);

  const triageForm = h("form", {},
    h("div", { class: "row" },
      h("label", {}, "Triageniveau", h("select", { name: "triage_level", required: true },
        h("option", { value: "" }, "Vælg ud fra din faglige vurdering"),
        Object.entries(TRIAGE_TEXT).map(([value, text]) => h("option", { value }, text)))),
      h("label", {}, "Note", h("input", { name: "triage_note", value: r.triage_note ?? "" }))),
    h("div", { class: "actions" }, h("button", {}, "Gem triage")));
  triageForm.elements.triage_level.value = r.triage_level ?? "";
  triageForm.addEventListener("submit", (event) => {
    event.preventDefault();
    staffAction(`${base}/triage`, formToJson(triageForm), "Triage gemt");
  });

  const examForm = h("form", {},
    h("div", { class: "checks" }, state.examTypes.map((type) => h("label", {},
      h("input", { type: "checkbox", name: "exam_type_ids", value: type.id, "data-list": true }), type.name))),
    h("div", { class: "actions" }, h("button", {}, "Bestil og send til afdeling")));
  examForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const ids = formToJson(examForm).exam_type_ids?.map(Number) ?? [];
    staffAction(`${base}/examinations`, { exam_type_ids: ids }, "Undersøgelse bestilt og sendt til afdelingen");
  });

  show($("#patient-detail"),
    h("h2", {}, `${r.name} · ${r.reg_number} `, arrived ? triageBadge(r.triage_level) : null),
    h("p", {}, statusBadge(r.status), " ",
      r.patient_updated_at ? badge(`opdateret af patient ${formatDate(r.patient_updated_at)}`, updatedSinceTriage ? "danger" : "muted") : null),
    h("dl", { class: "facts" },
      h("dt", {}, "Født"), h("dd", {}, r.birth_date),
      h("dt", {}, "Registreret"), h("dd", {}, `${formatDate(r.created_at)} · ${r.registered_from === "HJEMMEFRA" ? "hjemmefra" : "ved ankomst"} · sprog: ${r.language}`),
      h("dt", {}, "Ventet"), h("dd", {}, r.waited_minutes === null ? "Ikke ankommet endnu" : `${r.waited_minutes} min.`),
      h("dt", {}, "Symptomer"), h("dd", {}, r.symptoms),
      h("dt", {}, "Skadetype"), h("dd", {}, TEXT.da.injury[r.injury_type]),
      h("dt", {}, "Smertegrad"), h("dd", {}, `${r.pain_level} af 10`),
      h("dt", {}, "Medicin"), h("dd", {}, r.medication || "Ingen oplyst"),
      h("dt", {}, "Allergier"), h("dd", {}, r.allergies ? badge(r.allergies, "danger") : "Ingen oplyst"),
      r.triaged_at ? [h("dt", {}, "Vurderet af"), h("dd", {}, `${r.triaged_by_name} · ${formatDate(r.triaged_at)}`)] : null),

    closed || !arrived ? null : [h("h3", {}, "Triage"), triageForm],

    h("h3", { style: "margin-top:16px" }, "Undersøgelser"),
    examinations.length ? h("ul", { class: "list" }, examinations.map((e) => h("li", {},
      h("strong", {}, e.exam_name), ` → ${e.department_name} `,
      badge(e.status.toLowerCase(), e.status === "UDFØRT" ? "ok" : "warn"),
      h("br"), h("small", { class: "muted" }, `Bestilt af ${e.ordered_by_name} ${formatDate(e.ordered_at)}`,
        e.completed_at ? ` · udført af ${e.completed_by_name} ${formatDate(e.completed_at)}` : "")))) : h("p", { class: "empty" }, "Ingen undersøgelser bestilt."),
    closed || !arrived ? null : examForm,

    closed || !arrived ? null : h("div", { class: "actions", style: "margin-top:16px" },
      h("button", { disabled: r.status === "VENTER_PÅ_LÆGE", onclick: () => staffAction(`${base}/status`, { status: "VENTER_PÅ_LÆGE" }, "Patienten venter nu på lægen") }, "Send til læge"),
      h("button", { class: "secondary", disabled: currentUser().role !== "LÆGE", title: "Kun læger kan afslutte forløbet",
        onclick: () => staffAction(`${base}/status`, { status: "AFSLUTTET" }, "Forløbet er afsluttet") }, "Afslut forløb")),

    h("h3", { style: "margin-top:16px" }, "Forløb"),
    h("ul", { class: "list" }, timeline.map((e) => h("li", {}, `${formatDate(e.created_at)} · ${TEXT.da.status[e.status]}`,
      h("small", { class: "muted" }, ` · ${e.staff_name ?? "patienten"}`)))),

    h("h3", { style: "margin-top:16px" }, "Tidligere besøg"),
    history.length ? h("ul", { class: "list" }, history.map((v) => h("li", {},
      h("strong", {}, `${formatDate(v.created_at)} · ${TEXT.da.injury[v.injury_type]} `), v.triage_level ? triageBadge(v.triage_level) : null,
      h("br"), v.symptoms, v.triage_note ? h("small", { class: "muted" }, ` · ${v.triage_note}`) : null))) : h("p", { class: "empty" }, "Ingen tidligere besøg."),
  );
}

// ---------------------------------------------------------------- Undersøgelser sendt til afdelingerne (FR6)
async function loadExams() {
  const user = currentUser();
  const department = state.departments.find((d) => d.id === user?.department_id);
  $("#exams-title").textContent = department ? `Bestilte undersøgelser til ${department.name}` : "Bestilte undersøgelser – alle afdelinger";
  const rows = await userApi("/examinations");
  const open = rows.filter((e) => e.status === "BESTILT").length;
  $("#exam-count").textContent = open ? `(${open})` : "";
  renderTable($("#exam-table"), rows, [
    { label: "Bestilt", render: (e) => formatDate(e.ordered_at) },
    { label: "Undersøgelse", render: (e) => h("span", {}, h("strong", {}, e.exam_name), h("br"), h("small", { class: "muted" }, e.department_name)) },
    { label: "Patient", render: (e) => h("span", {}, e.patient_name, h("br"), h("small", { class: "muted" }, `${e.reg_number} · f. ${e.birth_date}`)) },
    { label: "Triage", render: (e) => triageBadge(e.triage_level) },
    { label: "Symptomer", render: (e) => `${TEXT.da.injury[e.injury_type]}: ${e.symptoms}` },
    { label: "Allergier", render: (e) => (e.allergies ? badge(e.allergies, "danger") : "–") },
    { label: "Status", render: (e) => (e.status === "UDFØRT" ? badge(`udført ${formatDate(e.completed_at)}`, "ok") : badge("bestilt", "warn")) },
    { label: "", render: (e) => (e.status === "BESTILT"
      ? h("button", { class: "small", onclick: () => staffAction(`/examinations/${e.id}/complete`, {}, "Undersøgelsen er markeret som udført") }, "Markér udført")
      : "") },
  ], "Ingen bestilte undersøgelser");
}

// ---------------------------------------------------------------- Overblik og log
async function loadOverview() {
  const s = await api("/stats");
  $("#stats-kpis").replaceChildren(
    kpi(s.active, "aktive forløb"),
    kpi(s.not_triaged, "ankommet, ikke vurderet"),
    kpi(s.not_arrived, "registreret hjemmefra, ikke ankommet"),
    kpi(s.open_examinations, "åbne undersøgelser"),
    kpi(s.avg_wait_minutes === null ? null : `${s.avg_wait_minutes} min.`, "gennemsnitlig ventetid (aktive)"),
    kpi(s.avg_fill_seconds === null ? null : `${Math.floor(s.avg_fill_seconds / 60)}:${String(s.avg_fill_seconds % 60).padStart(2, "0")}`, "gennemsnitlig udfyldelsestid"),
    kpi(`${s.within_fill_limit}/${s.fill_measured}`, "udfyldt på højst 5 min."),
  );
  $("#stats-assumption").textContent = s.assumption;
  renderTable($("#status-table"), STATUS_ORDER.map((status) => ({ status, count: s.per_status.find((p) => p.status === status)?.count ?? 0 })), [
    { label: "Status", render: (row) => statusBadge(row.status) },
    { label: "Antal", class: "num", key: "count" },
  ]);
  if (!isClinical()) {
    $("#log-table").replaceChildren(h("p", { class: "empty" }, "Loggen kan kun ses af sygeplejersker og læger."));
    return;
  }
  renderTable($("#log-table"), await userApi("/access-log"), [
    { label: "Tid", render: (l) => formatDate(l.created_at) },
    { label: "Medarbejder", key: "staff_name" },
    { label: "Patient", key: "reg_number" },
    { label: "Handling", key: "action" },
  ], "Ingen opslag endnu");
}

// ---------------------------------------------------------------- Opsætning (CRUD)
async function loadAdmin() {
  [state.examTypes, state.departments] = await Promise.all([api("/exam-types"), api("/departments")]);
  fillSelect($("#exam-type-form [name=department_id]"), state.departments, (d) => d.name);
  renderTable($("#exam-type-table"), state.examTypes, [
    { label: "Undersøgelse", key: "name" },
    { label: "Udføres af", render: (e) => state.departments.find((d) => d.id === e.department_id)?.name },
    { label: "", render: (e) => crudButtons("exam-types", $("#exam-type-form"), e, reloadEverything) },
  ]);
  renderTable($("#department-table"), state.departments, [
    { label: "Afdeling", key: "name" },
    { label: "", render: (d) => crudButtons("departments", $("#department-form"), d, reloadEverything) },
  ]);
}

function reloadEverything() {
  return loadAdmin().then(loadStaffViews);
}

bindCrudForm($("#exam-type-form"), "exam-types", reloadEverything);
bindCrudForm($("#department-form"), "departments", reloadEverything);

// ---------------------------------------------------------------- Start
async function loadStaff() {
  state.staff = await api("/staff");
  fillSelect($("#user-select"), state.staff, (s) => s.name);
  state.userId = Number($("#user-select").value);
}

async function loadStaffViews() {
  await Promise.all([loadQueue(), loadExams(), loadOverview()]);
  if (state.selectedId && isClinical()) renderDetail(await userApi(`/registrations/${state.selectedId}`));
}

$("#user-select").addEventListener("change", (event) => {
  state.userId = Number(event.target.value);
  loadStaffViews();
});

setupTabs((tab) => {
  if (tab === "queue") loadQueue();
  if (tab === "exams") loadExams();
  if (tab === "overview") loadOverview();
});

applyLanguage();
Promise.all([loadStaff(), loadAdmin()])
  .then(loadStaffViews)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
