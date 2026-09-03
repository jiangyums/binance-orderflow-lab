import os

import pandas as pd

from research import config


def render_markdown(hit_rate_df: pd.DataFrame,
                    strategy_df: pd.DataFrame,
                    quantile_df: pd.DataFrame = None,
                    per_trade: dict = None) -> str:
    """Renders the research report.

    per_trade: optional dict with 'hit_rate'/'quantile'/'strategy' DataFrames
    for the event-driven (per-trade) sampling track. When provided, an
    additional "逐笔事件驱动" section is appended.
    """
    lines = []
    lines.append('# 订单流指标预测力研究报告')
    lines.append('')
    _section_hit_rate(lines, hit_rate_df)
    _section_quantile(lines, quantile_df)
    _section_strategy(lines, strategy_df)

    if per_trade is not None:
        lines.append('# 逐笔事件驱动（每笔成交一行）')
        lines.append('')
        _section_hit_rate(lines, per_trade.get('hit_rate'))
        _section_quantile(lines, per_trade.get('quantile'))
        _section_strategy(lines, per_trade.get('strategy'))

    return '\n'.join(lines)


def _section_hit_rate(lines, hit_rate_df):
    lines.append('## 方向命中率')
    lines.append('')
    if hit_rate_df is not None and len(hit_rate_df):
        t = hit_rate_df.copy()
        t['显著'] = t['p_value'] < config.SIGNIFICANCE_ALPHA
        lines.append(t.to_markdown(index=False))
    else:
        lines.append('（无样本）')
    lines.append('')


def _section_quantile(lines, quantile_df):
    lines.append('## 极端分位命中率（20 等频桶）')
    lines.append('')
    if quantile_df is not None and len(quantile_df):
        t = quantile_df.copy()
        for col in ('neg_hit', 'mid_hit', 'pos_hit'):
            t[col] = t[col].round(3)
        for col in ('neg_ret', 'pos_ret'):
            t[col] = (t[col] * 1e4).round(3)  # bps
        t = t.rename(columns={
            'neg_hit': '最负分位命中', 'mid_hit': '中间分位命中', 'pos_hit': '最正分位命中',
            'neg_ret': '最负分位收益(bps)', 'pos_ret': '最正分位收益(bps)',
            'n_neg': '最负n', 'n_pos': '最正n',
        })
        lines.append(t.to_markdown(index=False))
    else:
        lines.append('（无样本）')
    lines.append('')


def _section_strategy(lines, strategy_df):
    lines.append('## 简单开平仓策略（taker 0.05% 双边）')
    lines.append('')
    if strategy_df is not None and len(strategy_df):
        lines.append(strategy_df.to_markdown(index=False))
    else:
        lines.append('（无交易）')
    lines.append('')


def save_report(content: str, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
