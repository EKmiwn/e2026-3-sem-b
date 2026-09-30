// Clever – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { userId: null, user: null, position: null, quoteBody: null, quote: null, sessionId: null, timer: null };

// Simulerede positioner (i appen: telefonens placering, kun med samtykke – SE-4)
const POSITIONS = [
  ["Hjemme i Greve", 55.5900, 12.2700],
  ["Ved Greve Hallen", 55.5887, 12.2991],
  ["Ved Greve Midtby Center", 55.5856, 12.2931],
  ["Ved Køge Nord Lynladepark", 55.4901, 12.1501],
  ["Ved Fisketorvet", 55.6631, 12.5621],
];
const STATUS_TEXT = { LEDIG: "✓ Ledig", OPTAGET: "● Optaget", UDE_AF_DRIFT: "✕ Ude af drift" };
const LIGHT_TEXT = { GRØN: "Normal pris", GUL: "Lidt over din normale pris", RØD: "Markant over din normale pris" };
const FAULT_GUIDE = {
  STARTER_IKKE: ["Tjek at stikket sidder helt i bilen og standeren.", "Lås bilen op og prøv igen.", "Prøv et andet udtag på samme lokation."],
  FORKERT_STATUS: ["Opdatér kortet i appen.", "Tjek om kablet sidder i et andet udtag.", "Send rapporten – så retter drift status."],
  STIK_BESKADIGET: ["Brug ikke udtaget.", "Tag gerne et foto af skaden.", "Vælg et andet udtag eller en anden stander."],
  BETALING: ["Tjek at dit kort er gyldigt under Profil.", "Opladningen er registreret, selv om betalingen fejler.", "Send rapporten, så ser kundeservice på det."],
  ANDET: ["Beskriv problemet kort.", "Skriv stander-ID'et fra skiltet."],
};

function userApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-User-Id": state.userId } });
}

function dk(value, decimals = 2) {
  return Number(value).toLocaleString("da-DK", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function status(value) {
  return h("span", { class: `st ${value}` }, STATUS_TEXT[value]);
}

function greenBadge(green) {
  return green
    ? h("span", { class: "green-badge", title: `Kilde: ${green.source}` }, `🌱 ${green.renewable_pct} % vedvarende · ${green.gco2_per_kwh} g CO₂/kWh`)
    : h("span", { class: "badge muted" }, "Ingen dokumenteret strømdata (udland)");
}

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [users, operators] = await Promise.all([api("/users"), api("/operators")]);
  const previous = state.userId;
  fillSelect($("#user-select"), users, (u) => u.name);
  if (previous) $("#user-select").value = previous;
  state.userId = Number($("#user-select").value);
  fillSelect($("#filter-form [name=operator_id]"), operators, (o) => o.name, { placeholder: "Alle" });
  fillSelect($("#position-select"), POSITIONS.map((p, i) => ({ id: i, name: p[0] })), (p) => p.name);
  state.position = POSITIONS[0];
}

async function loadUser() {
  state.user = await api(`/users/${state.userId}`);
  const filters = JSON.parse(state.user.filters || "{}");
  const form = $("#filter-form");
  form.reset();
  for (const [key, value] of Object.entries(filters)) {
    const field = form.elements[key];
    if (!field) continue;
    if (field.type === "checkbox") field.checked = !!value;
    else field.value = value;
  }
}

// ---------------------------------------------------------------- Find stander (FR-1, FR-2, FR-9, FR-16)
async function loadLocations() {
  const filters = formToJson($("#filter-form"));
  const params = new URLSearchParams({ lat: state.position[1], lng: state.position[2] });
  for (const [k, v] of Object.entries(filters)) if (v !== "" && v !== false) params.set(k, v === true ? 1 : v);
  const [locations, favorites] = await Promise.all([api(`/locations?${params}`), userApi("/my/favorites")]);
  const favIds = new Set(favorites.map((f) => f.id));
  $("#location-list").replaceChildren(...(locations.length ? locations.map((l) => h("div", { class: "card loc" },
    h("div", { class: "toolbar" },
      h("div", { style: "flex:1" }, h("h3", {}, l.name), h("small", { class: "muted" }, `${l.address}, ${l.city} · ${l.operator}${l.is_clever ? "" : " (roaming)"}`)),
      h("div", { style: "text-align:right" }, h("div", { class: "free" }, `${l.free}/${l.total}`), h("small", { class: "muted" }, "ledige"))),
    h("div", {}, l.distance_km !== null ? `${dk(l.distance_km, 1)} km · ` : "", `op til ${l.max_power_kw} kW · fra ${dk(l.min_price)} kr./kWh · ${l.plugs.join(", ")}`),
    greenBadge(l.green),
    h("div", { class: "actions" }, l.connectors.map((c) => h("span", {}, status(c.status), h("small", {}, ` ${c.code} ${c.plug_type} `)))),
    h("small", { class: "muted" }, `Status opdateret ${formatDate(l.updated_at)}`),
    h("div", { class: "actions" },
      favIds.has(l.id) ? badge("★ Fast stop", "ok") : h("button", { class: "small secondary", onclick: () => addFavorite(l) }, "☆ Gem som fast stop"),
      l.free ? h("button", { class: "small", onclick: () => startFrom(l) }, "Oplad her") : null)))
    : [h("div", { class: "card" }, h("p", { class: "empty" }, "Ingen standere matcher filtrene."))]));
}

$("#filter-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const filters = formToJson(event.target);
  await userApi(`/users/${state.userId}/filters`, { method: "PUT", body: filters });
  loadLocations();
});

