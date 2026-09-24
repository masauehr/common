# 気象庁 bosai API 仕様まとめ

参考資料:
- https://qiita.com/KAI_Mutsumi/items/2a005b084d95e417ac44
- https://qiita.com/e_toyoda/items/7a293313a725c4d306c0
- jma_mcp/server.py の実装・動作確認による知見

---

> ⚠️ **2026-05-28 の防災気象情報の新体系（警戒レベル中心）への移行で、警報・早期注意情報・気象情報・台風情報の配信先と形式が変わった**（第4・5・6・8章を更新済み）。
> 旧パスは削除されず **5/28（台風は 5/27）のまま更新されない**ため、旧パスのままだと古い内容が返り続ける（エラーにならず気づきにくい）。`r8` は令和8年版で、将来（r9 等）変わりうる。
> 変更されていないもの（2026-09-24 に鮮度を全数確認）: 予報（第2章）・概況（第3章）・気象台コメント（第7章）・地震（第9章）・津波（第10章）・潮位・地域コード `area.json`・`data.jma.go.jp` 系。
> 条件付き取得: すべての配信先が `If-None-Match` / `If-Modified-Since` に対応（変更なしなら 304・本文 0 バイト）。定時取得は負荷が大きいので、必要なときだけ取得し、条件付き取得を使うこと。

---

## 1. 共通事項

### ベースURL
```
https://www.jma.go.jp/bosai/
https://www.data.jma.go.jp/
```

### 共通定数エンドポイント
| URL | 内容 |
|-----|------|
| `/bosai/common/const/area.json` | 地域コード一覧（offices / centers / class10s / class15s / class20s） |
| `/bosai/forecast/const/forecast_area.json` | 予報エリアと地域コードの対応 |
| `/bosai/amedas/const/amedastable.json` | アメダス観測地点マスター |

### エリアコード（offices）
- 3桁（例: `130000` = 東京都、`471000` = 沖縄本島地方）
- `area.json` の `offices` キーで検索可能

---

## 2. 天気予報 API

### エンドポイント
```
GET https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json
```

### レスポンス構造（配列2要素）

```
[
  data[0],  # 短期予報（今日〜明後日）
  data[1]   # 週間予報（今日〜7日後）
]
```

---

### 2-1. 短期予報 data[0]

#### トップレベル
| フィールド | 内容 |
|-----------|------|
| `publishingOffice` | 発表官署名（例: `沖縄気象台`） |
| `reportDatetime` | 発表時刻（ISO 8601） |
| `timeSeries` | 予報データ配列（3要素） |

#### timeSeries[0] — 天気（日単位）

`timeDefines`: 発表タイミングにより2〜3件
- 5〜10時発表: 今日・明日の2件（明後日なし）
- 11〜16時発表: 今日・明日・明後日の3件
- 17時以降発表: 明日・明後日の2件

`areas[i]` のフィールド:
| フィールド | 内容 | 備考 |
|-----------|------|------|
| `area.name` | 地域名 | |
| `area.code` | 地域コード | |
| `weatherCodes` | テロップ番号（3桁文字列） | 天気アイコン・テキスト変換に使用 |
| `weathers` | 予報文（全角スペース区切り） | |
| `winds` | 風の予報文 | |
| `waves` | 波の予報文 | **沿岸地域のみ存在** |

#### timeSeries[1] — 降水確率（6時間単位）

`timeDefines`: 6時間刻み（06:00 / 12:00 / 18:00 / 00:00）
- 発表時刻によって最初の時間帯は省略される場合あり

`areas[i]` のフィールド:
| フィールド | 内容 |
|-----------|------|
| `pops` | 降水確率（%、文字列）の配列 |

#### timeSeries[2] — 気温（地点単位）

**timeSeries[0][1] が「地域」単位なのに対し、timeSeries[2] は「地点」単位**

`areas[i]` のフィールド:
| フィールド | 内容 |
|-----------|------|
| `area.name` | 地点名（例: `那覇`） |
| `temps` | 気温値（℃、文字列）の配列 |

