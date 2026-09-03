import os

import pandas as pd


def render_markdown(hit_rate_df: pd.DataFrame, strategy_df: pd.DataFrame) -> str:
    lines = []
    lines.append('# 订单流指标预测力研究报告')
    lines.append('')
    lines.append('## 方向命中率')
    lines.append('')
    if len(hit_rate_df):
        t = hit_rate_df.copy()
        t['显著'] = t['p_value'] < 0.05
        lines.append(t.to_markdown(index=False))
    else:
        lines.append('（无样本）')
    lines.append('')
    lines.append('## 简单开平仓策略（taker 0.05% 双边）')
    lines.append('')
    if len(strategy_df):
        lines.append(strategy_df.to_markdown(index=False))
    else:
        lines.append('（无交易）')
    lines.append('')
    return '\n'.join(lines)


def save_report(content: str, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
