// &LIVING Buyer Matchmaking – presentation layer. Fetches JSON from the Flask API and shows it in the DOM.

const state = { userId: null, group: null };

const TYPE_TEXT = { APARTMENT: "Apartment", TOWNHOUSE: "Townhouse", HOUSE: "House" };
const VIEWING_BADGE = { REQUESTED: "warn", CONFIRMED: "ok", DECLINED: "danger" };

// All calls send the signed-in buyer (simulated login)
function userApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-User-Id": state.userId } });
}

function dkk(value) {
  return `${Number(value).toLocaleString("da-DK")} DKK`;
}

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value ?? "–"), h("div", { class: "label" }, label));
}

function bar(value, label) {
  return h("div", {}, h("small", { class: "muted" }, `${label} ${value}`),
    h("div", { class: "bar" }, h("span", { style: `width:${value}%` })));
}

function goTo(tab) {
  document.querySelector(`.tabs button[data-tab="${tab}"]`).click();
}

// ---------------------------------------------------------------- Load
async function loadBase() {
  const buyers = await api("/buyers");
  const previous = state.userId;
  fillSelect($("#user-select"), buyers, (b) => `${b.name}${b.consent_at ? "" : " (no consent)"}`);
  if (previous) $("#user-select").value = previous;
  state.userId = Number($("#user-select").value);
}

// ---------------------------------------------------------------- Profile and consent
async function loadProfile() {
  const buyer = await api(`/buyers/${state.userId}`);
  const form = $("#profile-form");
  for (const field of form.elements) {
    if (field.name && field.name in buyer) field.value = buyer[field.name] ?? "";
  }
  $("#consent-box").replaceChildren(buyer.consent_at
    ? h("div", {}, h("p", {}, badge("Consent given", "ok"), ` ${formatDate(buyer.consent_at)}`),
      h("button", { class: "secondary", onclick: () => setConsent(false) }, "Withdraw consent"))
    : h("div", {}, h("p", {}, badge("No consent", "warn"), " You cannot be matched yet."),
      h("button", { onclick: () => setConsent(true) }, "I consent to matching")));
}

async function setConsent(consent) {
  await run(() => api(`/buyers/${state.userId}/consent`, { method: "POST", body: { consent } }),
    consent ? "Consent given" : "Consent withdrawn");
  reloadEverything();
}

bindCrudForm($("#profile-form"), "buyers", reloadEverything);

// ---------------------------------------------------------------- Matches
async function loadMatches() {
  try {
    const result = await userApi("/matches");
    $("#match-info").textContent = `Buyers with a match score of at least ${result.min_score}. Score = financial compatibility and lifestyle.`;
    $("#match-list").replaceChildren(...(result.matches.length ? result.matches.map((m) => h("div", { class: "card" },
      h("div", { class: "toolbar" },
        h("div", { style: "flex:1" }, h("h3", { style: "margin:0" }, `${m.buyer.name}, ${m.buyer.age}`),
          h("span", { class: "muted" }, `${m.buyer.preferred_location} · ${TYPE_TEXT[m.buyer.property_type]} · ${m.buyer.budget_band}`)),
        h("div", { class: "score" }, m.score)),
      bar(m.financial, "Financial"),
      bar(m.lifestyle, "Lifestyle"),
      h("ul", { class: "list" }, m.reasons.map((r) => h("li", {}, `✓ ${r}`))),
      h("p", { class: "muted" }, `Combined purchasing power: ${dkk(m.combined_power)}`),
      m.in_group ? badge("Already in a group", "muted")
        : h("button", { onclick: () => connect(m.buyer) }, state.group ? "Invite to our group" : "Connect")))
      : [h("p", { class: "empty" }, "No matches yet.")]));
  } catch (err) {
    $("#match-info").textContent = "";
    $("#match-list").replaceChildren(h("div", { class: "card" }, h("p", { class: "empty" }, err.message)));
  }
}

async function connect(buyer) {
  await run(() => userApi("/groups", { method: "POST", body: { buyer_id: buyer.id } }), `${buyer.name} is now in your group`);
  await loadAll();
  goTo("group");
}

