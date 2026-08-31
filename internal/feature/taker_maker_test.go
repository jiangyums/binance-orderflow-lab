package feature

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestTakerMakerCalculator_Update(t *testing.T) {
	tests := []struct {
		name         string
		trades       []model.Trade
		askDepth     float64
		bidDepth     float64
		expectedBuy  float64
		expectedSell float64
	}{
		{
			name: "buy trade with ask depth",
			trades: []model.Trade{
				{Side: "BUY", Quantity: 5.0},
			},
			askDepth:     10.0,
			bidDepth:     10.0,
			expectedBuy:  0.5,
			expectedSell: 0.0,
		},
		{
			name: "sell trade with bid depth",
			trades: []model.Trade{
				{Side: "SELL", Quantity: 3.0},
			},
			askDepth:     10.0,
			bidDepth:     10.0,
			expectedBuy:  0.0,
			expectedSell: 0.3,
		},
		{
			name: "mixed trades",
			trades: []model.Trade{
				{Side: "BUY", Quantity: 2.0},
				{Side: "SELL", Quantity: 4.0},
			},
			askDepth:     10.0,
			bidDepth:     10.0,
			expectedBuy:  0.2,
			expectedSell: 0.4,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			calc := &TakerMakerCalculator{}
			book := &model.OrderBook{
				Bids: map[float64]float64{100.0: tt.bidDepth},
				Asks: map[float64]float64{101.0: tt.askDepth},
			}
			feature := calc.Update(model.Event{}, book, tt.trades)
			assert.InDelta(t, tt.expectedBuy, feature.BuyBreakout, 0.001)
			assert.InDelta(t, tt.expectedSell, feature.SellBreakout, 0.001)
		})
	}
}
