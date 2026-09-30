// Coop – Grønne Besparelser – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { customerId: null, customer: null, employeeId: null, employees: [], product: null, discount: null, scanStartedAt: null };

const STATUS_BADGE = { AKTIV: "ok", UDSOLGT: "muted", UDLØBET: "danger", FJERNET: "muted" };

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

function formatDay(value) {
  return new Date(value).toLocaleDateString("da-DK", { weekday: "short", day: "numeric", month: "short" });
}

function tomorrow() {
  const d = new Date(Date.now() + 86400000);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [stores, customers, employees, products] = await Promise.all([
    api("/stores"), api("/customers"), api("/employees"), api("/products")]);
  const previous = state.customerId;
  fillSelect($("#customer-select"), customers, (c) => c.name);
  if (previous) $("#customer-select").value = previous;
  state.customerId = Number($("#customer-select").value);

  fillSelect($("#preferences-form [name=store_id]"), stores, (s) => s.name, { placeholder: "Vælg butik" });
  state.employees = employees;
  fillSelect($("#employee-select"), employees, (e) => `${e.name} – ${stores.find((s) => s.id === e.store_id)?.name}`);
  if (state.employeeId) $("#employee-select").value = state.employeeId;
  state.employeeId = Number($("#employee-select").value);

  $("#quick-scan").replaceChildren(...products.map((p) =>
    h("button", { class: "small secondary", onclick: () => scan(p.ean) }, p.name)));
}

// ---------------------------------------------------------------- Coop-appen: F1, F2, F5
async function loadCustomer() {
  state.customer = await api(`/customers/${state.customerId}`);
  const form = $("#preferences-form");
  form.elements.store_id.value = state.customer.store_id ?? "";
  form.elements.notifications_consent.checked = !!state.customer.notifications_consent;
  $("#consent-text").textContent = state.customer.notifications_consent
    ? `Samtykke til beskeder givet ${formatDate(state.customer.consent_at)}. Du kan altid slå det fra igen.`
    : "Vi sender kun beskeder, hvis du selv slår det til.";
  await Promise.all([loadFeed(), loadNotifications()]);
}

async function loadFeed() {
  if (!state.customer?.store_id) {
    $("#feed").replaceChildren(h("p", { class: "empty" }, "Vælg din butik for at se gule mærker."));
    return;
  }
  const feed = await api(`/stores/${state.customer.store_id}/feed`);
  $("#feed-title").textContent = `Gule mærker i ${feed.store.name}`;
  $("#feed-updated").textContent = `Opdateret ${formatDate(feed.updated_at)} · spar op til ${formatKr(feed.saving_total)}`;
  $("#feed").replaceChildren(feed.labels.length
    ? h("div", { class: "labels" }, feed.labels.map((l) => h("div", { class: "yellow" },
      h("span", { class: "pct" }, `-${l.discount_pct} %`),
      h("strong", {}, l.product_name),
      h("div", { class: "price" }, formatKr(l.new_price)),
      h("div", { class: "before" }, `Før ${formatKr(l.old_price)}`),
      h("div", {}, `Sidste dag: ${formatDay(l.expiry_date)}`),
      h("div", {}, `${l.quantity_left} stk. på hylden`))))
    : h("p", { class: "empty" }, "Ingen gule mærker lige nu. Kig forbi igen senere."));
}

async function loadNotifications() {
  const rows = await api(`/customers/${state.customerId}/notifications`);
  $("#notifications").replaceChildren(...(rows.length ? rows.map((n) => h("li", {},
    h("small", { class: "muted" }, formatDate(n.created_at)), " ",
    n.label_status !== "AKTIV" ? badge(n.label_status.toLowerCase(), STATUS_BADGE[n.label_status]) : null,
    h("br"), n.message)) : [h("li", { class: "empty" }, "Ingen beskeder")]));
}

$("#preferences-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formToJson(event.target);
  await run(() => api(`/customers/${state.customerId}/preferences`, { method: "PUT", body: data }), "Indstillinger gemt");
  loadCustomer();
});

$("#customer-select").addEventListener("change", (event) => {
  state.customerId = Number(event.target.value);
  loadCustomer();
});

// ---------------------------------------------------------------- Håndterminal: F3 (højst 3 tryk efter scanning)
async function scan(ean) {
  const result = await run(() => api(`/products/ean/${encodeURIComponent(ean)}`));
  state.product = result.product;
  state.discount = null;
  state.scanStartedAt = Date.now();
  const form = $("#label-form");
  form.hidden = false;
  form.elements.expiry_date.value = tomorrow();
  form.elements.quantity.value = 1;
  $("#scan-form").elements.ean.value = ean;
  $("#scan-product").textContent = `${result.product.name} · ${formatKr(result.product.normal_price)}`;
  $("#discounts").replaceChildren(...result.discounts.map((pct) => h("button", {
    type: "button",
    onclick: (e) => {
      state.discount = pct;
      $("#discounts").querySelectorAll("button").forEach((b) => b.classList.toggle("selected", b === e.currentTarget));
      updatePreview();
    },
  }, `-${pct} %`)));
  updatePreview();
}

function updatePreview() {
  $("#price-preview").textContent = state.discount
    ? `Ny pris: ${formatKr(Math.round(state.product.normal_price * (100 - state.discount)) / 100)}`
    : "Vælg rabat";
}

