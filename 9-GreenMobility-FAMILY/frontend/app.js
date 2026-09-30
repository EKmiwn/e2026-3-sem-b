// GreenMobility FAMILY – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { familyId: null, family: null, zones: [], carTypes: [] };

const CAPACITY_BADGE = { HØJ: "ok", OK: "ok", BEGRÆNSET: "warn", LAV: "danger" };

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

function localInput(date) {
  const d = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return d.toISOString().slice(0, 16);
}

function hours(minutes) {
  return `${Math.floor(minutes / 60)} t ${minutes % 60 ? `${minutes % 60} min` : ""}`.trim();
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [families, zones, carTypes] = await Promise.all([api("/families"), api("/zones"), api("/car-types")]);
  state.zones = zones;
  state.carTypes = carTypes;
  const previous = state.familyId;
  fillSelect($("#family-select"), families, (f) => f.name);
  if (previous) $("#family-select").value = previous;
  state.familyId = Number($("#family-select").value);
  fillSelect($("#signup-form [name=home_zone_id]"), zones, (z) => z.name);
  fillSelect($("#search-form [name=zone_id]"), zones, (z) => z.name);
  fillSelect($("#search-form [name=car_type_id]"), carTypes, (c) => `${c.name} (${c.seats} pladser)`);
  const start = new Date(Date.now() + 86400000);
  start.setHours(10, 0, 0, 0);
  $("#search-form").elements.start.value = localInput(start);
  $("#search-form").elements.end.value = localInput(new Date(start.getTime() + 3 * 3600000));
}

// ---------------------------------------------------------------- Opdager og tilmeld
async function loadOffer() {
  const o = await api("/offer");
  const form = $("#signup-form");
  $("#plan-list").replaceChildren(...o.plans.map((p) => h("div", {
    class: `plan ${Number(form.elements.plan_id.value) === p.id ? "selected" : ""}`,
    onclick: (e) => {
      form.elements.plan_id.value = p.id;
      document.querySelectorAll(".plan").forEach((el) => el.classList.toggle("selected", el === e.currentTarget));
      $("#selected-plan").textContent = `Valgt: ${p.name} – ${formatKr(p.monthly_price)} om måneden. Op til ${p.max_members} medlemmer.`;
    },
  },
  h("h3", {}, p.name),
  h("div", { class: "price" }, formatKr(p.monthly_price), h("small", { class: "muted", style: "font-size:0.9rem" }, " /md.")),
  h("p", {}, p.description),
  h("small", { class: "muted" }, `${p.included_hours} timer inkl. · ${p.discount_pct} % rabat · op til ${p.max_members} medlemmer`))));
  $("#partner-benefits").replaceChildren(...o.partners.map((p) => h("li", {}, h("strong", {}, p.name), ` – ${p.benefit} `, badge(`+${p.credits_per_activity} GreenCredits`, "ok"))));
  renderTable($("#car-type-table"), o.car_types, [
    { label: "Biltype", key: "name" },
    { label: "Pladser", class: "num", key: "seats" },
    { label: "Barnestol", render: (c) => (c.child_seat ? "✓" : "–") },
    { label: "Pris/min", class: "num", render: (c) => formatKr(c.price_per_min) },
  ]);
}

function addMemberRow(name = "", driver = false) {
  $("#member-rows").append(h("div", { class: "member-row" },
    h("label", {}, "Medlem", h("input", { "data-member": "name", value: name, placeholder: "Navn" })),
    h("label", {}, "E-mail", h("input", { "data-member": "email", type: "email" })),
    h("label", { style: "display:flex;gap:6px;align-items:center;color:var(--text)" },
      h("input", { type: "checkbox", "data-member": "is_driver", checked: driver }), "Fører")));
}

$("#add-member").addEventListener("click", () => addMemberRow());

