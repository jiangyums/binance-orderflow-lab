import argparse
import os
import sys

from research import analyze, config, prepare_data, report
from research.replay_indicators import build_hbt, replay_per_trade_to_df, replay_to_df


def _analyze(df):
    df = analyze.add_forward_returns(df)
    return {
        'hit_rate': analyze.hit_rate_table(df),
        'quantile': analyze.quantile_hit_table(df),
        'strategy': analyze.strategy_table(df),
    }


def main():
    parser = argparse.ArgumentParser(description='Order-flow indicator research')
    parser.add_argument('--start', default=config.START_DATE)
    parser.add_argument('--end', default=config.END_DATE)
    parser.add_argument('--no-download', action='store_true',
                        help='skip download, use cached feed.npz')
    parser.add_argument('--mode', choices=['second', 'per_trade', 'both'],
                        default='both', help='sampling mode (default both)')
    args = parser.parse_args()

    if args.no_download:
        days = [{'feed': os.path.join(config.DATA_DIR, 'hist', d, 'feed.npz'),
                 'snapshot': os.path.join(config.DATA_DIR, 'hist', d, 'snapshot.npz')}
                for d in _date_list(args.start, args.end)
                if os.path.exists(os.path.join(config.DATA_DIR, 'hist', d, 'feed.npz'))]
    else:
        days = prepare_data.prepare_range(args.start, args.end)

    feeds = [d['feed'] for d in days if os.path.exists(d['feed'])]
    snapshots = [d['snapshot'] for d in days if d['snapshot'] and os.path.exists(d['snapshot'])]

    if not feeds:
        raise SystemExit(
            'no feed data found; run without --no-download, or check data/hist/ cache'
        )

    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    hbt = build_hbt(feeds, snapshots)

    md_parts = []
    per_trade = None

    if args.mode in ('second', 'both'):
        df = replay_to_df(hbt)
        res = _analyze(df)
        for k in ('hit_rate', 'quantile', 'strategy'):
            res[k].to_csv(os.path.join(config.RESULTS_DIR, f'{k}.csv'), index=False)
        df.to_csv(os.path.join(config.RESULTS_DIR, 'indicators.csv'), index=False)
        md_parts.append(report.render_markdown(res['hit_rate'], res['strategy'], res['quantile']))

    if args.mode in ('per_trade', 'both'):
        df_pt = replay_per_trade_to_df(hbt)
        res_pt = _analyze(df_pt)
        for k in ('hit_rate', 'quantile', 'strategy'):
            res_pt[k].to_csv(os.path.join(config.RESULTS_DIR, f'{k}_per_trade.csv'), index=False)
        df_pt.to_csv(os.path.join(config.RESULTS_DIR, 'indicators_per_trade.csv'), index=False)
        if args.mode == 'both':
            # 合并到同一份报告：第二次渲染时用 per_trade 附加章节
            md_parts[0] = report.render_markdown(
                res['hit_rate'], res['strategy'], res['quantile'],
                per_trade=res_pt,
            )
        else:
            md_parts.append(report.render_markdown(res_pt['hit_rate'], res_pt['strategy'], res_pt['quantile']))

    md = '\n'.join(md_parts)
    report.save_report(md, os.path.join(config.RESULTS_DIR, 'report.md'))

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    print(md)


def _date_list(start, end):
    from datetime import date, timedelta
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    out = []
    d = s
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


if __name__ == '__main__':
    main()
