// Hovedstadens Letbane – rejseassistent – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { user: null, lang: "da", stations: [], stationId: "HER", staffId: null, timer: null };

// F-13: dansk og engelsk. Enkelt sprog – "aflyst" frem for "indstillet" (afsnit 16)
const TEXT = {
  da: {
    tagline: "Til tiden, tydelig information og nemme skift", tabHome: "Forside", tabBoard: "Afgange", tabTrip: "Rejse",
    tabFeedback: "Feedback", tabSettings: "Indstillinger", tabStaff: "Personale", myTrips: "Mine rejser",
    operations: "Driftsinformation", station: "Station", connections: "Skift til andre transportmidler", from: "Fra", to: "Til",
    time: "Afgang efter", search: "Find rejse", howWasTrip: "Hvordan var din rejse?", rating: "Vurdering (1 = meget dårlig, 5 = meget god)",
    topic: "Emne", catPunct: "Punktlighed", catInfo: "Information", catSpace: "Plads", catChange: "Skift", catOther: "Andet",
    comment: "Kommentar (valgfri)", send: "Send", settings: "Indstillinger", language: "Sprog", largeText: "Stor tekst",
    notify: "Giv mig besked ved forstyrrelser på mine rejser", save: "Gem", myData: "Mine data", deleteMe: "Slet mine data",
    onTime: "✓ Til tiden", late: "⚠ +{n} min", cancelled: "✕ Aflyst", towards: "mod", updated: "Opdateret kl.",
    noFavorites: "Du har ingen gemte rejser endnu. Find en rejse og tryk 'Gem som favorit'.", next: "Næste afgang",
    in: "om", min: "min", travelTime: "Rejsetid", saveFavorite: "☆ Gem som favorit", favoriteName: "Navn på rejsen (fx Til arbejde)",
    noTrip: "Rejsen kan ikke gennemføres med letbanen lige nu.", alternative: "Alternativ rejse", cancelledDepartures: "Aflyste afgange",
    walk: "gå", noMessages: "Ingen driftsforstyrrelser lige nu. 👍", elevator: "Elevator", noElevator: "Ingen elevator",
    bikes: "Cykelparkering", change: "Skiftestation", thanks: "Tak for din feedback!", arrive: "fremme",
    saved: "Gemt", remove: "Fjern", until: "til ca.",
  },
  en: {
    tagline: "On time, clear information and easy connections", tabHome: "Home", tabBoard: "Departures", tabTrip: "Journey",
    tabFeedback: "Feedback", tabSettings: "Settings", tabStaff: "Staff", myTrips: "My journeys",
    operations: "Service updates", station: "Station", connections: "Connections to other transport", from: "From", to: "To",
    time: "Depart after", search: "Find journey", howWasTrip: "How was your journey?", rating: "Rating (1 = very poor, 5 = very good)",
    topic: "Topic", catPunct: "Punctuality", catInfo: "Information", catSpace: "Space", catChange: "Connections", catOther: "Other",
    comment: "Comment (optional)", send: "Send", settings: "Settings", language: "Language", largeText: "Large text",
    notify: "Notify me about disruptions on my journeys", save: "Save", myData: "My data", deleteMe: "Delete my data",
    onTime: "✓ On time", late: "⚠ +{n} min", cancelled: "✕ Cancelled", towards: "to", updated: "Updated",
    noFavorites: "You have no saved journeys yet. Find a journey and tap 'Save as favourite'.", next: "Next departure",
    in: "in", min: "min", travelTime: "Travel time", saveFavorite: "☆ Save as favourite", favoriteName: "Name of the journey (e.g. To work)",
    noTrip: "The journey is not possible by light rail right now.", alternative: "Alternative journey", cancelledDepartures: "Cancelled departures",
    walk: "walk", noMessages: "No disruptions right now. 👍", elevator: "Lift", noElevator: "No lift",
    bikes: "Bike parking", change: "Interchange", thanks: "Thank you for your feedback!", arrive: "arrive",
    saved: "Saved", remove: "Remove", until: "until approx.",
  },
};

