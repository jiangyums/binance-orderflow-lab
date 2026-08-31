package signal

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestTradeOFISignalGenerator_Generate(t *testing.T) {
	tests := []struct {
		name             string
		tofi             float64
		threshold        float64
		scale            float64
		expectedSide     model.SignalSide
		expectedStrength float64
	}{
		{
			name:             "below threshold",
			tofi:             0.001,
			threshold:        0.01,
			scale:            1.0,
			expectedSide:     model.Flat,
			expectedStrength: 0.0,
		},
		{
			name:             "positive tofi",
			tofi:             0.5,
			threshold:        0.0,
			scale:            1.0,
			expectedSide:     model.Long,
			expectedStrength: 0.5,
		},
		{
			name:             "negative tofi",
			tofi:             -0.3,
			threshold:        0.0,
			scale:            1.0,
			expectedSide:     model.Short,
			expectedStrength: 0.3,
		},
		{
			name:             "strength capped at 1.0",
			tofi:             2.0,
			threshold:        0.0,
			scale:            1.0,
			expectedSide:     model.Long,
			expectedStrength: 1.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gen := &TradeOFISignalGenerator{
				threshold: tt.threshold,
				scale:     tt.scale,
				mode:      "linear",
			}
			feature := model.Feature{TOFI: tt.tofi}
			signal := gen.Generate(feature)
			assert.Equal(t, tt.expectedSide, signal.Side)
			assert.InDelta(t, tt.expectedStrength, signal.Strength, 0.001)
		})
	}
}
