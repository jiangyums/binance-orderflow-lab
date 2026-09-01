package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

// CVDCalculator 累计有符号吃单量(BUY +qty, SELL -qty)。
// 采用增量消费:只处理上次之后新增的 trades,避免全量重复累计。
type CVDCalculator struct {
	value    float64
	consumed int // 已消费的 trades 前缀长度
}

func NewCVDCalculator() *CVDCalculator {
	return &CVDCalculator{}
}

func (c *CVDCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade, feat *model.Feature) {
	for i := c.consumed; i < len(trades); i++ {
		t := trades[i]
		if t.Side == "BUY" {
			c.value += t.Quantity
		} else if t.Side == "SELL" {
			c.value -= t.Quantity
		}
	}
	c.consumed = len(trades)

	feat.CVD = c.value
}

func (c *CVDCalculator) Reset() {
	c.value = 0
	c.consumed = 0
}