function t(key) {
  return TEXT[state.lang][key] ?? key;
}

function translatePage() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  $("#lang-button").textContent = state.lang === "da" ? "English" : "Dansk";
}

function hhmm(value) {
  return value ? new Date(value).toLocaleTimeString("da-DK", { hour: "2-digit", minute: "2-digit" }) : "–";
}

// LF-2: status vises med farve OG tekst/ikon
function statusBadge(line) {
  if (line.status === "AFLYST") return h("span", { class: "st cancel" }, t("cancelled"));
  if (line.forsinkelse_min >= 2) return h("span", { class: "st late" }, t("late").replace("{n}", line.forsinkelse_min));
  return h("span", { class: "st ok" }, t("onTime"));
}

function msgTitle(m) {
  return state.lang === "en" && m.titel_en ? m.titel_en : m.titel_da;
}

function msgText(m) {
  return state.lang === "en" && m.tekst_en ? m.tekst_en : m.tekst_da;
}

function messageCard(m) {
  return h("div", { class: `card msg ${m.alvorlighed}` },
    h("h3", {}, m.alvorlighed === "KRITISK" ? "⛔ " : m.alvorlighed === "ADVARSEL" ? "⚠ " : "ℹ ", msgTitle(m)),
    h("p", {}, msgText(m)),
    m.alternativ_rejse ? h("p", {}, h("strong", {}, `${t("alternative")}: `), m.alternativ_rejse) : null,
    h("small", { class: "muted" }, `${m.beroerte_stationer.map(stationName).join(", ")}`,
      m.forventet_slut_tid ? ` · ${t("until")} ${hhmm(m.forventet_slut_tid)}` : ""));
}

function stationName(id) {
  return state.stations.find((s) => s.station_id === id)?.navn ?? id;
}

function minutesUntil(value) {
  return Math.max(0, Math.round((new Date(value) - Date.now()) / 60000));
}

// ---------------------------------------------------------------- Anonym bruger – id gemmes på enheden
function storedUserId() {
  try { return localStorage.getItem("letbane_bruger_id"); } catch { return null; }
}

function storeUserId(id) {
  try { id ? localStorage.setItem("letbane_bruger_id", id) : localStorage.removeItem("letbane_bruger_id"); } catch { /* privat vindue */ }
}

async function loadUser() {
  const id = storedUserId() || "3f6c2a1e-demo-4b8e-9d11-joan00000001";    // demo-brugeren "Joan" fra testdata
  try {
    state.user = await api(`/brugere/${id}`);
  } catch {
    state.user = await api("/brugere", { method: "POST", body: { sprog: "da" } });
  }
  storeUserId(state.user.bruger_id);
  applyUser();
}

function applyUser() {
  state.lang = state.user.sprog;
  document.body.classList.toggle("large", state.user.stor_tekst);
  const form = $("#settings-form");
  form.elements.sprog.value = state.user.sprog;
  form.elements.stor_tekst.checked = state.user.stor_tekst;
  form.elements.notifikationer_til.checked = state.user.notifikationer_til;
  translatePage();
}

async function saveUser(changes) {
  state.user = await api(`/brugere/${state.user.bruger_id}`, { method: "PUT", body: changes });
  applyUser();
  reloadActive();
}

$("#lang-button").addEventListener("click", () => saveUser({ sprog: state.lang === "da" ? "en" : "da" }));
$("#size-button").addEventListener("click", () => saveUser({ stor_tekst: !state.user.stor_tekst }));

