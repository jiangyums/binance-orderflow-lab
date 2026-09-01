package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type MicroPriceCalculator struct{}

func NewMicroPriceCalculator() *MicroPriceCalculator {
	return &MicroPriceCalculator{}
}

func (c *MicroPriceCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade, feat *model.Feature) {
	bidPrice, bidQty, bidOk := book.BestBid()
	askPrice, askQty, askOk := book.BestAsk()

	if !bidOk || !askOk {
		return
	}

	total := bidQty + askQty
	if total > 0 {
		feat.Microprice = (bidPrice*bidQty + askPrice*askQty) / total
	}

	feat.Mid = (bidPrice + askPrice) / 2
	feat.Spread = askPrice - bidPrice
	feat.BidDepth = bidQty
	feat.AskDepth = askQty
}

func (c *MicroPriceCalculator) Reset() {
}
