// Movia – Den Forudsigelige Rejse – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { passengerId: null, passenger: null, tripId: null, lastSearch: null, suggestion: null, recognition: null, greeted: false };

const LEVEL_TEXT = { ROLIG: "Rolig", MIDDEL: "Middel", TRAVL: "Travl" };
const LEVEL_SENTENCE = { ROLIG: "Der er roligt i bussen", MIDDEL: "Der er nogenlunde roligt i bussen", TRAVL: "Der er travlt i bussen" };
const AREA_TEXT = { FORREST: "Forrest", MIDTEN: "Midten", BAGERST: "Bagerst" };

function levelBadge(level) {
  return h("span", { class: `badge level-${level}` }, LEVEL_TEXT[level]);
}

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

// Som replaceChildren(), men springer null over og folder lister ud – ligesom h()
function show(container, ...children) {
  container.replaceChildren(...h("div", {}, children).childNodes);
}

function activeTab() {
  return document.querySelector(".tabs button.active")?.dataset.tab;
}

function openTab(name) {
  document.querySelector(`.tabs button[data-tab="${name}"]`).click();
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [stops, passengers, buses] = await Promise.all([api("/stops"), api("/passengers"), api("/buses")]);
  const form = $("#search-form");
  const chosen = { from: form.elements.from_stop_id.value, to: form.elements.to_stop_id.value };
  fillSelect(form.elements.from_stop_id, stops, (s) => s.name);
  fillSelect(form.elements.to_stop_id, stops, (s) => s.name);
  form.elements.from_stop_id.value = chosen.from || (stops.find((s) => s.name === "Husum Torv")?.id ?? stops[0].id);
  form.elements.to_stop_id.value = chosen.to || (stops.find((s) => s.name === "Nørreport St.")?.id ?? stops[1].id);

  const previous = state.passengerId;
  fillSelect($("#passenger-select"), passengers, (p) => p.name);
  if (previous) $("#passenger-select").value = previous;
  state.passengerId = Number($("#passenger-select").value);

  fillSelect($("#bus-select"), buses, (b) => b.number);
  fillSelect($("#reading-form [name=bus_id]"), buses, (b) => b.number);
}

// ---------------------------------------------------------------- P1: rolig rute (FR1, FR2, FR8)
$("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = await search(formToJson(event.target));
  guideSay(`${result.recommendation.replace("kl.", "klokken")}. Tryk på Vælg denne rejse, eller sig ja tak.`);
});

function heatRow(calm) {
  return h("div", { class: "heat" }, calm.areas.map((a) => h("div", { class: `level-${a.level}` },
    h("strong", {}, AREA_TEXT[a.area] + (a.quiet_zone ? " · rolig zone" : "")),
    h("div", {}, LEVEL_TEXT[a.level]),
    h("small", {}, `${Math.round(a.noise_db)} dB · ${a.crowding_pct} % fyldt`))));
}

// Viser kun den anbefalede (roligste) afgang stort. De andre afgange ligger foldet sammen nedenunder.
async function search(query) {
  state.lastSearch = query;
  const result = await run(() => api(`/journeys?${new URLSearchParams(query)}`));
  const best = result.options.find((o) => o.is_calmest);
  const others = result.options.filter((o) => o !== best);
  state.suggestion = { departure_id: best.departure_id, from_stop_id: result.from_stop_id, to_stop_id: result.to_stop_id };
  show($("#recommendation"), h("div", { class: "card highlight best" },
    h("h2", {}, "Vi anbefaler den roligste bus"),
    h("div", { class: "time" }, `${best.leaves_at} → ${best.arrives_at}`),
    h("p", {}, h("strong", {}, `Linje ${best.line}`), ` · ${result.from_stop} → ${result.to_stop}`,
      best.day === "i morgen" ? [" ", badge("i morgen", "warn")] : null),
    h("p", {}, `${best.travel_min} min. · ${best.stops} stop · kører om ${best.wait_min} min.`),
    h("p", {}, levelBadge(best.calm.level), ` ${LEVEL_SENTENCE[best.calm.level]}. `,
      best.has_quiet_zone ? `Rolig zone ${AREA_TEXT[best.calm.quiet_zone].toLowerCase()}.` : "Ingen rolig zone."),
    h("details", { class: "more" }, h("summary", {}, "Se hvor der er roligt i bussen"), heatRow(best.calm),
      h("small", { class: "muted" }, `Målt ${formatDate(best.calm.updated_at)}`)),
    h("button", { class: "big", onclick: () => chooseDeparture(best, query) }, "Vælg denne rejse")));
  show($("#options"), others.length ? h("details", { class: "more card" },
    h("summary", {}, `Se ${others.length} andre afgange`),
    others.map((o) => h("div", { class: "other" },
      h("div", {},
        h("div", { class: "time" }, `${o.leaves_at} → ${o.arrives_at} · ${o.line}`),
        h("div", {}, levelBadge(o.calm.level), h("small", { class: "muted" },
          ` ${o.has_quiet_zone ? `rolig zone ${AREA_TEXT[o.calm.quiet_zone].toLowerCase()}` : "ingen rolig zone"} · om ${o.wait_min} min.`))),
      h("button", { class: "secondary", onclick: () => chooseDeparture(o, query) }, "Vælg")))) : null);
  return result;
}

