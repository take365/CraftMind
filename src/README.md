# Source Overview

現行の公開対象は、2D 図面比較とデモ用自動見積の HTML です。

## 主な構成

- `src/viewer/`
  - 正式採用の公開領域
- `src/compare/`
  - 図面比較アセットの生成スクリプト
- `src/cad/`
  - DXF / STEP など CAD 入力の簡易解析コード
- `src/master/demo/`
  - デモ用の材質 / 工程 / 表面処理 / 熱処理マスター
- `src/sample_data/`
  - 公開差し替え用の自作サンプル DXF / STEP / メモ
- `src/workflow/`
  - テンプレートとワークフロー補助文書

## 開き方

```powershell
cd src/viewer
python -m http.server 8000
```

開く URL:

```text
http://localhost:8000/
http://localhost:8000/workflow_demo.html
http://localhost:8000/master_demo.html
http://localhost:8000/demos/public_sample_plate_grid_300x200_v1_drawing_only.html
http://localhost:8000/demos/cad_input_dxf_guide_block_b.html
http://localhost:8000/demos/lb001_l_bracket_2d.html
```

## 再生成

```powershell
python src/compare/cad_input_dxf_guide_block_b.py
python src/compare/public_sample_plate_grid_300x200_v1_drawing_only_demo.py
python src/compare/lb001_l_bracket_2d.py
```

## 新規デモ雛形

```powershell
python src/compare/scaffold_2d_demo.py sample_part ^
  --product-name "サンプル部品" ^
  --drawing-reference "meviy_quotation_examples/pdfs/REPLACE_ME.pdf"
```

この雛形生成で次をまとめて作成します。

- `src/compare/<part_key>_2d.py`
- `src/viewer/demos/<part_key>_2d.html`
- `src/viewer/assets/<part_key>_2d/estimate_input.json`
- `src/viewer/assets/<part_key>_2d/manifest.json`
- `src/workflow/<part_key>_*.md`
- `src/viewer/index.html` と README の導線

## 補足

- 正式採用の入口は `src/viewer/index.html`
