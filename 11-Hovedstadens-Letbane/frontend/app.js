// Hovedstadens Letbane – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { user: null, lang: "da", stations: [], stationId: "HER", timer: null, liveTimer: null, points: null,
  maps: {}, live: [], follow: null, position: null, positionSimulated: false, celebration: null };

// F-13: dansk og engelsk. Enkelt sprog – "aflyst" frem for "indstillet" (afsnit 16)
const TEXT = {
  da: {
    tagline: "Til tiden, tydelig information og nemme skift", tabHome: "Forside", tabBoard: "Afgange", tabTrip: "Rejse",
    tabTickets: "Billetter", tabLive: "Live", tabRewards: "Belønninger", tabFeedback: "Feedback", tabSettings: "Indstillinger",
    whereTo: "Hvor skal du hen?", myTrips: "Mine rejser",
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
    // Kort og live
    mapTitle: "Kort – se hvor du er, og følg letbanen", mapStandard: "Standardkort", mapSatellite: "Satellitkort",
    myLocation: "📍 Min placering", wholeLine: "Vis hele linjen", youAreHere: "Du er her",
    locationReal: "Kortene viser din placering. Zoom ind og ud for at se området omkring dig.",
    locationSimulated: "Din placering kunne ikke hentes – kortene viser Herlev St. som eksempel.",
    mapUnavailable: "Kortet kunne ikke hentes. Tjek internetforbindelsen.", showDepartures: "tryk for afgange",
    liveTitle: "Følg letbanen live", liveList: "Letbanetog i drift lige nu", train: "Tog", nextStop: "Næste station",
    arrival: "Ankomst", status: "Status", show: "Vis på kort", noTrams: "Ingen letbanetog i drift lige nu.",
    followLive: "📡 Følg letbanen live", notDeparted: "Letbanen er ikke kørt fra endestationen endnu. Prøv igen om lidt.",
    liveEvery: "opdateres hvert 5. sekund",
    // Billetter
    buyTicket: "🎟 Køb billet", buyTitle: "Køb billet", ticketType: "Billettype", adult: "Voksen", child: "Barn (under 16 år)",
    count: "Antal", payment: "Betaling", card: "Betalingskort", mobilepay: "MobilePay", credit: "Rejsekredit", freeTicket: "Gratis billet",
    zones: "zoner", validFor: "gyldig i", total: "I alt", pay: "Betal og hent billet", cancel: "Fortryd",
    ticketBought: "Billetten er købt", myTickets: "Mine billetter", noTickets: "Du har ingen billetter endnu. Find en rejse og tryk 'Køb billet'.",
    validUntil: "Gyldig til kl.", controlCode: "Kontrolkode", endTrip: "Afslut rejse (+10 point)", bought: "Købt",
    VALID: "Gyldig", USED: "Brugt", EXPIRED: "Udløbet", activeTickets: "Dine gyldige billetter", seeTickets: "Se billetter",
    // Point og belønninger
    points: "point", yourPoints: "Dine point", nextReward: "Næste belønning", missing: "Du mangler {n} point",
    allUnlocked: "Du har point nok til alle belønninger!", perTrip: "Du optjener {n} point, hver gang du rejser med letbanen.",
    seeRewards: "Se belønninger", rewardsTitle: "Brug dine point", redeem: "Indløs", redeemConfirm: "Vil du bruge {n} point på",
    redeemedToast: "Belønningen er indløst", redeemed: "Dine indløste belønninger", noRedemptions: "Du har ikke indløst belønninger endnu.",
    pointHistory: "Seneste point", noHistory: "Ingen point endnu.", tripGeneric: "Rejse med letbanen", code: "Kode",
    balance: "Rejsekredit: {kr} kr. · Gratis billetter: {n}", youCanRedeem: "Du kan nu indløse", wellDone: "godt gået!",
    tickets: "billetter",
  },
  en: {
    tagline: "On time, clear information and easy connections", tabHome: "Home", tabBoard: "Departures", tabTrip: "Journey",
    tabTickets: "Tickets", tabLive: "Live", tabRewards: "Rewards", tabFeedback: "Feedback", tabSettings: "Settings",
    whereTo: "Where are you going?", myTrips: "My journeys",
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
    mapTitle: "Maps – see where you are and follow the light rail", mapStandard: "Standard map", mapSatellite: "Satellite map",
    myLocation: "📍 My location", wholeLine: "Show the whole line", youAreHere: "You are here",
    locationReal: "The maps show your location. Zoom in and out to see the area around you.",
    locationSimulated: "Your location could not be found – the maps show Herlev St. as an example.",
    mapUnavailable: "The map could not be loaded. Check your internet connection.", showDepartures: "tap for departures",
    liveTitle: "Follow the light rail live", liveList: "Trains in service right now", train: "Train", nextStop: "Next station",
    arrival: "Arrival", status: "Status", show: "Show on map", noTrams: "No trains in service right now.",
    followLive: "📡 Follow the train live", notDeparted: "The train has not left the terminus yet. Try again shortly.",
    liveEvery: "updates every 5 seconds",
    buyTicket: "🎟 Buy ticket", buyTitle: "Buy ticket", ticketType: "Ticket type", adult: "Adult", child: "Child (under 16)",
    count: "Number", payment: "Payment", card: "Payment card", mobilepay: "MobilePay", credit: "Travel credit", freeTicket: "Free ticket",
    zones: "zones", validFor: "valid for", total: "Total", pay: "Pay and get ticket", cancel: "Cancel",
    ticketBought: "The ticket has been bought", myTickets: "My tickets", noTickets: "You have no tickets yet. Find a journey and tap 'Buy ticket'.",
    validUntil: "Valid until", controlCode: "Control code", endTrip: "End journey (+10 points)", bought: "Bought",
    VALID: "Valid", USED: "Used", EXPIRED: "Expired", activeTickets: "Your valid tickets", seeTickets: "See tickets",
    points: "points", yourPoints: "Your points", nextReward: "Next reward", missing: "You need {n} more points",
    allUnlocked: "You have enough points for every reward!", perTrip: "You earn {n} points every time you travel by light rail.",
    seeRewards: "See rewards", rewardsTitle: "Use your points", redeem: "Redeem", redeemConfirm: "Do you want to spend {n} points on",
    redeemedToast: "The reward has been redeemed", redeemed: "Your redeemed rewards", noRedemptions: "You have not redeemed any rewards yet.",
    pointHistory: "Latest points", noHistory: "No points yet.", tripGeneric: "Journey by light rail", code: "Code",
    balance: "Travel credit: DKK {kr} · Free tickets: {n}", youCanRedeem: "You can now redeem", wellDone: "well done!",
    tickets: "tickets",
  },
};

