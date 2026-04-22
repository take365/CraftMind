function yen(value) {
  return `${Math.round(value).toLocaleString("ja-JP")} 円`;
}

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

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

function resolveAssetPath(manifestPath, assetPath) {
  if (assetPath.startsWith("./assets/")) {
    return new URL(`../${assetPath.slice(2)}`, window.location.href).toString();
  }
  if (assetPath.startsWith("assets/")) {
    return new URL(`../${assetPath}`, window.location.href).toString();
  }
  return new URL(assetPath, new URL(manifestPath, window.location.href)).toString();
}

function renderViews(manifest, manifestPath) {
  const root = document.getElementById("views");
  if (!root) {
    return;
  }

  for (const view of manifest.views) {
    const cropPath = resolveAssetPath(manifestPath, view.crop_path);
    const svgPath = resolveAssetPath(manifestPath, view.svg_path);
    const inputPanelLabel = view.input_panel_label || "元図面からの切り出し";
    const featurePanelLabel = view.feature_panel_label || "簡易 2D CAD スケッチ";
    const comparisonNote = view.comparison_note || (
      Array.isArray(view.crop_box)
        ? `Crop box: ${view.crop_box.join(", ")}. CAD 側は比較確認用の簡略表現です。`
        : "比較確認用の簡略表現です。"
    );
    const card = document.createElement("section");
    card.className = "view-card";
    card.innerHTML = `
      <div class="section-head">
        <div>
          <h2>${escapeHtml(view.title)}</h2>
          <p class="subline">${escapeHtml(view.subtitle)}</p>
        </div>
        <span class="chip">${escapeHtml(view.key)}</span>
      </div>
      <div class="view-grid">
        <div class="panel">
          <h3>${escapeHtml(inputPanelLabel)}</h3>
          <img src="${escapeHtml(cropPath)}" alt="${escapeHtml(view.title)} crop" />
        </div>
        <div class="panel">
          <h3>${escapeHtml(featurePanelLabel)}</h3>
          <object data="${escapeHtml(svgPath)}" type="image/svg+xml"></object>
        </div>
      </div>
      <p class="note">${escapeHtml(comparisonNote)}</p>
    `;
    root.appendChild(card);
  }
}

function lookupById(items, id) {
  return items.find((item) => item.id === id) || null;
}

function lookupMaterial(items, selector) {
  if (!selector) {
    return null;
  }

  return (
    items.find((item) => item.id === selector || item.code === selector) ||
    null
  );
}

function makeStateLabel(mode) {
  switch (mode) {
    case "drawing_spec":
      return "図面記載";
    case "user_specified":
      return "ユーザー指定";
    case "estimated":
      return "推定";
    case "assumed":
      return "仮定";
    case "explicit":
      return "図面記載";
    case "inferred":
      return "推定";
    case "fallback_none":
      return "指示なし扱い";
    case "fallback_default":
      return "仮設定";
    default:
      return "未分類";
  }
}

function densityForFamily(family) {
  const densityMap = {
    steel: 7.85e-6,
    alloy_steel: 7.85e-6,
    sheet_steel: 7.85e-6,
    bearing_steel: 7.83e-6,
    tool_steel: 7.8e-6,
    stainless: 7.93e-6,
    aluminum: 2.7e-6,
    copper: 8.96e-6,
  };
  return densityMap[family] || densityMap.steel;
}

