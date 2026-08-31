# Go Refactoring Design: binance-orderflow-lab

**Date:** 2026-08-31
**Status:** Approved
**Approach:** Go-Idiomatic Redesign (Option B)

---

## 1. Overview

Refactor the entire Python orderflow research laboratory to Go, using Go-idiomatic patterns:
- Interface-based design with composition
- Goroutine + Channel concurrency model
- Functional options pattern
- Table-driven tests with testify

### Goals
- Maintain feature parity with Python version
- Improve performance and resource efficiency
- Enable easier deployment (single binary)
- Support both CSV and Parquet output formats

### Constraints
- Go 1.21+
- Single Go module (`internal/` package structure)
- YAML configuration
- Preserve real-time signal evaluation

---

## 2. Project Structure

```
binance-orderflow-lab/
├── cmd/orderflow/
│   └── main.go                    # Entry point
├── internal/
│   ├── config/
│   │   └── config.go              # YAML config parsing
│   ├── model/
│   │   ├── orderbook.go           # OrderBook type
│   │   ├── signal.go              # Signal type
│   │   ├── feature.go             # Feature type
│   │   └── event.go               # Event type
│   ├── collector/
│   │   ├── depth.go               # L2 depth data collection
│   │   └── trade.go               # Trade data collection
│   ├── event/
│   │   ├── queue.go               # Event queue
│   │   └── processor.go           # Event dispatcher
│   ├── feature/
│   │   ├── calculator.go          # Calculator interface
│   │   ├── ofi.go                 # OFI calculation
│   │   ├── cvd.go                 # CVD calculation
│   │   ├── imbalance.go           # OBI calculation
│   │   ├── microprice.go          # MicroPrice calculation
│   │   └── taker_maker.go         # Taker/Maker ratio
│   ├── signal/
│   │   ├── generator.go           # Generator interface
│   │   ├── trade_ofi.go           # TradeOFI signal generation
│   │   └── tracker.go             # Signal state tracking
│   ├── engine/
│   │   └── engine.go              # Core engine coordinator
│   ├── evaluator/
│   │   └── evaluator.go           # Real-time P&L evaluation
│   ├── recorder/
│   │   ├── feature.go             # Feature CSV/Parquet recording
│   │   └── signal.go              # Signal CSV/Parquet recording
│   ├── monitor/
│   │   └── monitor.go             # Real-time statistics monitoring
│   └── validator/
│       └── stream.go              # Stream validator
├── pkg/
│   └── websocket/
│       └── client.go              # WebSocket client wrapper
├── configs/
│   └── default.yaml               # Default config
├── go.mod
└── go.sum
```

---

## 3. Core Types and Interfaces

### 3.1 Event Types

```go
// internal/model/event.go
type EventType int
const (
    BookUpdated EventType = iota
    TradeUpdated
    BookError
    TradeError
)

type Event struct {
    Type      EventType
    Timestamp int64
    Error     error
}
```

### 3.2 Signal Types

```go
// internal/model/signal.go
type SignalSide int
const (
    Long SignalSide = iota
    Short
    Flat
)

type Signal struct {
    Timestamp int64
    Side      SignalSide
    Strength  float64
    Reason    string
}
```

### 3.3 Feature Type

```go
// internal/model/feature.go
type Feature struct {
    Timestamp   int64
    Mid         float64
    Microprice  float64
    Spread      float64
    OBI1        float64
    OBI5        float64
    OBI10       float64
    OFI         float64
    TradeSide   string
    TradePrice  float64
    TradeQty    float64
    CVD         float64
    BidDepth    float64
    AskDepth    float64
    BuyBreakout float64
    SellBreakout float64
    TOFI        float64
}
```

### 3.4 OrderBook Type

```go
// internal/model/orderbook.go
type OrderBook struct {
    Bids         map[float64]float64
    Asks         map[float64]float64
    LastUpdateID int64
}
```

### 3.5 Interfaces

```go
// internal/feature/calculator.go
type Calculator interface {
    Update(event Event, book *OrderBook, trades []Trade) Feature
    Reset()
}

// internal/signal/generator.go
type Generator interface {
    Generate(feature Feature) *Signal
}

// internal/recorder/recorder.go
type Recorder interface {
    Write(feature Feature) error
    WriteSignal(signal Signal) error
    Close() error
}
```

---

## 4. Concurrency Model

### 4.1 Goroutine Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    main goroutine                        │
│                        │                                │
│                        ▼                                │
│              ┌─────────────────┐                        │
│              │   Engine.Run()  │                        │
│              └─────────────────┘                        │
│                        │                                │
│         ┌──────────────┼──────────────┐                 │
│         ▼              ▼              ▼                 │
│  ┌─────────────┐ ┌───────────┐ ┌──────────────┐        │
│  │depthWorker  │ │tradeWorker│ │eventProcessor│        │
│  │  goroutine  │ │ goroutine │ │  goroutine   │        │
│  └─────────────┘ └───────────┘ └──────────────┘        │
│         │              │              │                 │
│         └──────────────┼──────────────┘                 │
│                        ▼                                │
│              ┌─────────────────┐                        │
│              │   eventCh       │                        │
│              │  (chan Event)   │                        │
│              └─────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Shared State Protection

- **OrderBook**: Protected by `sync.RWMutex`
- **Trades slice**: Protected by `sync.Mutex`
- **Event channel**: Type-safe channel (no mutex needed)

### 4.3 Engine Core