async function chooseDeparture(option, query) {
  const trip = await run(() => api("/trips", {
    method: "POST",
    body: { passenger_id: state.passengerId, departure_id: option.departure_id,
      from_stop_id: Number(query.from_stop_id), to_stop_id: Number(query.to_stop_id) },
  }), "Rejsen er gemt");
  state.tripId = trip.id;
  state.suggestion = null;
  await loadTrips();
  openTab("trip");
  guideSay(`Rejsen er gemt. Linje ${trip.line} kører klokken ${trip.timeline[0].time} fra ${trip.timeline[0].name}. Tryk på Jeg er steget på, når du er i bussen.`);
}

// ---------------------------------------------------------------- P3 + P4: min rejse (FR3–FR5, FR7)
async function loadTrips() {
  const trips = await api(`/passengers/${state.passengerId}/trips`);
  const select = $("#trip-select");
  fillSelect(select, trips, (t) => `${t.line} kl. ${t.departs_at} · ${t.from_stop} → ${t.to_stop} (${t.status.toLowerCase()})`,
    { placeholder: trips.length ? null : "Ingen rejser endnu" });
  if (state.tripId && trips.some((t) => t.id === state.tripId)) select.value = state.tripId;
  state.tripId = Number(select.value) || null;
  await loadTrip();
}

async function loadTrip() {
  if (!state.tripId) {
    show($("#trip-view"), h("div", { class: "card" },
      h("p", {}, "Du har ikke valgt en rejse endnu."),
      h("button", { class: "big", onclick: () => openTab("plan") }, "Planlæg en rejse")));
    return;
  }
  renderTrip(await api(`/trips/${state.tripId}`));
}

function renderTrip(t) {
  // Ved målet er "stå af her" vigtigere end spørgsmålet om feedback
  const latest = t.notifications.find((n) => n.type === "STÅ_AF_NU") ?? t.notifications[0];
  const step = { PLANLAGT: 0, OMBORD: 1, AFSLUTTET: 2 }[t.status];
  const action = {
    PLANLAGT: h("button", { class: "big", onclick: () => tripAction("board") }, "Jeg er steget på"),
    OMBORD: h("button", { class: "big secondary", onclick: () => tripAction("advance") }, "Simulér: bussen kører til næste stop"),
    AFSLUTTET: h("button", { class: "big secondary", onclick: () => openTab("plan") }, "Planlæg en ny rejse"),
  }[t.status];
  show($("#trip-view"),
    h("div", { class: "steps" }, ["Planlagt", "I bussen", "Fremme"].map((label, i) =>
      h("div", { class: i < step ? "done" : i === step ? "now" : "" }, label))),
    h("div", { class: "card" },
      h("h2", {}, `Linje ${t.line} · ${t.timeline[0].name} → ${t.timeline.at(-1).name}`),
      latest ? h("div", { class: "message" }, latest.message) : null,
      h("ol", { class: "timeline" }, t.timeline.map((s) => h("li", { class: s.state },
        h("span", { class: "dot" }), h("span", {}, s.time),
        h("span", {}, s.name, s.is_destination ? " 🏁" : "", s.state === "HER" ? " – du er her" : "")))),
      t.status === "OMBORD" ? h("p", {}, h("strong", {}, `${t.stops_left} stop tilbage`)) : null,
      action,
      t.status === "OMBORD" ? h("p", { class: "muted", style: "margin-bottom:0" }, "I prototypen flytter knappen bussen. I virkeligheden sker det med bussens GPS. Du får besked, før du skal af.") : null),
    h("div", { class: "card" },
      h("p", {}, "🪑 ", t.quiet_zone !== "INGEN" ? `Rolig zone ${AREA_TEXT[t.quiet_zone].toLowerCase()} i bussen.` : "Denne bus har ingen rolig zone."),
      h("p", { style: "margin-bottom:0" }, "🌻 ", t.signal
        ? (t.signal.acknowledged_at ? "Chaufføren har set dit solsikkesignal." : "Chaufføren har fået dit solsikkesignal.")
        : t.status === "PLANLAGT" ? (state.passenger?.sunflower_enabled ? "Chaufføren får et solsikkesignal, når du stiger på." : "Solsikkesignalet er slået fra i din profil.")
          : "Der blev ikke sendt et solsikkesignal."),
      t.notifications.length > 1 ? h("details", { class: "more" }, h("summary", {}, "Tidligere beskeder"),
        h("ul", { class: "list" }, t.notifications.slice(1).map((n) => h("li", {}, h("small", { class: "muted" }, formatDate(n.created_at)), h("br"), n.message)))) : null),
    t.status === "AFSLUTTET" ? h("div", { class: "card" }, feedbackBox(t)) : null);
}