async function addFavorite(location) {
  const label = prompt("Navn på dit faste stop", location.name);
  if (label === null) return;
  await run(() => userApi("/my/favorites", { method: "POST", body: { location_id: location.id, label } }), `${label} er gemt`);
  loadLocations();
  loadFavorites();
}

function startFrom(location) {
  const connector = location.connectors.find((c) => c.status === "LEDIG");
  document.querySelector('.tabs button[data-tab="charge"]').click();
  getQuote({ method: "ID", code: connector.code });
}

// ---------------------------------------------------------------- Start: pris før start og bekræftelse (FR-3, FR-4, FR-11)
$("#auto-button").addEventListener("click", () => getQuote({ method: "AUTO", lat: state.position[1], lng: state.position[2] }));
$("#code-form").addEventListener("submit", (event) => {
  event.preventDefault();
  getQuote({ method: "QR", code: event.target.elements.code.value });
});

async function getQuote(body) {
  const q = await run(() => userApi("/quote", { method: "POST", body }));
  state.quoteBody = { ...body, connector_id: q.connector.id };
  state.quote = q;
  $("#quote").replaceChildren(h("div", { class: "card highlight" },
    h("h2", {}, `${q.connector.location_name} · ${q.connector.code}`),
    h("p", {}, status(q.connector.status), ` ${q.connector.plug_type} · op til ${q.expected_power_kw} kW med din bil · ${q.connector.operator}`),
    h("div", { class: "big" }, `${dk(q.price_per_kwh)} kr./kWh`),
    h("p", {}, q.start_fee ? `Startgebyr ${dk(q.start_fee)} kr. · ` : "", q.minute_price ? `Tidspris ${dk(q.minute_price)} kr./min · ` : "",
      h("span", { class: `light ${q.price_level}` }), LIGHT_TEXT[q.price_level],
      q.your_average ? h("span", { class: "muted" }, ` (din normale pris: ${dk(q.your_average)} kr./kWh)`) : null),
    q.price_warning ? h("p", { class: "warning" }, `⚠ ${q.price_warning}`) : null,
    h("p", {}, greenBadge(q.green)),
    ...q.problems.map((p) => h("p", { class: "warning" }, p)),
    h("button", { class: "primary-cta", disabled: !q.can_start, onclick: startSession },
      `Bekræft pris og start`)));
}

async function startSession() {
  const s = await run(() => userApi("/sessions", {
    method: "POST", body: { ...state.quoteBody, price_confirmed: true, quoted_price: state.quote.price_per_kwh },
  }), "Opladningen er startet");
  $("#quote").replaceChildren();
  showSession(s);
}

// ---------------------------------------------------------------- Følg opladning live (FR-6, FR-7, FR-8)
function showSession(s) {
  state.sessionId = s.id;
  $("#start-area").hidden = true;
  renderSession(s);
  clearInterval(state.timer);
  state.timer = setInterval(async () => {
    if (document.hidden || !state.sessionId) return;
    renderSession(await userApi(`/sessions/${state.sessionId}`));
  }, 2000);
}