$("#signup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  if (!form.elements.plan_id.value) return toast("Vælg et abonnement", "error");
  const members = [...$("#member-rows").children].map((row) => ({
    name: row.querySelector('[data-member="name"]').value,
    email: row.querySelector('[data-member="email"]').value || null,
    is_driver: row.querySelector('[data-member="is_driver"]').checked,
  }));
  const data = { ...formToJson(form), plan_id: Number(form.elements.plan_id.value), members };
  const family = await run(() => api("/families", { method: "POST", body: data }), (f) => `Velkommen, ${f.name}! Betalingen er godkendt, og medlemskabet er aktivt.`);
  state.familyId = family.id;
  form.reset();
  $("#member-rows").replaceChildren();
  addMemberRow("", true);
  await loadBase();
  await loadAll();
  document.querySelector('.tabs button[data-tab="family"]').click();
});

// ---------------------------------------------------------------- Vores familie: overblik, reservationer, ture, Book igen
async function loadFamily() {
  const f = await api(`/families/${state.familyId}/dashboard`);
  state.family = f;
  fillSelect($("#search-form [name=member_id]"), f.members.filter((m) => m.is_driver), (m) => m.name);
  const usedPct = Math.min(100, Math.round((100 * f.used_minutes) / Math.max(1, f.included_minutes)));
  const tripBox = h("div");
  renderTable(tripBox, f.trips, [
    { label: "Start", render: (t) => formatDate(t.started_at) },
    { label: "Biltype", key: "car_type" },
    { label: "Fra → til", render: (t) => `${t.zone} → ${t.end_zone}` },
    { label: "Min", class: "num", key: "minutes" },
    { label: "Km", class: "num", key: "km" },
    { label: "Pris", class: "num", render: (t) => formatKr(t.price) },
  ], "Ingen ture endnu");
  $("#dashboard").replaceChildren(
    h("div", { class: "kpis" },
      kpi(f.plan_name, `${formatKr(f.monthly_price)} /md. · betaling ••••${f.card_last4}`),
      kpi(hours(f.remaining_minutes), `tilbage af ${f.included_hours} timer denne måned`),
      kpi(f.credits, "GreenCredits"),
      kpi(f.members.length, "medlemmer")),
    h("div", { class: "usage" }, h("span", { style: `width:${usedPct}%` })),
    f.suggestion ? h("div", { class: "card highlight", style: "margin-top:16px" },
      h("h3", {}, "Book igen"), h("p", {}, f.suggestion.text),
      h("button", { onclick: () => bookAgain(f.suggestion) }, "Find bil")) : null,
    h("div", { class: "grid wide", style: "margin-top:16px" },
      h("div", { class: "card" }, h("h2", {}, "Kommende reservationer"), renderReservations(f.reservations)),
      h("div", { class: "card" }, h("h2", {}, "Familien"),
        h("ul", { class: "list" }, f.members.map((m) => h("li", {}, m.name, m.is_driver ? " " : "", m.is_driver ? badge("fører", "ok") : null))))),
    h("div", { class: "card" }, h("h2", {}, "Seneste ture"), tripBox));
}

function renderReservations(rows) {
  const box = h("div");
  renderTable(box, rows, [
    { label: "Tid", render: (r) => `${formatDate(r.start_at)} – ${r.end_at.slice(11, 16)}` },
    { label: "Bil", render: (r) => `${r.plate} · ${r.car_type}` },
    { label: "Zone", key: "zone" },
    { label: "Fører", key: "member" },
    {
      label: "",
      render: (r) => h("div", { class: "actions" },
        h("button", { class: "small", onclick: () => completeTrip(r) }, "Afslut tur (simulér)"),
        h("button", { class: "small danger", onclick: () => cancelReservation(r.id) }, "Annullér")),
    },
  ], "Ingen reservationer");
  return box;
}

async function cancelReservation(id) {
  if (!confirm("Annullér reservationen?")) return;
  await run(() => api(`/reservations/${id}/cancel`, { method: "POST" }), "Reservationen er annulleret");
  loadFamily();
}

async function completeTrip(reservation) {
  const km = prompt("Hvor mange km kørte I?", "25");
  if (km === null) return;
  const zone = state.zones.find((z) => z.name === prompt(`Hvor blev bilen parkeret? (${state.zones.map((z) => z.name).join(", ")})`, reservation.zone));
  if (!zone) return toast("Ukendt zone", "error");
  const useCredits = state.family.credits > 0 && confirm(`Brug jeres ${state.family.credits} GreenCredits på turen?`);
  await run(() => api(`/reservations/${reservation.id}/complete`, {
    method: "POST", body: { km: Number(km), end_zone_id: zone.id, use_credits: useCredits },
  }), (r) => `Tur registreret: ${r.summary}`);
  loadFamily();
  loadOps();
}

