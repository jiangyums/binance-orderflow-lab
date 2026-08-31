# OBI Calculator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Order Book Imbalance (OBI) calculator that computes the ratio of bid volume to ask volume across N levels.

**Architecture:** A calculator struct with a configurable `levels` field (1, 5, 10) that implements the existing `Calculator` interface. Uses `OrderBook.BidVolume()` and `AskVolume()` methods to compute OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol). Results are stored in `Feature.OBI1`, `OBI5`, `OBI10` accordingly.

**Tech Stack:** Go, testify/assert for testing.

---

## File Structure

- **Create:** `internal/feature/imbalance.go` – OBI calculator implementation.
- **Create:** `internal/feature/imbalance_test.go` – Table‑driven tests for OBI calculator.
- **No modifications** to existing files.

---

### Task 1: Implement OBI calculator with tests

**Files:**
- Create: `internal/feature/imbalance.go`
- Create: `internal/feature/imbalance_test.go`

- [ ] **Step 1: Write the failing test**

```go
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
			expected: 0.0, // (10-10)/(10+10) = 0
		},
		{
			name:   "bid heavy",
			levels: 1,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 15.0},
				Asks: map[float64]float64{101.0: 5.0},
			},
			expected: 0.5, // (15-5)/(15+5) = 0.5
		},
		{
			name:   "ask heavy",
			levels: 1,
			book: model.OrderBook{
				Bids: map[float64]float64{100.0: 5.0},
				Asks: map[float64]float64{101.0: 15.0},
			},
			expected: -0.5, // (5-15)/(5+15) = -0.5
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/feature/... -v -run TestOBICalculator`

Expected: FAIL with "undefined: OBICalculator"

- [ ] **Step 3: Write minimal implementation**

```go
package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type OBICalculator struct {
	levels int
}

func NewOBICalculator(levels int) *OBICalculator {
	return &OBICalculator{levels: levels}
}

func (c *OBICalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
	feature := model.Feature{Timestamp: event.Timestamp}

	bidVol := book.BidVolume(c.levels)
	askVol := book.AskVolume(c.levels)

	total := bidVol + askVol
	if total > 0 {
		obi := (bidVol - askVol) / total
		switch c.levels {
		case 1:
			feature.OBI1 = obi
		case 5:
			feature.OBI5 = obi
		case 10:
			feature.OBI10 = obi
		}
	}

	return feature
}

func (c *OBICalculator) Reset() {
	// No state to reset
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/feature/... -v -run TestOBICalculator`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/feature/imbalance.go internal/feature/imbalance_test.go
git commit -m "feat: add OBI calculator with tests"
```

---

## Notes

- The `OrderBook.BidVolume()` and `AskVolume()` methods iterate over unordered maps, so the "top N levels" is nondeterministic. This is a known limitation that will be addressed in a future task by sorting by price before truncating.
- The `OBICalculator` follows the same pattern as `OFICalculator` and `CVDCalculator`: implements the `Calculator` interface, uses constructor function, and resets state via `Reset()`.
- The test uses `assert.InDelta` with a tolerance of 0.001 for floating‑point comparison.