function renderSession(s) {
  if (s.status !== "AKTIV") return;
  const l = s.live;
  $("#session-area").replaceChildren(h("div", { class: "card dark" },
    h("h2", {}, `Oplader ved ${s.location_name} · ${s.code}`),
    h("div", { class: "kpis" },
      h("div", {}, h("div", { class: "big" }, `${dk(l.power_kw, 0)} kW`), h("small", { class: "muted" }, "effekt nu")),
      h("div", {}, h("div", { class: "big" }, dk(l.kwh, 1)), h("small", { class: "muted" }, "kWh")),
      h("div", {}, h("div", { class: "big" }, `${dk(l.price)} kr.`), h("small", { class: "muted" }, "indtil nu")),
      h("div", {}, h("div", { class: "big" }, `${l.minutes} min`), h("small", { class: "muted" }, "ladetid (simuleret)"))),
    h("div", { class: "battery" }, h("span", { style: `width:${l.battery_pct}%` })),
    h("p", {}, `Batteri ${l.battery_pct} %`),
    l.power_drop && l.explanation.length ? h("div", { class: "warning" }, h("strong", {}, "Hvorfor lader bilen langsommere?"),
      h("ul", {}, l.explanation.map((e) => h("li", {}, e)))) : null,
    h("p", {}, greenBadge(s.green)),
    h("button", { class: "primary-cta", onclick: stopSession }, "Stop opladning")));
}

async function stopSession() {
  const s = await run(() => userApi(`/sessions/${state.sessionId}/stop`, { method: "POST" }));
  clearInterval(state.timer);
  state.sessionId = null;
  const r = s.receipt;
  $("#session-area").replaceChildren(h("div", { class: "card highlight" },
    h("h2", {}, "Kvittering ", r.payment_status === "GENNEMFØRT" ? badge("Betalt", "ok") : badge("Betaling fejlede", "danger")),
    h("p", {}, `${s.location_name} · ${s.code} · ${r.receipt_no}`),
    h("div", { class: "big" }, `${dk(r.price)} kr.`),
    h("p", {}, `${dk(r.kwh, 1)} kWh à ${dk(r.price_per_kwh)} kr. · ${r.minutes} min · ${r.method}`),
    h("p", {}, greenBadge(s.green), r.co2_kg !== null ? ` · ${dk(r.co2_kg, 1)} kg CO₂` : ""),
    r.next_step ? h("p", { class: "warning" }, r.next_step) : null,
    h("button", { class: "secondary", onclick: () => { $("#session-area").replaceChildren(); $("#start-area").hidden = false; } }, "Færdig")));
  loadLocations();
  loadOverview();
}

async function loadActiveSession() {
  clearInterval(state.timer);
  const s = await userApi("/my/active-session");
  if (s) {
    showSession(s);
  } else {
    state.sessionId = null;
    $("#session-area").replaceChildren();
    $("#start-area").hidden = false;
  }
}

// ---------------------------------------------------------------- Faste stop og advarsler (FR-9, FR-10)
async function loadFavorites() {
  const [favorites, alerts] = await Promise.all([userApi("/my/favorites"), userApi("/my/alerts")]);
  $("#alert-count").textContent = alerts.length ? `(${alerts.length})` : "";
  $("#alerts").replaceChildren(...(alerts.length ? alerts.map((a) => h("li", {},
    h("small", { class: "muted" }, formatDate(a.created_at)), " ",
    a.type === "FAVORIT_UDE_AF_DRIFT" ? badge("Ude af drift", "danger") : a.type === "HØJ_PRIS" ? badge("Pris", "warn") : badge("Sag"),
    h("br"), a.message)) : [h("li", { class: "empty" }, "Ingen advarsler")]));
  $("#favorite-list").replaceChildren(...favorites.map((f) => h("div", { class: "card loc" },
    h("div", { class: "toolbar" },
      h("div", { style: "flex:1" }, h("h3", {}, `★ ${f.label}`), h("small", { class: "muted" }, f.name)),
      h("div", { class: "free" }, `${f.free}/${f.total}`)),
    h("div", { class: "actions" }, f.connectors.map((c) => status(c.status))),
    greenBadge(f.green),
    h("div", { class: "actions" },
      f.free ? h("button", { class: "small", onclick: () => startFrom(f) }, "Oplad her") : null,
      h("button", {
        class: "small secondary",
        onclick: async () => {
          await run(() => userApi(`/my/favorites/${f.favorite_id}`, { method: "DELETE" }), "Fjernet");
          loadFavorites();
          loadLocations();
        },
      }, "Fjern")))));
}

