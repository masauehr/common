# 気象庁 bosai API 仕様まとめ

参考資料:
- https://qiita.com/KAI_Mutsumi/items/2a005b084d95e417ac44
- https://qiita.com/e_toyoda/items/7a293313a725c4d306c0
- jma_mcp/server.py の実装・動作確認による知見

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

## 4. 警報・注意報 API

```
GET https://www.jma.go.jp/bosai/warning/data/warning/{area_code}.json
```

レスポンスの `areaTypes` 配下に市区町村ごとの警報情報。
`warnings[i].code` は TELOPS コード（気象庁XML技術資料準拠）。

主要コード:
| コード | 名称 |
|-------|------|
| 3 | 大雨警報 |
| 4 | 洪水警報 |
| 5 | 暴風警報 |
| 6 | 大雪警報 |
| 10 | 大雨注意報 |
| 14 | 雷注意報 |
| 15 | 強風注意報 |

---

## 5. 早期注意情報（警報級の可能性）API

```
GET https://www.jma.go.jp/bosai/probability/data/probability/{area_code}.json
```

5時間帯（今夕まで・今夜・明日昼・明日夜・明後日以降）×現象種別（大雨/暴風/波浪/高潮/大雪）の組み合わせ。
値: `"高"` / `"中"` / `""（なし）`

---

## 6. 気象情報 API

```
GET https://www.jma.go.jp/bosai/information/data/information.json  # 一覧
GET https://www.jma.go.jp/bosai/information/data/denbun/{json_name}.json  # 個別XML電文
```

一覧JSONの各要素:
| フィールド | 内容 |
|-----------|------|
| `controlTitle` | 情報種別（府県気象情報・地方気象情報・全般気象情報 など） |
| `headTitle` | タイトル |
| `reportDatetime` | 発表時刻 |
| `publishingOffice` | 発表官署 |
| `areaCode` | 対象エリアコード |
| `jsonName` | 電文取得用キー |
| `header` | 電文種別コード（VPFJ50=府県気象情報、VPZJ50=全般気象情報 など） |

個別電文は XML 形式。`Body/Comment/Text` に本文。

---

## 7. 気象台コメント API

```
GET https://www.jma.go.jp/bosai/forecaster_comment/data/comments/{area_code}.txt
```

テキスト形式で警報等の見込み・特記事項を返す。
気象庁Webサイト上に専用の公開ページは存在しない（2026年4月確認）。

---

## 8. 台風情報 API

```
GET https://www.jma.go.jp/bosai/information/data/typhoon.json  # 一覧
GET https://www.jma.go.jp/bosai/information/data/typhoon/{json_name}  # 個別
```

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
