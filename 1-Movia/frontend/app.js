// Movia – Den Forudsigelige Rejse – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { passengerId: null, tripId: null, lastSearch: null };

const LEVEL_TEXT = { ROLIG: "Rolig", MIDDEL: "Middel", TRAVL: "Travl" };
const AREA_TEXT = { FORREST: "Forrest", MIDTEN: "Midten", BAGERST: "Bagerst" };

function levelBadge(level) {
  return h("span", { class: `badge level-${level}` }, LEVEL_TEXT[level]);
}

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [stops, passengers, buses] = await Promise.all([api("/stops"), api("/passengers"), api("/buses")]);
  const form = $("#search-form");
  fillSelect(form.elements.from_stop_id, stops, (s) => s.name);
  fillSelect(form.elements.to_stop_id, stops, (s) => s.name);
  form.elements.from_stop_id.value = stops.find((s) => s.name === "Lyngby St.")?.id ?? stops[0].id;
  form.elements.to_stop_id.value = stops.find((s) => s.name === "Østerport St.")?.id ?? stops[1].id;
  form.elements.time.value = new Date().toTimeString().slice(0, 5);

  const previous = state.passengerId;
  fillSelect($("#passenger-select"), passengers, (p) => p.name);
  if (previous) $("#passenger-select").value = previous;
  state.passengerId = Number($("#passenger-select").value);

  fillSelect($("#bus-select"), buses, (b) => b.number);
  fillSelect($("#reading-form [name=bus_id]"), buses, (b) => b.number);
}

// ---------------------------------------------------------------- P1: rolig rute (FR1, FR2, FR8)
$("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  search(formToJson(event.target));
});

async function search(query) {
  state.lastSearch = query;
  const params = new URLSearchParams(query);
  const result = await run(() => api(`/journeys?${params}`));
  $("#recommendation").replaceChildren(h("div", { class: "card highlight" },
    h("h2", {}, `${result.from_stop} → ${result.to_stop}`),
    h("p", { style: "margin:0;font-size:1.1rem" }, result.recommendation)));
  $("#options").replaceChildren(...result.options.map((o) => h("div", { class: `card option ${o.is_calmest ? "highlight" : ""}` },
    h("div", { class: "actions" }, levelBadge(o.calm.level), o.is_calmest ? badge("Roligste", "ok") : null,
      o.has_quiet_zone ? badge(`Rolig zone ${AREA_TEXT[o.calm.quiet_zone].toLowerCase()}`) : badge("Ingen rolig zone", "muted"),
      o.day === "i morgen" ? badge("i morgen", "warn") : null),
    h("div", { class: "time" }, `${o.leaves_at} → ${o.arrives_at}`),
    h("div", { class: "muted" }, `${o.line} · ${o.travel_min} min · ${o.stops} stop · afgang om ${o.wait_min} min`),
    h("div", { class: "actions" },
      h("button", { class: "secondary", onclick: () => showHeatmap(o.departure_id) }, "Se varmekort"),
      h("button", { onclick: () => chooseDeparture(o, query) }, "Vælg afgang")))));
  $("#heatmap").replaceChildren();
}

async function showHeatmap(departureId) {
  const m = await api(`/departures/${departureId}/heatmap`);
  $("#heatmap").replaceChildren(h("div", { class: "card" },
    h("h2", {}, `Sensorisk varmekort · ${m.line} kl. ${m.departs_at} (${m.bus_number})`),
    h("div", { class: "heat" }, m.areas.map((a) => h("div", { class: `level-${a.level}` },
      h("strong", {}, AREA_TEXT[a.area] + (a.quiet_zone ? " · rolig zone" : "")),
      h("div", {}, LEVEL_TEXT[a.level]),
      h("small", {}, `${Math.round(a.noise_db)} dB · ${a.crowding_pct} % fyldt`)))),
    h("p", { class: "muted" }, `Målt ${formatDate(m.updated_at)}. Samlet vurdering: `, levelBadge(m.level))));
  $("#heatmap").scrollIntoView({ behavior: "smooth" });
}

async function chooseDeparture(option, query) {
  const trip = await run(() => api("/trips", {
    method: "POST",
    body: { passenger_id: state.passengerId, departure_id: option.departure_id,
      from_stop_id: Number(query.from_stop_id), to_stop_id: Number(query.to_stop_id) },
  }), "Rejsen er gemt");
  state.tripId = trip.id;
  await loadTrips();
  document.querySelector('.tabs button[data-tab="trip"]').click();
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
  const box = $("#trip-view");
  if (!state.tripId) {
    box.replaceChildren(h("p", { class: "empty" }, "Vælg en afgang under \"Planlæg rejse\"."));
    return;
  }
  renderTrip(await api(`/trips/${state.tripId}`));
}

