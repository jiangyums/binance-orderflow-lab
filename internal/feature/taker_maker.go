package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

// TakerMakerCalculator 计算主动买卖量与最优档位的比值。
// 采用增量消费:只处理上次之后新增的 trades,避免全量重复累计。
type TakerMakerCalculator struct {
	buyVolume  float64
	sellVolume float64
	consumed   int // 已消费的 trades 前缀长度
}

func NewTakerMakerCalculator() *TakerMakerCalculator {
	return &TakerMakerCalculator{}
}

func (c *TakerMakerCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade, feat *model.Feature) {
	for i := c.consumed; i < len(trades); i++ {
		t := trades[i]
		if t.Side == "BUY" {
			c.buyVolume += t.Quantity
		} else if t.Side == "SELL" {
			c.sellVolume += t.Quantity
		}
	}
	c.consumed = len(trades)

	_, askQty, askOk := book.BestAsk()
	_, bidQty, bidOk := book.BestBid()

	if askOk && askQty > 0 {
		feat.BuyBreakout = c.buyVolume / askQty
	}
	if bidOk && bidQty > 0 {
		feat.SellBreakout = c.sellVolume / bidQty
	}
}

func (c *TakerMakerCalculator) Reset() {
	c.buyVolume = 0
	c.sellVolume = 0
	c.consumed = 0
}
