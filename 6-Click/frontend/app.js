// Fotohuset Click – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { order: null, products: [], settings: {}, operatorId: null, operatorName: null };

const CROP_TEXT = { FYLD: "Fyld (beskær kanterne)", TILPAS_MED_KANT: "Tilpas med hvid kant", HELT_TIL_KANT: "Helt til kant" };
const STATUS_TEXT = { KURV: "Kurv", MODTAGET: "Modtaget", I_PRODUKTION: "I produktion", KLAR: "Klar", AFHENTET: "Afhentet" };
const STATUS_BADGE = { KURV: "muted", MODTAGET: "warn", I_PRODUKTION: "", KLAR: "ok", AFHENTET: "muted" };
const NEXT_ACTION = { MODTAGET: ["release", "Frigiv til print"], I_PRODUKTION: ["KLAR", "Markér klar"], KLAR: ["AFHENTET", "Afhentet"] };

// api.js er fælles for alle prototyper og ændres ikke. Her sender Click operatørens login med på alle kald,
// så også de fælles CRUD-formularer (bindCrudForm, crudButtons) i produktkataloget er logget ind (FK23, §15).
const sharedApi = api;
api = (path, options = {}) => sharedApi(path, {
  ...options,
  headers: { ...(state.operatorId ? { "X-User-Id": state.operatorId } : {}), ...(options.headers || {}) },
});

// Kundens kald sender adgangsnøglen med
function orderApi(path, options) {
  return api(`/orders/${state.order.id}${path}${path.includes("?") ? "&" : "?"}key=${encodeURIComponent(state.order.access_key)}`, options);
}

function operatorApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-User-Id": state.operatorId } });
}

function mb(bytes) {
  return `${(bytes / 1024 / 1024).toLocaleString("da-DK", { maximumFractionDigits: 1 })} MB`;
}

function cm(product) {
  return `${product.label} · ${product.surface === "BLANK" ? "blank" : "silke"} · ${product.quality === "HØJ" ? "høj kvalitet" : "standard"}`;
}

// ---------------------------------------------------------------- Indlæsning
async function loadBase() {
  const [products, settings] = await Promise.all([api("/products"), api("/settings")]);
  state.products = products.filter((p) => p.active);
  state.settings = Object.fromEntries(settings.map((s) => [s.key, s.value]));
  $("#shipping-price").textContent = formatKr(state.settings.shipping_price);
  $("#retention-days").textContent = state.settings.retention_days;
}

// ---------------------------------------------------------------- Wizard
function showStep(step) {
  document.querySelectorAll(".step").forEach((s) => s.classList.toggle("active", s.id === `step-${step}`));
  document.querySelectorAll("#wizard span").forEach((s) => {
    s.classList.toggle("active", Number(s.dataset.step) === step);
    s.classList.toggle("done", Number(s.dataset.step) < step);
  });
  if (step === 2) renderConfig();
  if (step === 3) renderCart();
  if (step === 4) renderCheckout();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll("[data-goto]").forEach((button) => button.addEventListener("click", () => {
  const step = Number(button.dataset.goto);
  if (step === 2 && !state.order.images.length) return toast("Upload mindst ét billede først", "error");
  if (step >= 3 && !state.order.lines.length) return toast("Vælg format til mindst ét billede og læg det i kurven", "error");
  showStep(step);
}));

async function startOrder() {
  const created = await api("/orders", { method: "POST" });
  state.order = { id: created.id, access_key: created.access_key, images: [], lines: [] };
  state.choices = {};
  $("#thumbs").replaceChildren();
  lockCheckout(false);
  $("#checkout-form").reset();
  showStep(1);
}

async function refreshOrder() {
  const key = state.order.access_key;
  state.order = await orderApi("");
  state.order.access_key = key;
}

// ---------------------------------------------------------------- Trin 1: upload (FK1, FK2)
function fileType(name) {
  const ext = name.split(".").pop().toUpperCase();
  return { JPG: "JPEG", JPEG: "JPEG", PNG: "PNG", TIF: "TIFF", TIFF: "TIFF" }[ext] ?? ext;
}

function readImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`${file.name} kan ikke vises i denne browser (TIFF vises kun i Safari)`));
    img.src = URL.createObjectURL(file);
  });
}

