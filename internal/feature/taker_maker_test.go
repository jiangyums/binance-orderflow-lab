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
			feat := &model.Feature{}
			calc.Update(model.Event{}, book, tt.trades, feat)
			assert.InDelta(t, tt.expectedBuy, feat.BuyBreakout, 0.001)
			assert.InDelta(t, tt.expectedSell, feat.SellBreakout, 0.001)
		})
	}
}

// 增量语义:同一 trades 切片多次 Update,只累计新增部分,不重复计算。
func TestTakerMakerCalculator_Incremental(t *testing.T) {
	calc := &TakerMakerCalculator{}
	book := &model.OrderBook{
		Bids: map[float64]float64{100.0: 10.0},
		Asks: map[float64]float64{101.0: 10.0},
	}
	feat := &model.Feature{}

	trades := []model.Trade{{Side: "BUY", Quantity: 2.0}}
	calc.Update(model.Event{}, book, trades, feat)
	assert.InDelta(t, 0.2, feat.BuyBreakout, 0.001)

	// 追加一条成交:buyVolume 只应增加 1.0,而非重新累计全部
	trades = append(trades, model.Trade{Side: "BUY", Quantity: 1.0})
	calc.Update(model.Event{}, book, trades, feat)
	assert.InDelta(t, 0.3, feat.BuyBreakout, 0.001)
}