##### timeDefines と temps の対応（重要）

**日中発表（5〜16時）の場合 — 4要素:**
```
[
  "今日 09:00",  → 今日・日中の最高気温（暫定）
  "今日 00:00",  → 今日・全日の最高気温（確定値）  ← 00:00 だが最高気温！
  "明日 00:00",  → 明日朝の最低気温
  "明日 09:00"   → 明日・日中の最高気温
]
```

**夜間発表（17〜23時）の場合 — 2要素:**
```
[
  "明日 00:00",  → 明日朝の最低気温
  "明日 09:00"   → 明日・日中の最高気温
]
```

**判定ロジック（jma_mcp実装）:**
- 日付ごとの最初のエントリ時刻を確認
- 最初が `hour >= 6`（09:00） → その日の全エントリを**最高気温**扱い（最低気温なし）
- 最初が `hour < 6`（00:00） → `00:00=最低気温`、`09:00=最高気温`

---

### 2-2. 週間予報 data[1]

#### トップレベル
| フィールド | 内容 |
|-----------|------|
| `publishingOffice` | 発表官署名 |
| `reportDatetime` | 発表時刻 |
| `timeSeries` | 2要素 |

#### timeSeries[0] — 天気・降水確率・信頼度

`timeDefines`: 今日〜7日後（日単位、00:00）

`areas[i]` のフィールド:
| フィールド | 内容 | 備考 |
|-----------|------|------|
| `weatherCodes` | テロップ番号 | |
| `pops` | 降水確率（%） | 今日分は空文字の場合あり |
| `reliabilities` | 信頼度 A/B/C | 今日・明日は空文字。A=高・B=中・C=低 |

信頼度の意味: 予報に雨の表現が付くか付かないかが今後変わる可能性の度合い

#### timeSeries[1] — 気温（幅付き予報）

`areas[i]` のフィールド:
| フィールド | 内容 |
|-----------|------|
| `tempsMin` | 最低気温（予報値） |
| `tempsMinUpper` | 最低気温（上限） |
| `tempsMinLower` | 最低気温（下限） |
| `tempsMax` | 最高気温（予報値） |
| `tempsMaxUpper` | 最高気温（上限） |
| `tempsMaxLower` | 最高気温（下限） |

今日分は空文字の場合あり。

#### 平年値フィールド（data[1] トップレベル）
| フィールド | 内容 |
|-----------|------|
| `tempAverage.areas[i].min` | 最低気温の平年値（4日後） |
| `tempAverage.areas[i].max` | 最高気温の平年値（4日後） |
| `precipAverage.areas[i].min/max` | 降水量平年値の下限/上限（7日間合計） |

---

### 2-3. 発表時刻に関する注意

| 発表時刻 | 内容 |
|---------|------|
| 5時（〜10時） | 通常発表。明後日の予報なし |
| 11時 | 通常発表。3日分あり |
| 17時 | 通常発表。当日分なし |
| 23時台後半〜翌4時台前半 | 前回予報の訂正扱い |

帯広測候所（`014030`）・名瀬測候所（`460040`）は予報発表なし。

---

## 3. 天気概況 API

```
GET https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area_code}.json
```

| フィールド | 内容 |
|-----------|------|
| `publishingOffice` | 発表官署名 |
| `reportDatetime` | 発表時刻 |
| `targetArea` | 対象地域名 |
| `headlineText` | 見出し文 |
| `text` | 本文（概況テキスト） |

---

## 4. 警報・注意報 API（新体系: 2026-05-28〜）

```
GET https://www.jma.go.jp/bosai/warning/data/r8/{area_code}.json     # 警報・注意報（府県予報区）
GET https://www.jma.go.jp/bosai/warning/data/r8/map_time.json         # 警報システム全体の最終更新（動作中かの判定）
（旧: warning/data/warning/{area_code}.json ← 2026-05-28 のまま凍結。使わない）
```

**報のリスト形式**（旧は辞書）。データ種別（`dataTypeCode`）ごとの報で、**種別ごとに最新の報だけ**が現状（継続中の警報は古い報のまま残る）。