function makeThumbnail(draw, width, height) {
  const scale = 240 / Math.max(width, height);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  draw(canvas.getContext("2d"), canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.7);
}

async function uploadMeta(meta) {
  await run(() => orderApi("/images", { method: "POST", body: meta }));
}

$("#file-input").addEventListener("change", async (event) => {
  for (const file of event.target.files) {
    try {
      const img = await readImage(file);
      await uploadMeta({
        filename: file.name, file_type: fileType(file.name), file_size: file.size,
        px_width: img.naturalWidth, px_height: img.naturalHeight,
        thumbnail: makeThumbnail((ctx, w, h) => ctx.drawImage(img, 0, 0, w, h), img.naturalWidth, img.naturalHeight),
      });
    } catch (err) {
      toast(err.message, "error");
    }
  }
  event.target.value = "";
  await refreshOrder();
  renderThumbs();
});

// Eksempelbilleder med realistiske pixelmål, så DPI-advarslen kan afprøves uden egne filer
const SAMPLES = [
  { filename: "ferie-kamera.jpg", px_width: 6000, px_height: 4000, file_size: 9800000, colors: ["#4aa3df", "#f5d76e"] },
  { filename: "barnebarn-telefon.jpg", px_width: 3024, px_height: 4032, file_size: 3200000, colors: ["#f39c9c", "#fce4c4"] },
  { filename: "gammelt-billede.png", px_width: 1080, px_height: 1350, file_size: 850000, colors: ["#7f8c8d", "#d5dbdb"] },
];

$("#sample-button").addEventListener("click", async () => {
  for (const s of SAMPLES) {
    await uploadMeta({
      filename: s.filename, file_type: fileType(s.filename), file_size: s.file_size, px_width: s.px_width, px_height: s.px_height,
      thumbnail: makeThumbnail((ctx, w, h) => {
        const gradient = ctx.createLinearGradient(0, 0, w, h);
        gradient.addColorStop(0, s.colors[0]);
        gradient.addColorStop(1, s.colors[1]);
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = "#fff";
        ctx.font = "bold 18px system-ui";
        ctx.fillText(`${s.px_width} × ${s.px_height}`, 12, h - 14);
      }, s.px_width, s.px_height),
    });
  }
  await refreshOrder();
  renderThumbs();
});

function renderThumbs() {
  $("#thumbs").replaceChildren(...state.order.images.map((img) => h("div", { class: "thumb" },
    h("img", { src: img.thumbnail || "data:,", alt: img.filename }),
    h("strong", {}, img.filename), h("br"),
    h("small", { class: "muted" }, `${img.file_type} · ${mb(img.file_size)} · ${img.px_width} × ${img.px_height} px`),
    h("div", {}, h("button", { class: "small secondary", onclick: () => removeImage(img.id) }, "Fjern")))));
}

async function removeImage(imageId) {
  delete state.choices[imageId];
  await run(() => orderApi(`/images/${imageId}`, { method: "DELETE" }), "Billedet er fjernet");
  await refreshOrder();
  renderThumbs();
}

// ---------------------------------------------------------------- Trin 2: format, overflade, kvalitet, beskæring (FK3–FK9)
function productFor(label, surface, quality) {
  return state.products.find((p) => p.label === label && p.surface === surface && p.quality === quality);
}

// Kundens valg pr. billede bevares, så de står der stadig, når man går tilbage fra kurven
state.choices = {};