// Feedback med fem store knapper i stedet for et talfelt
function feedbackBox(t) {
  if (t.feedback) {
    return h("p", { style: "margin:0" }, badge("Tak for din feedback", "ok"), ` Du gav rejsen ${t.feedback.calm_rating} af 5.`);
  }
  let rating = null;
  const buttons = ["😟", "🙁", "😐", "🙂", "😊"].map((face, i) => h("button", {
    type: "button", "aria-label": `${i + 1} af 5`,
    onclick: (event) => {
      rating = i + 1;
      buttons.forEach((b) => b.classList.toggle("chosen", b === event.currentTarget));
    },
  }, face));
  const form = h("form", {},
    h("h2", {}, "Hvor rolig var rejsen?"),
    h("div", { class: "rating" }, buttons),
    h("label", { class: "check" }, h("input", { type: "checkbox", name: "felt_safe", checked: true }), "Jeg følte mig tryg"),
    h("details", { class: "more", style: "margin-top:0" }, h("summary", {}, "Skriv en kommentar"), h("textarea", { name: "comment", "aria-label": "Kommentar" })),
    h("button", { class: "big" }, "Send"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!rating) return toast("Vælg et ansigt først", "error");
    renderTrip(await run(() => api(`/trips/${t.id}/feedback`, { method: "POST", body: { ...formToJson(form), calm_rating: rating } }), "Tak for din feedback"));
    loadStats();
  });
  return form;
}

async function tripAction(action) {
  const trip = await run(() => api(`/trips/${state.tripId}/${action}`, { method: "POST" }));
  renderTrip(trip);
  const news = trip.notifications.find((n) => n.type === "STÅ_AF_NU") ?? trip.notifications[0];
  if (news) guideSay(news.message);                          // guiden læser den nye besked højt
  loadTrips();
  loadDriver();
}

$("#trip-select").addEventListener("change", (event) => {
  state.tripId = Number(event.target.value) || null;
  loadTrip();
});

// ---------------------------------------------------------------- Rejseguiden: stemmeassistent (tale ind og ud i browseren)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function bubble(text, who) {
  const log = $("#guide-log");
  log.append(h("div", { class: `bubble ${who}` }, text));
  log.scrollTop = log.scrollHeight;
}

function voiceOn() {
  return Boolean(state.passenger?.voice_guide);
}

function speak(text) {
  if (!voiceOn() || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();                                  // kun én besked ad gangen
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "da-DK";
  utterance.rate = 0.95;
  const danish = speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith("da"));
  if (danish) utterance.voice = danish;
  speechSynthesis.speak(utterance);
}

// Guiden siger noget af sig selv, fx når rejsen ændrer sig
function guideSay(text) {
  bubble(text, "guide");
  speak(text);
}

function renderVoiceButton() {
  $("#voice-button").textContent = voiceOn() ? "🔊 Læser højt" : "🔇 Kun tekst";
}