function t(key) {
  return TEXT[state.lang][key] ?? key;
}

function translatePage() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  $("#lang-button").textContent = state.lang === "da" ? "English" : "Dansk";
  if (state.points) $("#points-chip").textContent = `⭐ ${state.points.point} ${t("points")}`;
}

function hhmm(value) {
  return value ? new Date(value).toLocaleTimeString("da-DK", { hour: "2-digit", minute: "2-digit" }) : "–";
}

function byLang(row, field) {
  return state.lang === "en" && row[`${field}_en`] ? row[`${field}_en`] : row[`${field}_da`];
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

// LF-2: status vises med farve OG tekst/ikon
function statusBadge(line) {
  if (line.status === "AFLYST") return h("span", { class: "st cancel" }, t("cancelled"));
  if (line.forsinkelse_min >= 2) return h("span", { class: "st late" }, t("late").replace("{n}", line.forsinkelse_min));
  return h("span", { class: "st ok" }, t("onTime"));
}

function messageCard(m) {
  return h("div", { class: `card msg ${m.alvorlighed}` },
    h("h3", {}, m.alvorlighed === "KRITISK" ? "⛔ " : m.alvorlighed === "ADVARSEL" ? "⚠ " : "ℹ ", byLang(m, "titel")),
    h("p", {}, byLang(m, "tekst")),
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
  renderLocationNote();
  reloadActive();
}

$("#lang-button").addEventListener("click", () => saveUser({ sprog: state.lang === "da" ? "en" : "da" }));
$("#size-button").addEventListener("click", () => saveUser({ stor_tekst: !state.user.stor_tekst }));
$("#points-chip").addEventListener("click", () => openTab("rewards"));

// ---------------------------------------------------------------- Point: saldo og fremskridt mod næste belønning
async function refreshPoints() {
  state.points = await api(`/brugere/${state.user.bruger_id}/point`);
  $("#points-chip").textContent = `⭐ ${state.points.point} ${t("points")}`;
  return state.points;
}

function pointsBox(p, { link } = {}) {
  const next = p.naeste_beloenning;
  return h("div", { class: "points" },
    h("div", {}, h("span", { class: "muted" }, t("yourPoints")), h("div", { class: "total" }, `⭐ ${p.point} ${t("points")}`)),
    h("div", { class: "progress", role: "progressbar", "aria-valuenow": p.fremskridt_pct, "aria-valuemin": 0, "aria-valuemax": 100 },
      h("span", { style: `width:${p.fremskridt_pct}%` })),
    next
      ? h("div", {}, h("strong", {}, `${t("nextReward")}: ${byLang(next, "navn")}`), ` · ${p.point} / ${next.pris_point} · ${t("missing").replace("{n}", p.mangler_point)}`)
      : h("strong", {}, t("allUnlocked")),
    h("small", { class: "muted" }, t("perTrip").replace("{n}", p.point_pr_rejse)),
    link ? h("div", { class: "actions" }, h("button", { class: "small secondary", onclick: () => openTab("rewards") }, t("seeRewards"))) : null);
}

function celebrationBanner() {
  const c = state.celebration;
  if (!c) return null;
  return h("div", { class: "celebrate" }, `🎉 ${state.lang === "en" ? c.besked_en : c.besked_da}`,
    c.ny_beloenning ? h("small", {}, `${t("youCanRedeem")}: ${byLang(c.ny_beloenning, "navn")}`) : null);
}

// ---------------------------------------------------------------- Forside
async function loadHome() {
  const id = state.user.bruger_id;
  const [favorites, messages, notices, points, tickets] = await Promise.all([
    api(`/brugere/${id}/favoritter`), api("/driftsmeddelelser?aktive=true"), api(`/brugere/${id}/notifikationer`),
    refreshPoints(), api(`/brugere/${id}/billetter`)]);
  show($("#notices"), celebrationBanner(), notices.map((n) => h("div", { class: "notice" },
    `🔔 ${byLang(n, "titel")} – ${n.favorit_navn ?? ""}`,
    n.alternativ_rejse ? h("div", { style: "font-weight:400" }, `${t("alternative")}: ${n.alternativ_rejse}`) : null)));
  show($("#home-points"), pointsBox(points, { link: true }));
  const valid = tickets.filter((b) => b.status === "GYLDIG");
  show($("#home-tickets"), valid.length ? [h("h2", {}, t("activeTickets")), h("div", { class: "grid" }, valid.map(ticketCard))] : null);
  show($("#favorites"), favorites.length ? favorites.map((f) => {
    const leg = f.naeste.rejseben.find((b) => b.type === "LETBANE");
    return h("div", { class: "card fav" },
      h("h3", {}, `★ ${f.navn ?? ""}`), h("p", { class: "muted" }, `${f.fra_navn} → ${f.til_navn}`),
      leg ? h("div", {},
        h("div", { class: "big" }, `${hhmm(leg.forventet_afgang)} `, statusBadge(leg)),
        h("p", {}, `${t("next")} ${t("in")} ${minutesUntil(leg.forventet_afgang)} ${t("min")} · ${t("arrive")} ${hhmm(leg.forventet_ankomst)}`))
        : h("p", { class: "notice" }, t("noTrip"), f.naeste.alternativ_rejse ? h("div", { style: "font-weight:400" }, `${t("alternative")}: ${f.naeste.alternativ_rejse}`) : null),
      h("div", { class: "actions" },
        h("button", { class: "small", onclick: () => planTrip(f.fra_station_id, f.til_station_id) }, t("search")),
        h("button", { class: "small secondary", onclick: () => deleteFavorite(f.favorit_id) }, t("remove"))));
  }) : h("p", { class: "empty" }, t("noFavorites")));
  show($("#messages"), messages.length ? messages.map(messageCard) : h("p", { class: "empty" }, t("noMessages")));
}

async function deleteFavorite(id) {
  await run(() => api(`/favoritter/${id}`, { method: "DELETE" }));
  loadHome();
}

// Rejseplanlæggeren på forsiden sender videre til fanen Rejse
const homeForm = $("#home-trip-form");
homeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const q = formToJson(homeForm);
  planTrip(q.fra, q.til, q.tid);
});

