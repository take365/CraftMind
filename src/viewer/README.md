# Viewer Structure

`src/viewer/` は正式採用の 2D 比較 / 自動見積デモ用の公開領域です。

## 構成

- `index.html`
  - 正式採用デモの入口
- `demos/`
  - 個別案件の HTML
- `shared/`
  - 共通 CSS / JS
- `assets/`
  - 各案件の画像、SVG、manifest、見積入力、ブラウザ読込用マスター

## 配信方法

```powershell
cd src/viewer
python -m http.server 8000
```

## URL

- `http://localhost:8000/`
- `http://localhost:8000/workflow_demo.html`
- `http://localhost:8000/master_demo.html`
- `http://localhost:8000/demos/public_sample_plate_grid_300x200_v1_drawing_only.html`
- `http://localhost:8000/demos/cad_input_dxf_guide_block_b.html`
- `http://localhost:8000/demos/lb001_l_bracket_2d.html`

## 新規デモ雛形

新しいデモを作るときは、次の雛形生成スクリプトを先に使います。

```powershell
python src/compare/scaffold_2d_demo.py sample_part ^
  --product-name "サンプル部品" ^
  --drawing-reference "meviy_quotation_examples/pdfs/REPLACE_ME.pdf"
```