async function ask(message) {
  bubble(message, "me");
  let answer;
  try {
    answer = await api("/assistant", {
      method: "POST",
      body: { message, passenger_id: state.passengerId, trip_id: state.tripId, tab: activeTab(),
        from_stop_id: Number($("#search-form").elements.from_stop_id.value) || null, suggestion: state.suggestion },
    });
  } catch (err) {
    return guideSay(`Det kunne jeg ikke lige nu. ${err.message}`);
  }
  guideSay(answer.reply);
  const action = answer.action;
  if (!action) return;
  if (action.type === "SHOW_JOURNEY") {                      // vis forslaget på skærmen, så tale og skærm siger det samme
    const form = $("#search-form");
    form.elements.from_stop_id.value = action.from_stop_id;
    form.elements.to_stop_id.value = action.to_stop_id;
    form.elements.time.value = "";
    openTab("plan");
    await search(formToJson(form));
    state.suggestion = action;
  } else if (action.type === "TRIP_CREATED" || action.type === "TRIP_UPDATED") {
    state.tripId = action.trip_id;
    state.suggestion = null;
    openTab("trip");
    await loadTrips();
    loadDriver();
  } else if (action.type === "OPEN_TAB") {
    openTab(action.tab);
  }
}

function openGuide() {
  $("#guide").hidden = false;
  $("#guide-button").hidden = true;
  if (!state.greeted) {
    state.greeted = true;
    ask("Hej");
  }
}

$("#guide-button").addEventListener("click", openGuide);
$("#guide-close").addEventListener("click", () => {
  $("#guide").hidden = true;
  $("#guide-button").hidden = false;
  window.speechSynthesis?.cancel();
  state.recognition?.stop();
});

$("#guide-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = event.target.elements.message;
  const message = input.value.trim();
  input.value = "";
  if (message) ask(message);
});

document.querySelectorAll("[data-say]").forEach((button) => button.addEventListener("click", () => ask(button.dataset.say)));

$("#voice-button").addEventListener("click", async () => {
  state.passenger = await run(() => api(`/passengers/${state.passengerId}`, { method: "PUT", body: { voice_guide: voiceOn() ? 0 : 1 } }));
  if (!voiceOn()) window.speechSynthesis?.cancel();
  renderVoiceButton();
  loadProfile();
});

// Mikrofonen: tryk, tal, og guiden svarer. Uden talegenkendelse i browseren skriver man i feltet.
$("#mic-button").addEventListener("click", () => {
  if (!SpeechRecognition) {
    guideSay("Din browser kan ikke lytte. Skriv til mig i feltet, så svarer jeg.");
    return $("#guide-form").elements.message.focus();
  }
  if (state.recognition) return state.recognition.stop();
  window.speechSynthesis?.cancel();
  const recognition = new SpeechRecognition();
  recognition.lang = "da-DK";
  recognition.interimResults = false;
  recognition.onresult = (event) => ask(event.results[0][0].transcript);
  recognition.onerror = (event) => { if (event.error !== "no-speech") toast(`Mikrofon: ${event.error}`, "error"); };
  recognition.onend = () => {
    state.recognition = null;
    $("#mic-button").classList.remove("listening");
  };
  state.recognition = recognition;
  $("#mic-button").classList.add("listening");
  recognition.start();
});

// ---------------------------------------------------------------- Chauffør (P3)
async function loadDriver() {
  const busId = $("#bus-select").value;
  if (!busId) return;
  const result = await api(`/buses/${busId}/signals`);
  $("#driver-signals").replaceChildren(result.signals.length
    ? h("div", { class: "grid" }, result.signals.map((s) => h("div", { class: "signal" },
      h("div", {}, `🌻 Solsikke-passager steget på ved ${s.stop_name}`),
      h("small", { class: "muted" }, `Kode ${s.token} · ${formatDate(s.sent_at)}`),
      h("p", { style: "font-size:0.95rem" }, "Giv ekstra tid ved af- og påstigning. Passageren behøver ikke at sige noget."),
      s.status === "SENDT"
        ? h("button", { onclick: () => ackSignal(s.id) }, "Set ✓")
        : badge("Set af chauffør", "ok"))))
    : h("div", { class: "card" }, h("p", { class: "empty" }, `Ingen aktive solsikkesignaler i ${result.bus}.`)));
}

async function ackSignal(id) {
  await run(() => api(`/signals/${id}/ack`, { method: "POST" }), "Signal bekræftet");
  loadDriver();
  loadTrip();
}

$("#bus-select").addEventListener("change", loadDriver);

