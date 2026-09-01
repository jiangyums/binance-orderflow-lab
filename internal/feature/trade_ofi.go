package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

// TradeOFICalculator 计算 TOFI(Trade-based OFI):
// 本步新增的有符号吃单量(BUY +qty, SELL -qty),与 Python 研究中
// diff(cvd) 的口径一致;深度事件(无新成交)时 TOFI 为 0。
// 同时填充本步最新一笔成交的 TradeSide/TradePrice/TradeQty。
type TradeOFICalculator struct {
	consumed int // 已消费的 trades 前缀长度
}

func NewTradeOFICalculator() *TradeOFICalculator {
	return &TradeOFICalculator{}
}

func (c *TradeOFICalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade, feat *model.Feature) {
	var tofi float64

	for i := c.consumed; i < len(trades); i++ {
		t := trades[i]
		if t.Side == "BUY" {
			tofi += t.Quantity
		} else {
			tofi -= t.Quantity
		}
		feat.TradeSide = t.Side
		feat.TradePrice = t.Price
		feat.TradeQty = t.Quantity
	}
	c.consumed = len(trades)

	feat.TOFI = tofi
}

func (c *TradeOFICalculator) Reset() {
	c.consumed = 0
}
