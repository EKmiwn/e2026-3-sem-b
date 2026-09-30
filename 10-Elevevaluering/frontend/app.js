// Elevevaluering (Læringsrum 2.0) – præsentationslag. Henter JSON fra Flask-API'et og viser det i DOM'en.

const state = { user: null, answers: {}, classes: [], rounds: [] };

const FACES = ["😞", "🙁", "😐", "🙂", "😄"];
const CATEGORY_TEXT = { TRIVSEL: "Trivsel", LÆRING: "Læring", MØBLER: "Møbler", MILJØ: "Miljø og larm" };

function userApi(path, options = {}) {
  return api(path, { ...options, headers: { "X-User-Id": state.user.id } });
}

function distributionBar(distribution) {
  return h("div", { class: "bars", title: Object.entries(distribution).map(([k, v]) => `${k}: ${v} %`).join(" · ") },
    [1, 2, 3, 4, 5].map((k) => h("span", { class: `v${k}`, style: `width:${distribution[k] ?? 0}%` })));
}

function pct(value) {
  return value === null || value === undefined ? "–" : `${value} %`;
}

// ---------------------------------------------------------------- Login og roller
async function showLogin() {
  const users = await api("/users");
  $("#login-users").replaceChildren(...users.map((u) => h("button", {
    class: "small secondary", onclick: () => login(u.username),
  }, `${u.name}${u.class_name && u.role === "ELEV" ? ` (${u.class_name})` : ""}`)));
}

$("#login-form").addEventListener("submit", (event) => {
  event.preventDefault();
  login(event.target.elements.username.value);
});

async function login(username) {
  state.user = await run(() => api("/login", { method: "POST", body: { username } }));
  $("#login-card").hidden = true;
  $("#tabs").hidden = false;
  $("#who").replaceChildren(h("span", {}, `${state.user.name} · ${state.user.role.toLowerCase()}`),
    h("button", { class: "small secondary", onclick: logout }, "Log ud"));
  const buttons = [...document.querySelectorAll("#tabs button")];
  buttons.forEach((b) => { b.hidden = !b.dataset.roles.split(" ").includes(state.user.role); });
  if (state.user.role !== "ELEV") await loadTeacherBase();
  buttons.find((b) => !b.hidden).click();
}

function logout() {
  state.user = null;
  $("#tabs").hidden = true;
  $("#login-card").hidden = false;
  $("#who").replaceChildren();
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
}

// ---------------------------------------------------------------- Elev: spørgeskema (kort og trygt)
async function loadSurvey() {
  const s = await userApi("/my/survey");
  const box = $("#survey");
  if (!s.round) {
    box.replaceChildren(h("p", { class: "empty" }, "Der er ingen åben måling lige nu."));
    return;
  }
  if (s.answered) {
    box.replaceChildren(h("h2", {}, "Tak for dine svar! 🎉"), h("p", {}, `Du har svaret i "${s.round.name}". Se din feedback under "Min udvikling".`));
    return;
  }
  state.answers = {};
  const submit = h("button", { disabled: true }, "Send mine svar");
  const counter = h("span", { class: "muted" }, `0 af ${s.questions.length} besvaret`);
  const update = () => {
    const n = Object.keys(state.answers).length;
    counter.textContent = `${n} af ${s.questions.length} besvaret`;
    submit.disabled = n < s.questions.length;
  };
  const form = h("form", {},
    h("h2", {}, s.round.name),
    h("p", { class: "muted" }, "Der er ingen rigtige eller forkerte svar. Din lærer ser kun klassens samlede svar – aldrig dine alene."),
    ...s.questions.map((q) => h("div", { class: "question" },
      h("p", {}, `${q.emoji ?? ""} ${q.text}`),
      h("div", { class: "scale" }, FACES.map((face, i) => h("button", {
        type: "button", title: `${i + 1}`,
        onclick: (e) => {
          state.answers[q.id] = i + 1;
          e.currentTarget.parentElement.querySelectorAll("button").forEach((b) => b.classList.toggle("selected", b === e.currentTarget));
          update();
        },
      }, face))),
      h("div", { class: "scale-labels" }, h("span", {}, "Slet ikke"), h("span", {}, "Helt enig")))),
    h("label", {}, "Vil du fortælle mere? (valgfrit)", h("textarea", { name: "comment" })),
    h("div", { class: "actions", style: "align-items:center" }, submit, counter));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await run(() => userApi("/my/responses", { method: "POST", body: { answers: state.answers, comment: form.elements.comment.value } }), "Tak! Dine svar er gemt");
    loadSurvey();
    document.querySelector('#tabs button[data-tab="me"]').click();
  });
  box.replaceChildren(form);
}

