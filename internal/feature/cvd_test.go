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
			feat := &model.Feature{}
			calc.Update(model.Event{}, nil, tt.trades, feat)
			assert.InDelta(t, tt.expected, feat.CVD, 0.001)
		})
	}
}

// 增量语义:同一 trades 切片多次 Update,只累计新增部分,不重复计算。
func TestCVDCalculator_Incremental(t *testing.T) {
	calc := &CVDCalculator{}
	feat := &model.Feature{}

	trades := []model.Trade{{Side: "BUY", Quantity: 1.0}}
	calc.Update(model.Event{}, nil, trades, feat)
	assert.InDelta(t, 1.0, feat.CVD, 0.001)

	// 模拟 TradeWorker 追加一条成交
	trades = append(trades, model.Trade{Side: "SELL", Quantity: 0.5})
	calc.Update(model.Event{}, nil, trades, feat)
	assert.InDelta(t, 0.5, feat.CVD, 0.001)

	// 无新增:CVD 保持不变
	calc.Update(model.Event{}, nil, trades, feat)
	assert.InDelta(t, 0.5, feat.CVD, 0.001)
}
