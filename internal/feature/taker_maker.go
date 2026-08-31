package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type TakerMakerCalculator struct {
	buyVolume  float64
	sellVolume float64
}

func NewTakerMakerCalculator() *TakerMakerCalculator {
	return &TakerMakerCalculator{}
}

func (c *TakerMakerCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
	feature := model.Feature{Timestamp: event.Timestamp}

	for _, trade := range trades {
		if trade.Side == "BUY" {
			c.buyVolume += trade.Quantity
		} else if trade.Side == "SELL" {
			c.sellVolume += trade.Quantity
		}
	}

	_, askQty, askOk := book.BestAsk()
	_, bidQty, bidOk := book.BestBid()

	if askOk && askQty > 0 {
		feature.BuyBreakout = c.buyVolume / askQty
	}
	if bidOk && bidQty > 0 {
		feature.SellBreakout = c.sellVolume / bidQty
	}

	return feature
}

func (c *TakerMakerCalculator) Reset() {
	c.buyVolume = 0
	c.sellVolume = 0
}
