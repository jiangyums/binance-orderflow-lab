import argparse
import os
import sys

from research import analyze, config, prepare_data, report
from research.replay_indicators import build_hbt, replay_to_df


def main():
    parser = argparse.ArgumentParser(description='Order-flow indicator research')
    parser.add_argument('--start', default=config.START_DATE)
    parser.add_argument('--end', default=config.END_DATE)
    parser.add_argument('--no-download', action='store_true',
                        help='跳过下载，使用已有缓存')
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

    hbt = build_hbt(feeds, snapshots)
    df = replay_to_df(hbt)
    df = analyze.add_forward_returns(df)

    ht = analyze.hit_rate_table(df)
    st = analyze.strategy_table(df)

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    ht.to_csv(os.path.join(config.RESULTS_DIR, 'hit_rate.csv'), index=False)
    st.to_csv(os.path.join(config.RESULTS_DIR, 'strategy.csv'), index=False)
    df.to_csv(os.path.join(config.RESULTS_DIR, 'indicators.csv'), index=False)

    md = report.render_markdown(ht, st)
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
