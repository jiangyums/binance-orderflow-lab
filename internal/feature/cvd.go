package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type CVDCalculator struct {
	value float64
}

func NewCVDCalculator() *CVDCalculator {
	return &CVDCalculator{}
}

func (c *CVDCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
	feature := model.Feature{Timestamp: event.Timestamp}

	for _, trade := range trades {
		if trade.Side == "BUY" {
			c.value += trade.Quantity
		} else if trade.Side == "SELL" {
			c.value -= trade.Quantity
		}
	}

	feature.CVD = c.value
	return feature
}

func (c *CVDCalculator) Reset() {
	c.value = 0
}
