# 2D Auto Quote Demo Templates

`src/templates/2d_auto_quote_demo/` は、新しい 2D 図面自動見積デモを追加するときの雛形置き場です。

## 含まれるテンプレート

- `compare_script.py.tmpl`
  - `src/compare/<part_key>_2d.py` 用
- `demo_page.html.tmpl`
  - `src/viewer/demos/<part_key>_2d.html` 用
- `estimate_input.json.tmpl`
  - `src/viewer/assets/<part_key>_2d/estimate_input.json` 用
- `manifest.json.tmpl`
  - `src/viewer/assets/<part_key>_2d/manifest.json` の初期値

## 使い方

通常はテンプレートを直接編集せず、次の雛形生成スクリプトを使います。

```powershell
python src/compare/scaffold_2d_demo.py sample_part ^
  --product-name "サンプル部品" ^
  --drawing-reference "meviy_quotation_examples/pdfs/REPLACE_ME.pdf"
```

生成後にやること:

1. compare スクリプト内の PDF パスと crop 範囲を実図面に合わせる
2. `estimate_input.json` の材質、工程、表面処理、熱処理を埋める
3. `python src/compare/<part_key>_2d.py` でアセットを再生成する
4. `src/viewer/demos/<part_key>_2d.html` をブラウザで確認する
