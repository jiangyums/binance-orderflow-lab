package monitor

import (
    "log"
    "time"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

type Monitor struct {
    counts    map[model.SignalSide]int
    strength  []float64
    interval  time.Duration
    lastReset time.Time
}

func NewMonitor(interval time.Duration) *Monitor {
    return &Monitor{
        counts:    make(map[model.SignalSide]int),
        strength:  make([]float64, 0),
        interval:  interval,
        lastReset: time.Now(),
    }
}

func (m *Monitor) Update(signal *model.Signal) {
    m.counts[signal.Side]++
    m.strength = append(m.strength, signal.Strength)

    if time.Since(m.lastReset) > m.interval {
        m.report()
        m.Reset()
    }
}

func (m *Monitor) report() {
    total := 0
    for _, count := range m.counts {
        total += count
    }

    var avgStrength float64
    if len(m.strength) > 0 {
        sum := 0.0
        for _, s := range m.strength {
            sum += s
        }
        avgStrength = sum / float64(len(m.strength))
    }

    log.Printf("signal statistics total=%d long=%d short=%d flat=%d avg_strength=%.4f",
        total, m.counts[model.Long], m.counts[model.Short], m.counts[model.Flat], avgStrength)
}

func (m *Monitor) Reset() {
    m.counts = make(map[model.SignalSide]int)
    m.strength = make([]float64, 0)
    m.lastReset = time.Now()
}