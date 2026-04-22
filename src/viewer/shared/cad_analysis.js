function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`json load failed: ${path} (${response.status})`);
  }
  return response.json();
}

function renderCadAnalysis(analysis) {
  const summaryRoot = document.getElementById("cad-summary");
  const sectionsRoot = document.getElementById("cad-sections");

  if (summaryRoot) {
    summaryRoot.innerHTML = (analysis.summary_cards || [])
      .map(
        (card) => `
          <article class="summary-card">
            <h3>${escapeHtml(card.label)}</h3>
            <p class="summary-value">${escapeHtml(card.value)}</p>
            <p class="summary-note">${escapeHtml(card.note || "")}</p>
          </article>
        `,
      )
      .join("");
  }

  if (sectionsRoot) {
    sectionsRoot.innerHTML = (analysis.sections || [])
      .map(
        (section) => `
          <article class="info-card">
            <h3>${escapeHtml(section.title)}</h3>
            <ul>
              ${(section.items || [])
                .map((item) => `<li>${escapeHtml(item)}</li>`)
                .join("")}
            </ul>
          </article>
        `,
      )
      .join("");
  }
}

async function initCadAnalysis() {
  const analysisPath = document.body.dataset.analysis;
  if (!analysisPath) {
    return;
  }
  const analysis = await fetchJson(analysisPath);
  renderCadAnalysis(analysis);
}

initCadAnalysis().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML("beforeend", `<pre class="error">${escapeHtml(String(error))}</pre>`);
});
