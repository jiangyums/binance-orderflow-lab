package signal

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type Tracker struct {
	lastSide model.SignalSide
	emitFlat bool
}

func NewTracker(emitFlat bool) *Tracker {
	return &Tracker{
		lastSide: model.Flat,
		emitFlat: emitFlat,
	}
}

func (t *Tracker) Update(signal *model.Signal) *model.Signal {
	if signal.Side == t.lastSide {
		return nil
	}

	t.lastSide = signal.Side

	if signal.Side == model.Flat && !t.emitFlat {
		return nil
	}

	return signal
}

func (t *Tracker) Reset() {
	t.lastSide = model.Flat
}
