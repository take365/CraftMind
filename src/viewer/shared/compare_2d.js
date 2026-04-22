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

  for (const view of manifest.views) {
    const cropPath = resolveAssetPath(manifestPath, view.crop_path);
    const svgPath = resolveAssetPath(manifestPath, view.svg_path);
    const card = document.createElement("section");
    card.className = "view-card";
    card.innerHTML = `
      <div class="section-head">
        <div>
          <h2>${view.title}</h2>
          <p class="subline">${view.subtitle}</p>
        </div>
        <span class="chip">${view.key}</span>
      </div>
      <div class="view-grid">
        <div class="panel">
          <h3>元図面からの切り出し</h3>
          <img src="${cropPath}" alt="${view.title} crop" />
        </div>
        <div class="panel">
          <h3>簡易 2D CAD スケッチ</h3>
          <object data="${svgPath}" type="image/svg+xml"></object>
        </div>
      </div>
      <p class="note">
        Crop box: ${view.crop_box.join(", ")}. CAD 側は比較確認用の簡略表現です。
      </p>
    `;
    root.appendChild(card);
  }
}

async function init() {
  const manifestPath = document.body.dataset.manifest;
  if (!manifestPath) {
    throw new Error("data-manifest が未指定です");
  }
  const response = await fetch(manifestPath);
  if (!response.ok) {
    throw new Error(`manifest load failed: ${response.status}`);
  }
  const manifest = await response.json();
  renderViews(manifest, manifestPath);
}

init().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML("beforeend", `<pre class="error">${String(error)}</pre>`);
});
