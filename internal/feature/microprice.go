package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type MicroPriceCalculator struct{}

func NewMicroPriceCalculator() *MicroPriceCalculator {
	return &MicroPriceCalculator{}
}

func (c *MicroPriceCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
	feature := model.Feature{Timestamp: event.Timestamp}

	bidPrice, bidQty, bidOk := book.BestBid()
	askPrice, askQty, askOk := book.BestAsk()

	if !bidOk || !askOk {
		return feature
	}

	total := bidQty + askQty
	if total > 0 {
		feature.Microprice = (bidPrice*bidQty + askPrice*askQty) / total
	}

	feature.Mid = (bidPrice + askPrice) / 2
	feature.Spread = askPrice - bidPrice
	feature.BidDepth = bidQty
	feature.AskDepth = askQty

	return feature
}

func (c *MicroPriceCalculator) Reset() {
}