$("#scan-form").addEventListener("submit", (event) => {
  event.preventDefault();
  scan(event.target.elements.ean.value.trim());
});

$("#label-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.discount) {
    toast("Vælg en rabat", "error");
    return;
  }
  const result = await run(() => api("/labels", {
    method: "POST",
    body: {
      ...formToJson(event.target),
      employee_id: state.employeeId,
      ean: state.product.ean,
      discount_pct: state.discount,
      creation_seconds: Math.round((Date.now() - state.scanStartedAt) / 1000),
    },
  }), (r) => `Mærke oprettet – ${r.notified_customers} kunder har fået besked`);
  event.target.hidden = true;
  $("#scan-form").reset();
  loadLabels();
  loadCustomer();
  loadStats();
  return result;
});

async function loadLabels() {
  const employee = state.employees.find((e) => e.id === state.employeeId);
  const labels = await api(`/labels?store_id=${employee.store_id}`);
  renderTable($("#label-table"), labels, [
    { label: "Vare", key: "product_name" },
    { label: "Pris", class: "num", render: (l) => `${formatKr(l.new_price)} (-${l.discount_pct} %)` },
    { label: "Dato", render: (l) => formatDay(l.expiry_date) },
    { label: "Tilbage", class: "num", render: (l) => `${l.quantity_left}/${l.quantity}` },
    { label: "Status", render: (l) => badge(l.status, STATUS_BADGE[l.status]) },
    {
      label: "",
      render: (l) => (l.status === "AKTIV" ? h("div", { class: "actions" },
        h("button", { class: "small", onclick: () => labelAction(l.id, "sell", "Solgt i kassen") }, "Sælg 1"),
        h("button", { class: "small danger", onclick: () => labelAction(l.id, "remove", "Mærke fjernet") }, "Fjern")) : null),
    },
  ], "Ingen mærker endnu");
}

async function labelAction(id, action, message) {
  await run(() => api(`/labels/${id}/${action}`, { method: "POST", body: action === "sell" ? { quantity: 1 } : undefined }), message);
  loadLabels();
  loadFeed();
  loadStats();
}

$("#employee-select").addEventListener("change", (event) => {
  state.employeeId = Number(event.target.value);
  loadLabels();
});

// ---------------------------------------------------------------- Nøgletal
async function loadStats() {
  const s = await api("/stats");
  $("#stats-kpis").replaceChildren(
    kpi(s.units_sold, "varer solgt med gult mærke"),
    kpi(`${s.sell_through_pct} %`, "solgt før udløb"),
    kpi(s.avg_creation_seconds ? `${s.avg_creation_seconds} sek.` : "–", "gns. tid pr. mærke"),
    kpi(s.within_20s_pct !== null ? `${s.within_20s_pct} %` : "–", "oprettet på højst 20 sek."),
    kpi(s.notifications, "beskeder sendt"),
  );
  renderTable($("#store-stats"), s.per_store, [
    { label: "Butik", key: "name" },
    { label: "Mærker", class: "num", key: "labels" },
    { label: "Aktive", class: "num", key: "active" },
    { label: "Udsolgt", class: "num", key: "sold_out" },
    { label: "Udløbet", class: "num", key: "expired" },
    { label: "Solgt (stk.)", class: "num", key: "units_sold" },
    { label: "Spild (stk.)", class: "num", key: "units_wasted" },
    { label: "Gns. sek.", class: "num", key: "avg_creation_seconds" },
    { label: "Abonnenter", class: "num", key: "subscribers" },
  ]);
}

// ---------------------------------------------------------------- Varer og kunder (CRUD)
async function loadAdmin() {
  const [products, customers] = await Promise.all([api("/products"), api("/customers")]);
  renderTable($("#product-table"), products, [
    { label: "EAN", key: "ean" },
    { label: "Navn", key: "name" },
    { label: "Normalpris", class: "num", render: (p) => formatKr(p.normal_price) },
    { label: "", render: (p) => crudButtons("products", $("#product-form"), p, reloadEverything) },
  ]);
  renderTable($("#customer-table"), customers, [
    { label: "Navn", key: "name" },
    { label: "E-mail", key: "email" },
    { label: "Beskeder", render: (c) => (c.notifications_consent ? badge("Til", "ok") : badge("Fra", "muted")) },
    { label: "", render: (c) => crudButtons("customers", $("#customer-form"), c, reloadEverything) },
  ]);
}

function reloadEverything() {
  loadBase().then(loadAll);
}

bindCrudForm($("#product-form"), "products", reloadEverything);
bindCrudForm($("#customer-form"), "customers", reloadEverything);

// ---------------------------------------------------------------- Start
function loadAll() {
  return Promise.all([loadCustomer(), loadLabels(), loadStats(), loadAdmin()]);
}

// Appen skal spejle hylden: nye mærker vises inden for 5 sekunder
setInterval(() => {
  if ($("#tab-app").classList.contains("active") && !document.hidden) {
    loadFeed();
    loadNotifications();
  }
}, 5000);

setupTabs((tab) => {
  if (tab === "app") loadCustomer();
  if (tab === "stats") loadStats();
});
loadBase()
  .then(loadAll)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