// ---------------------------------------------------------------- Group: members, purchasing power, messages
async function loadGroup() {
  state.group = await userApi("/my-group");
  const g = state.group;
  if (!g) {
    $("#group-view").replaceChildren(h("div", { class: "card" }, h("p", { class: "empty" }, "You are not in a group yet. Connect with a match to start one.")));
    return;
  }
  const form = h("form", { class: "toolbar" },
    h("input", { name: "text", placeholder: "Write a message…", required: true, style: "flex:1" }), h("button", {}, "Send"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await run(() => userApi(`/groups/${g.id}/messages`, { method: "POST", body: formToJson(form) }));
    loadGroup();
  });
  $("#group-view").replaceChildren(h("div", { class: "grid wide" },
    h("div", { class: "card" },
      h("h2", {}, g.name),
      h("div", { class: "power" }, dkk(g.purchasing_power)),
      h("p", { class: "muted" }, `Combined purchasing power (loans + down payments) · ${g.members.length} of max. ${g.max_group_size} buyers`),
      renderMembers(g.members),
      h("p", {}, `Needs at least ${g.required_area} m² · max. ${g.max_transport_min} min transport · ${g.locations.join(", ")}`),
      h("div", { class: "actions" },
        h("button", { onclick: () => goTo("homes") }, "See matching homes"),
        h("button", { class: "danger", onclick: leaveGroup }, "Leave group"))),
    h("div", { class: "card" },
      h("h2", {}, "Messages"),
      h("p", { class: "muted" }, "Talk safely before you share personal contact details."),
      h("div", { class: "chat" }, g.messages.map((m) => h("div", { class: `bubble ${m.sender_id === g.me ? "mine" : ""}` },
        h("small", { class: "muted" }, `${m.sender} · ${formatDate(m.created_at)}`), h("br"), m.text))),
      form)));
  const chat = $("#group-view .chat");
  chat.scrollTop = chat.scrollHeight;
}

function renderMembers(membersList) {
  const box = h("div");
  renderTable(box, membersList, [
    { label: "Buyer", render: (m) => `${m.name}, ${m.age}` },
    { label: "Budget", key: "budget_band" },
    { label: "Wants", render: (m) => `${TYPE_TEXT[m.property_type]}, ${m.min_area} m², ${m.preferred_location}` },
    { label: "Contact", render: (m) => (m.email ? `${m.email} ${m.phone ?? ""}` : h("span", { class: "muted" }, "Not shared")) },
  ]);
  return box;
}

async function leaveGroup() {
  if (!confirm("Leave the group? The others keep the shortlist.")) return;
  await run(() => userApi(`/groups/${state.group.id}/leave`, { method: "POST" }), "You left the group");
  loadAll();
}

// ---------------------------------------------------------------- Homes for the group
async function loadHomes() {
  if (!state.group) {
    $("#power-kpis").replaceChildren();
    $("#home-list").replaceChildren(h("div", { class: "card" }, h("p", { class: "empty" }, "Form a group to search homes together.")));
    return;
  }
  const { power, properties } = await userApi(`/groups/${state.group.id}/properties`);
  $("#power-kpis").replaceChildren(
    kpi(dkk(power.purchasing_power), "purchasing power"),
    kpi(`${power.required_area} m²`, "minimum area"),
    kpi(`${power.max_transport_min} min`, "max. transport"),
    kpi(properties.length, "matching homes"),
  );
  $("#home-list").replaceChildren(properties.length ? h("div", { class: "grid" }, properties.map((p) => h("div", { class: "card" },
    h("div", { class: "actions" }, badge(`Fit ${p.fit}`, p.fit >= 80 ? "ok" : "warn"),
      p.off_market ? badge("Off-market – only via &LIVING") : null),
    h("h3", {}, p.address),
    h("p", {}, `${p.location} · ${TYPE_TEXT[p.property_type]} · ${p.area} m² · ${p.rooms} rooms`),
    h("p", {}, h("strong", {}, dkk(p.price)), h("span", { class: "muted" }, ` · ${dkk(p.price_per_member)} per buyer · ${dkk(p.monthly_cost)}/month`)),
    h("ul", { class: "list" }, p.reasons.map((r) => h("li", {}, `✓ ${r}`))),
    p.shortlisted ? badge("On shortlist", "ok")
      : h("button", { onclick: () => addToShortlist(p.id) }, "Save to shortlist"))))
    : h("div", { class: "card" }, h("p", { class: "empty" }, "No homes match the group's purchasing power and space needs.")));
}

async function addToShortlist(propertyId) {
  await run(() => userApi(`/groups/${state.group.id}/shortlist`, { method: "POST", body: { property_id: propertyId } }), "Saved to shortlist");
  await loadGroup();
  loadHomes();
  loadShortlist();
}

// ---------------------------------------------------------------- Shortlist: vote, discuss and request viewing
function loadShortlist() {
  const g = state.group;
  if (!g) {
    $("#shortlist").replaceChildren(h("div", { class: "card" }, h("p", { class: "empty" }, "Form a group to use a shared shortlist.")));
    $("#viewing-table").replaceChildren();
    return;
  }
  $("#shortlist").replaceChildren(g.shortlist.length ? h("div", { class: "grid wide" }, g.shortlist.map(shortlistCard))
    : h("div", { class: "card" }, h("p", { class: "empty" }, "The shortlist is empty. Save homes from the Homes tab.")));
  renderTable($("#viewing-table"), g.viewings, [
    { label: "Home", key: "address" },
    { label: "Type", render: (v) => (v.type === "PRIVATE" ? "Private viewing" : "Open house") },
    { label: "Date", key: "preferred_date" },
    { label: "Requested by", key: "requested_by_name" },
    { label: "Status", render: (v) => badge(v.status, VIEWING_BADGE[v.status]) },
    { label: "Agent", key: "agent_note" },
  ], "No viewing requests yet");
}

