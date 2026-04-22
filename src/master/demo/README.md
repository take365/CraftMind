# デモ用マスター

このフォルダは、見積デモ用の簡易マスターを置くためのものです。

## 方針

- 価格はデモ用の概算値です。
- 実際の加工可否条件、サイズ制限、個別査定条件はこのマスターでは無視します。
- 後で見積ロジックから引き当てやすいよう、`id` を固定しています。
- 価格体系は以下で統一しています。

## 価格体系

- 材質:
  - `demo_price_per_kg_jpy`
- 工程:
  - `demo_setup_price_jpy`
  - `demo_run_price_jpy`
  - `demo_run_unit`
- 表面処理:
  - `demo_base_price_jpy`
  - `demo_piece_price_jpy`
- 熱処理:
  - `demo_base_price_jpy`
  - `demo_piece_price_jpy`

## ファイル

- `index.json`
- `material_master.json`
- `process_master.json`
- `surface_treatment_master.json`
- `heat_treatment_master.json`

## 参考にしたページ

- 切削の材質・表面処理:
  - `https://jp-2dx.meviy.misumi-ec.com/meviy-guide/ja/customer_manual/2dx_mpb/1520/`
- 切削の加工条件詳細:
  - `https://jp-2dx.meviy.misumi-ec.com/meviy-guide/ja/customer_manual/2dx_mpb/1514/`
- 板金・シムの見積可能形状:
  - `https://jp-2dx.meviy.misumi-ec.com/meviy-guide/ja/customer_manual/2dx_shm/3617/`
- 板金・シムの材質・表面処理:
  - `https://jp-2dx.meviy.misumi-ec.com/meviy-guide/ja/customer_manual/2dx_shm/3619/`
- 塗装:
  - `https://jp-2dx.meviy.misumi-ec.com/guide/ja/customer_manual/2dx_shm/3623/`
- 板金・シムの穴加工:
  - `https://jp-2dx.meviy.misumi-ec.com/meviy-guide/ja/customer_manual/2dx_shm/11013/`
- 切削の熱処理:
  - `https://jp-2dx.meviy.misumi-ec.com/meviy-guide/ja/customer_manual/2dx_mpb/1517/`
- 旋盤:
  - `https://jp-2dx.meviy.misumi-ec.com/meviy-guide/ja/customer_manual/2dx_mlm/750/`