function choiceFor(img, labels) {
  if (!state.choices[img.id]) {
    const line = state.order.lines.find((l) => l.image_id === img.id);
    state.choices[img.id] = line
      ? { label: line.label, surface: line.surface, quality: line.quality, crop: line.crop, rotation: line.rotation, quantity: line.quantity }
      : { label: labels[1] ?? labels[0], surface: "BLANK", quality: "STANDARD", crop: "FYLD", rotation: 0, quantity: 1 };
  }
  return state.choices[img.id];
}

function renderConfig() {
  const labels = [...new Set(state.products.map((p) => p.label))];
  $("#config-list").replaceChildren(...state.order.images.map((img) => {
    const choice = choiceFor(img, labels);
    const preview = h("img", { src: img.thumbnail || "data:,", alt: img.filename });
    const result = h("div", {});
    const select = (name, options, onchange) => {
      const el = h("select", { onchange: (e) => { onchange(e.target.value); update(); } },
        options.map(([value, text]) => h("option", { value }, text)));
      el.value = choice[name];
      return el;
    };
    let timer;
    const update = () => {
      preview.style.transform = `rotate(${choice.rotation}deg)`;
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const product = productFor(choice.label, choice.surface, choice.quality);
        if (!product) {
          result.replaceChildren(h("p", { class: "empty" }, "Kombinationen findes ikke i kataloget."));
          return;
        }
        const q = await api("/quote", { method: "POST", body: { px_width: img.px_width, px_height: img.px_height, product_id: product.id, quantity: choice.quantity, rotation: choice.rotation } });
        result.replaceChildren(
          q.dpi_warning ? h("div", { class: "dpi-warning" }, `⚠ ${q.dpi_warning}`)
            : h("p", { class: "dpi-ok" }, `✓ God kvalitet (${q.effective_dpi} dpi)`),
          h("p", { class: "total" }, `${formatKr(q.line_price)}`, h("span", { class: "muted", style: "font-size:1rem;font-weight:normal" }, ` (${formatKr(q.unit_price)} pr. stk.)`)));
      }, 150);
    };
    const quantity = h("input", {
      type: "number", min: 1, max: 999, value: choice.quantity, inputmode: "numeric",
      oninput: (e) => { e.target.value = e.target.value.replace(/\D/g, "").slice(0, 3); choice.quantity = Number(e.target.value) || 1; update(); },
    });
    const card = h("div", { class: "card config" },
      h("div", {}, preview, h("small", { class: "muted" }, `${img.filename} · ${img.px_width} × ${img.px_height} px`)),
      h("div", {},
        h("div", { class: "row", style: "display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr))" },
          h("label", {}, "Størrelse", select("label", labels.map((l) => [l, l]), (v) => (choice.label = v))),
          h("label", {}, "Overflade", select("surface", [["BLANK", "Blank"], ["SILKE", "Silke"]], (v) => (choice.surface = v))),
          h("label", {}, "Kvalitet", select("quality", [["STANDARD", "Standard"], ["HØJ", "Høj kvalitet"]], (v) => (choice.quality = v))),
          h("label", {}, "Beskæring", select("crop", Object.entries(CROP_TEXT), (v) => (choice.crop = v))),
          h("label", {}, "Antal", quantity)),
        h("div", { class: "actions", style: "margin:10px 0" },
          h("button", { class: "secondary", onclick: () => { choice.rotation = (choice.rotation + 90) % 360; update(); } }, "↻ Rotér 90°")),
        result));
    update();
    return card;
  }));
}

// Én knap lægger alle billeder i kurven og går videre til kurven
$("#add-all-button").addEventListener("click", async () => {
  const lines = [];
  for (const img of state.order.images) {
    const c = state.choices[img.id];
    const product = productFor(c.label, c.surface, c.quality);
    if (!product) return toast(`Vælg et format, der findes i kataloget, til ${img.filename}`, "error");
    lines.push({ image_id: img.id, product_id: product.id, quantity: c.quantity, crop: c.crop, rotation: c.rotation });
  }
  const order = await run(() => orderApi("/lines", { method: "PUT", body: { lines } }),
    (o) => (o.warnings ? "Lagt i kurven – bemærk advarslen om kvalitet" : "Lagt i kurven"));
  state.order = { ...order, access_key: state.order.access_key };
  showStep(3);
});

