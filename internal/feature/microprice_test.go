package feature

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestMicroPriceCalculator_Update(t *testing.T) {
	tests := []struct {
		name     string
		book     model.OrderBook
		expected float64
	}{
		{
			name: "balanced",
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 10.0},
				Asks: map[float64]float64{101.0: 10.0},
			},
			expected: 100.5,
		},
		{
			name: "bid heavy",
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 20.0},
				Asks: map[float64]float64{101.0: 10.0},
			},
			expected: 100.333,
		},
		{
			name: "ask heavy",
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 10.0},
				Asks: map[float64]float64{101.0: 20.0},
			},
			expected: 100.667,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			calc := &MicroPriceCalculator{}
			feature := calc.Update(model.Event{}, &tt.book, nil)
			assert.InDelta(t, tt.expected, feature.Microprice, 0.001)
		})
	}
}