function collectMaterialRows(input, masters, baseMaterial, quantity) {
  const stockItems = Array.isArray(input.material_stock_items) && input.material_stock_items.length > 0
    ? input.material_stock_items
    : [
        {
          label: input.material?.code || "素材",
          ...input.stock_dimensions_mm,
          quantity: 1,
        },
      ];

  const rows = [];
  let totalVolumeMm3 = 0;
  let totalWeightKg = 0;
  let totalPrice = 0;

  for (const item of stockItems) {
    const itemMaterial = lookupMaterial(
      masters.materials.items,
      item.material?.id || item.material?.code || input.material?.id || input.material?.code,
    ) || baseMaterial;
    const length = Number(item.length || 0);
    const width = Number(item.width || 0);
    const height = Number(item.height || 0);
    const itemCount = Number(item.quantity || 1);
    const stockVolumeMm3 = length * width * height * itemCount;
    const density = densityForFamily(itemMaterial?.family);
    const stockWeightKg = round(stockVolumeMm3 * density, 3);
    const materialCost = round(stockWeightKg * (itemMaterial?.demo_price_per_kg_jpy || 0) * quantity);

    totalVolumeMm3 += stockVolumeMm3;
    totalWeightKg += stockWeightKg;
    totalPrice += materialCost;

    const basisSegments = [
      `${length} x ${width} x ${height} mm`,
      itemCount > 1 ? `${itemCount} 点` : null,
      `推定重量 ${stockWeightKg} kg`,
      item.note || null,
    ].filter(Boolean);

    rows.push({
      kind: "素材",
      name: item.label || itemMaterial?.display_name || input.material?.code || "未設定",
      basis: basisSegments.join(" / "),
      price: materialCost,
    });
  }

  return {
    rows,
    stockVolumeMm3: round(totalVolumeMm3, 3),
    stockWeightKg: round(totalWeightKg, 3),
    materialCost: round(totalPrice),
  };
}

function computeEstimate(input, masters) {
  const material = lookupMaterial(
    masters.materials.items,
    input.material?.id || input.material?.code,
  );
  const surface = lookupById(
    masters.surfaces.items,
    input.surface_treatment?.id || "surf_none",
  );
  const heat = lookupById(
    masters.heats.items,
    input.heat_treatment?.id || "heat_none",
  );

  const quantity = Number(input.quantity || 1);
  const materialSummary = collectMaterialRows(input, masters, material, quantity);

  const processRows = [];
  let processTotal = 0;
  for (const step of input.process_plan || []) {
    const master = lookupById(masters.processes.items, step.id);
    if (!master) {
      processRows.push({
        kind: "工程",
        name: `${step.id} (未登録)`,
        basis: step.note || "工程マスター未登録のため 0 円扱い",
        price: 0,
      });
      continue;
    }

    const stepCount = Number(step.count || 0);
    const runCount = stepCount * quantity;
    const price = master.demo_setup_price_jpy + master.demo_run_price_jpy * runCount;
    processTotal += price;
    processRows.push({
      kind: "工程",
      name: master.display_name,
      basis: `${stepCount} ${master.demo_run_unit} x ${quantity} 個. ${step.note || ""}`.trim(),
      price,
    });
  }

  const surfaceCost = surface
    ? surface.demo_base_price_jpy + surface.demo_piece_price_jpy * quantity
    : 0;
  const heatCost = heat
    ? heat.demo_base_price_jpy + heat.demo_piece_price_jpy * quantity
    : 0;

  const rows = [
    ...materialSummary.rows,
    ...processRows,
    {
      kind: "表面処理",
      name: surface ? surface.display_name : "未設定",
      basis: input.surface_treatment?.note || "指定なし",
      price: surfaceCost,
    },
    {
      kind: "熱処理",
      name: heat ? heat.display_name : "未設定",
      basis: input.heat_treatment?.note || "指定なし",
      price: heatCost,
    },
  ];

  const total = round(materialSummary.materialCost + processTotal + surfaceCost + heatCost);
  const stateCards = [
    {
      label: "材質",
      state: makeStateLabel(input.material?.mode),
      value: material ? material.display_name : input.material?.code || "未設定",
      note: input.material?.note || "",
    },
    {
      label: "工程",
      state: makeStateLabel(input.process_mode),
      value: input.service_family_label || input.service_family,
      note: input.process_note || "",
    },
    {
      label: "表面処理",
      state: makeStateLabel(input.surface_treatment?.mode),
      value: surface ? surface.display_name : "未設定",
      note: input.surface_treatment?.note || "",
    },
    {
      label: "熱処理",
      state: makeStateLabel(input.heat_treatment?.mode),
      value: heat ? heat.display_name : "未設定",
      note: input.heat_treatment?.note || "",
    },
  ];

  return {
    quantity,
    stockWeightKg: materialSummary.stockWeightKg,
    stockVolumeMm3: materialSummary.stockVolumeMm3,
    materialCost: materialSummary.materialCost,
    processTotal,
    surfaceCost,
    heatCost,
    total,
    rows,
    stateCards,
    assumptions: input.assumptions || [],
    warnings: input.warnings || [],
  };
}