// ---------------------------------------------------------------- Trin 3: kurv
function renderCart() {
  const o = state.order;
  const box = h("div");
  renderTable(box, o.lines, [
    { label: "Billede", key: "filename" },
    { label: "Format", render: (l) => cm(l) },
    { label: "Beskæring", render: (l) => `${CROP_TEXT[l.crop]}${l.rotation ? ` · ${l.rotation}°` : ""}` },
    { label: "Kvalitet", render: (l) => (l.dpi_warning ? badge(`${l.effective_dpi} dpi – lav`, "warn") : badge(`${l.effective_dpi} dpi`, "ok")) },
    { label: "Antal", class: "num", key: "quantity" },
    { label: "Pris", class: "num", render: (l) => formatKr(l.line_price) },
    { label: "", render: (l) => h("button", { class: "small secondary", onclick: () => removeLine(l.id) }, "Fjern") },
  ], "Kurven er tom – vælg format til dine billeder.");
  $("#cart").replaceChildren(box, h("p", { class: "total" }, `I alt ${formatKr(o.subtotal)}`),
    o.warnings ? h("p", { class: "dpi-warning" }, `⚠ ${o.warnings} print har lav opløsning og kan blive uskarpe.`) : null);
}

async function removeLine(lineId) {
  await run(() => orderApi(`/lines/${lineId}`, { method: "DELETE" }));
  await refreshOrder();
  renderCart();
}

// ---------------------------------------------------------------- Trin 4: oplysninger og betaling (FK10–FK12)
const PHONE_RULES = { "+45": [8, 8], "+46": [7, 10], "+47": [8, 8], "+49": [10, 11], "+298": [6, 6], "+299": [6, 6] };

function updatePhoneRule() {
  const [low, high] = PHONE_RULES[$("#phone-country").value];
  const input = $("#phone");
  input.maxLength = high;
  input.value = input.value.slice(0, high);
  input.pattern = `[0-9]{${low},${high}}`;
  input.title = low === high ? `${low} cifre` : `${low}–${high} cifre`;
  input.placeholder = "12345678901".slice(0, low);
}

// Filtrerer tegn væk, mens kunden skriver: telefon og postnummer kun tal, by ingen tal
function onlyAllow(selector, pattern) {
  $(selector).addEventListener("input", (e) => {
    const clean = e.target.value.replace(pattern, "");
    if (clean !== e.target.value) e.target.value = clean;
  });
}

onlyAllow("#phone", /\D/g);
onlyAllow("[name=postal_code]", /\D/g);
onlyAllow("[name=city]", /[0-9]/g);

$("#phone-country").addEventListener("change", updatePhoneRule);
updatePhoneRule();

function renderCheckout() {
  const form = $("#checkout-form");
  const shipping = form.elements.delivery.value === "FORSENDELSE" ? state.settings.shipping_price : 0;
  $("#address-fields").hidden = !shipping;
  ["street", "postal_code", "city"].forEach((name) => (form.elements[name].required = !!shipping));
  $("#checkout-total").textContent = `I alt ${formatKr(state.order.subtotal + shipping)}`;
}

$("#checkout-form").addEventListener("change", renderCheckout);

// Når kunden går til betaling, låses oplysningerne, så det der vises, også er det der bliver gemt.
// "Ret oplysninger" låser op igen og skjuler betalingen, indtil kunden har trykket "Gå til betaling" igen.
function lockCheckout(locked) {
  for (const field of $("#checkout-form").elements) field.disabled = locked;
  $("#checkout-actions").hidden = locked;
  $("#payment").hidden = !locked;
}

