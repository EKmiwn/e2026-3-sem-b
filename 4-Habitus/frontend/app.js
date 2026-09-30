// Habitus – tale-til-tekst – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { userId: null, residents: [], recording: false, startedAt: null, recognition: null, confidences: [] };

const CATEGORY_TEXT = { OBSERVATION: "Observation", UDVIKLING: "Udvikling", MEDICIN: "Medicin" };
const CATEGORY_BADGE = { OBSERVATION: "", UDVIKLING: "ok", MEDICIN: "warn" };
const STATUS_BADGE = { AFVENTER_GODKENDELSE: "warn", GODKENDT: "ok", FORKASTET: "muted" };

// Alle kald sender den valgte medarbejder med (simuleret login)
function userApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-User-Id": state.userId } });
}

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

function meter(value, label) {
  return h("div", {}, h("small", { class: "muted" }, `${label}: ${Math.round(value * 100)} %`),
    h("div", { class: "meter" }, h("span", { style: `width:${Math.round(value * 100)}%` })));
}

function residentName(id) {
  return state.residents.find((r) => r.id === id)?.name ?? "–";
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [staff, departments] = await Promise.all([api("/staff"), api("/departments")]);
  const previous = state.userId;
  fillSelect($("#user-select"), staff, (s) => `${s.name} · ${departments.find((d) => d.id === s.department_id)?.name}`);
  if (previous) $("#user-select").value = previous;
  state.userId = Number($("#user-select").value);
  fillSelect($("#resident-form [name=department_id]"), departments, (d) => d.name);
  await loadResidents();
}

async function loadResidents() {
  state.residents = await userApi("/my-residents");
  fillSelect($("#record-resident"), state.residents, (r) => `${r.name} (${r.room ?? ""})`, { placeholder: "Lad systemet foreslå" });
  const journalSelect = $("#journal-resident");
  const previous = journalSelect.value;
  fillSelect(journalSelect, state.residents, (r) => r.name);
  if (previous && state.residents.some((r) => String(r.id) === previous)) journalSelect.value = previous;
}

// ---------------------------------------------------------------- Optag: start/stop med tydelig status (afsnit 9 og 10)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
$("#speech-support").textContent = SpeechRecognition
  ? "Browseren kan genkende dansk tale. Tillad brug af mikrofonen."
  : "Browseren understøtter ikke talegenkendelse – skriv teksten, som om du talte.";

function setStatus(status) {
  const el = $("#rec-status");
  el.textContent = status;
  el.className = `rec-status ${status}`;
}

function startRecording() {
  state.recording = true;
  state.startedAt = Date.now();
  state.confidences = [];
  $("#record-button").textContent = "■ Stop";
  $("#record-button").classList.add("recording");
  setStatus("OPTAGER");
  if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = "da-DK";
    recognition.continuous = true;
    recognition.interimResults = false;
    const before = $("#transcript").value;
    recognition.onresult = (event) => {
      let text = "";
      for (const result of event.results) {
        text += result[0].transcript;
        state.confidences.push(result[0].confidence || 0.9);
      }
      $("#transcript").value = `${before} ${text}`.trim();
    };
    recognition.onerror = (event) => toast(`Talegenkendelse: ${event.error}`, "error");
    recognition.start();
    state.recognition = recognition;
  } else {
    $("#transcript").focus();
  }
}

async function stopRecording() {
  state.recording = false;
  state.recognition?.stop();
  state.recognition = null;
  $("#record-button").textContent = "● Start";
  $("#record-button").classList.remove("recording");
  const transcript = $("#transcript").value.trim();
  if (!transcript) {
    setStatus("KLAR");
    toast("Der blev ikke optaget noget", "error");
    return;
  }
  setStatus("BEHANDLER");
  const confidence = state.confidences.length
    ? state.confidences.reduce((a, b) => a + b, 0) / state.confidences.length
    : 1;
  try {
    const result = await run(() => userApi("/recordings", {
      method: "POST",
      body: {
        transcript,
        resident_id: Number($("#record-resident").value) || null,
        transcript_confidence: Number(confidence.toFixed(2)),
        duration_sec: Math.max(1, Math.round((Date.now() - state.startedAt) / 1000)),
      },
    }), (r) => r.message);
    setStatus(result.recording.status === "GODKENDT" ? "GEMT" : "AFVENTER");
    renderResult(result);
    $("#transcript").value = "";
    loadPending();
    loadOverview();
  } catch {
    setStatus("KLAR");
  }
}

$("#record-button").addEventListener("click", () => (state.recording ? stopRecording() : startRecording()));

document.querySelectorAll("[data-example]").forEach((button) => button.addEventListener("click", () => {
  $("#transcript").value = button.dataset.example;
}));

