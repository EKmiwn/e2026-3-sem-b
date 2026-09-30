// NORMAL – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { storeId: null, productId: null, stores: [] };

const STATUS_BADGE = { PÅ_LAGER: "ok", FÅ_TILBAGE: "warn", UDSOLGT: "danger" };
const STATUS_LABEL = { PÅ_LAGER: "På lager", FÅ_TILBAGE: "Få tilbage", UDSOLGT: "Udsolgt" };

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

function setStep(step) {
  document.querySelectorAll("#steps span").forEach((span, i) => span.classList.toggle("done", i < step));
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [stores, categories] = await Promise.all([api("/stores"), api("/categories")]);
  state.stores = stores;
  const previous = state.storeId;
  fillSelect($("#store-select"), stores, (s) => `${s.name} (${s.city})`);
  if (previous) $("#store-select").value = previous;
  state.storeId = Number($("#store-select").value);
  fillSelect($("#product-form [name=category_id]"), categories, (c) => c.name);
}

// ---------------------------------------------------------------- 1–2: søg og vælg produkt
$("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const { q } = formToJson(event.target);
  const result = await run(() => api(`/search?q=${encodeURIComponent(q)}`));
  setStep(1);
  $("#availability").replaceChildren();
  const box = $("#results");
  if (!result.count) {
    box.replaceChildren(h("p", { class: "empty" }, `Ingen produkter matcher "${result.query}". Prøv et andet ord.`));
    return;
  }
  box.replaceChildren(
    h("p", { class: "muted" }, `${result.count} produkter – vælg det, du leder efter:`),
    h("div", { class: "products" }, result.products.map((p) => h("button", {
      class: "product",
      onclick: (e) => {
        box.querySelectorAll(".product").forEach((b) => b.classList.remove("selected"));
        e.currentTarget.classList.add("selected");
        state.productId = p.id;
        checkAvailability();
      },
    }, h("strong", {}, p.name), h("span", { class: "muted" }, `${p.brand} · ${p.category}`), h("br"), formatKr(p.price)))),
  );
});

// ---------------------------------------------------------------- 3–4: vælg butik og se lagerstatus
async function checkAvailability() {
  if (!state.productId) return;
  setStep(3);
  const a = await run(() => api(`/products/${state.productId}/availability?store_id=${state.storeId}`));
  setStep(4);
  $("#availability").replaceChildren(h("div", { class: "card highlight" },
    h("h2", {}, `${a.product.name} · ${a.store.name}`),
    h("div", { class: "row", style: "display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))" },
      h("label", {}, "Butik", storePicker()),
      h("div", {}, h("div", { class: `status ${a.status}` }, a.status_text))),
    h("p", {}, a.message),
    h("p", { class: "muted" }, `${a.store.address} · ${a.store.opening_hours}`,
      a.updated_at ? ` · lager opdateret ${formatDate(a.updated_at)}` : ""),
    a.alternatives.length ? h("div", {},
      h("h3", {}, "Her er varen på lager"),
      renderAlternatives(a.alternatives)) : null,
    a.status === "UDSOLGT" && !a.alternatives.length ? h("p", { class: "empty" }, "Varen er ikke på lager i nogen butik lige nu.") : null));
}

function storePicker() {
  const select = h("select", {
    onchange: (e) => {
      state.storeId = Number(e.target.value);
      $("#store-select").value = state.storeId;
      checkAvailability();
    },
  });
  fillSelect(select, state.stores, (s) => `${s.name} (${s.city})`);
  select.value = state.storeId;
  return select;
}

function renderAlternatives(stores) {
  const box = h("div");
  renderTable(box, stores, [
    { label: "Butik", render: (s) => h("span", {}, s.name, s.same_city ? " " : "", s.same_city ? badge("samme by") : null) },
    { label: "Adresse", key: "address" },
    { label: "Status", render: (s) => badge(STATUS_LABEL[s.status], STATUS_BADGE[s.status]) },
    { label: "", render: (s) => h("button", { class: "small", onclick: () => chooseStore(s.store_id) }, "Vælg butik") },
  ]);
  return box;
}

function chooseStore(storeId) {
  state.storeId = storeId;
  $("#store-select").value = storeId;
  checkAvailability();
  loadStaff();
}