// ---------------------------------------------------------------- Forside
async function loadHome() {
  const [favorites, messages, notices] = await Promise.all([
    api(`/brugere/${state.user.bruger_id}/favoritter`), api("/driftsmeddelelser?aktive=true"),
    api(`/brugere/${state.user.bruger_id}/notifikationer`)]);
  $("#notices").replaceChildren(...notices.map((n) => h("div", { class: "notice" },
    `🔔 ${state.lang === "en" && n.titel_en ? n.titel_en : n.titel_da} – ${n.favorit_navn ?? ""}`,
    n.alternativ_rejse ? h("div", { style: "font-weight:400" }, `${t("alternative")}: ${n.alternativ_rejse}`) : null)));
  $("#favorites").replaceChildren(...(favorites.length ? favorites.map((f) => {
    const leg = f.naeste.rejseben.find((b) => b.type === "LETBANE");
    return h("div", { class: "card fav" },
      h("h3", {}, `★ ${f.navn ?? ""}`), h("p", { class: "muted" }, `${f.fra_navn} → ${f.til_navn}`),
      leg ? h("div", {},
        h("div", { class: "big" }, `${hhmm(leg.forventet_afgang)} `, statusBadge(leg)),
        h("p", {}, `${t("next")} ${t("in")} ${minutesUntil(leg.forventet_afgang)} ${t("min")} · ${t("arrive")} ${hhmm(leg.forventet_ankomst)}`))
        : h("p", { class: "notice" }, t("noTrip"), f.naeste.alternativ_rejse ? h("div", { style: "font-weight:400" }, `${t("alternative")}: ${f.naeste.alternativ_rejse}`) : null),
      h("button", { class: "small secondary", onclick: () => deleteFavorite(f.favorit_id) }, t("remove")));
  }) : [h("p", { class: "empty" }, t("noFavorites"))]));
  $("#messages").replaceChildren(...(messages.length ? messages.map(messageCard) : [h("p", { class: "empty" }, t("noMessages"))]));
}

async function deleteFavorite(id) {
  await run(() => api(`/favoritter/${id}`, { method: "DELETE" }));
  loadHome();
}

// ---------------------------------------------------------------- Afgangstavle – opdateres hvert 30. sekund (P-2, P-3)
async function loadBoard() {
  const station = state.stations.find((s) => s.station_id === state.stationId);
  $("#station-icons").replaceChildren(
    h("span", {}, station.har_elevator ? `🛗 ${t("elevator")}` : `🚫 ${t("noElevator")}`),
    station.cykelparkering ? h("span", {}, `🚲 ${t("bikes")}`) : null,
    station.er_skiftestation ? h("span", {}, `🔁 ${t("change")}`) : null);
  const [board, connections] = await Promise.all([api(`/stationer/${state.stationId}/afgange`), api(`/stationer/${state.stationId}/skift`)]);
  $("#board-updated").textContent = `${t("updated")} ${hhmm(board.opdateret_tid)}`;
  $("#board-messages").replaceChildren(...board.driftsmeddelelser.map(messageCard));
  const byDirection = ["SYD", "NORD"].map((dir) => board.afgange.filter((a) => a.retning === dir));
  $("#board").replaceChildren(...byDirection.filter((lines) => lines.length).map((lines) => h("div", { class: "card" },
    h("h3", {}, `${t("towards")} ${lines[0].mod}`),
    h("table", { class: "board" }, h("tbody", {}, lines.map((a) => h("tr", { class: a.status },
      h("td", { class: "time" }, hhmm(a.planlagt_afgang)),
      h("td", {}, statusBadge(a)),
      h("td", { class: "num" }, a.status === "AFLYST" ? "" : `${minutesUntil(a.forventet_afgang)} ${t("min")}`))))))));
  renderTable($("#connections"), connections, [
    { label: "", render: (c) => ({ S_TOG: "🚆", REGIONALTOG: "🚄", BUS: "🚌", METRO: "🚇" }[c.type]) },
    { label: "", render: (c) => h("strong", {}, c.linje) },
    { label: "", render: (c) => `${c.gangtid_min} ${t("min")} ${t("walk")}` },
    { label: "", key: "beskrivelse" },
  ], "–");
}

$("#station-select").addEventListener("change", (event) => {
  state.stationId = event.target.value;
  loadBoard();
});

// ---------------------------------------------------------------- Rejsesøgning
$("#trip-form").addEventListener("submit", (event) => {
  event.preventDefault();
  searchTrip();
});