function renderResult({ recording: r, keywords, message }) {
  $("#result").replaceChildren(
    h("p", {}, badge(CATEGORY_TEXT[r.category], CATEGORY_BADGE[r.category]), " ",
      badge(r.status.replaceAll("_", " ").toLowerCase(), STATUS_BADGE[r.status])),
    h("p", { style: "font-size:1.05rem" }, `"${r.transcript}"`),
    h("p", {}, "Beboer: ", h("strong", {}, r.resident_name ?? (r.suggested_resident_name ? `${r.suggested_resident_name} (forslag)` : "ikke genkendt"))),
    h("p", {}, "Felt: ", h("strong", {}, `Sofus · ${r.target_field}`), r.handover ? " + Outlook · Vagtoverlevering" : ""),
    meter(r.category_confidence, "Sikkerhed på kategori"),
    meter(r.transcript_confidence, "Sikkerhed på transskription"),
    ...r.uncertain.map((u) => h("div", { class: "warning" }, `⚠ ${u.text}`)),
    h("p", { class: "muted" }, "Genkendte ord: ", Object.entries(keywords).filter(([, w]) => w.length)
      .map(([c, w]) => `${CATEGORY_TEXT[c]}: ${w.join(", ")}`).join(" · ") || "ingen"),
    h("p", {}, message),
    r.status === "AFVENTER_GODKENDELSE"
      ? h("button", { onclick: () => document.querySelector('.tabs button[data-tab="approve"]').click() }, "Gå til godkendelse")
      : null,
  );
}

// ---------------------------------------------------------------- Godkendelse: gennemse, ret og godkend
async function loadPending() {
  const rows = await userApi("/recordings?status=AFVENTER_GODKENDELSE");
  $("#pending-count").textContent = rows.length ? `(${rows.length})` : "";
  $("#pending").replaceChildren(...(rows.length ? rows.map(pendingCard)
    : [h("div", { class: "card" }, h("p", { class: "empty" }, "Intet afventer godkendelse."))]));
}

function pendingCard(r) {
  const residentSelect = h("select", { name: "resident_id", "data-number": true });
  fillSelect(residentSelect, state.residents, (x) => x.name, { placeholder: "Vælg beboer" });
  residentSelect.value = r.resident_id ?? r.suggested_resident_id ?? "";
  const categorySelect = h("select", { name: "category" },
    Object.entries(CATEGORY_TEXT).map(([value, text]) => h("option", { value }, text)));
  categorySelect.value = r.category;
  const form = h("form", {},
    h("div", { class: "row" }, h("label", {}, "Beboer", residentSelect), h("label", {}, "Kategori", categorySelect)),
    h("label", {}, "Tekst (ret før godkendelse)", h("textarea", { name: "text", class: "transcript" }, r.transcript)),
    r.contains_medication ? h("label", { style: "display:flex;gap:8px;align-items:center;color:var(--text)" },
      h("input", { type: "checkbox", name: "medication_confirmed" }),
      h("strong", {}, "Jeg bekræfter, at medicin, dosis og tidspunkt er korrekte")) : null,
    h("div", { class: "actions" },
      h("button", {}, "Godkend og overfør"),
      h("button", { type: "button", class: "danger", onclick: () => decide(r.id, "reject") }, "Forkast")));
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    decide(r.id, "approve", formToJson(form));
  });
  return h("div", { class: `card ${r.contains_medication ? "highlight" : ""}` },
    h("h3", {}, badge(CATEGORY_TEXT[r.category], CATEGORY_BADGE[r.category]), " ",
      r.contains_medication ? badge("Medicin – obligatorisk godkendelse", "danger") : null,
      h("span", { class: "muted", style: "font-weight:normal" }, ` · ${r.staff_name} · ${formatDate(r.recorded_at)}`)),
    ...r.uncertain.map((u) => h("div", { class: "warning" }, `⚠ ${u.text}`)),
    form);
}

async function decide(id, action, body) {
  await run(() => userApi(`/recordings/${id}/${action}`, { method: "POST", body: body ?? {} }),
    action === "approve" ? "Godkendt og overført – lydfilen er slettet" : "Forkastet – lydfilen er slettet");
  loadPending();
  loadJournal();
  loadOverview();
}