$("#swap-button").addEventListener("click", () => {
  const { fra, til } = homeForm.elements;
  [fra.value, til.value] = [til.value, fra.value];
});

function planTrip(fra, til, tid = "") {
  const form = $("#trip-form");
  form.elements.fra.value = fra;
  form.elements.til.value = til;
  form.elements.tid.value = tid;
  openTab("trip");
  searchTrip();
}

// ---------------------------------------------------------------- Kort: standard og satellit med egen placering, stationer og tog
const TILES = {
  standard: { url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", attribution: "© OpenStreetMap" },
  satellite: { url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attribution: "Tiles © Esri" },
};

function tileLayer(kind) {
  return L.tileLayer(TILES[kind].url, { maxZoom: 19, attribution: TILES[kind].attribution });
}

function createMap(elementId, kind, { switchable } = {}) {
  if (!window.L) {
    $(`#${elementId}`).replaceChildren(h("p", { class: "empty", style: "padding:16px" }, t("mapUnavailable")));
    return null;
  }
  const layers = { standard: tileLayer("standard"), satellite: tileLayer("satellite") };
  const map = L.map(elementId, { layers: [layers[kind]] });
  if (switchable) L.control.layers({ [t("mapStandard")]: layers.standard, [t("mapSatellite")]: layers.satellite }, null, { collapsed: false }).addTo(map);
  const line = L.polyline(state.stations.map((s) => [s.latitude, s.longitude]),
    { color: kind === "satellite" ? "#7dffa8" : "#00843d", weight: 5, opacity: 0.9 }).addTo(map);
  for (const s of state.stations) {
    L.circleMarker([s.latitude, s.longitude], { radius: 7, color: "#005c2b", weight: 3, fillColor: "#fff", fillOpacity: 1 })
      .bindTooltip(`${s.navn} – ${t("showDepartures")}`)
      .on("click", () => {                       // tryk på en station åbner dens afgangstavle
        state.stationId = s.station_id;
        $("#station-select").value = s.station_id;
        openTab("board");
      })
      .addTo(map);
  }
  map.fitBounds(line.getBounds(), { padding: [20, 20] });
  const entry = { map, line, trams: new Map(), userMarker: null };
  placeUser(entry, !switchable);            // forsidens kort centreres på brugeren, live-kortet viser hele linjen
  updateTrams(entry);
  return entry;
}

function allMaps() {
  return Object.values(state.maps).filter(Boolean);
}

function placeUser(entry, center) {
  if (!state.position) return;
  const pos = [state.position.lat, state.position.lng];
  if (entry.userMarker) entry.userMarker.setLatLng(pos);
  else {
    entry.userMarker = L.circleMarker(pos, { radius: 9, color: "#fff", weight: 3, fillColor: "#1a73e8", fillOpacity: 1 })
      .bindTooltip(t("youAreHere"), { permanent: true, direction: "top", offset: [0, -8] }).addTo(entry.map);
  }
  if (center) entry.map.setView(pos, 13);
}

function renderLocationNote() {
  if (state.position) $("#location-note").textContent = t(state.positionSimulated ? "locationSimulated" : "locationReal");
}

function setPosition(position, simulated) {
  state.position = position;
  state.positionSimulated = simulated;
  allMaps().forEach((entry) => placeUser(entry, true));
  renderLocationNote();
}

// Henter enhedens placering. Kan den ikke hentes (afvist eller ikke understøttet), vises Herlev St. som eksempel.
function locate() {
  const herlev = state.stations.find((s) => s.station_id === "HER");
  const fallback = () => setPosition({ lat: herlev.latitude, lng: herlev.longitude }, true);
  if (!navigator.geolocation) return fallback();
  navigator.geolocation.getCurrentPosition(
    (pos) => setPosition({ lat: pos.coords.latitude, lng: pos.coords.longitude }, false),
    fallback, { timeout: 8000, maximumAge: 60000 });
}

$("#locate-button").addEventListener("click", locate);
$("#fit-button").addEventListener("click", () => allMaps().forEach((entry) => entry.map.fitBounds(entry.line.getBounds(), { padding: [20, 20] })));

// ---------------------------------------------------------------- Live tracker: togenes position hentes hvert 5. sekund
function tramLabel(v) {
  return `${v.koeretoej_id} ${t("towards")} ${v.mod} · ${v.naeste_station_navn} ${hhmm(v.forventet_ankomst)}`;
}

function updateTrams(entry) {
  const seen = new Set();
  for (const v of state.live) {
    seen.add(v.afgang_id);
    let marker = entry.trams.get(v.afgang_id);
    if (!marker) {
      marker = L.marker([v.latitude, v.longitude], {
        icon: L.divIcon({ className: `tram ${v.retning}`, html: "🚊", iconSize: [32, 32] }), zIndexOffset: 500,
      }).bindTooltip(tramLabel(v)).addTo(entry.map);
      entry.trams.set(v.afgang_id, marker);
    } else {
      marker.setLatLng([v.latitude, v.longitude]);          // CSS-overgangen på .tram får toget til at glide
      marker.setTooltipContent(tramLabel(v));
    }
    marker.getElement()?.classList.toggle("follow", v.afgang_id === state.follow);
  }
  for (const [id, marker] of entry.trams) {
    if (!seen.has(id)) {
      marker.remove();
      entry.trams.delete(id);
    }
  }
}

async function refreshLive() {
  const tab = activeTab();
  if (document.hidden || !["home", "live"].includes(tab)) return;
  let data;
  try { data = await api("/live"); } catch { return; }
  state.live = data.koeretoejer;
  allMaps().forEach(updateTrams);
  if (tab === "live") renderLiveList(data);
}

function renderLiveList(data) {
  $("#live-updated").textContent = `${t("updated")} ${new Date(data.opdateret_tid).toLocaleTimeString("da-DK")} · ${t("liveEvery")}`;
  renderTable($("#live-list"), [...state.live].sort((a, b) => (a.afgang_id === state.follow ? -1 : b.afgang_id === state.follow ? 1 : 0)), [
    { label: t("train"), render: (v) => h("strong", {}, `${v.afgang_id === state.follow ? "⭐ " : ""}${v.koeretoej_id}`) },
    { label: "", render: (v) => `${t("towards")} ${v.mod}` },
    { label: t("nextStop"), key: "naeste_station_navn" },
    { label: t("arrival"), render: (v) => `${hhmm(v.forventet_ankomst)} (${minutesUntil(v.forventet_ankomst)} ${t("min")})` },
    { label: t("status"), render: (v) => statusBadge(v) },
    { label: "", render: (v) => h("button", { class: "small secondary", onclick: () => followTram(v.afgang_id) }, t("show")) },
  ], t("noTrams"));
}

async function loadLive() {
  state.maps.live ??= createMap("map-live", "standard", { switchable: true });
  state.maps.live?.map.invalidateSize();
  await refreshLive();
}

// Åbner Live-fanen og fremhæver det tog, der kører den valgte afgang
async function followTram(afgangId) {
  state.follow = afgangId;
  if (activeTab() !== "live") openTab("live");
  await loadLive();
  const v = state.live.find((x) => x.afgang_id === afgangId);
  if (!v) return toast(t("notDeparted"), "error");
  state.maps.live?.map.setView([v.latitude, v.longitude], 14);
  $("#map-live").scrollIntoView({ behavior: "smooth", block: "center" });
}

// ---------------------------------------------------------------- Afgangstavle – opdateres hvert 30. sekund (P-2, P-3)
async function loadBoard() {
  const station = state.stations.find((s) => s.station_id === state.stationId);
  $("#station-icons").replaceChildren(
    h("span", {}, station.har_elevator ? `🛗 ${t("elevator")}` : `🚫 ${t("noElevator")}`),
    ...(station.cykelparkering ? [h("span", {}, `🚲 ${t("bikes")}`)] : []),
    ...(station.er_skiftestation ? [h("span", {}, `🔁 ${t("change")}`)] : []));
  const [board, connections] = await Promise.all([api(`/stationer/${state.stationId}/afgange`), api(`/stationer/${state.stationId}/skift`)]);
  $("#board-updated").textContent = `${t("updated")} ${hhmm(board.opdateret_tid)}`;
  $("#board-messages").replaceChildren(...board.driftsmeddelelser.map(messageCard));
  const byDirection = ["SYD", "NORD"].map((dir) => board.afgange.filter((a) => a.retning === dir));
  $("#board").replaceChildren(...byDirection.filter((lines) => lines.length).map((lines) => h("div", { class: "card" },
    h("h3", {}, `${t("towards")} ${lines[0].mod}`),
    h("table", { class: "board" }, h("tbody", {}, lines.map((a) => h("tr", { class: a.status },
      h("td", { class: "time" }, hhmm(a.planlagt_afgang)),
      h("td", {}, statusBadge(a)),
      h("td", { class: "num" }, a.status === "AFLYST" ? "" : `${minutesUntil(a.forventet_afgang)} ${t("min")}`),
      h("td", {}, a.status === "AFLYST" ? null
        : h("button", { class: "small secondary", title: t("followLive"), onclick: () => followTram(a.afgang_id) }, "📡")))))))));
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
  $("#purchase").replaceChildren();
  const r = await run(() => api(`/rejse?${params}`));
  const leg = r.rejseben.find((b) => b.type === "LETBANE");
  const changes = r.rejseben.filter((b) => b.type === "SKIFT");
  show($("#trip-result"), h("div", { class: "card highlight" },
    h("h2", {}, `${r.fra_navn} → ${r.til_navn}`),
    leg ? h("div", {},
      h("p", { class: "fav" }, h("span", { class: "big" }, `${hhmm(leg.forventet_afgang)} → ${hhmm(leg.forventet_ankomst)} `), statusBadge(leg)),
      h("p", {}, `${t("travelTime")}: ${r.samlet_rejsetid_min} ${t("min")} · ${t("in")} ${r.ventetid_min} ${t("min")}`))
      : h("p", { class: "notice" }, t("noTrip")),
    r.alternativ_rejse ? h("p", {}, h("strong", {}, `${t("alternative")}: `), r.alternativ_rejse) : null,
    r.aflyste_afgange.length ? h("p", { class: "muted" }, `${t("cancelledDepartures")}: ${r.aflyste_afgange.map((a) => hhmm(a.planlagt_afgang)).join(", ")}`) : null,
    changes.length ? h("div", {}, h("h3", {}, `🔁 ${t("connections")} – ${r.til_navn}`),
      h("ul", { class: "list" }, changes.map((c) => h("li", {}, h("strong", {}, c.linje), ` · ${c.gangtid_min} ${t("min")} ${t("walk")} · ${c.beskrivelse ?? ""}`)))) : null,
    r.driftsmeddelelser.map(messageCard),
    h("div", { class: "actions" },
      leg ? h("button", { onclick: () => showPurchase(r, leg) }, t("buyTicket")) : null,
      leg ? h("button", { class: "secondary", onclick: () => followTram(leg.afgang_id) }, t("followLive")) : null,
      h("button", { class: "secondary", onclick: () => saveFavorite(r) }, t("saveFavorite")))));
}

async function saveFavorite(r) {
  const name = prompt(t("favoriteName"), "");
  if (name === null) return;
  await run(() => api("/favoritter", {
    method: "POST", body: { bruger_id: state.user.bruger_id, fra_station_id: r.fra_station_id, til_station_id: r.til_station_id, navn: name },
  }), t("saved"));
}

// ---------------------------------------------------------------- Billetkøb til den planlagte rejse (betalingen er simuleret)
async function showPurchase(r, leg) {
  const [price, points] = await Promise.all([
    run(() => api(`/billetpris?fra=${r.fra_station_id}&til=${r.til_station_id}`)), refreshPoints()]);
  const total = h("span", { class: "total-price" });
  const form = h("form", {},
    h("div", { class: "row" },
      h("label", {}, t("ticketType"), h("select", { name: "billettype" },
        h("option", { value: "VOKSEN" }, `${t("adult")} – ${price.priser.VOKSEN} kr.`),
        h("option", { value: "BARN" }, `${t("child")} – ${price.priser.BARN} kr.`))),
      h("label", {}, t("count"), h("input", { name: "antal", type: "number", min: 1, max: 9, value: 1, required: true })),
      h("label", {}, t("payment"), h("select", { name: "betalingsmetode" },
        h("option", { value: "KORT" }, t("card")),
        h("option", { value: "MOBILEPAY" }, t("mobilepay")),
        h("option", { value: "REJSEKREDIT", disabled: points.rejsekredit_kr <= 0 }, `${t("credit")} (${points.rejsekredit_kr} kr.)`),
        h("option", { value: "GRATIS_BILLET", disabled: points.gratis_billetter <= 0 }, `${t("freeTicket")} (${points.gratis_billetter})`)))),
    h("p", {}, `${t("total")}: `, total),
    h("div", { class: "actions" },
      h("button", {}, t("pay")),
      h("button", { type: "button", class: "secondary", onclick: () => $("#purchase").replaceChildren() }, t("cancel"))));
  const update = () => {
    const f = form.elements;
    const free = f.betalingsmetode.value === "GRATIS_BILLET";
    if (free) f.antal.value = 1;
    f.antal.disabled = free;
    total.textContent = `${free ? 0 : price.priser[f.billettype.value] * (Number(f.antal.value) || 1)} kr.`;
  };
  form.addEventListener("input", update);
  update();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const f = form.elements;
    await run(() => api("/billetter", {
      method: "POST",
      body: { bruger_id: state.user.bruger_id, fra_station_id: r.fra_station_id, til_station_id: r.til_station_id, afgang_id: leg.afgang_id,
        billettype: f.billettype.value, antal: Number(f.antal.value), betalingsmetode: f.betalingsmetode.value },
    }), t("ticketBought"));
    $("#purchase").replaceChildren();
    state.celebration = null;
    openTab("tickets");
  });
  show($("#purchase"), h("div", { class: "card" },
    h("h2", {}, `${t("buyTitle")}: ${r.fra_navn} → ${r.til_navn}`),
    h("p", { class: "muted" }, `${price.zoner} ${t("zones")} · ${t("validFor")} ${price.gyldighed_min} ${t("min")} · ${hhmm(leg.forventet_afgang)} → ${hhmm(leg.forventet_ankomst)}`),
    form));
  $("#purchase").scrollIntoView({ behavior: "smooth", block: "center" });
}

