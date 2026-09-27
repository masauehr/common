"""予報の変遷（発表日の違う予報の比較）の作図部品。複数のプロジェクトで共通に使う。

「発表日（run_date）ごとの予報スナップショット」を蓄積したデータから、次の3種類の図を描く:
  plot_vintages   発表日の違う予報（今日発表・1日前発表・2日前発表…）を同じ日付軸に重ねて、実績と比べる
  plot_revision   起点の発表日の予報が、過去の発表からどれだけ修正されたか（差）
  plot_evolution  ある日（target_date）の予報が、発表日ごとにどう変わってきたか

データの形（DataFrame）: run_date（発表日）, target_date（予報の対象日）, lead_time_days, 予報の値の列（value_col）。
実績は、target_date を index にした Series（無ければ None）。

使い方（ml_forecast の例）:
    import sys; sys.path.insert(0, '/Users/masahiro/projects/common')
    import forecast_vintage_viz as fv
    fv.plot_vintages(log, 'pred_rf_kwh', actual=actual_kwh, title='発電量予測 v3', ylabel='kWh', ax=ax)

nouken の nouken_viz.py に、同じ考え方を先に実装した版（GSR・SSD・最高気温向けで、画像から読み取った推定値の区別表示などを含む）がある。
"""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# 発表日ごとの系列スタイル（色だけに頼らず線種・マーカーも変え、近い色でも区別できるようにする。
# 色は色覚多様性に配慮した配色で、実績の青と紛れないよう青系は避ける）。先頭（起点）が太い実線。
COLORS = ['#D55E00', '#009E73', '#CC79A7', '#6A3D9A', '#E69F00', '#8C510A', '#666666']
LINESTYLES = ['-', '--', '-.', ':', '--', '-.', ':']
MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X']
COLOR_ACTUAL = '#1f77b4'
COLOR_NOTE = '#7f7f7f'