// ---------------------------------------------------------------- Medarbejder: lager
async function loadStaff() {
  const store = state.stores.find((s) => s.id === state.storeId);
  $("#staff-store-name").textContent = store?.name ?? "";
  const filter = $("#staff-filter").value;
  const rows = (await api(`/stores/${state.storeId}/stock`)).filter((r) => !filter || r.status === filter);
  renderTable($("#stock-table"), rows, [
    { label: "Varenr.", key: "sku" },
    { label: "Produkt", render: (r) => `${r.name} (${r.brand})` },
    { label: "Kategori", key: "category" },
    { label: "Status", render: (r) => badge(STATUS_LABEL[r.status], STATUS_BADGE[r.status]) },
    { label: "Antal", render: (r) => stockForm(r) },
    { label: "Opdateret", render: (r) => formatDate(r.updated_at) },
  ], "Ingen produkter med denne status");
}

function stockForm(row) {
  const form = h("form", { class: "actions", style: "display:flex" },
    h("input", { type: "number", name: "quantity", min: 0, value: row.quantity, class: "qty", required: true }),
    h("button", { class: "small" }, "Gem"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await run(() => api(`/stores/${state.storeId}/stock/${row.product_id}`, { method: "PUT", body: formToJson(form) }),
      (r) => `${row.name}: ${STATUS_LABEL[r.status]}`);
    loadStaff();
    loadStats();
  });
  return form;
}

$("#staff-filter").addEventListener("change", loadStaff);

// ---------------------------------------------------------------- Nøgletal
async function loadStats() {
  const s = await api("/stats");
  $("#stats-kpis").replaceChildren(
    kpi(s.searches, "søgninger"),
    kpi(s.searches_without_result, "søgninger uden resultat"),
    kpi(s.lookups, "lageropslag"),
    kpi(s.sold_out_lookups, "opslag på udsolgt vare"),
    kpi(s.stores, "butikker"),
    kpi(s.employees, "medarbejdere"),
  );
  renderTable($("#top-searches"), s.top_searches, [
    { label: "Søgning", key: "query" },
    { label: "Antal", class: "num", key: "count" },
    { label: "Resultater", class: "num", render: (r) => (r.results ? r.results : badge("0", "danger")) },
  ]);
  renderTable($("#top-products"), s.top_products, [
    { label: "Produkt", key: "name" },
    { label: "Opslag", class: "num", key: "lookups" },
    { label: "Heraf udsolgt", class: "num", key: "sold_out" },
  ]);
  renderTable($("#store-stats"), s.per_store, [
    { label: "Butik", key: "name" },
    { label: "By", key: "city" },
    { label: "Medarbejdere", class: "num", key: "employees" },
    { label: "Udsolgte produkter", class: "num", key: "sold_out_products" },
    { label: "Kundeopslag", class: "num", key: "lookups" },
  ]);
}

// ---------------------------------------------------------------- Sortiment og butikker (CRUD)
async function loadCatalog() {
  const [products, stores] = await Promise.all([api("/products"), api("/stores")]);
  renderTable($("#product-table"), products, [
    { label: "Varenr.", key: "sku" },
    { label: "Navn", key: "name" },
    { label: "Mærke", key: "brand" },
    { label: "Pris", class: "num", render: (p) => formatKr(p.price) },
    { label: "", render: (p) => crudButtons("products", $("#product-form"), p, reloadEverything) },
  ]);
  renderTable($("#store-table"), stores, [
    { label: "Navn", key: "name" },
    { label: "By", key: "city" },
    { label: "", render: (s) => crudButtons("stores", $("#store-form"), s, reloadEverything) },
  ]);
}

function reloadEverything() {
  loadBase().then(loadAll);
}

bindCrudForm($("#product-form"), "products", reloadEverything);
bindCrudForm($("#store-form"), "stores", reloadEverything);

// ---------------------------------------------------------------- Start
$("#store-select").addEventListener("change", (event) => {
  state.storeId = Number(event.target.value);
  checkAvailability();
  loadStaff();
});

function loadAll() {
  return Promise.all([loadStaff(), loadStats(), loadCatalog()]);
}

setupTabs((tab) => {
  if (tab === "stats") loadStats();
});
loadBase()
  .then(loadAll)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
