package feature

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestTradeOFICalculator_Update(t *testing.T) {
	t.Run("no trades yields zero tofi", func(t *testing.T) {
		calc := &TradeOFICalculator{}
		feat := &model.Feature{}
		calc.Update(model.Event{}, nil, nil, feat)
		assert.InDelta(t, 0.0, feat.TOFI, 0.001)
		assert.Empty(t, feat.TradeSide)
	})

	t.Run("single buy trade", func(t *testing.T) {
		calc := &TradeOFICalculator{}
		feat := &model.Feature{}
		trades := []model.Trade{{Side: "BUY", Price: 100.0, Quantity: 2.0}}
		calc.Update(model.Event{}, nil, trades, feat)
		assert.InDelta(t, 2.0, feat.TOFI, 0.001)
		assert.Equal(t, "BUY", feat.TradeSide)
		assert.InDelta(t, 100.0, feat.TradePrice, 0.001)
		assert.InDelta(t, 2.0, feat.TradeQty, 0.001)
	})

	t.Run("single sell trade", func(t *testing.T) {
		calc := &TradeOFICalculator{}
		feat := &model.Feature{}
		trades := []model.Trade{{Side: "SELL", Price: 99.0, Quantity: 3.0}}
		calc.Update(model.Event{}, nil, trades, feat)
		assert.InDelta(t, -3.0, feat.TOFI, 0.001)
		assert.Equal(t, "SELL", feat.TradeSide)
	})

	t.Run("mixed trades in one step", func(t *testing.T) {
		calc := &TradeOFICalculator{}
		feat := &model.Feature{}
		trades := []model.Trade{
			{Side: "BUY", Price: 100.0, Quantity: 5.0},
			{Side: "SELL", Price: 100.0, Quantity: 2.0},
		}
		calc.Update(model.Event{}, nil, trades, feat)
		assert.InDelta(t, 3.0, feat.TOFI, 0.001)
		// TradeSide/Price/Qty 记录本步最后一笔
		assert.Equal(t, "SELL", feat.TradeSide)
		assert.InDelta(t, 2.0, feat.TradeQty, 0.001)
	})
}

// 增量语义:同一 trades 切片多次 Update,TOFI 只反映新增部分(diff(cvd) 口径)。
func TestTradeOFICalculator_Incremental(t *testing.T) {
	calc := &TradeOFICalculator{}
	feat := &model.Feature{}

	trades := []model.Trade{{Side: "BUY", Quantity: 1.0}}
	calc.Update(model.Event{}, nil, trades, feat)
	assert.InDelta(t, 1.0, feat.TOFI, 0.001)

	// 深度事件:无新成交,TOFI 归零(与 Python diff(cvd) 一致)
	calc.Update(model.Event{}, nil, trades, feat)
	assert.InDelta(t, 0.0, feat.TOFI, 0.001)

	// 追加一笔卖单:TOFI 只反映这一笔
	trades = append(trades, model.Trade{Side: "SELL", Quantity: 0.5})
	calc.Update(model.Event{}, nil, trades, feat)
	assert.InDelta(t, -0.5, feat.TOFI, 0.001)
}