```go
// internal/engine/engine.go
type Engine struct {
    eventCh      chan model.Event
    book         *model.OrderBook
    bookMu       sync.RWMutex
    trades       []model.Trade
    tradesMu     sync.Mutex
    calculators  []feature.Calculator
    generator    signal.Generator
    tracker      *signal.Tracker
    evaluators   []*evaluator.Evaluator
    recorders    []recorder.Recorder
    monitor      *monitor.Monitor
    validator    *validator.StreamValidator
    config       *config.Config
    logger       *slog.Logger
}

func (e *Engine) Run(ctx context.Context) error {
    ctx, cancel := context.WithCancel(ctx)
    defer cancel()

    g, ctx := errgroup.WithContext(ctx)

    g.Go(func() error {
        return collector.DepthWorker(ctx, e.config, e.book, e.bookMu, e.eventCh)
    })

    g.Go(func() error {
        return collector.TradeWorker(ctx, e.config, &e.trades, e.tradesMu, e.eventCh)
    })

    g.Go(func() error {
        return e.processEvents(ctx)
    })

    return g.Wait()
}
```

---

## 5. Module Details

### 5.1 Collector Module

**depth.go**: Implements two-phase synchronization protocol
- WebSocket consumer buffers events
- REST snapshot fetcher
- Buffer replay after sync
- Gap detection and reconnection

**trade.go**: Simple WebSocket consumer
- Parses trade messages
- Updates shared trades slice
- Emits trade events

### 5.2 Feature Module

| Calculator | Description |
|------------|-------------|
| OFI | Order Flow Imbalance at touch |
| CVD | Cumulative Volume Delta |
| OBI | Order Book Imbalance (1/5/10 levels) |
| MicroPrice | Volume-weighted mid price |
| TakerMaker | Taker buy/sell breakout ratios |

### 5.3 Signal Module

**TradeOFISignalGenerator**:
- Uses TOFI (CVD diff) as directional driver
- Threshold-based signal generation
- Strength = min(abs(tofi)/scale, 1.0)

**Tracker**:
- Deduplication filter
- Only emits on side changes
- Configurable flat emission

### 5.4 Recorder Module

Supports three output modes:
- `csv`: Legacy CSV format
- `parquet`: High-performance Parquet
- `both`: Simultaneous CSV + Parquet

### 5.5 Evaluator Module

Real-time P&L computation:
- Sliding window of recent prices
- Pending signal tracking
- Return computation at 1s, 5s, 10s horizons
- Output to evaluation CSV

### 5.6 Monitor Module

Live statistics:
- Signal counts by side
- Strength distribution
- Periodic reporting (configurable interval)

---

## 6. Configuration

```yaml
# configs/default.yaml
symbol: btcusdt

websocket:
  depth_url: wss://fstream.binance.com/ws/btcusdt@depth@100ms
  trade_url: wss://fstream.binance.com/ws/btcusdt@trade
  timeout_seconds: 30

rest:
  snapshot_url: https://fapi.binance.com/fapi/v1/depth
  time_url: https://fapi.binance.com/fapi/v1/time
  depth_limit: 1000

signal:
  tofi_threshold: 0.0
  tofi_scale: 1.0
  tofi_mode: linear

output:
  features: data/features.csv
  signals: data/signals.csv
  evaluation: data/evaluation.csv
  format: both  # csv, parquet, both

latency:
  max_ms: 1000
  gap_warn_ms: 3000

monitor:
  interval_seconds: 60
```

---

## 7. Error Handling

### Custom Error Types

```go
type OrderFlowError struct {
    Code    string
    Message string
    Cause   error
}

func NewGapError(expected, got int64) *OrderFlowError
func NewLatencyError(ts, now int64) *OrderFlowError
func NewConnectionError(url string, cause error) *OrderFlowError
```

### Retry Strategy

- Exponential backoff (3s initial)
- Context-aware cancellation
- Gap detection triggers full resync

---

## 8. Testing Strategy

### Unit Tests

- Table-driven tests for all calculators
- Mock WebSocket server for collectors
- Interface-based mocking

### Integration Tests

- End-to-end pipeline test
- Mock Binance API
- Verify output files

### Benchmarks

- Feature calculation performance
- Channel throughput
- Memory allocation profiling

---

## 9. Dependencies

```go
module github.com/jiangyums/binance-orderflow-lab

go 1.21

require (
    github.com/gorilla/websocket v1.5.1
    github.com/stretchr/testify v1.8.4
    gopkg.in/yaml.v3 v3.0.1
    github.com/parquet-go/parquet-go v0.20.0
    golang.org/x/sync v0.5.0
)
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Core Types + Config)
- Model types (Event, Signal, Feature, OrderBook)
- Config parsing
- Error types

### Phase 2: Data Collection
- WebSocket client wrapper
- Depth worker with sync protocol
- Trade worker

### Phase 3: Feature Computation
- Calculator interface
- OFI, CVD, OBI, MicroPrice, TakerMaker calculators

### Phase 4: Signal Generation
- Generator interface
- TradeOFISignal generator
- Signal tracker

### Phase 5: Output & Evaluation
- CSV/Parquet recorders
- Real-time evaluator
- Monitor

### Phase 6: Integration
- Engine coordinator
- Event processing pipeline
- Graceful shutdown

### Phase 7: Testing & Validation
- Unit tests for all modules
- Integration tests
- Benchmark tests
- Validation against Python output
