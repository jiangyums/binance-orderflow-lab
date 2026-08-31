package feature

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestCVDCalculator_Update(t *testing.T) {
	tests := []struct {
		name     string
		trades   []model.Trade
		expected float64
	}{
		{
			name: "buy trade",
			trades: []model.Trade{
				{Side: "BUY", Quantity: 1.0},
			},
			expected: 1.0,
		},
		{
			name: "sell trade",
			trades: []model.Trade{
				{Side: "SELL", Quantity: 2.0},
			},
			expected: -2.0,
		},
		{
			name: "mixed trades",
			trades: []model.Trade{
				{Side: "BUY", Quantity: 3.0},
				{Side: "SELL", Quantity: 1.0},
			},
			expected: 2.0,
		},
		{
			name:     "no trades",
			trades:   []model.Trade{},
			expected: 0.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			calc := &CVDCalculator{}
			feature := calc.Update(model.Event{}, nil, tt.trades)
			assert.InDelta(t, tt.expected, feature.CVD, 0.001)
		})
	}
}