// ---------------------------------------------------------------- Billetter
const TICKET_STATUS = { GYLDIG: ["VALID", "ok"], BRUGT: ["USED", "muted"], UDLOEBET: ["EXPIRED", "warn"] };
const PAYMENT_TEXT = { KORT: "card", MOBILEPAY: "mobilepay", REJSEKREDIT: "credit", GRATIS_BILLET: "freeTicket" };

function ticketCard(b) {
  const [statusKey, variant] = TICKET_STATUS[b.status];
  return h("div", { class: `card ticket ${b.status}` },
    h("h3", {}, `🎟 ${b.fra_navn} → ${b.til_navn} `, badge(t(statusKey), variant)),
    h("p", {}, `${b.antal} × ${t(b.billettype === "BARN" ? "child" : "adult")} · ${b.zoner} ${t("zones")} · ${b.pris_kr} kr. (${t(PAYMENT_TEXT[b.betalingsmetode])})`),
    h("p", {}, h("strong", {}, `${t("validUntil")} ${hhmm(b.gyldig_til)}`), h("small", { class: "muted" }, ` · ${t("bought")} ${formatDate(b.koebt_tid)}`)),
    h("div", { class: "barcode", "aria-hidden": "true" }),
    h("div", {}, h("small", { class: "muted" }, `${t("controlCode")} `), h("span", { class: "code" }, b.kontrolkode)),
    b.status === "GYLDIG" ? h("div", { class: "actions", style: "margin-top:10px" },
      h("button", { onclick: () => endTrip(b) }, t("endTrip")),
      b.afgang_id ? h("button", { class: "secondary", onclick: () => followTram(b.afgang_id) }, t("followLive")) : null) : null);
}

