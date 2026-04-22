async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`json load failed: ${path} (${response.status})`);
  }
  return response.json();
}

function yen(value) {
  return `${Number(value).toLocaleString("ja-JP")} 円`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSummary(cards) {
  const root = document.getElementById("master-summary");
  root.innerHTML = cards
    .map(
      (card) => `
        <a class="summary-link" href="#${escapeHtml(card.anchor)}">
          <article class="summary-card ${card.emphasis ? "emphasis" : ""}">
            <h3>${escapeHtml(card.title)}</h3>
            <p class="summary-value">${escapeHtml(card.value)}</p>
            <p class="summary-note">${escapeHtml(card.note)}</p>
          </article>
        </a>
      `,
    )
    .join("");
}

function renderTable(columns, rows) {
  const header = columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("");
  const body = rows
    .map(
      (row) => `
        <tr>
          ${columns
            .map((column) => `<td>${row[column.key] ?? ""}</td>`)
            .join("")}
        </tr>
      `,
    )
    .join("");

  return `
    <div class="estimate-table-wrap">
      <table class="estimate-table">
        <thead><tr>${header}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
}

function renderSections(sections) {
  const root = document.getElementById("master-sections");
  root.innerHTML = sections
    .map(
      (section) => `
        <section class="view-card" id="${escapeHtml(section.anchor)}">
          <div class="section-head">
            <div>
              <h2>${escapeHtml(section.title)}</h2>
              <p class="subline">${escapeHtml(section.subtitle)}</p>
            </div>
            <span class="chip">${escapeHtml(section.countLabel)}</span>
          </div>
          <p class="note">${escapeHtml(section.note)}</p>
          ${renderTable(section.columns, section.rows)}
        </section>
      `,
    )
    .join("");
}

async function init() {
  const base = document.body.dataset.masterBase || "./assets/demo_master";
  const [materials, processes, surfaces, heats] = await Promise.all([
    fetchJson(`${base}/material_master.json`),
    fetchJson(`${base}/process_master.json`),
    fetchJson(`${base}/surface_treatment_master.json`),
    fetchJson(`${base}/heat_treatment_master.json`),
  ]);

  renderSummary([
    {
      title: "材質マスター",
      value: `${materials.items.length} 件`,
      note: "kg 単価ベースのデモ価格",
      emphasis: true,
      anchor: "materials",
    },
    {
      title: "工程マスター",
      value: `${processes.items.length} 件`,
      note: "段取り費 + 実行単価",
      anchor: "processes",
    },
    {
      title: "表面処理マスター",
      value: `${surfaces.items.length} 件`,
      note: "基本料金 + 個数単価",
      anchor: "surfaces",
    },
    {
      title: "熱処理マスター",
      value: `${heats.items.length} 件`,
      note: "基本料金 + 個数単価",
      anchor: "heats",
    },
  ]);

  renderSections([
    {
      anchor: "materials",
      title: "材質マスター",
      subtitle: "見積時は材質コードと service family で引き当て",
      countLabel: `${materials.items.length} 件`,
      note: materials.pricing_note,
      columns: [
        { key: "code", label: "コード" },
        { key: "display_name", label: "表示名" },
        { key: "family", label: "family" },
        { key: "service_families", label: "対応分類" },
        { key: "price", label: "デモ単価" },
      ],
      rows: materials.items.map((item) => ({
        code: escapeHtml(item.code),
        display_name: escapeHtml(item.display_name),
        family: escapeHtml(item.family),
        service_families: escapeHtml((item.service_families || []).join(", ")),
        price: yen(item.demo_price_per_kg_jpy || 0),
      })),
    },
    {
      anchor: "processes",
      title: "工程マスター",
      subtitle: "段取り費と実行単価を feature / bend / part 単位で保持",
      countLabel: `${processes.items.length} 件`,
      note: processes.pricing_note,
      columns: [
        { key: "id", label: "ID" },
        { key: "display_name", label: "表示名" },
        { key: "service_family", label: "分類" },
        { key: "setup", label: "段取り費" },
        { key: "run", label: "実行単価" },
        { key: "unit", label: "単位" },
      ],
      rows: processes.items.map((item) => ({
        id: escapeHtml(item.id),
        display_name: escapeHtml(item.display_name),
        service_family: escapeHtml(item.service_family),
        setup: yen(item.demo_setup_price_jpy || 0),
        run: yen(item.demo_run_price_jpy || 0),
        unit: escapeHtml(item.demo_run_unit || ""),
      })),
    },
    {
      anchor: "surfaces",
      title: "表面処理マスター",
      subtitle: "処理カテゴリごとに基本料金と個数単価を保持",
      countLabel: `${surfaces.items.length} 件`,
      note: surfaces.pricing_note,
      columns: [
        { key: "id", label: "ID" },
        { key: "display_name", label: "表示名" },
        { key: "category", label: "カテゴリ" },
        { key: "families", label: "対応分類" },
        { key: "base", label: "基本料金" },
        { key: "piece", label: "個数単価" },
      ],
      rows: surfaces.items.map((item) => ({
        id: escapeHtml(item.id),
        display_name: escapeHtml(item.display_name),
        category: escapeHtml(item.category || ""),
        families: escapeHtml((item.service_families || []).join(", ")),
        base: yen(item.demo_base_price_jpy || 0),
        piece: yen(item.demo_piece_price_jpy || 0),
      })),
    },
    {
      anchor: "heats",
      title: "熱処理マスター",
      subtitle: "見積時は指示なしなら `なし` を引き当て",
      countLabel: `${heats.items.length} 件`,
      note: heats.pricing_note,
      columns: [
        { key: "id", label: "ID" },
        { key: "display_name", label: "表示名" },
        { key: "category", label: "カテゴリ" },
        { key: "families", label: "対応分類" },
        { key: "base", label: "基本料金" },
        { key: "piece", label: "個数単価" },
      ],
      rows: heats.items.map((item) => ({
        id: escapeHtml(item.id),
        display_name: escapeHtml(item.display_name),
        category: escapeHtml(item.category || ""),
        families: escapeHtml((item.service_families || []).join(", ")),
        base: yen(item.demo_base_price_jpy || 0),
        piece: yen(item.demo_piece_price_jpy || 0),
      })),
    },
  ]);
}

init().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML("beforeend", `<pre class="error">${escapeHtml(String(error))}</pre>`);
});
