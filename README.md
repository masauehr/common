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