function renderTrip(t) {
  const latest = t.notifications[0];
  const actions = {
    PLANLAGT: h("button", { class: "big", onclick: () => tripAction("board") }, "Jeg er steget på"),
    OMBORD: h("button", { class: "big secondary", onclick: () => tripAction("advance") }, "Simulér: bussen kører til næste stop"),
    AFSLUTTET: null,
  };
  $("#trip-view").replaceChildren(h("div", { class: "grid wide" },
    h("div", { class: "card" },
      h("h2", {}, `${t.line} · ${t.bus_number}`),
      h("p", { class: "muted" }, t.quiet_zone !== "INGEN"
        ? `Rolig zone ${AREA_TEXT[t.quiet_zone].toLowerCase()} i bussen.` : "Denne bus har ingen rolig zone."),
      latest ? h("div", { class: "card highlight", style: "font-size:1.1rem" }, latest.message) : null,
      h("ol", { class: "timeline" }, t.timeline.map((s) => h("li", { class: s.state },
        h("span", { class: "dot" }), h("span", {}, s.time),
        h("span", {}, s.name, s.is_destination ? " 🏁" : "", s.state === "HER" ? " – du er her" : "")))),
      h("div", { class: "actions" }, actions[t.status]),
      t.status === "OMBORD" ? h("p", { class: "muted" }, `${t.stops_left} stop tilbage`) : null),
    h("div", { class: "card" },
      h("h3", {}, "Solsikkesignal"),
      t.signal ? h("p", {}, badge(t.signal.status.replaceAll("_", " "), t.signal.acknowledged_at ? "ok" : "warn"),
        ` sendt ${formatDate(t.signal.sent_at)} ved ${t.signal.stop_name}`)
        : h("p", { class: "muted" }, t.status === "PLANLAGT" ? "Sendes automatisk, når du stiger på (hvis slået til i profilen)."
          : "Intet signal sendt – solsikkesignalet er slået fra i din profil."),
      h("h3", {}, "Notifikationer"),
      h("ul", { class: "list" }, t.notifications.map((n) => h("li", {}, h("small", { class: "muted" }, formatDate(n.created_at)), h("br"), n.message))),
      t.status === "AFSLUTTET" ? feedbackBox(t) : null)));
}

function feedbackBox(t) {
  if (t.feedback) {
    return h("p", {}, badge("Tak for din feedback", "ok"), ` Rolighed ${t.feedback.calm_rating}/5`);
  }
  const form = h("form", {},
    h("h3", {}, "Hvordan var rejsen?"),
    h("label", {}, "Hvor rolig var rejsen? (1–5)", h("input", { type: "number", name: "calm_rating", min: 1, max: 5, value: 4, required: true })),
    h("label", { style: "display:flex;gap:8px;align-items:center" }, h("input", { type: "checkbox", name: "felt_safe", checked: true }), "Jeg følte mig tryg"),
    h("label", {}, "Kommentar (valgfri)", h("textarea", { name: "comment" })),
    h("button", {}, "Send feedback"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    renderTrip(await run(() => api(`/trips/${t.id}/feedback`, { method: "POST", body: formToJson(form) }), "Tak for din feedback"));
    loadStats();
  });
  return form;
}

async function tripAction(action) {
  renderTrip(await run(() => api(`/trips/${state.tripId}/${action}`, { method: "POST" })));
  loadTrips();
  loadDriver();
}

$("#trip-select").addEventListener("change", (event) => {
  state.tripId = Number(event.target.value) || null;
  loadTrip();
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

// ---------------------------------------------------------------- Sensordata (P2, NFR1)
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
  const passenger = await api(`/passengers/${state.passengerId}`);
  const form = $("#profile-form");
  for (const field of form.elements) {
    if (field.name && field.name in passenger) field.value = passenger[field.name] ?? "";
  }
}

bindCrudForm($("#profile-form"), "passengers", () => loadBase().then(loadAll));

$("#passenger-select").addEventListener("change", (event) => {
  state.passengerId = Number(event.target.value);
  state.tripId = null;
  loadAll();
});

// ---------------------------------------------------------------- Start
function loadAll() {
  return Promise.all([loadTrips(), loadDriver(), loadFleet(), loadStats(), loadProfile()]);
}

setupTabs((tab) => {
  if (tab === "driver") loadDriver();
  if (tab === "sensors") loadFleet();
});
loadBase()
  .then(loadAll)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