$("#checkout-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  // formToJson (fælles) tager ikke højde for radioknapper, så leveringsformen læses direkte
  const body = { ...formToJson(event.target), delivery: event.target.elements.delivery.value };
  const result = await run(() => orderApi("/checkout", { method: "POST", body }));
  await refreshOrder();
  const c = state.order.customer;
  $("#payment-summary").replaceChildren(
    h("p", { style: "margin:0 0 4px" }, h("strong", {}, "Dine oplysninger")),
    h("p", { style: "margin:0" }, `${c.name} · ${c.email} · ${c.phone}`),
    h("p", { style: "margin:0 0 8px" }, state.order.delivery === "AFHENTNING" ? "Hentes i butikken" : `Sendes til ${c.address}`));
  $("#payment-amount").textContent = `Beløb: ${formatKr(result.amount)}`;
  lockCheckout(true);
});

$("#edit-details-button").addEventListener("click", () => lockCheckout(false));

async function pay(approved) {
  try {
    const order = await orderApi("/payment", { method: "POST", body: { approved } });
    state.order = { ...order, access_key: state.order.access_key };
    renderReceipt();
    showStep(5);
  } catch (err) {
    toast(err.message, "error");
  }
}

$("#pay-button").addEventListener("click", () => pay(true));
$("#decline-button").addEventListener("click", () => pay(false));

// ---------------------------------------------------------------- Trin 5: kvittering
function renderReceipt() {
  const o = state.order;
  $("#receipt").replaceChildren(
    h("h2", {}, `Tak for din bestilling, ${o.customer.name}!`),
    h("p", {}, `Du har betalt ${formatKr(o.total)}`),
    h("p", {}, o.delivery === "AFHENTNING"
      ? `Dine print er klar til afhentning i butikken ${new Date(o.desired_ready).toLocaleDateString("da-DK", { weekday: "long", day: "numeric", month: "long" })}. Vi giver besked, når de er klar.`
      : `Dine print sendes til ${o.customer.address} og er forventet fremme ${new Date(o.desired_ready).toLocaleDateString("da-DK")}.`),
    h("div", { class: "receipt-box" },
      h("p", { style: "margin-top:0" }, h("strong", {}, "Gem disse to oplysninger."), " Du skal bruge dem under ", h("em", {}, "Min ordre"), " for at følge ordren eller slette dine billeder."),
      h("dl", {},
        h("dt", {}, "Ordrenummer"), h("dd", {}, o.id),
        h("dt", {}, "Adgangsnøgle"), h("dd", {}, o.access_key)),
      h("div", { class: "actions", style: "margin-top:10px" },
        h("button", { class: "secondary", onclick: () => navigator.clipboard.writeText(`Ordrenummer: ${o.id}\nAdgangsnøgle: ${o.access_key}`).then(() => toast("Kopieret")) }, "Kopiér"))),
    h("p", { class: "muted" }, `Betalingsreference fra betalingsudbyderen (står på din kontoudskrift): ${o.payment_ref}`));
}

$("#new-order-button").addEventListener("click", startOrder);

// ---------------------------------------------------------------- Min ordre: status, indsigt og sletning
$("#lookup-form").addEventListener("submit", (event) => {
  event.preventDefault();
  lookup(formToJson(event.target));
});