function renderEstimate(input, estimate) {
  const summaryRoot = document.getElementById("estimate-summary");
  const detailsRoot = document.getElementById("estimate-details");
  const assumptionsRoot = document.getElementById("estimate-assumptions");

  if (summaryRoot) {
    summaryRoot.innerHTML = `
      <article class="summary-card emphasis">
        <h3>概算合計</h3>
        <p class="summary-value">${yen(estimate.total)}</p>
        <p class="summary-note">${escapeHtml(input.part_name)} / ${estimate.quantity} 個</p>
      </article>
      <article class="summary-card">
        <h3>素材費</h3>
        <p class="summary-value">${yen(estimate.materialCost)}</p>
        <p class="summary-note">推定素材重量 ${estimate.stockWeightKg} kg</p>
      </article>
      <article class="summary-card">
        <h3>工程費</h3>
        <p class="summary-value">${yen(estimate.processTotal)}</p>
        <p class="summary-note">工程 ${input.process_plan.length} 項目</p>
      </article>
      <article class="summary-card">
        <h3>処理費</h3>
        <p class="summary-value">${yen(estimate.surfaceCost + estimate.heatCost)}</p>
        <p class="summary-note">表面処理 + 熱処理</p>
      </article>
    `;
  }

  if (detailsRoot) {
    const rowsHtml = estimate.rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.kind)}</td>
            <td>${escapeHtml(row.name)}</td>
            <td>${escapeHtml(row.basis)}</td>
            <td class="price-cell">${yen(row.price)}</td>
          </tr>
        `,
      )
      .join("");

    detailsRoot.innerHTML = `
      <div class="estimate-table-wrap">
        <table class="estimate-table">
          <thead>
            <tr>
              <th>区分</th>
              <th>項目</th>
              <th>根拠</th>
              <th>金額</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
  }

  if (assumptionsRoot) {
    const states = estimate.stateCards
      .map(
        (card) => `
          <article class="state-card">
            <div class="state-row">
              <h3>${escapeHtml(card.label)}</h3>
              <span class="state-badge">${escapeHtml(card.state)}</span>
            </div>
            <p class="state-value">${escapeHtml(card.value)}</p>
            <p class="state-note">${escapeHtml(card.note)}</p>
          </article>
        `,
      )
      .join("");

    const warnings = estimate.warnings
      .map((warning) => `<li>${escapeHtml(warning)}</li>`)
      .join("");
    const assumptions = estimate.assumptions
      .map((assumption) => `<li>${escapeHtml(assumption)}</li>`)
      .join("");

    assumptionsRoot.innerHTML = `
      <div class="state-grid">${states}</div>
      <div class="assumption-grid">
        <article class="info-card warn">
          <h3>注意</h3>
          <ul>${warnings}</ul>
        </article>
        <article class="info-card">
          <h3>計算前提</h3>
          <ul>${assumptions}</ul>
        </article>
      </div>
    `;
  }
}

async function init() {
  const manifestPath = document.body.dataset.manifest || "./assets/docking_frame_004_2d/manifest.json";
  const estimatePath = document.body.dataset.estimate || "./assets/docking_frame_004_2d/estimate_input.json";
  const masterBase = document.body.dataset.masterBase || "./assets/demo_master";

  const [manifest, input, materials, processes, surfaces, heats] = await Promise.all([
    fetchJson(manifestPath),
    fetchJson(estimatePath),
    fetchJson(`${masterBase}/material_master.json`),
    fetchJson(`${masterBase}/process_master.json`),
    fetchJson(`${masterBase}/surface_treatment_master.json`),
    fetchJson(`${masterBase}/heat_treatment_master.json`),
  ]);

  renderViews(manifest, manifestPath);
  const estimate = computeEstimate(input, {
    materials,
    processes,
    surfaces,
    heats,
  });
  renderEstimate(input, estimate);
}

init().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML("beforeend", `<pre class="error">${escapeHtml(String(error))}</pre>`);
});
