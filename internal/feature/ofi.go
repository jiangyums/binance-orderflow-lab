package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type OFICalculator struct {
	lastBidPrice float64
	lastBidQty   float64
	lastAskPrice float64
	lastAskQty   float64
}

func NewOFICalculator() *OFICalculator {
	return &OFICalculator{}
}

func (c *OFICalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade, feat *model.Feature) {
	bidPrice, bidQty, bidOk := book.BestBid()
	askPrice, askQty, askOk := book.BestAsk()

	if !bidOk || !askOk {
		return
	}

	feat.Mid = (bidPrice + askPrice) / 2
	feat.Spread = askPrice - bidPrice
	feat.BidDepth = bidQty
	feat.AskDepth = askQty

	var ofi float64

	if c.lastBidPrice == 0 && c.lastAskPrice == 0 {
		ofi = 0
	} else if bidPrice > c.lastBidPrice {
		ofi = bidQty
	} else if bidPrice < c.lastBidPrice {
		ofi = -c.lastBidQty
	} else {
		ofi = bidQty - c.lastBidQty
	}

	if c.lastAskPrice == 0 {
		// No previous ask
	} else if askPrice < c.lastAskPrice {
		ofi -= askQty
	} else if askPrice > c.lastAskPrice {
		ofi += c.lastAskQty
	} else {
		ofi -= (askQty - c.lastAskQty)
	}

	feat.OFI = ofi

	c.lastBidPrice = bidPrice
	c.lastBidQty = bidQty
	c.lastAskPrice = askPrice
	c.lastAskQty = askQty
}

func (c *OFICalculator) Reset() {
	c.lastBidPrice = 0
	c.lastBidQty = 0
	c.lastAskPrice = 0
	c.lastAskQty = 0
}