async function searchTrip() {
  const q = formToJson($("#trip-form"));
  const params = new URLSearchParams({ fra: q.fra, til: q.til });
  if (q.tid) params.set("tid", q.tid);
  const r = await run(() => api(`/rejse?${params}`));
  const leg = r.rejseben.find((b) => b.type === "LETBANE");
  const changes = r.rejseben.filter((b) => b.type === "SKIFT");
  $("#trip-result").replaceChildren(h("div", { class: "card highlight" },
    h("h2", {}, `${r.fra_navn} → ${r.til_navn}`),
    leg ? h("div", {},
      h("p", { class: "fav" }, h("span", { class: "big" }, `${hhmm(leg.forventet_afgang)} → ${hhmm(leg.forventet_ankomst)} `), statusBadge(leg)),
      h("p", {}, `${t("travelTime")}: ${r.samlet_rejsetid_min} ${t("min")} · ${t("in")} ${r.ventetid_min} ${t("min")}`))
      : h("p", { class: "notice" }, t("noTrip")),
    r.alternativ_rejse ? h("p", {}, h("strong", {}, `${t("alternative")}: `), r.alternativ_rejse) : null,
    r.aflyste_afgange.length ? h("p", { class: "muted" }, `${t("cancelledDepartures")}: ${r.aflyste_afgange.map((a) => hhmm(a.planlagt_afgang)).join(", ")}`) : null,
    changes.length ? h("div", {}, h("h3", {}, `🔁 ${t("connections")} – ${r.til_navn}`),
      h("ul", { class: "list" }, changes.map((c) => h("li", {}, h("strong", {}, c.linje), ` · ${c.gangtid_min} ${t("min")} ${t("walk")} · ${c.beskrivelse ?? ""}`)))) : null,
    ...r.driftsmeddelelser.map(messageCard),
    h("button", { class: "secondary", onclick: () => saveFavorite(r) }, t("saveFavorite"))));
}

async function saveFavorite(r) {
  const name = prompt(t("favoriteName"), "");
  if (name === null) return;
  await run(() => api("/favoritter", {
    method: "POST", body: { bruger_id: state.user.bruger_id, fra_station_id: r.fra_station_id, til_station_id: r.til_station_id, navn: name },
  }), t("saved"));
  loadHome();
}

// ---------------------------------------------------------------- Feedback
$("#feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await run(() => api("/feedback", { method: "POST", body: { ...formToJson(event.target), bruger_id: state.user.bruger_id } }), t("thanks"));
  event.target.reset();
});

// ---------------------------------------------------------------- Indstillinger og mine data (S-4)
$("#settings-form").addEventListener("submit", (event) => {
  event.preventDefault();
  saveUser(formToJson(event.target)).then(() => toast(t("saved")));
});

async function loadMyData() {
  const d = await api(`/brugere/${state.user.bruger_id}/data`);
  $("#my-data").replaceChildren(h("ul", { class: "list" },
    h("li", {}, h("strong", {}, "bruger_id: "), h("code", {}, d.bruger.bruger_id), h("br"), h("small", { class: "muted" }, d.formaal.bruger_id)),
    h("li", {}, h("strong", {}, `${d.favoritter.length} favoritter`), h("br"), h("small", { class: "muted" }, d.formaal.favoritter)),
    h("li", {}, h("strong", {}, `${d.feedback.length} feedback`), h("br"), h("small", { class: "muted" }, d.formaal.feedback))));
}

$("#delete-me").addEventListener("click", async () => {
  if (!confirm(t("deleteMe") + "?")) return;
  await run(() => api(`/brugere/${state.user.bruger_id}`, { method: "DELETE" }));
  storeUserId(null);
  state.user = await api("/brugere", { method: "POST", body: { sprog: state.lang } });
  storeUserId(state.user.bruger_id);
  applyUser();
  loadMyData();
});

// ---------------------------------------------------------------- Personale (S-2)
function staffApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-Personale-Id": state.staffId } });
}