| dataTypeCode | 種別 |
|---|---|
| VPWW55 | 大雨 |
| VPWW56 | 土砂災害 |
| VPWW57 | 高潮 |
| VPWW58 | 暴風 |
| VPWW59 | 波浪 |
| VPWW60 | （大雪等。実データでは未確認） |
| VPWW61 | その他の注意報（雷・濃霧・乾燥・霜） |

各報のキー: `reportDatetime`・`infoType`・`publishingOffice`・`headlineText`・`notice`（特記事項。例: 千葉豪雨による暫定基準の運用）・`warning.class10Items[]` / `warning.class20Items[]`（`areaCode` と `kinds[]`）。
`kinds[]` は `{code, status}`。`status` は 発表／継続／解除、または `{status: "発表警報・注意報はなし"}`（`code` なし）。**`code` は "03" のような2桁文字列**（int に正規化して照合する）。

**警報コード（新体系のレベル付き名称）**:
| 種類 | レベル2 注意報 | レベル3 警報 | レベル4 危険警報 | レベル5 特別警報 |
|---|---|---|---|---|
| 大雨 | 10 | 3 | 43 | 33 |
| 土砂災害 | 29 | 9 | 49 | 39 |
| 高潮 | 19 | 8 | 48 | 38 |

その他: 洪水 18（注意報）・4（警報）、暴風 5、波浪 7・16、大雪 6・12、雷 14、強風 15、濃霧 20、乾燥 21、霜 24 など（従来どおり）。

**鮮度の判定**: 報ごとの経過時間ではなく、`map_time.json` の `latestControlDatetime` が取得の数時間以内かで判定する（継続中の警報は古い報のままなので）。

### 4-2. 時系列情報（警報等の見通し）※新規

```
GET https://www.jma.go.jp/bosai/warning_timeline/data/{area_code}.json     # 版の番号なし
```

警報・注意報に先立つ**予測情報**。**3時間ごとの明日までの見通し**を市町村単位で提供する。5時・11時・17時・23時に発表（更新）され、必要に応じて随時更新される。**時間が過ぎた区分の値は消える**。
`timeSeries[0]`（`duration: PT3H`×12区分）の `class20Items[].kinds[].significancyParts[]`（`type`: 大雨浸水危険度・土砂災害危険度・高潮危険度・風危険度・雷危険度・波危険度 など、`locals[].codes[]`: 区分ごとのコード）。
**コードの十の位が危険度レベル**（1=なし 2=注意 3=警戒 4=危険 5=災害切迫。例: `21` = 注意）。`forecastParts` は 1時間最大雨量・風向・最大風速・波高・潮位 などの予測値。
実際の警報・注意報の発表状況と整合しない場合がある（予測情報のため）。

---

## 5. 早期注意情報（警報級の可能性）API（新体系: 2026-05-28〜）

```
GET https://www.jma.go.jp/bosai/probability/data/probability/r8/{area_code}.json
（旧: probability/data/probability/{area_code}.json ← 2026-05-28 のまま凍結。使わない）
```

`data[0]` = 短期（**6時間ごと・明後日まで**。8区分。`timeDefineArray` の `duration: PT6H`）、`data[1]` = 週間（日ごと・4区分）。各地域に解説文 `text` を追加。
現象種別: 短期は**大雨・土砂災害**（旧「雨」を分離）・雪・風（風雪）・波・潮位、週間は雨・雪・風（風雪）・波・潮位。値: `"高"` / `"中"` / `"なし"`（雪）/ `""`（なし・低い）。
全国のまとめ: `probability/data/probability/r8/map.json`（約130KB）。

---

## 6. 気象情報 API（新体系: 2026-05-28〜）

```
GET https://www.jma.go.jp/bosai/information/data/r8/information.json           # 一覧（約1か月分・約270件）
GET https://www.jma.go.jp/bosai/information/data/r8/denbun/{json_name}.json    # 個別電文（JSON）
（旧: information/data/information.json・information/data/denbun/ ← 2026-05-28 のまま凍結。使わない）
```