// ---------------------------------------------------------------- Elev: egen udvikling og feedback
async function loadMe() {
  const d = await userApi("/my/development");
  $("#my-feedback").replaceChildren(...(d.feedback.length ? d.feedback.map((f) => h("li", {},
    h("strong", {}, f.text), f.praise ? ` ${f.praise}` : "",
    f.tip ? h("div", { class: "tip" }, `💡 ${f.tip}`) : null)) : [h("li", { class: "empty" }, "Svar på spørgeskemaet for at få feedback.")]));
  $("#my-follow-ups").replaceChildren(...(d.follow_ups.length ? d.follow_ups.map((f) => h("li", {},
    badge(CATEGORY_TEXT[f.category]), ` ${f.text}`, h("br"), h("small", { class: "muted" }, `${f.teacher} · ${formatDate(f.created_at)}`)))
    : [h("li", { class: "empty" }, "Ingen opfølgning endnu.")]));
  renderTable($("#my-history"), d.rounds, [
    { label: "Måling", key: "round_name" },
    ...Object.entries(d.categories).map(([cat, label]) => ({
      label, class: "num", render: (r) => (r.categories[cat] ? `${r.categories[cat].toFixed(1)} / 5` : "–"),
    })),
  ], "Ingen målinger endnu");
}

// ---------------------------------------------------------------- Lærer og administrator: resultater samlet
async function loadTeacherBase() {
  const [classes, rounds] = await Promise.all([api("/classes"), api("/rounds")]);
  state.classes = state.user.role === "LÆRER" ? classes.filter((c) => c.id === state.user.class_id) : classes;
  state.rounds = rounds;
  fillSelect($("#class-select"), state.classes, (c) => c.name);
  fillSelect($("#round-select"), [...rounds].reverse(), (r) => `${r.name} (${r.opens_on})`);
}

async function loadResults() {
  const classId = $("#class-select").value;
  const r = await userApi(`/classes/${classId}/results?round_id=${$("#round-select").value}`);
  $("#participation").replaceChildren(`${r.respondents} af ${r.students} elever har svaret (${r.participation_pct} %). `,
    r.hidden ? badge(`Vises først ved mindst ${r.min_respondents} svar – så ingen elev kan genkendes`, "warn") : null);
  $("#category-cards").replaceChildren(...r.categories.map((c) => h("div", { class: "kpi cat-card" },
    h("div", { class: "label" }, c.label),
    h("div", { class: "value" }, pct(c.positive_pct)),
    h("div", { class: "label" }, `positive · gns. ${c.average?.toFixed(1) ?? "–"} · ${c.negative_pct ?? "–"} % negative`),
    distributionBar(c.distribution))));
  renderTable($("#question-table"), r.questions, [
    { label: "Spørgsmål", render: (q) => `${q.emoji ?? ""} ${q.text}` },
    { label: "Kategori", render: (q) => badge(CATEGORY_TEXT[q.category]) },
    { label: "Gns.", class: "num", render: (q) => q.average.toFixed(1) },
    { label: "Positive", class: "num", render: (q) => pct(q.positive_pct) },
    { label: "Negative", class: "num", render: (q) => (q.negative_pct >= 30 ? badge(pct(q.negative_pct), "danger") : pct(q.negative_pct)) },
    { label: "Fordeling 1–5", render: (q) => distributionBar(q.distribution) },
  ], r.hidden ? "For få svar til at vise resultater" : "Ingen svar");
  $("#comments").replaceChildren(...(r.comments.length ? r.comments.map((c) => h("li", {}, `"${c}"`)) : [h("li", { class: "empty" }, "Ingen kommentarer")]));
}