def setup_font():
    """日本語表示用フォントを設定する（macOS のヒラギノ/AppleGothic）。"""
    plt.rcParams['font.family'] = ['Hiragino Sans', 'AppleGothic', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False


def style(i):
    """i 番目（0=起点の発表）の色・線種・マーカーを返す。"""
    k = i % len(COLORS)
    return {'color': COLORS[k], 'linestyle': LINESTYLES[k], 'marker': MARKERS[k],
            'linewidth': 2.6 if i == 0 else 1.6, 'markersize': 4.5 if i == 0 else 4}


def resolve_base(df, base_run_date=None, run_col='run_date'):
    """比較の起点にする発表日を決める。None なら最新。指定日が無ければ、それより前で最も近い発表日を使う。

    戻り値は (使う発表日, 指定日から変更したか)。
    """
    have = sorted(pd.to_datetime(df[run_col].unique()))
    if base_run_date is None:
        return have[-1], False
    b = pd.Timestamp(base_run_date)
    if b in set(have):
        return b, False
    earlier = [d for d in have if d < b]
    if not earlier:
        raise ValueError(f'{b:%Y-%m-%d} 以前の発表日がありません（最古は {have[0]:%Y-%m-%d}）')
    return earlier[-1], True


def pick_run_dates(df, offsets=(0, 1, 2, 3), base_run_date=None, run_col='run_date'):
    """比較する発表日を選ぶ。offsets は「起点の何日前の発表か」。その日の発表が無ければ含めない（補間しない）。

    戻り値は (選べた発表日のリスト[起点が先頭・新しい順], 選べなかった発表日のリスト)。
    """
    have = set(pd.to_datetime(df[run_col].unique()))
    base, _ = resolve_base(df, base_run_date, run_col)
    wanted = [base - pd.Timedelta(days=int(o)) for o in offsets]
    return sorted([d for d in wanted if d in have], reverse=True), sorted([d for d in wanted if d not in have], reverse=True)


def _forecast_rows(df, run, value_col, run_col, lead_col, horizon):
    f = df[(pd.to_datetime(df[run_col]) == run) & (df[lead_col] >= 0)]
    if horizon is not None:
        f = f[f[lead_col] <= horizon]
    return f.dropna(subset=[value_col]).sort_values('target_date')


def _day_ticks(ax, max_ticks=7):
    """横軸を日単位の目盛りにする（期間が短いと12時間刻みの目盛りが同じ日付で重複表示されるため）。"""
    lo, hi = ax.get_xlim()
    span = max(1, int(round(hi - lo)))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, -(-span // max_ticks))))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))


def plot_vintages(df, value_col, actual=None, offsets=(0, 1, 2, 3), base_run_date=None, horizon=None,
                  title='', ylabel='', past_days=3, run_col='run_date', target_col='target_date',
                  lead_col='lead_time_days', ax=None):
    """発表日の違う予報を同じ日付軸に重ね、実績（青）と比べる。起点の発表を太い実線で描く。"""
    setup_font()
    ax = ax or plt.subplots(figsize=(11, 3.8))[1]
    runs, missing = pick_run_dates(df, offsets, base_run_date, run_col)
    if not runs:
        ax.text(0.5, 0.5, '比較できる発表日がありません', transform=ax.transAxes, ha='center')
        return ax
    base = runs[0]
    rows = [_forecast_rows(df, r, value_col, run_col, lead_col, horizon) for r in runs]
    tmin = min(pd.to_datetime(f[target_col]).min() for f in rows if len(f)) if any(len(f) for f in rows) else base
    tmax = max(pd.to_datetime(f[target_col]).max() for f in rows if len(f)) if any(len(f) for f in rows) else base
    if actual is not None and len(actual):
        a = actual[(actual.index >= tmin - pd.Timedelta(days=past_days)) & (actual.index <= tmax)].dropna()
        ax.plot(a.index, a.values, color=COLOR_ACTUAL, lw=1.8, marker='o', ms=3, label='実績', zorder=6)
    for i, (r, f) in enumerate(zip(runs, rows)):
        ax.plot(pd.to_datetime(f[target_col]), f[value_col], zorder=5 - min(i, 4),
                label=f'{r:%m/%d}発表' + ('（起点）' if i == 0 else f'（{(base - r).days}日前）'), **style(i))
    ax.axvline(base, color=COLOR_NOTE, lw=0.8, ls=':')
    ax.set_ylabel(ylabel)
    t = f'{title}: 発表日の違う予報の比較（{base:%m/%d}発表を起点）' if title else f'発表日の違う予報の比較（{base:%m/%d}発表を起点）'
    if missing:
        t += '  ※欠測の発表日: ' + ', '.join(f'{d:%m/%d}' for d in missing)
    ax.set_title(t, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(loc='best', ncol=3, fontsize=8)
    _day_ticks(ax)
    return ax


def plot_revision(df, value_col, offsets=(1, 2, 3), base_run_date=None, horizon=None, title='', ylabel='',
                  run_col='run_date', target_col='target_date', lead_col='lead_time_days', ax=None):
    """予報の修正量（起点の発表 − 過去の発表）を、同じ対象日ごとに描く。色・線種は plot_vintages と共通。"""
    setup_font()
    ax = ax or plt.subplots(figsize=(11, 3.4))[1]
    runs, missing = pick_run_dates(df, (0,) + tuple(offsets), base_run_date, run_col)
    if len(runs) < 2:
        ax.text(0.5, 0.5, '比較できる過去の発表日がありません', transform=ax.transAxes, ha='center')
        return ax
    cur = _forecast_rows(df, runs[0], value_col, run_col, lead_col, horizon).set_index(target_col)[value_col]
    for i, r in enumerate(runs[1:], start=1):
        old = _forecast_rows(df, r, value_col, run_col, lead_col, horizon).set_index(target_col)[value_col]
        d = (cur - old).dropna()
        ax.plot(pd.to_datetime(d.index), d.values, label=f'{runs[0]:%m/%d}発表 − {r:%m/%d}発表（{(runs[0] - r).days}日前）', **style(i))
    ax.axhline(0, color='k', lw=0.8)
    ax.set_ylabel(f'修正量 {ylabel}'.strip())
    t = f'{title}: 予報の修正量（{runs[0]:%m/%d}発表 − 過去の発表）' if title else f'予報の修正量（{runs[0]:%m/%d}発表 − 過去の発表）'
    if missing:
        t += '  ※欠測の発表日: ' + ', '.join(f'{d:%m/%d}' for d in missing)
    ax.set_title(t, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(loc='best', ncol=2, fontsize=8)
    _day_ticks(ax)
    return ax


def plot_evolution(df, value_col, target_date, actual=None, title='', ylabel='', run_col='run_date',
                   target_col='target_date', lead_col='lead_time_days', ax=None):
    """ある日（target_date）の予報が、発表日ごとにどう変わってきたかを描く。実績が分かっていれば水平線で示す。"""
    setup_font()
    ax = ax or plt.subplots(figsize=(6, 3.4))[1]
    td = pd.Timestamp(target_date)
    f = df[(pd.to_datetime(df[target_col]) == td) & (df[lead_col] >= 0)].dropna(subset=[value_col]).sort_values(run_col)
    ax.plot(pd.to_datetime(f[run_col]), f[value_col], color=COLORS[0], lw=1.8, marker='o', ms=4, label='予報（発表日ごと）')
    if actual is not None and td in actual.index and pd.notna(actual.loc[td]):
        ax.axhline(actual.loc[td], color=COLOR_ACTUAL, lw=1.6, label=f'実績 {actual.loc[td]:.1f}')
    ax.set_xlabel('予報の発表日')
    ax.set_ylabel(ylabel)
    ax.set_title(f'{td:%m/%d} の{title}予報は発表日ごとにどう変わったか', fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(loc='best', fontsize=8)
    _day_ticks(ax, max_ticks=6)
    if f.empty:
        ax.text(0.5, 0.5, 'この日を対象にした予報がありません', transform=ax.transAxes, ha='center')
    return ax