// ---------------------------------------------------------------- Journal
async function loadJournal() {
  const residentId = $("#journal-resident").value;
  if (!residentId) return;
  const j = await userApi(`/residents/${residentId}/journal`);
  $("#journal-medication").textContent = j.medications.length
    ? `Medicinliste: ${j.medications.map((m) => `${m.name} ${m.dose}${m.is_pn ? " (PN)" : ""}`).join(" · ")}`
    : "Ingen medicin registreret.";
  renderTable($("#journal-table"), j.entries, [
    { label: "Tid", render: (e) => formatDate(e.created_at) },
    { label: "System", render: (e) => badge(e.target_system, e.target_system === "SOFUS" ? "" : "muted") },
    { label: "Felt", key: "target_field" },
    { label: "Tekst", render: (e) => h("span", {}, e.text, e.updated_at ? h("br") : null,
      e.updated_at ? h("small", { class: "muted" }, `Rettet af ${e.updated_by_name} ${formatDate(e.updated_at)}`) : null) },
    { label: "Af", key: "staff_name" },
    {
      label: "",
      render: (e) => h("div", { class: "actions" },
        h("button", { class: "small secondary", onclick: () => editEntry(e) }, "Ret"),
        h("button", { class: "small danger", onclick: () => deleteEntry(e) }, "Slet")),
    },
  ], "Ingen dokumentation endnu");
}

async function editEntry(entry) {
  const text = prompt("Ret teksten", entry.text);
  if (!text || text === entry.text) return;
  await run(() => userApi(`/journal/${entry.id}`, { method: "PUT", body: { text } }), "Posten er rettet");
  loadJournal();
}

async function deleteEntry(entry) {
  if (!confirm("Vil du slette denne post?")) return;
  await run(() => userApi(`/journal/${entry.id}`, { method: "DELETE" }), "Posten er slettet");
  loadJournal();
}

$("#journal-resident").addEventListener("change", loadJournal);

// ---------------------------------------------------------------- Overblik
async function loadOverview() {
  const [s, rows] = await Promise.all([api("/stats"), userApi("/recordings")]);
  $("#stats-kpis").replaceChildren(
    kpi(s.recordings, "optagelser"),
    kpi(s.auto_saved, "gemt uden ekstra gennemsyn"),
    kpi(s.pending, "afventer godkendelse"),
    kpi(s.medication, "med medicin (godkendt manuelt)"),
    kpi(s.audio_stored, "lydfiler endnu ikke slettet"),
    kpi(`${s.minutes_saved} min.`, "anslået sparet tid"),
  );
  $("#stats-assumption").textContent = s.assumption;
  renderTable($("#recording-table"), rows, [
    { label: "Tid", render: (r) => formatDate(r.recorded_at) },
    { label: "Medarbejder", key: "staff_name" },
    { label: "Beboer", render: (r) => r.resident_name ?? r.suggested_resident_name ?? "–" },
    { label: "Kategori", render: (r) => badge(CATEGORY_TEXT[r.category], CATEGORY_BADGE[r.category]) },
    { label: "Status", render: (r) => badge(r.status.replaceAll("_", " ").toLowerCase(), STATUS_BADGE[r.status]) },
    { label: "Lyd", render: (r) => (r.audio_stored ? "gemt midlertidigt" : "slettet") },
    { label: "Tekst", render: (r) => r.final_text ?? r.transcript },
  ]);
}

// ---------------------------------------------------------------- Beboere og medicin (CRUD)
async function loadAdmin() {
  const [residents, medications] = await Promise.all([api("/residents"), api("/medications")]);
  renderTable($("#resident-table"), residents, [
    { label: "Navn", key: "name" },
    { label: "Kaldenavn", key: "nickname" },
    { label: "Værelse", key: "room" },
    { label: "", render: (r) => crudButtons("residents", $("#resident-form"), r, reloadEverything) },
  ]);
  fillSelect($("#medication-form [name=resident_id]"), residents, (r) => r.name);
  renderTable($("#medication-table"), medications, [
    { label: "Beboer", render: (m) => residents.find((r) => r.id === m.resident_id)?.name },
    { label: "Præparat", key: "name" },
    { label: "Dosis", key: "dose" },
    { label: "", render: (m) => (m.is_pn ? badge("PN") : "") },
    { label: "", render: (m) => crudButtons("medications", $("#medication-form"), m, reloadEverything) },
  ]);
}

function reloadEverything() {
  loadBase().then(loadAll);
}

bindCrudForm($("#resident-form"), "residents", reloadEverything);
bindCrudForm($("#medication-form"), "medications", reloadEverything);

// ---------------------------------------------------------------- Start
$("#user-select").addEventListener("change", (event) => {
  state.userId = Number(event.target.value);
  loadResidents().then(loadAll);
});

function loadAll() {
  return Promise.all([loadPending(), loadJournal(), loadOverview(), loadAdmin()]);
}

setupTabs((tab) => {
  if (tab === "approve") loadPending();
  if (tab === "journal") loadJournal();
});
loadBase()
  .then(loadAll)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
