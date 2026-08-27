import aiohttp

SYMBOL = "BTCUSDT"

SNAPSHOT_URL = "https://fapi.binance.com" "/fapi/v1/depth"


async def get_snapshot(limit=1000):
    """
    获取 Binance Futures L2 order book snapshot

    返回:

    {
        "lastUpdateId": xxx,
        "bids": [
            ["price","qty"],
            ...
        ],
        "asks": [
            ["price","qty"],
            ...
        ]
    }

    """

    params = {"symbol": SYMBOL, "limit": limit}

    async with aiohttp.ClientSession() as session:

        async with session.get(SNAPSHOT_URL, params=params) as response:

            response.raise_for_status()

            data = await response.json()

            return data
