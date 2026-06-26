# common — 気象庁API共通リソース

気象庁API利用プロジェクト（jma_mcp 等）から共有して参照するマスターデータ・仕様書。

---

## ファイル一覧

### area.json
気象庁の地域コードマスター。`/bosai/common/const/area.json` のローカルコピー。

| キー | 件数 | 内容 |
|-----|-----|------|
| `centers` | 11件 | 管区・地方気象台単位の広域地域（例: 北海道地方） |
| `offices` | 58件 | 府県予報区単位（例: `471000` = 沖縄本島地方）。**天気予報APIのエリアコードはここを使用** |
| `class10s` | 142件 | 一次細分区域（例: 宗谷地方） |
| `class15s` | 375件 | 二次細分区域（例: 宗谷北部） |
| `class20s` | 1796件 | 市区町村単位 |

**使い方例:**
```python
import json
with open('/Users/masahiro/projects/common/area.json') as f:
    d = json.load(f)
# 地域名でofficesを検索
for code, v in d['offices'].items():
    if 'キーワード' in v.get('name', ''):
        print(code, v['name'])
```

---

### amedastable.json
アメダス観測地点マスター。`/bosai/amedas/const/amedastable.json` のローカルコピー。1286地点。

| フィールド | 内容 |
|-----------|------|
| キー（数値文字列） | アメダス地点ID |
| `type` | 観測種別（`C`=総合, `A`=雨量のみ 等） |
| `elems` | 観測要素フラグ（8桁ビット列） |
| `lat` | 緯度（`[度, 分]`） |
| `lon` | 経度（`[度, 分]`） |
| `alt` | 標高（m） |
| `kjName` | 地点名（漢字） |
| `knName` | 地点名（カナ） |
| `enName` | 地点名（英語） |

**使い方例:**
```python
import json
with open('/Users/masahiro/projects/common/amedastable.json') as f:
    tbl = json.load(f)
# 地点名で検索
for sid, v in tbl.items():
    if '那覇' in v.get('kjName', ''):
        print(sid, v)
```

---

### stations.json
気象官署・アメダス統合地点リスト。914地点の配列。

| フィールド | 内容 |
|-----------|------|
| `obs_id` | 観測ID |
| `name` | 地点名 |
| `prefecture` | 都道府県名 |
| `intl_id` | 国際地点番号 |
| `amedas_code` | アメダスコード |

---

### okinawa_stations.json
沖縄県のアメダス観測地点リスト。`amedastable.json` から生成した沖縄県分（観測点番号 91000〜94999）の抜粋。34地点。

| フィールド | 内容 |
|-----------|------|
| `id` | アメダス地点ID（文字列） |
| `name` | 地点名（漢字） |
| `name_kana` | 地点名（カナ） |
| `lat` | 緯度（十進法） |
| `lon` | 経度（十進法） |
| `alt` | 標高（m） |
| `type` | 観測種別（`A`=気象官署, `B`=4要素, `C`=1要素） |
| `has_temp` | 気温観測あり（`true`=25地点, `false`=9地点） |

**使い方例:**
```python
import json
with open('/Users/masahiro/projects/common/okinawa_stations.json') as f:
    stations = json.load(f)

# 気温観測あり地点のIDリスト
temp_ids = [s['id'] for s in stations if s['has_temp']]

# IDから地点名を引く辞書
id_to_name = {s['id']: s['name'] for s in stations}
```

---

### jma_api_spec.md
気象庁 bosai API 仕様まとめ。Qiita記事と jma_mcp 実装・動作確認による知見を統合した仕様書。

主な内容:
- 天気予報API（短期・週間）の完全なJSON構造
- timeSeries[0][1][2] の各フィールド定義
- 気温データの最高/最低判定ロジック（発表時刻によるパターン違い）
- 警報・注意報 / 早期注意情報 / 気象情報 / アメダス / MDRR統計 など全エンドポイント
- テロップ番号（天気コード）体系
- 出典Webページ一覧

---

### AMD_Tools4.py / AMD_Tools4_ue3.py