function shortlistCard(item) {
  const mine = item.votes.find((v) => v.buyer_id === state.group.me);
  const voteForm = h("form", {},
    h("label", {}, "Comment", h("input", { name: "comment", value: mine?.comment ?? "" })),
    h("div", { class: "actions" },
      h("button", { type: "button", onclick: () => castVote(item.id, 1, voteForm) }, "👍 Yes"),
      h("button", { type: "button", class: "secondary", onclick: () => castVote(item.id, -1, voteForm) }, "👎 No")));
  const viewingForm = h("form", { class: "row" },
    h("label", {}, "Viewing", h("select", { name: "type" }, h("option", { value: "OPEN_HOUSE" }, "Open house"), h("option", { value: "PRIVATE" }, "Private viewing"))),
    h("label", {}, "Preferred date", h("input", { type: "date", name: "preferred_date", required: true })),
    h("button", {}, "Request viewing"));
  viewingForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await run(() => userApi(`/groups/${state.group.id}/viewings`, {
      method: "POST", body: { ...formToJson(viewingForm), property_id: item.property_id },
    }), "Viewing requested – the agent will confirm");
    await loadGroup();
    loadShortlist();
    loadAgent();
  });
  return h("div", { class: "card" },
    h("div", { class: "toolbar" }, h("h3", { style: "margin:0;flex:1" }, item.address), h("div", { class: "score" }, item.score > 0 ? `+${item.score}` : item.score)),
    h("p", { class: "muted" }, `${item.location} · ${item.area} m² · ${dkk(item.price)} · saved by ${item.added_by_name}`),
    h("ul", { class: "list" }, item.votes.map((v) => h("li", {}, `${v.value > 0 ? "👍" : "👎"} ${v.name}`, v.comment ? `: ${v.comment}` : ""))),
    voteForm, h("hr"), viewingForm);
}

async function castVote(itemId, value, form) {
  state.group = await run(() => userApi(`/shortlist/${itemId}/vote`, { method: "POST", body: { value, ...formToJson(form) } }), "Vote saved");
  loadShortlist();
}

// ---------------------------------------------------------------- Agent
async function loadAgent() {
  const [a, properties] = await Promise.all([api("/agent/groups"), api("/properties")]);
  renderTable($("#agent-groups"), a.groups, [
    { label: "Group", key: "name" },
    { label: "Members", render: (g) => g.members.join(", ") },
    { label: "Purchasing power", class: "num", render: (g) => dkk(g.purchasing_power) },
    { label: "Needs", render: (g) => `${g.required_area} m² · ${g.locations.join(", ")}` },
    { label: "Shortlist", class: "num", key: "shortlist" },
  ], "No qualified groups yet");
  renderTable($("#agent-viewings"), a.viewings, [
    { label: "Group", key: "group_name" },
    { label: "Home", key: "address" },
    { label: "Type", render: (v) => (v.type === "PRIVATE" ? "Private" : "Open house") },
    { label: "Date", key: "preferred_date" },
    { label: "Status", render: (v) => badge(v.status, VIEWING_BADGE[v.status]) },
    {
      label: "",
      render: (v) => (v.status === "REQUESTED" ? h("div", { class: "actions" },
        h("button", { class: "small", onclick: () => answerViewing(v.id, "CONFIRMED") }, "Confirm"),
        h("button", { class: "small danger", onclick: () => answerViewing(v.id, "DECLINED") }, "Decline")) : v.agent_note),
    },
  ], "No viewing requests");
  renderTable($("#property-table"), properties, [
    { label: "Address", key: "address" },
    { label: "Location", key: "location" },
    { label: "Price", class: "num", render: (p) => dkk(p.price) },
    { label: "m²", class: "num", key: "area" },
    { label: "", render: (p) => (p.off_market ? badge("Off-market") : "") },
    { label: "", render: (p) => crudButtons("properties", $("#property-form"), p, reloadEverything) },
  ]);
}

async function answerViewing(id, status) {
  const agentNote = status === "CONFIRMED" ? prompt("Note to the buyers", "See you at the viewing!") : prompt("Reason", "");
  await run(() => api(`/viewings/${id}`, { method: "PUT", body: { status, agent_note: agentNote } }), `Viewing ${status.toLowerCase()}`);
  loadAgent();
  await loadGroup();
  loadShortlist();
}

bindCrudForm($("#property-form"), "properties", reloadEverything);

// ---------------------------------------------------------------- Start
function reloadEverything() {
  return loadBase().then(loadAll);
}

async function loadAll() {
  await Promise.all([loadProfile(), loadGroup(), loadAgent()]);
  await Promise.all([loadMatches(), loadHomes()]);
  loadShortlist();
}

$("#user-select").addEventListener("change", (event) => {
  state.userId = Number(event.target.value);
  loadAll();
});

setupTabs((tab) => {
  if (tab === "matches") loadMatches();
  if (tab === "homes") loadHomes();
});
loadBase()
  .then(loadAll)
  .catch((err) => toast(`Cannot fetch data from the backend: ${err.message}`, "error"));