一覧JSONの各要素:
| フィールド | 内容 |
|-----------|------|
| `controlTitle` | 情報種別（府県気象解説情報・地方気象解説情報・全般気象解説情報・府県気象防災速報・竜巻注意情報（目撃情報付き）・地方天候情報 など）。**PDF資料の項目には無い** |
| `headTitle` | タイトル（例: 千葉県気象解説情報（大雨）） |
| `reportDatetime` | 発表時刻 |
| `publishingOffice` | 発表官署 |
| `areaType` / `areaCode` / `areaCodes` | 対象（offices=府県予報区、centers=地方、japan=全国）とエリアコード |
| `jsonName` | 電文取得用キー（`dataType` が `pdf` のものは無い） |

個別電文（JSON）: `headlineText`（概要）・`commentText`（本文。**`<br>` を含む**）など。**約1か月分の履歴が取れる**ため、過去の出来事の公式な裏付けに使える。

---

## 7. 気象台コメント API

```
GET https://www.jma.go.jp/bosai/forecaster_comment/data/comments/{area_code}.txt
```

テキスト形式で警報等の見込み・特記事項を返す。
気象庁Webサイト上に専用の公開ページは存在しない（2026年4月確認）。

---

## 8. 台風情報 API（新体系: 2026-05-28〜）

```
GET https://www.jma.go.jp/bosai/typhoon/data/targetTc.json                     # 発生中の台風の一覧
GET https://www.jma.go.jp/bosai/typhoon/data/{TC番号}/specifications.json      # 諸元（実況・予報）
GET https://www.jma.go.jp/bosai/typhoon/data/{TC番号}/forecast.json            # 予報円・暴風警戒域
（旧: information/data/typhoon.json・information/data/typhoon/{name} ← 2026-05-27 のまま凍結。使わない）
```

- `targetTc.json`: `[{"tropicalCyclone": "TC2632", "typhoonNumber": "2626", "category": "TS", "issue": "..."}]`（空配列 = 発生中の台風なし）。`typhoonNumber` の下2桁が台風番号（26号）。
- `specifications.json`: `part` が `"title"`（発表時刻・台風番号・名前）と、実況（`advancedHours: 0`）・予報（12/24/45/69/93/117時間後）。各パートに `position.deg`（[緯度, 経度]）・`pressure`・`maximumWind`（sustained/gust の m/s）・`course`・`speed`・`galeWarning`/`stormWarning`（強風域・暴風域の方位別半径 km）・`probabilityCircleRadius`（予報円の半径 km）・`intensity`（強い 等）。
- `forecast.json`: 実況の進路 `track`（`typhoon`/`preTyphoon`）と、予報の `probabilityCircle`（半径 m と接線）・`stormWarningArea`（円弧）・`validtime`。
- 台風に関する気象解説情報（例: 「千葉県気象解説情報（台風第２５号）」）は第6章の気象情報に含まれる。

---

## 9. 地震情報 API

```
GET https://www.jma.go.jp/bosai/quake/data/list.json
```

`list.json` の各要素に震源・規模・最大震度などが含まれる。

---

## 10. 津波情報 API

```
GET https://www.jma.go.jp/bosai/tsunami/data/list.json
```

---

## 11. アメダス API

```
GET https://www.jma.go.jp/bosai/amedas/data/latest_time.txt          # 最新データ時刻
GET https://www.jma.go.jp/bosai/amedas/data/map/{yyyymmddHHmmss}.json # 全国マップ用
GET https://www.jma.go.jp/bosai/amedas/data/point/{stnid}/{yyyymmdd}_{h3}.json  # 地点系
```

全国マップ用JSONは地点IDをキーとしたオブジェクト。各観測値は `[数値, AQCフラグ]` の配列形式。AQCフラグが 0 のものが正常値。

観測項目例: `temp`（気温）、`humidity`（湿度）、`precipitation10m`（10分降水量）、`wind`（風速）、`windDirection`（風向）

