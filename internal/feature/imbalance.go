package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type OBICalculator struct {
	levels int
}

func NewOBICalculator(levels int) *OBICalculator {
	return &OBICalculator{levels: levels}
}

func (c *OBICalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade, feat *model.Feature) {
	bidVol := book.BidVolume(c.levels)
	askVol := book.AskVolume(c.levels)

	total := bidVol + askVol
	if total > 0 {
		obi := (bidVol - askVol) / total
		switch c.levels {
		case 1:
			feat.OBI1 = obi
		case 5:
			feat.OBI5 = obi
		case 10:
			feat.OBI10 = obi
		}
	}
}

func (c *OBICalculator) Reset() {
}