async function loadTickets() {
  const tickets = await api(`/brugere/${state.user.bruger_id}/billetter`);
  show($("#ticket-banner"), celebrationBanner());
  show($("#tickets"), tickets.length ? tickets.map(ticketCard) : h("p", { class: "empty" }, t("noTickets")));
}

// Efter rejsen: billetten bliver brugt, og brugeren får besked om de optjente point
async function endTrip(ticket) {
  const result = await run(() => api(`/billetter/${ticket.billet_id}/afslut`, { method: "POST", body: {} }),
    (r) => (state.lang === "en" ? r.besked_en : r.besked_da));
  state.celebration = result;
  await refreshPoints();
  reloadActive();
}

// ---------------------------------------------------------------- Belønninger: brug point
async function loadRewards() {
  const [rewards, p] = await Promise.all([api("/beloenninger"), refreshPoints()]);
  show($("#rewards-points"), pointsBox(p),
    h("p", { class: "muted", style: "margin-bottom:0" }, t("balance").replace("{kr}", p.rejsekredit_kr).replace("{n}", p.gratis_billetter)));
  show($("#rewards"), rewards.map((r) => {
    const missing = r.pris_point - p.point;
    return h("div", { class: `card reward ${missing <= 0 ? "highlight" : ""}` },
      h("div", { class: "cost" }, `${r.pris_point} ${t("points")}`),
      h("h3", {}, `${{ GRATIS_BILLET: "🎟", REJSEKREDIT: "💳", STOR: "🏆" }[r.type]} ${byLang(r, "navn")}`),
      h("p", {}, byLang(r, "beskrivelse")),
      h("div", { class: "progress" }, h("span", { style: `width:${Math.min(100, Math.round(100 * p.point / r.pris_point))}%` })),
      h("p", {}, missing > 0 ? h("small", { class: "muted" }, t("missing").replace("{n}", missing)) : null),
      h("button", { disabled: missing > 0, onclick: () => redeem(r) }, t("redeem")));
  }));
  show($("#redemptions"), p.indloesninger.length ? h("ul", { class: "list" }, p.indloesninger.map((i) => h("li", {},
    h("strong", {}, byLang(i, "navn")), h("small", { class: "muted" }, ` · ${formatDate(i.tidspunkt)}`),
    i.kode ? h("div", {}, `${t("code")}: `, h("code", {}, i.kode)) : null))) : h("p", { class: "empty" }, t("noRedemptions")));
  renderTable($("#point-history"), p.historik, [
    { label: "", render: (x) => formatDate(x.tidspunkt) },
    { label: "", render: (x) => (x.type === "REJSE" ? (x.fra_navn ? `${x.fra_navn} → ${x.til_navn}` : t("tripGeneric")) : byLang(x, "navn")) },
    { label: "", class: "num", render: (x) => h("strong", {}, `${x.point > 0 ? "+" : ""}${x.point}`) },
  ], t("noHistory"));
}

