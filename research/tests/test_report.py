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
    md = report.render_markdown(ht, st)
    assert '# 订单流指标预测力研究报告' in md
    assert '命中率' in md and '简单开平仓策略' in md


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