地点マスターは `amedastable.json` を参照。

---

## 12. 統計・ランキング API (MDRR)

```
ベースURL: https://www.data.jma.go.jp/stats/data/mdrr/
```

### 日別ランキング
```
GET .../rank_daily/data{mmdd}.html  # 例: data0423.html
```
全国の観測値を要素別に高い順（または低い順）でランキング表示（HTML）。

### 観測史上1位更新状況
```
GET .../rank_update/d{mmdd}.html  # 例: d0423.html
```
その日に観測史上1位または月の1位を更新した地点一覧（HTML）。

### 最新観測値CSV
```
GET .../pre_rct/alltable/pre1h00_rct.csv      # 1時間降水量
GET .../pre_rct/alltable/pre24h00_rct.csv     # 24時間降水量
GET .../tem_rct/alltable/mxtemsadext00_rct.csv # 最高気温
GET .../tem_rct/alltable/mntemsadext00_rct.csv # 最低気温
GET .../wind_rct/alltable/mxwsp00_rct.csv     # 最大風速
GET .../snc_rct/alltable/snc00_rct.csv        # 現在積雪深
```
CSV形式。都道府県・地点名・観測値・統計情報が含まれる。

---

## 13. 長期予報 API

### 2週間気温予報
```
GET https://www.data.jma.go.jp/risk/probability/guidance/download2w.php?2week_t_{num}.csv
```

### 1ヶ月予報
```
GET https://www.data.jma.go.jp/risk/probability/guidance/download.php?month1_t_{num}.csv
```

### 3ヶ月・6ヶ月予報解説
```
https://www.data.jma.go.jp/cpd/longfcst/kaisetsu/?term=P3M  # 3ヶ月
https://www.data.jma.go.jp/cpd/longfcst/kaisetsu/?term=P6M  # 6ヶ月
```
※ JavaScript SPA のため静的スクレイピング不可

### 早期天候情報
```
GET https://www.data.jma.go.jp/cpd/souten/data/{reg_no}.json  # 地域別データ
GET https://www.data.jma.go.jp/cpd/souten/data/flg.json       # 発表有無フラグ
```

---

## 14. エルニーニョ監視速報

```
https://www.data.jma.go.jp/cpd/elnino/
```
※ JavaScript SPA のため静的スクレイピング不可。HTML本文を解析して取得。

---

## 15. テロップ番号（天気コード）

3桁の数字で天気を表現。百の位が大分類。

| 範囲 | 大分類 |
|-----|-------|
| 100番台 | 晴れ系 |
| 200番台 | くもり系 |
| 300番台 | 雨系 |
| 400番台 | 雪系 |

十の位・一の位で「後」「時々」「一時」や降水種別（雨・雪・雷）を表現。
詳細は気象庁防災情報XML技術資料の付録一覧を参照。
`https://xml.kishou.go.jp/tec_material.html`

---

## 16. ウェブページ（スクレイピング/参照用）

| URL | 内容 |
|-----|------|
| `https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={code}` | 天気予報 |
| `https://www.jma.go.jp/bosai/probability/#area_type=offices&area_code={code}&lang=ja` | 早期注意情報 |
| `https://www.jma.go.jp/bosai/information/#area_type=offices&area_code={code}&format=table` | 気象情報一覧 |
| `https://www.jma.go.jp/bosai/information/typhoon.html#` | 台風情報 |
| `https://www.jma.go.jp/bosai/map.html#5/38.411/143.987/&elem=info&contents=tsunami` | 津波情報 |
| `https://www.data.jma.go.jp/cpd/longfcst/kaisetsu/?term=P1M` | 1ヶ月予報解説 |
| `https://www.data.jma.go.jp/cpd/longfcst/kaisetsu/?term=P3M` | 3ヶ月予報解説 |
| `https://www.data.jma.go.jp/stats/data/mdrr/rank_daily/data{mmdd}.html` | 日別ランキング |
| `https://www.data.jma.go.jp/stats/data/mdrr/rank_update/d{mmdd}.html` | 極値更新状況 |
