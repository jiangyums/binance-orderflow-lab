package signal

import (
	"fmt"
	"math"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
)

type TradeOFISignalGenerator struct {
	threshold float64
	scale     float64
	mode      string
}

func NewTradeOFISignalGenerator(threshold, scale float64, mode string) *TradeOFISignalGenerator {
	return &TradeOFISignalGenerator{
		threshold: threshold,
		scale:     scale,
		mode:      mode,
	}
}

func (g *TradeOFISignalGenerator) Generate(feature model.Feature) *model.Signal {
	// TOFI == 0 表示本步无新成交(深度事件),必须视为 Flat;
	// 否则 threshold=0 时每个深度事件都会产生虚假信号。
	if feature.TOFI == 0 || math.Abs(feature.TOFI) < g.threshold {
		return &model.Signal{
			Timestamp: feature.Timestamp,
			Side:      model.Flat,
			Strength:  0,
			Reason:    "below threshold",
		}
	}

	side := model.Long
	if feature.TOFI < 0 {
		side = model.Short
	}

	var strength float64
	if g.mode == "linear" {
		strength = math.Min(math.Abs(feature.TOFI)/g.scale, 1.0)
	}

	return &model.Signal{
		Timestamp: feature.Timestamp,
		Side:      side,
		Strength:  strength,
		Reason:    fmt.Sprintf("tofi=%.4f", feature.TOFI),
	}
}