// ---------------------------------------------------------------- Rute med ladestop (FR-13, FR-14)
$("#route-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const params = new URLSearchParams(formToJson(event.target));
  const r = await run(() => userApi(`/route?${params}`));
  $("#route-result").replaceChildren(h("div", { class: "card" },
    h("h2", {}, `${r.origin} → ${r.destination} · ${r.distance_km} km`),
    h("p", { class: "muted" }, `${r.car} · via ${r.via.join(", ") || "direkte"}`),
    h("ul", { class: "stops" },
      h("li", {}, h("strong", {}, r.origin), ` – start med ${r.start_battery_pct} %`),
      r.stops.map((s) => h("li", {},
        h("strong", {}, `${s.name}, ${s.city} (${s.country})`), ` · km ${s.km_from_start}`, h("br"),
        `Ankomst ${s.arrive_battery_pct} % → lad til ${s.charge_to_pct} % (ca. ${s.charge_minutes} min ved ${s.max_power_kw} kW) · ${dk(s.price_per_kwh)} kr./kWh · ${s.free}/${s.total} ledige `,
        s.roaming ? badge(`Roaming: ${s.operator}`, "warn") : badge("Clever", "ok"))),
      h("li", {}, h("strong", {}, r.destination), r.reachable ? ` – ankomst med ${r.arrive_battery_pct} %` : "")),
    r.reachable ? null : h("p", { class: "warning" }, "Turen kan ikke gennemføres med de ladestandere, din bil kan bruge på ruten."),
    h("button", {
      class: "secondary",
      onclick: async () => {
        const res = await run(() => userApi("/route/send-to-car", { method: "POST", body: { stops: r.stops } }));
        toast(res.message);
      },
    }, "Send til bilens skærm (CarPlay / Android Auto)")));
});

async function loadRouteOptions() {
  const r = await userApi("/route?from=Greve&to=Odense");
  fillSelect($("#route-form [name=from]"), r.origins.map((o) => ({ id: o, name: o })), (o) => o.name);
  fillSelect($("#route-form [name=to]"), r.destinations.map((d) => ({ id: d, name: d })), (d) => d.name);
  $("#route-form [name=to]").value = "Hamburg";
}

// ---------------------------------------------------------------- Fejlrapport (FR-12)
function renderGuide() {
  $("#fault-guide").replaceChildren(...FAULT_GUIDE[$("#fault-category").value].map((step) => h("li", {}, step)));
}
$("#fault-category").addEventListener("change", renderGuide);

function readPhoto(file) {
  return new Promise((resolve) => {
    if (!file) return resolve(null);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const scale = 480 / Math.max(img.width, img.height, 480);
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", 0.7));
    };
    img.onerror = () => resolve(null);
    img.src = URL.createObjectURL(file);
  });
}

$("#fault-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const photo = await readPhoto($("#fault-photo").files[0]);
  await run(() => userApi("/fault-reports", { method: "POST", body: { ...formToJson(event.target), photo } }),
    "Tak! Rapporten er sendt til drift – du kan følge sagen her");
  event.target.reset();
  renderGuide();
  loadReports();
});

async function loadReports() {
  const rows = await userApi("/fault-reports");
  renderTable($("#my-reports"), rows, [
    { label: "Tid", render: (r) => formatDate(r.created_at) },
    { label: "Stander", render: (r) => `${r.code} · ${r.location_name}` },
    { label: "Problem", render: (r) => $(`#fault-category option[value="${r.category}"]`).textContent },
    { label: "Status", render: (r) => badge(r.status.replace("_", " ").toLowerCase(), r.status === "LØST" ? "ok" : "warn") },
  ], "Ingen sager");
}

