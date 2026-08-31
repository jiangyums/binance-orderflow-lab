package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type OBICalculator struct {
	levels int
}

func NewOBICalculator(levels int) *OBICalculator {
	return &OBICalculator{levels: levels}
}

func (c *OBICalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
	feature := model.Feature{Timestamp: event.Timestamp}

	bidVol := book.BidVolume(c.levels)
	askVol := book.AskVolume(c.levels)

	total := bidVol + askVol
	if total > 0 {
		obi := (bidVol - askVol) / total
		switch c.levels {
		case 1:
			feature.OBI1 = obi
		case 5:
			feature.OBI5 = obi
		case 10:
			feature.OBI10 = obi
		}
	}

	return feature
}

func (c *OBICalculator) Reset() {
}