function bookAgain(suggestion) {
  const form = $("#search-form");
  form.elements.zone_id.value = suggestion.zone_id;
  form.elements.car_type_id.value = suggestion.car_type_id;
  const start = new Date(suggestion.start_at);
  form.elements.start.value = localInput(start);
  form.elements.end.value = localInput(new Date(start.getTime() + 3 * 3600000));
  document.querySelector('.tabs button[data-tab="book"]').click();
  form.requestSubmit();
}

// ---------------------------------------------------------------- Planlæg og reserver
$("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const q = formToJson(event.target);
  const params = new URLSearchParams({ zone_id: q.zone_id, car_type_id: q.car_type_id, start: q.start, end: q.end });
  const a = await run(() => api(`/availability?${params}`));
  const carCard = (c) => h("div", { class: "card" },
    h("h3", {}, c.plate), h("p", {}, `${a.car_type.name} · ${c.zone} · batteri ${c.battery_pct} %`),
    h("button", { onclick: () => reserve(c, q) }, "Reservér"));
  $("#availability").replaceChildren(
    h("div", { class: "card highlight" },
      h("p", {}, badge(`Kapacitet: ${a.capacity.toLowerCase()}`, CAPACITY_BADGE[a.capacity]), ` ${a.message}`),
      h("p", { class: "muted" }, `Forventet efterspørgsel: ${a.expected_demand} ture i tidsrummet (gennemsnit af de seneste uger)`)),
    a.cars.length ? h("div", { class: "grid" }, a.cars.map(carCard)) : null,
    a.alternatives.length ? h("div", {}, h("h3", {}, "Ledige i andre zoner"), h("div", { class: "grid" }, a.alternatives.map(carCard))) : null);
});

async function reserve(car, q) {
  await run(() => api("/reservations", {
    method: "POST",
    body: { family_id: state.familyId, member_id: q.member_id, car_id: car.id, start_at: q.start, end_at: q.end },
  }), (r) => r.message);
  $("#availability").replaceChildren();
  await loadFamily();
  document.querySelector('.tabs button[data-tab="family"]').click();
}

// ---------------------------------------------------------------- Belønnes: partnere og GreenCredits
async function loadCredits() {
  const partners = await api("/partners");
  fillSelect($("#activity-form [name=partner_id]"), partners, (p) => `${p.name} (+${p.credits_per_activity})`);
  $("#credit-balance").textContent = `${state.family.credits} GreenCredits`;
  renderTable($("#credit-table"), state.family.credit_history, [
    { label: "Tid", render: (c) => formatDate(c.created_at) },
    { label: "Beskrivelse", key: "description" },
    { label: "Partner", key: "partner" },
    { label: "Credits", class: "num", render: (c) => (c.amount > 0 ? `+${c.amount}` : c.amount) },
  ], "Ingen GreenCredits endnu");
  renderTable($("#partner-table"), partners, [
    { label: "Navn", key: "name" },
    { label: "Kategori", key: "category" },
    { label: "Fordel", key: "benefit" },
    { label: "Credits", class: "num", key: "credits_per_activity" },
    { label: "", render: (p) => crudButtons("partners", $("#partner-form"), p, reloadEverything) },
  ]);
}

$("#activity-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await run(() => api("/partner-activities", { method: "POST", body: { ...formToJson(event.target), family_id: state.familyId } }), (r) => r.message);
  event.target.reset();
  await loadFamily();
  loadCredits();
});

bindCrudForm($("#partner-form"), "partners", () => reloadEverything());

