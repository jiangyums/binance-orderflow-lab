import os
import tempfile

import pandas as pd

from research import analyze, report


def test_render_markdown_contains_tables():
    ht = pd.DataFrame({'indicator': ['obi'], 'horizon_s': [5],
                       'hit_rate': [0.6], 'n': [100], 'p_value': [0.02]})
    st = pd.DataFrame({'indicator': ['obi'], 'horizon_s': [5], 'n_trades': [10],
                       'win_rate': [0.5], 'cum_profit': [0.01],
                       'max_drawdown': [-0.02], 'sharpe': [1.2]})
    qt = pd.DataFrame({'indicator': ['obi'], 'horizon_s': [5],
                       'neg_hit': [0.5], 'mid_hit': [0.5], 'pos_hit': [0.6],
                       'neg_ret': [-1e-4], 'pos_ret': [1e-4],
                       'n_neg': [100], 'n_pos': [100]})
    md = report.render_markdown(ht, st, qt)
    assert '# 订单流指标预测力研究报告' in md
    assert '命中率' in md and '简单开平仓策略' in md
    assert '极端分位命中率' in md
    assert '最正分位命中' in md


def test_render_markdown_per_trade_section():
    ht = pd.DataFrame({'indicator': ['trade_ofi'], 'horizon_s': [5],
                       'hit_rate': [0.6], 'n': [100], 'p_value': [0.02]})
    st = pd.DataFrame({'indicator': ['trade_ofi'], 'horizon_s': [5], 'n_trades': [10],
                       'win_rate': [0.5], 'cum_profit': [0.01],
                       'max_drawdown': [-0.02], 'sharpe': [1.2]})
    qt = pd.DataFrame({'indicator': ['trade_ofi'], 'horizon_s': [5],
                       'neg_hit': [0.5], 'mid_hit': [0.5], 'pos_hit': [0.6],
                       'neg_ret': [-1e-4], 'pos_ret': [1e-4],
                       'n_neg': [100], 'n_pos': [100]})
    per_trade = {'hit_rate': ht, 'quantile': qt, 'strategy': st}
    md = report.render_markdown(ht, st, qt, per_trade=per_trade)
    assert '逐笔事件驱动' in md
    # 两组（每秒 + 逐笔）各渲染三节，trade_ofi 作为 indicator 值出现 6 次
    assert md.count('trade_ofi') == 6


def test_empty_input_pipeline_no_crash():
    empty = pd.DataFrame(columns=['timestamp', 'mid', 'obi', 'trade_ofi',
                                  'book_ofi', 'trend', 'bid_qty', 'ask_qty'])
    empty = analyze.add_forward_returns(empty)
    ht = analyze.hit_rate_table(empty)
    st = analyze.strategy_table(empty)
    md = report.render_markdown(ht, st)
    assert len(ht) == 12 and (ht['n'] == 0).all()
    assert ht['p_value'].isna().all()
    assert len(st) == 12 and (st['n_trades'] == 0).all()
    assert '# 订单流指标预测力研究报告' in md
    assert 'obi' in md


def test_save_report_writes_file():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'report.md')
        report.save_report('content', path)
        assert os.path.exists(path)
        with open(path, encoding='utf-8') as f:
            assert f.read() == 'content'
