package feature

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestOBICalculator_Update(t *testing.T) {
	tests := []struct {
		name     string
		levels   int
		book     model.OrderBook
		expected float64
	}{
		{
			name:   "balanced book",
			levels: 1,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 10.0},
				Asks: map[float64]float64{101.0: 10.0},
			},
			expected: 0.0,
		},
		{
			name:   "bid heavy",
			levels: 1,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 15.0},
				Asks: map[float64]float64{101.0: 5.0},
			},
			expected: 0.5,
		},
		{
			name:   "ask heavy",
			levels: 1,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 5.0},
				Asks: map[float64]float64{101.0: 15.0},
			},
			expected: -0.5,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			calc := &OBICalculator{levels: tt.levels}
			feature := calc.Update(model.Event{}, &tt.book, nil)
			assert.InDelta(t, tt.expected, feature.OBI1, 0.001)
		})
	}
}