// ---------------------------------------------------------------- Forbrugsoverblik (FR-15)
async function loadOverview() {
  const o = await userApi("/my/overview");
  const total = o.months.reduce((sum, m) => ({ kwh: sum.kwh + m.kwh, price: sum.price + m.price, co2: sum.co2 + m.co2_kg }), { kwh: 0, price: 0, co2: 0 });
  $("#overview-kpis").replaceChildren(
    kpi(`${dk(total.kwh, 0)} kWh`, "ladet på 12 måneder"),
    kpi(`${dk(total.price, 0)} kr.`, "betalt for udeopladning"),
    kpi(`${dk(total.co2, 0)} kg`, "CO₂ (dokumenteret, DK)"),
    kpi(o.your_average_price ? `${dk(o.your_average_price)} kr.` : "–", "din gns. pris pr. kWh (30 dage)"),
    kpi(o.subscription?.type.replace("_", " ") ?? "–", o.subscription?.monthly_price ? `${dk(o.subscription.monthly_price, 0)} kr./md.` : "abonnement"),
  );
  renderTable($("#month-table"), o.months, [
    { label: "Måned", key: "month" },
    { label: "Opladninger", class: "num", key: "sessions" },
    { label: "kWh", class: "num", render: (m) => dk(m.kwh, 1) },
    { label: "Pris", class: "num", render: (m) => `${dk(m.price)} kr.` },
    { label: "CO₂", class: "num", render: (m) => `${dk(m.co2_kg, 1)} kg` },
    { label: "Grøn andel", class: "num", render: (m) => (m.renewable_pct ? `${m.renewable_pct} %` : "–") },
  ], "Ingen opladninger endnu");
  $("#advice").textContent = o.advice ?? "";
}

// ---------------------------------------------------------------- Drift
async function loadOps() {
  const [reports, locations] = await Promise.all([api("/fault-reports"), api("/locations")]);
  renderTable($("#ops-reports"), reports, [
    { label: "Tid", render: (r) => formatDate(r.created_at) },
    { label: "Stander", render: (r) => `${r.code} · ${r.location_name}` },
    { label: "Bruger", key: "user_name" },
    { label: "Problem", render: (r) => h("span", {}, $(`#fault-category option[value="${r.category}"]`).textContent, r.description ? h("br") : null, r.description ? h("small", { class: "muted" }, r.description) : null) },
    { label: "Foto", render: (r) => (r.has_photo ? "📷" : "") },
    {
      label: "Status",
      render: (r) => {
        const select = h("select", {
          onchange: async (e) => {
            await run(() => api(`/fault-reports/${r.id}`, { method: "PUT", body: { status: e.target.value } }), "Brugeren har fået besked");
            loadReports();
          },
        }, ["MODTAGET", "UNDER_BEHANDLING", "LØST"].map((s) => h("option", { value: s }, s.replace("_", " ").toLowerCase())));
        select.value = r.status;
        return select;
      },
    },
    { label: "", render: (r) => h("button", { class: "small danger", onclick: () => setCharger(r.charger_id, "UDE_AF_DRIFT") }, "Sæt ude af drift") },
  ], "Ingen fejlrapporter");
  const chargers = new Map();
  for (const l of locations) {
    for (const c of l.connectors) {
      const entry = chargers.get(c.charger_id) ?? { id: c.charger_id, code: c.code, location: l.name, statuses: [] };
      entry.statuses.push(c.status);
      chargers.set(c.charger_id, entry);
    }
  }
  renderTable($("#ops-chargers"), [...chargers.values()], [
    { label: "Stander", key: "code" },
    { label: "Lokation", key: "location" },
    { label: "Udtag", render: (c) => h("span", { class: "actions" }, c.statuses.map(status)) },
    {
      label: "",
      render: (c) => (c.statuses.includes("UDE_AF_DRIFT")
        ? h("button", { class: "small", onclick: () => setCharger(c.id, "LEDIG") }, "Sæt i drift")
        : h("button", { class: "small danger", onclick: () => setCharger(c.id, "UDE_AF_DRIFT") }, "Sæt ude af drift")),
    },
  ]);
}

async function setCharger(chargerId, value) {
  await run(() => api(`/chargers/${chargerId}/status`, { method: "PUT", body: { status: value } }),
    (r) => `${r.charger}: ${value === "LEDIG" ? "i drift" : "ude af drift"}${r.users_alerted ? ` – ${r.users_alerted} brugere advaret` : ""}`);
  loadOps();
  loadLocations();
  loadFavorites();
}

// ---------------------------------------------------------------- Start
$("#user-select").addEventListener("change", (event) => {
  state.userId = Number(event.target.value);
  loadAll();
});
$("#position-select").addEventListener("change", (event) => {
  state.position = POSITIONS[Number(event.target.value)];
  loadLocations();
});

async function loadAll() {
  await loadUser();
  return Promise.all([loadLocations(), loadActiveSession(), loadFavorites(), loadReports(), loadOverview(), loadOps()]);
}

renderGuide();
setupTabs((tab) => {
  if (tab === "map") loadLocations();
  if (tab === "ops") loadOps();
  if (tab === "favorites") loadFavorites();
});
loadBase()
  .then(() => Promise.all([loadAll(), loadRouteOptions()]))
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