async function lookup({ id, key }) {
  const o = await run(() => api(`/orders/${id}?key=${encodeURIComponent(key)}`));
  const box = h("div");
  renderTable(box, o.lines, [
    { label: "Billede", key: "filename" },
    { label: "Format", render: (l) => cm(l) },
    { label: "Antal", class: "num", key: "quantity" },
    { label: "Pris", class: "num", render: (l) => formatKr(l.line_price) },
  ]);
  const stored = o.images.filter((i) => !i.deleted_at).length;
  $("#my-order").replaceChildren(h("div", { class: "card" },
    h("h2", {}, `Ordre ${o.id} `, badge(STATUS_TEXT[o.status], STATUS_BADGE[o.status])),
    o.desired_ready ? h("p", {}, `Forventet klar: ${o.desired_ready}`) : null,
    box,
    h("p", {}, `${stored} af ${o.images.length} billedfiler er gemt.`),
    stored ? h("button", {
      class: "danger",
      onclick: async () => {
        if (!confirm("Slet dine billedfiler nu? Ordren kan så ikke printes igen.")) return;
        await run(() => api(`/orders/${id}/images?key=${encodeURIComponent(key)}`, { method: "DELETE" }), "Dine billeder er slettet");
        lookup({ id, key });
      },
    }, "Slet mine billeder") : badge("Billederne er slettet", "muted")));
}

// ---------------------------------------------------------------- Operatørfladen (FK13–FK21)
$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const operator = await run(() => api("/operators/login", { method: "POST", body: formToJson(event.target) }));
  state.operatorId = operator.id;
  state.operatorName = operator.name;
  event.target.reset();
  $("#login-card").hidden = true;
  $("#operator-area").hidden = false;
  $("#operator-name").textContent = `· ${operator.name}`;
  loadQueue();
});

$("#logout-button").addEventListener("click", () => {
  state.operatorId = null;
  $("#login-card").hidden = false;
  $("#operator-area").hidden = true;
  $("#slip-card").replaceChildren();
});

