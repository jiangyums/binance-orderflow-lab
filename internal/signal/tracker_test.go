package signal

import (
	"testing"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/stretchr/testify/assert"
)

func TestTracker_Update(t *testing.T) {
	tests := []struct {
		name         string
		emitFlat     bool
		lastSide     model.SignalSide
		inputSide    model.SignalSide
		expectNil    bool
		expectedSide model.SignalSide
	}{
		{
			name:         "same side - dedup",
			emitFlat:     false,
			lastSide:     model.Long,
			inputSide:    model.Long,
			expectNil:    true,
			expectedSide: model.Long,
		},
		{
			name:         "different side - emit",
			emitFlat:     false,
			lastSide:     model.Long,
			inputSide:    model.Short,
			expectNil:    false,
			expectedSide: model.Short,
		},
		{
			name:         "flat - no emit",
			emitFlat:     false,
			lastSide:     model.Long,
			inputSide:    model.Flat,
			expectNil:    true,
			expectedSide: model.Long,
		},
		{
			name:         "flat - emit",
			emitFlat:     true,
			lastSide:     model.Long,
			inputSide:    model.Flat,
			expectNil:    false,
			expectedSide: model.Flat,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tracker := &Tracker{
				lastSide: tt.lastSide,
				emitFlat: tt.emitFlat,
			}
			signal := &model.Signal{
				Side: tt.inputSide,
			}
			result := tracker.Update(signal)
			if tt.expectNil {
				assert.Nil(t, result)
			} else {
				assert.NotNil(t, result)
				assert.Equal(t, tt.expectedSide, result.Side)
			}
		})
	}
}
