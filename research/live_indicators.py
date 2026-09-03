"""Live-track sampling: Python LiveBot over iceoryx2 shared memory.

The connector process (Rust, `connector.exe <name> binancefutures <config>`)
streams Binance depth/trade events via iceoryx2; the LiveBot rebuilds the
order book in real time. This module reuses the replay track's njit sampling
loop (_run_sample) so both tracks share identical indicator semantics.
"""

from hftbacktest import LiveInstrument, build_hashmap_livebot
from hftbacktest.binding import HashMapMarketDepthLiveBot_

from research import config
from research.replay_indicators import OUT_COLS, _run_sample


def build_live_hbt(connector_name: str,
                   symbol: str = None,
                   tick_size: float = 0.1,
                   lot_size: float = 0.001):
    """Builds a live bot bound to a running `connector` via iceoryx2.

    The connector with the same `connector_name` must be running on this
    machine before sampling starts.
    """
    symbol = symbol or config.SYMBOL
    inst = (
        LiveInstrument()
        .connector(connector_name)
        .symbol(symbol)
        .tick_size(tick_size)
        .lot_size(lot_size)
        .last_trades_capacity(config.LAST_TRADES_CAP)
    )
    ptr = build_hashmap_livebot([inst])
    return HashMapMarketDepthLiveBot_(ptr)


def live_sample_to_df(hbt):
    """Samples indicators from the live stream until the stream ends.

    Uses the SAME njit loop as the replay track. Live `elapse` waits in real
    time and returns 0 on normal timeout, so sampling proceeds at wall-clock
    pace; the run is bounded by the loop's max_rows (1,000,000 rows) or stream
    interruption. Returns the standard OUT_COLS DataFrame.

    Note: warm-up behavior matches the replay track — book_ofi is NaN on the
    first sample and trend is NaN for the first TREND_WINDOW (60s).
    """
    return _run_sample(hbt)