// ---------------------------------------------------------------- Operations: forecast og flådeplacering
async function loadForecast(weekday, block) {
  const params = new URLSearchParams();
  if (weekday !== undefined) params.set("weekday", weekday);
  if (block !== undefined) params.set("block", block);
  const f = await api(`/forecast?${params}`);
  const form = $("#forecast-form");
  if (!form.elements.weekday.options.length) {
    fillSelect(form.elements.weekday, f.weekdays.map((d, i) => ({ id: i, name: d })), (d) => d.name);
    fillSelect(form.elements.block, f.blocks.map((b, i) => ({ id: i, name: b })), (b) => b.name);
  }
  form.elements.weekday.value = f.weekdays.indexOf(f.weekday);
  form.elements.block.value = f.blocks.indexOf(f.block);
  $("#forecast-info").textContent = `Forventede ture pr. ${f.weekday} ${f.block.toLowerCase()} – gennemsnit af de seneste ${f.history_weeks} uger – sammenholdt med biler, der står i zonen nu.`;
  const zones = [...new Set(f.rows.map((r) => r.zone))];
  const types = [...new Set(f.rows.map((r) => r.car_type))];
  $("#forecast-table").replaceChildren(h("div", { class: "table-wrap" }, h("table", {},
    h("thead", {}, h("tr", {}, h("th", {}, "Zone"), types.map((t) => h("th", {}, t)))),
    h("tbody", {}, zones.map((z) => h("tr", {}, h("td", {}, z), types.map((t) => {
      const r = f.rows.find((x) => x.zone === z && x.car_type === t);
      return h("td", { class: r.gap > 0 ? "gap-pos" : r.available_cars > r.expected_trips + 0.5 ? "gap-neg" : "" },
        `${r.expected_trips} ture / ${r.available_cars} biler`);
    })))))));
  $("#moves").replaceChildren(f.recommended_moves.length ? h("ul", { class: "list" }, f.recommended_moves.map((m) => h("li", {},
    h("strong", {}, `${m.plate} (${m.car_type})`), `: ${m.from_zone} → ${m.to_zone}`, h("br"), h("small", { class: "muted" }, m.reason), " ",
    h("button", {
      class: "small",
      onclick: async () => {
        await run(() => api("/relocations", { method: "POST", body: { car_id: m.car_id, to_zone_id: m.to_zone_id, reason: m.reason } }), `${m.plate} flyttet til ${m.to_zone}`);
        loadOps(form.elements.weekday.value, form.elements.block.value);
      },
    }, "Flyt bil"))))
    : h("p", { class: "empty" }, "Ingen flytninger nødvendige."));
}

$("#forecast-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const { weekday, block } = formToJson(event.target);
  loadForecast(weekday, block);
});

async function loadOps(weekday, block) {
  const [stats, cars, relocations] = await Promise.all([api("/stats"), api("/cars"), api("/relocations")]);
  $("#stats-kpis").replaceChildren(
    kpi(stats.families, "aktive familier"),
    kpi(stats.members, "medlemmer"),
    kpi(formatKr(stats.monthly_revenue), "abonnementer pr. måned"),
    kpi(stats.trips_30d, "ture (30 dage)"),
    kpi(`${stats.km_30d} km`, "kørt (30 dage)"),
    kpi(stats.credits_issued, "GreenCredits udstedt"));
  renderTable($("#car-table"), cars, [
    { label: "Bil", key: "plate" },
    { label: "Type", render: (c) => state.carTypes.find((t) => t.id === c.car_type_id)?.name },
    { label: "Zone", render: (c) => state.zones.find((z) => z.id === c.zone_id)?.name },
    { label: "Batteri", class: "num", render: (c) => `${c.battery_pct} %` },
    { label: "Status", render: (c) => badge(c.status.toLowerCase(), c.status === "KLAR" ? "ok" : "warn") },
  ]);
  renderTable($("#relocation-table"), relocations, [
    { label: "Tid", render: (r) => formatDate(r.created_at) },
    { label: "Bil", key: "plate" },
    { label: "Flytning", render: (r) => `${r.from_zone} → ${r.to_zone}` },
  ], "Ingen flytninger endnu");
  loadForecast(weekday, block);
}

// ---------------------------------------------------------------- Start
function reloadEverything() {
  return loadBase().then(loadAll);
}

async function loadAll() {
  await loadFamily();
  return Promise.all([loadOffer(), loadCredits(), loadOps()]);
}

$("#family-select").addEventListener("change", async (event) => {
  state.familyId = Number(event.target.value);
  await loadFamily();
  loadCredits();
});

addMemberRow("", true);
addMemberRow();
setupTabs();
loadBase()
  .then(loadAll)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