$("#class-select").addEventListener("change", () => { loadResults(); loadTrend(); });
$("#round-select").addEventListener("change", loadResults);

$("#follow-up-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await run(() => userApi(`/classes/${$("#class-select").value}/follow-ups`, { method: "POST", body: formToJson(event.target) }), "Delt med klassen");
  event.target.reset();
});

// ---------------------------------------------------------------- Sammenlign over tid
async function loadTrend() {
  const t = await userApi(`/classes/${$("#class-select").value}/trend`);
  renderTable($("#trend-table"), t.trend, [
    { label: "Måling", render: (r) => `${r.round_name} (${r.opens_on})` },
    { label: "Svar", class: "num", key: "respondents" },
    ...Object.entries(t.categories).map(([cat, label]) => ({
      label, class: "num", render: (r) => (r.hidden ? h("span", { class: "muted" }, "for få svar") : pct(r.categories[cat].positive_pct)),
    })),
  ]);
  const changes = Object.entries(t.change_positive_pct);
  $("#trend-summary").textContent = changes.length
    ? `Ændring fra første til seneste måling: ${changes.map(([cat, v]) => `${t.categories[cat]} ${v > 0 ? "+" : ""}${v} procentpoint`).join(" · ")}`
    : "Der skal være mindst to målinger med nok svar for at sammenligne.";
}

// ---------------------------------------------------------------- Administrator (Læringsrum 2.0)
async function loadOverview() {
  const o = await userApi("/overview");
  renderTable($("#overview-table"), o.rows, [
    { label: "Skole", key: "school" },
    { label: "Klasse", key: "class" },
    { label: "Måling", key: "round" },
    { label: "Svar", class: "num", render: (r) => `${r.respondents}/${r.students}` },
    ...Object.entries(o.categories).map(([cat, label]) => ({
      label, class: "num", render: (r) => (r.hidden ? h("span", { class: "muted" }, "–") : pct(r[cat])),
    })),
  ]);
}

async function loadAdmin() {
  const [questions, rounds] = await Promise.all([api("/questions"), api("/rounds")]);
  renderTable($("#question-admin-table"), questions, [
    { label: "", key: "emoji" },
    { label: "Spørgsmål", key: "text" },
    { label: "Kategori", render: (q) => CATEGORY_TEXT[q.category] },
    { label: "Aktiv", render: (q) => (q.active ? "✓" : "–") },
    { label: "", render: (q) => crudButtons("questions", $("#question-form"), q, loadAdmin) },
  ]);
  renderTable($("#round-table"), rounds, [
    { label: "Navn", key: "name" },
    { label: "Periode", render: (r) => `${r.opens_on} – ${r.closes_on}` },
    { label: "", render: (r) => crudButtons("rounds", $("#round-form"), r, loadAdmin) },
  ]);
}

bindCrudForm($("#question-form"), "questions", loadAdmin);
bindCrudForm($("#round-form"), "rounds", () => { loadAdmin(); loadTeacherBase(); });

// ---------------------------------------------------------------- Start
setupTabs((tab) => {
  ({ survey: loadSurvey, me: loadMe, results: loadResults, trend: loadTrend, overview: loadOverview, admin: loadAdmin })[tab]?.();
});
showLogin().catch((err) => toast(`Kan ikke hente data fra backenden: ${err.message}`, "error"));