async function redeem(reward) {
  if (!confirm(`${t("redeemConfirm").replace("{n}", reward.pris_point)} "${byLang(reward, "navn")}"?`)) return;
  await run(() => api(`/brugere/${state.user.bruger_id}/indloesninger`, { method: "POST", body: { beloenning_id: reward.beloenning_id } }), t("redeemedToast"));
  state.celebration = null;
  loadRewards();
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
  const line = (title, purpose) => h("li", {}, h("strong", {}, title), h("br"), h("small", { class: "muted" }, purpose));
  $("#my-data").replaceChildren(h("ul", { class: "list" },
    h("li", {}, h("strong", {}, "bruger_id: "), h("code", {}, d.bruger.bruger_id), h("br"), h("small", { class: "muted" }, d.formaal.bruger_id)),
    line(`${d.favoritter.length} favoritter`, d.formaal.favoritter),
    line(`${d.billetter.length} ${t("tickets")}`, d.formaal.billetter),
    line(`${d.point} ${t("points")}`, d.formaal.point),
    line(`${d.feedback.length} feedback`, d.formaal.feedback)));
}

$("#delete-me").addEventListener("click", async () => {
  if (!confirm(t("deleteMe") + "?")) return;
  await run(() => api(`/brugere/${state.user.bruger_id}`, { method: "DELETE" }));
  storeUserId(null);
  state.user = await api("/brugere", { method: "POST", body: { sprog: state.lang } });
  storeUserId(state.user.bruger_id);
  state.celebration = null;
  applyUser();
  refreshPoints();
  loadMyData();
});