// ---------------------------------------------------------------- Movia-data: sensorer, linjer og feedback (P2, NFR1)
async function loadFleet() {
  const buses = await api("/fleet");
  renderTable($("#fleet-table"), buses, [
    { label: "Bus", key: "bus_number" },
    { label: "Linje", key: "line" },
    { label: "Rolig zone", render: (b) => (b.quiet_zone === "INGEN" ? "–" : AREA_TEXT[b.quiet_zone]) },
    ...["FORREST", "MIDTEN", "BAGERST"].map((area) => ({
      label: AREA_TEXT[area],
      render: (b) => {
        const a = b.areas.find((x) => x.area === area);
        return a ? h("span", { class: `badge level-${a.level}` }, `${Math.round(a.noise_db)} dB · ${a.crowding_pct} %`) : "–";
      },
    })),
    { label: "Vurdering", render: (b) => levelBadge(b.level) },
    { label: "Opdateret", render: (b) => formatDate(b.updated_at) },
  ]);
}

async function loadLines() {
  const lines = await api("/lines");
  const stops = await Promise.all(lines.map((l) => api(`/lines/${l.id}/stops`)));
  renderTable($("#line-table"), lines.map((l, i) => ({ ...l, stops: stops[i] })), [
    { label: "Linje", render: (l) => h("strong", {}, l.name) },
    { label: "Stoppesteder", render: (l) => l.stops.map((s) => s.name).join(" → ") },
    { label: "Køretid", class: "num", render: (l) => `${l.stops.at(-1).minutes_from_start} min.` },
  ]);
}

async function loadStats() {
  const s = await api("/stats");
  $("#stats-kpis").replaceChildren(
    kpi(s.trips, "rejser planlagt"),
    kpi(s.signals_sent, "solsikkesignaler sendt"),
    kpi(s.signals_acknowledged, "set af chauffør"),
    kpi(s.avg_calm_rating ? `${s.avg_calm_rating}/5` : "–", "oplevet rolighed"),
    kpi(s.felt_safe_pct !== null ? `${s.felt_safe_pct} %` : "–", "følte sig trygge"),
    kpi(s.buses_with_quiet_zone, "busser med rolig zone"),
  );
  renderTable($("#feedback-table"), s.feedback, [
    { label: "Tid", render: (f) => formatDate(f.created_at) },
    { label: "Linje", key: "line" },
    { label: "Rolighed", class: "num", render: (f) => `${f.calm_rating}/5` },
    { label: "Tryg", render: (f) => (f.felt_safe ? badge("Ja", "ok") : badge("Nej", "danger")) },
    { label: "Kommentar", key: "comment" },
  ], "Ingen feedback endnu");
}

$("#simulate-button").addEventListener("click", async () => {
  await run(() => api("/sensors/simulate", { method: "POST" }), (r) => `${r.readings} nye målinger modtaget`);
  loadFleet();
  if (state.lastSearch) search(state.lastSearch);
});

$("#reading-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await run(() => api("/sensor-readings", { method: "POST", body: formToJson(event.target) }), "Måling modtaget");
  loadFleet();
});

// ---------------------------------------------------------------- Profil (FR6)
async function loadProfile() {
  state.passenger = await api(`/passengers/${state.passengerId}`);
  const form = $("#profile-form");
  for (const field of form.elements) {
    if (field.name && field.name in state.passenger) field.value = state.passenger[field.name] ?? "";
  }
  renderVoiceButton();
}

bindCrudForm($("#profile-form"), "passengers", () => loadBase().then(loadAll));

$("#passenger-select").addEventListener("change", (event) => {
  state.passengerId = Number(event.target.value);
  state.tripId = null;
  state.suggestion = null;
  state.greeted = false;
  $("#guide-log").replaceChildren();
  window.speechSynthesis?.cancel();
  loadAll();
});

// Chauffør- og datasiderne er kun til fremvisning og er skjult for passageren som udgangspunkt
$("#demo-button").addEventListener("click", (event) => {
  const on = document.body.classList.toggle("demo");
  event.target.textContent = on ? "Skjul demo-skærme" : "Vis demo-skærme (chauffør og Movia-data)";
  if (!on && ["driver", "sensors"].includes(activeTab())) openTab("plan");
});

// ---------------------------------------------------------------- Start
function loadAll() {
  return Promise.all([loadProfile().then(loadTrips), loadDriver(), loadFleet(), loadLines(), loadStats()]);
}

setupTabs((tab) => {
  if (tab === "driver") loadDriver();
  if (tab === "sensors") loadFleet();
});
loadBase()
  .then(loadAll)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