async function loadStaff() {
  const [messages, report, status] = await Promise.all([
    api("/driftsmeddelelser?aktive=true"), staffApi("/feedback/rapport"), api("/status")]);
  $("#status-kpis").replaceChildren(
    ...[[`${status.punktlighed_pct ?? "–"} %`, "punktlighed i dag (≤ 2 min)"], [status.forsinkede, "forsinkede afgange"],
      [status.delvist_aflyste, "delvist aflyste"], [status.aflyste, "aflyste"], [status.aktive_meddelelser, "aktive meddelelser"]]
      .map(([v, l]) => h("div", { class: "kpi" }, h("div", { class: "value" }, v), h("div", { class: "label" }, l))));
  renderTable($("#staff-messages"), messages, [
    { label: "Id", key: "meddelelse_id" },
    { label: "Titel", key: "titel_da" },
    { label: "", render: (m) => badge(m.alvorlighed, m.alvorlighed === "KRITISK" ? "danger" : m.alvorlighed === "ADVARSEL" ? "warn" : "") },
    { label: "Afgange", class: "num", key: "antal_beroerte_afgange" },
    {
      label: "",
      render: (m) => h("button", {
        class: "small secondary",
        onclick: async () => {
          await run(() => staffApi(`/driftsmeddelelser/${m.meddelelse_id}/afslut`, { method: "PUT" }), "Meddelelsen er afsluttet");
          loadStaff();
        },
      }, "Afslut"),
    },
  ], "Ingen aktive meddelelser");
  $("#feedback-report").replaceChildren(
    h("p", {}, `${report.antal} svar · gennemsnit ${report.gennemsnit ?? "–"} / 5`),
    h("div", {}, renderInto(report.kategorier, [
      { label: "Kategori", key: "kategori" }, { label: "Antal", class: "num", key: "antal" }, { label: "Gns.", class: "num", key: "gennemsnit" }])),
    h("ul", { class: "list" }, report.kommentarer.map((k) => h("li", {}, badge(k.kategori, "muted"), ` ${k.vurdering}/5 – ${k.kommentar}`))));
}

function renderInto(rows, columns) {
  const box = h("div");
  renderTable(box, rows, columns);
  return box;
}

$("#staff-select").addEventListener("change", (event) => {
  state.staffId = event.target.value;
  loadStaff();
});

$("#message-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const { minutter, ...data } = formToJson(event.target);
  data.beroerte_stationer = [...document.querySelectorAll("#station-checks input:checked")].map((c) => c.value);
  data.forventet_slut_tid = new Date(Date.now() + (minutter || 60) * 60000).toISOString();
  await run(() => staffApi("/driftsmeddelelser", { method: "POST", body: data }),
    (r) => `${r.driftsmeddelelse.meddelelse_id} udsendt – ${r.driftsmeddelelse.antal_beroerte_afgange} afgange berørt, ${r.notificerede_brugere} brugere får besked`);
  event.target.reset();
  loadStaff();
});

// ---------------------------------------------------------------- Start
function reloadActive() {
  const tab = document.querySelector(".tabs button.active")?.dataset.tab;
  ({ home: loadHome, board: loadBoard, settings: loadMyData, staff: loadStaff })[tab]?.();
}

async function start() {
  state.stations = await api("/stationer");
  for (const select of [$("#station-select"), $("#trip-form [name=fra]"), $("#trip-form [name=til]")]) {
    fillSelect(select, state.stations, (s) => s.navn, { valueKey: "station_id" });
  }
  $("#station-select").value = state.stationId;
  $("#trip-form [name=fra]").value = "LYN";
  $("#trip-form [name=til]").value = "GLO";
  $("#station-checks").replaceChildren(...state.stations.map((s) => h("label", {}, h("input", { type: "checkbox", value: s.station_id }), ` ${s.navn}`)));
  const staffList = await api("/personale");
  fillSelect($("#staff-select"), staffList, (p) => `${p.personale_id} · ${p.rolle.toLowerCase()}`);
  $("#staff-select").value = "P-044";
  state.staffId = "P-044";
  await loadUser();
  loadHome();
  clearInterval(state.timer);
  state.timer = setInterval(() => { if (!document.hidden) reloadActive(); }, 30000);
}

setupTabs(() => reloadActive());
start().catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