農研機構メッシュ農業気象データ（AMD）取得ライブラリ。オリジナル配布版（OHNO, Hiroyuki 著）から独自修正を加えたものであり、**オリジナルとは異なる**。転載・商用利用禁止。

#### AMD_Tools4.py

オリジナルに対して以下の独自修正を加えたもの。

- `colorbar` 警告修正（別 Figure への追加を `ScalarMappable` で回避）

#### AMD_Tools4_ue3.py — uehara 独自拡張版（推奨）

| 版 | 経緯 |
|----|------|
| ue2 | AMD_Tools4.py 最新版（20250901）をベースに `linefig_ue` 関数を追加 |
| ue3 | 20260616 に ue2 からリネーム。Basic認証 → Oracle OAuthデバイスフロー認証に移行 |

当リポジトリのプロジェクトでは `AMD_Tools4_ue3` を使用する。  
トークンファイル: `~/.idcs_device_tokens.json`（初回実行時にデバイスフロー認証で生成）

---

## 参考: 天気予報APIのエリアコード早見表

| エリアコード | 地域名 |
|------------|-------|
| `016000` | 石狩・空知・後志地方 |
| `130000` | 東京都 |
| `270000` | 大阪府 |
| `400000` | 福岡県 |
| `471000` | 沖縄本島地方 |
| `473000` | 宮古島地方 |
| `474000` | 八重山地方 |

全コードは `area.json` の `offices` キーを参照。

---

## 朝の自動実行スケジュール

MacのlaunchdによるmacOS自動実行ジョブ一覧（2026-06-26 現在）。

### タイムライン

```
6:00  nouken      農研機構 GSR グラフ生成 → GitHub push
6:10  okiden      沖縄電力 日次CSV取得・グラフ更新 → GitHub push
6:30  ml_forecast 発電量予測（AMD気象データ + RF モデル）→ README更新 → GitHub push
```

### ジョブ一覧

| 時刻 | ジョブ名 | リポジトリ | 内容 | ログ |
|------|---------|-----------|------|------|
| **6:00** | nouken | `~/projects/nouken/` | 農研機構メッシュ農業気象データからGSR（全天日射量）・SSD（日照時間）グラフを毎日生成しGitHub push。リトライ: 6:30, 7:00 | `nouken/nouken_launchd.log` |
| **6:10** | okiden | `~/projects/okiden/` | 沖縄電力の30分値CSVをダウンロードして日次グラフ・月次レポートを自動生成・push。月次は15日以降に確定データ公開を確認してから実行 | `okiden/okiden_launchd.log` |
| **6:30** | ml_forecast | `~/projects/ml_forecast/` | AMD気象予報値（GSR・SSD・気温）を取得しRandomForestモデルで当日〜4日先の太陽光発電量を予測。README・検証グラフ自動更新 → GitHub push。noukenグラフ（6:00完了）をREADMEに取り込む | `ml_forecast/hatuden_launchd.log` |
| ~~6:20~~ | hatuden.deploy | `~/projects/ml_forecast_pages/` | ml_forecast README を Jekyll でビルドして xrea（uehr.net/ml_forecast/）にFTPデプロイ。**※ml_forecast(6:30)より前に起動するため要調整** | `ml_forecast_pages/deploy.log` |

### 設定ファイル

各ジョブの plist は `~/Library/LaunchAgents/` にロードされており、プロジェクト内にもコピーを置いている。

| ジョブ | LaunchAgents plist | プロジェクト内コピー |
|--------|--------------------|---------------------|
| nouken | `com.user.nouken.plist` | `~/projects/nouken/com.user.nouken.plist` |
| okiden | `com.user.okiden.plist` | `~/projects/okiden/com.user.okiden.plist` |
| ml_forecast | `com.user.hatuden.plist` | `~/projects/ml_forecast/com.user.hatuden.plist` |
| hatuden.deploy | `com.user.hatuden.deploy.plist` | `~/projects/ml_forecast_pages/com.user.hatuden.deploy.plist` |

詳細設定・変更手順 → [pc_docs/manuals/pc-tips/launchd.md](../pc_docs/manuals/pc-tips/launchd.md)