// ---------------------------------------------------------------- Start
function reloadActive() {
  const tab = activeTab();
  if (tab === "home") ["standard", "satellite"].forEach((kind) => state.maps[kind]?.map.invalidateSize());
  ({ home: loadHome, board: loadBoard, tickets: loadTickets, live: loadLive, rewards: loadRewards, settings: loadMyData })[tab]?.();
}

async function start() {
  state.stations = await api("/stationer");
  for (const select of [$("#station-select"), ...document.querySelectorAll("[name=fra], [name=til]")]) {
    fillSelect(select, state.stations, (s) => s.navn, { valueKey: "station_id" });
  }
  $("#station-select").value = state.stationId;
  for (const form of [homeForm, $("#trip-form")]) {
    form.elements.fra.value = "LYN";
    form.elements.til.value = "GLO";
  }
  await loadUser();
  state.maps.standard = createMap("map-standard", "standard");
  state.maps.satellite = createMap("map-satellite", "satellite");
  locate();
  loadHome();
  refreshLive();
  clearInterval(state.timer);
  clearInterval(state.liveTimer);
  state.timer = setInterval(() => { if (!document.hidden) reloadActive(); }, 30000);
  state.liveTimer = setInterval(refreshLive, 5000);
}

setupTabs(() => reloadActive());
start().catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
