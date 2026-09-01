package feature

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestOFICalculator_Update(t *testing.T) {
	tests := []struct {
		name         string
		lastBidPrice float64
		lastBidQty   float64
		lastAskPrice float64
		lastAskQty   float64
		book         model.OrderBook
		expected     float64
	}{
		{
			name:         "bid size increase",
			lastBidPrice: 100.0,
			lastBidQty:   10.0,
			lastAskPrice: 101.0,
			lastAskQty:   5.0,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 15.0},
				Asks: map[float64]float64{101.0: 5.0},
			},
			expected: 5.0, // 15 - 10 = 5
		},
		{
			name:         "ask size increase",
			lastBidPrice: 100.0,
			lastBidQty:   10.0,
			lastAskPrice: 101.0,
			lastAskQty:   5.0,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 10.0},
				Asks: map[float64]float64{101.0: 10.0},
			},
			expected: -5.0, // -(10 - 5) = -5
		},
		{
			name:         "bid price increase",
			lastBidPrice: 100.0,
			lastBidQty:   10.0,
			lastAskPrice: 101.0,
			lastAskQty:   5.0,
			book: model.OrderBook{
				Bids: map[float64]float64{102.0: 8.0},
				Asks: map[float64]float64{101.0: 5.0},
			},
			expected: 8.0, // new bid at higher price
		},
		{
			name:         "ask price decrease",
			lastBidPrice: 100.0,
			lastBidQty:   10.0,
			lastAskPrice: 101.0,
			lastAskQty:   5.0,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 10.0},
				Asks: map[float64]float64{99.0: 7.0},
			},
			expected: -7.0, // new ask at lower price
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			calc := &OFICalculator{
				lastBidPrice: tt.lastBidPrice,
				lastBidQty:   tt.lastBidQty,
				lastAskPrice: tt.lastAskPrice,
				lastAskQty:   tt.lastAskQty,
			}
			feat := &model.Feature{}
			calc.Update(model.Event{}, &tt.book, nil, feat)
			assert.InDelta(t, tt.expected, feat.OFI, 0.001)
		})
	}
}