async function loadQueue() {
  if (!state.operatorId) return;
  const roll = $("#roll-filter").value;
  const q = await operatorApi(`/queue${roll ? `?roll_width=${roll}` : ""}`);
  renderTable($("#queue-table"), q.orders, [
    { label: "Ordre", key: "id" },
    { label: "Færdig", render: (o) => h("strong", {}, o.desired_ready) },
    { label: "Kunde", key: "customer_name" },
    { label: "Levering", render: (o) => (o.delivery === "AFHENTNING" ? "Afhentning" : "Forsendelse") },
    { label: "Print", class: "num", key: "prints" },
    { label: "Ruller (mm)", render: (o) => o.roll_widths.join(", ") },
    { label: "Status", render: (o) => h("span", {}, badge(STATUS_TEXT[o.status], STATUS_BADGE[o.status]), o.warnings ? badge("lav DPI", "warn") : null) },
    {
      label: "",
      render: (o) => h("div", { class: "actions" },
        h("button", { class: "small secondary", onclick: () => showSlip(o.id) }, "Ordreseddel"),
        h("button", { class: "small", onclick: () => nextStatus(o) }, NEXT_ACTION[o.status][1])),
    },
  ], "Ingen ordrer i køen");
  $("#queue-info").textContent = `Sorteret efter ønsket færdigdato.${q.images_purged ? ` ${q.images_purged} billedfiler slettet efter opbevaringsfristen.` : ""}`
    + (q.recently_closed.length ? ` Senest afhentet: ${q.recently_closed.map((o) => `#${o.id}`).join(", ")}.` : "");
}

async function nextStatus(order) {
  const [action] = NEXT_ACTION[order.status];
  if (action === "release") {
    const r = await run(() => operatorApi(`/orders/${order.id}/release`, { method: "POST" }), "Printjob afleveret til C8");
    showSlip(order.id, r.print_job);
  } else {
    const r = await run(() => operatorApi(`/orders/${order.id}/status`, { method: "PUT", body: { status: action } }), `Ordre ${order.id}: ${STATUS_TEXT[action].toLowerCase()}`);
    if (r.notification) toast(`Besked sendt til kunden: "${r.notification}"`);
  }
  loadQueue();
}

async function showSlip(orderId, printJob) {
  const s = await operatorApi(`/orders/${orderId}/slip`);
  $("#slip-card").replaceChildren(h("div", { class: "card" },
    h("div", { class: "slip" },
      h("div", { class: "toolbar" }, h("h2", { style: "margin:0;flex:1" }, `Ordreseddel · ordre ${s.order_id}`), h("span", { class: "barcode" }, s.barcode)),
      h("p", {}, `${s.customer.name} · ${s.customer.phone} · ${s.customer.email}`),
      h("p", {}, `${s.delivery === "AFHENTNING" ? "Afhentning" : `Forsendelse: ${s.customer.address}`} · færdig ${s.desired_ready} · ${formatKr(s.total)}`),
      ...s.roll_groups.map((g) => {
        const box = h("div");
        renderTable(box, g.lines, [
          { label: "Billede", key: "filename" },
          { label: "Format", render: (l) => cm(l) },
          { label: "Beskæring", render: (l) => `${CROP_TEXT[l.crop]}${l.rotation ? ` · ${l.rotation}°` : ""}` },
          { label: "DPI", class: "num", key: "effective_dpi" },
          { label: "Antal", class: "num", key: "quantity" },
        ]);
        return h("div", {}, h("h3", {}, `Papirrulle ${g.roll_width_mm} mm`), box);
      }),
      h("p", { class: "muted" }, `${s.roll_changes} rulleskift`)),
    printJob ? h("details", { open: true }, h("summary", {}, "Printjob til C8"), h("pre", { class: "json" }, JSON.stringify(printJob, null, 2))) : null,
    h("div", { class: "actions no-print", style: "margin-top:10px" }, h("button", { class: "secondary", onclick: () => window.print() }, "Udskriv ordreseddel"))));
  $("#slip-card").scrollIntoView({ behavior: "smooth" });
}

$("#roll-filter").addEventListener("change", loadQueue);

// ---------------------------------------------------------------- Produktkatalog og indstillinger (FK23, §14)
async function loadCatalog() {
  $("#catalog-locked").hidden = !!state.operatorId;
  $("#catalog-area").hidden = !state.operatorId;
  if (!state.operatorId) return;
  const [products, settings, stats] = await Promise.all([api("/products"), api("/settings"), api("/stats")]);
  renderTable($("#product-table"), products, [
    { label: "Format", key: "label" },
    { label: "Mål (mm)", render: (p) => `${p.width_mm} × ${p.height_mm}` },
    { label: "Rulle", class: "num", key: "roll_width_mm" },
    { label: "Overflade", render: (p) => (p.surface === "BLANK" ? "Blank" : "Silke") },
    { label: "Kvalitet", render: (p) => (p.quality === "HØJ" ? "Høj" : "Standard") },
    { label: "Pris", class: "num", render: (p) => formatKr(p.price) },
    { label: "", render: (p) => crudButtons("products", $("#product-form"), p, reloadCatalog) },
  ]);
  renderTable($("#setting-table"), settings, [
    { label: "Nøgle", key: "key" },
    { label: "Værdi", class: "num", key: "value" },
    { label: "Beskrivelse", key: "description" },
    { label: "", render: (s) => h("button", { class: "small secondary", onclick: () => fillForm($("#setting-form"), s) }, "Redigér") },
  ]);
  renderTable($("#popular-table"), stats.popular, [
    { label: "Format", key: "label" },
    { label: "Overflade", render: (p) => (p.surface === "BLANK" ? "Blank" : "Silke") },
    { label: "Print", class: "num", key: "prints" },
    { label: "Omsætning", class: "num", render: (p) => formatKr(p.revenue) },
  ]);
}

function reloadCatalog() {
  loadBase().then(loadCatalog);
}

bindCrudForm($("#product-form"), "products", reloadCatalog);
bindCrudForm($("#setting-form"), "settings", reloadCatalog);

// ---------------------------------------------------------------- Start
$("#debug-panel").hidden = !new URLSearchParams(location.search).has("debug");
setupTabs((tab) => {
  if (tab === "queue") loadQueue();
  if (tab === "catalog") loadCatalog();
});
loadBase()
  .then(startOrder)
  .catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
