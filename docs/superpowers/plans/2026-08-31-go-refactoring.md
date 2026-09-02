# Go Refactoring Implementation Plan

> **SUPERSEDED on 2026-09-02**：本项目方向已转向 **Rust + hftbacktest** 方案，本计划作废。
> 请参见 `specs/2026-09-02-orderflow-indicator-research-design.md`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Python orderflow research laboratory to Go with idiomatic patterns, maintaining feature parity and improving performance.

**Architecture:** Goroutine + Channel concurrency model with interface-based design. Each component (collector, feature, signal, recorder) implements well-defined interfaces. The engine coordinates all components via event channels.

**Tech Stack:** Go 1.21+, gorilla/websocket, testify, yaml.v3, parquet-go, log/slog

---

## Task 1: Initialize Go Module and Project Structure

**Files:**
- Create: `go.mod`
- Create: `go.sum`
- Create: `internal/config/config.go`
- Create: `internal/model/event.go`
- Create: `internal/model/signal.go`
- Create: `internal/model/feature.go`
- Create: `internal/model/orderbook.go`
- Create: `configs/default.yaml`

- [ ] **Step 1: Initialize Go module**

Run: `go mod init github.com/jiangyums/binance-orderflow-lab`

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p cmd/orderflow
mkdir -p internal/config
mkdir -p internal/model
mkdir -p internal/collector
mkdir -p internal/event
mkdir -p internal/feature
mkdir -p internal/signal
mkdir -p internal/engine
mkdir -p internal/evaluator
mkdir -p internal/recorder
mkdir -p internal/monitor
mkdir -p internal/validator
mkdir -p pkg/websocket
mkdir -p configs
```

- [ ] **Step 3: Create event types**

```go
// internal/model/event.go
package model

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

- [ ] **Step 4: Create signal types**

```go
// internal/model/signal.go
package model

type SignalSide int

const (
    Long SignalSide = iota
    Short
    Flat
)

func (s SignalSide) String() string {
    switch s {
    case Long:
        return "LONG"
    case Short:
        return "SHORT"
    case Flat:
        return "FLAT"
    default:
        return "UNKNOWN"
    }
}

type Signal struct {
    Timestamp int64
    Side      SignalSide
    Strength  float64
    Reason    string
}
```

- [ ] **Step 5: Create feature type**

```go
// internal/model/feature.go
package model

type Feature struct {
    Timestamp    int64
    Mid          float64
    Microprice   float64
    Spread       float64
    OBI1         float64
    OBI5         float64
    OBI10        float64
    OFI          float64
    TradeSide    string
    TradePrice   float64
    TradeQty     float64
    CVD          float64
    BidDepth     float64
    AskDepth     float64
    BuyBreakout  float64
    SellBreakout float64
    TOFI         float64
}
```

- [ ] **Step 6: Create OrderBook type**

```go
// internal/model/orderbook.go
package model

import "sync"

type OrderBook struct {
    Bids         map[float64]float64
    Asks         map[float64]float64
    LastUpdateID int64
    mu           sync.RWMutex
}

func NewOrderBook() *OrderBook {
    return &OrderBook{
        Bids: make(map[float64]float64),
        Asks: make(map[float64]float64),
    }
}

func (ob *OrderBook) Reset() {
    ob.mu.Lock()
    defer ob.mu.Unlock()
    ob.Bids = make(map[float64]float64)
    ob.Asks = make(map[float64]float64)
    ob.LastUpdateID = 0
}

func (ob *OrderBook) BestBid() (float64, float64, bool) {
    ob.mu.RLock()
    defer ob.mu.RUnlock()
    
    var bestPrice float64
    var bestQty float64
    found := false
    
    for price, qty := range ob.Bids {
        if !found || price > bestPrice {
            bestPrice = price
            bestQty = qty
            found = true
        }
    }
    return bestPrice, bestQty, found
}

func (ob *OrderBook) BestAsk() (float64, float64, bool) {
    ob.mu.RLock()
    defer ob.mu.RUnlock()
    
    var bestPrice float64
    var bestQty float64
    found := false
    
    for price, qty := range ob.Asks {
        if !found || price < bestPrice {
            bestPrice = price
            bestQty = qty
            found = true
        }
    }
    return bestPrice, bestQty, found
}

func (ob *OrderBook) MidPrice() float64 {
    bid, _, _ := ob.BestBid()
    ask, _, _ := ob.BestAsk()
    if bid == 0 || ask == 0 {
        return 0
    }
    return (bid + ask) / 2
}

func (ob *OrderBook) Spread() float64 {
    bid, _, _ := ob.BestBid()
    ask, _, _ := ob.BestAsk()
    return ask - bid
}

func (ob *OrderBook) BidVolume(levels int) float64 {
    ob.mu.RLock()
    defer ob.mu.RUnlock()
    
    var total float64
    count := 0
    for _, qty := range ob.Bids {
        total += qty
        count++
        if count >= levels {
            break
        }
    }
    return total
}

func (ob *OrderBook) AskVolume(levels int) float64 {
    ob.mu.RLock()
    defer ob.mu.RUnlock()
    
    var total float64
    count := 0
    for _, qty := range ob.Asks {
        total += qty
        count++
        if count >= levels {
            break
        }
    }
    return total
}
```

- [ ] **Step 7: Create config types**

```go
// internal/config/config.go
package config

import (
    "os"
    "gopkg.in/yaml.v3"
)

type Config struct {
    Symbol    string        `yaml:"symbol"`
    WebSocket WebSocketCfg  `yaml:"websocket"`
    REST      RESTCfg       `yaml:"rest"`
    Signal    SignalCfg     `yaml:"signal"`
    Output    OutputCfg     `yaml:"output"`
    Latency   LatencyCfg    `yaml:"latency"`
    Monitor   MonitorCfg    `yaml:"monitor"`
}

type WebSocketCfg struct {
    DepthURL string `yaml:"depth_url"`
    TradeURL string `yaml:"trade_url"`
    Timeout  int    `yaml:"timeout_seconds"`
}

type RESTCfg struct {
    SnapshotURL string `yaml:"snapshot_url"`
    TimeURL     string `yaml:"time_url"`
    DepthLimit  int    `yaml:"depth_limit"`
}

type SignalCfg struct {
    TOFIThreshold float64 `yaml:"tofi_threshold"`
    TOFIScale     float64 `yaml:"tofi_scale"`
    TOFIMode      string  `yaml:"tofi_mode"`
}

type OutputCfg struct {
    Features   string `yaml:"features"`
    Signals    string `yaml:"signals"`
    Evaluation string `yaml:"evaluation"`
    Format     string `yaml:"format"`
}

type LatencyCfg struct {
    MaxMS     int64 `yaml:"max_ms"`
    GapWarnMS int64 `yaml:"gap_warn_ms"`
}

type MonitorCfg struct {
    IntervalSeconds int `yaml:"interval_seconds"`
}

func Load(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }

    cfg := &Config{}
    if err := yaml.Unmarshal(data, cfg); err != nil {
        return nil, err
    }

    // Set defaults
    if cfg.Symbol == "" {
        cfg.Symbol = "btcusdt"
    }
    if cfg.WebSocket.Timeout == 0 {
        cfg.WebSocket.Timeout = 30
    }
    if cfg.REST.DepthLimit == 0 {
        cfg.REST.DepthLimit = 1000
    }
    if cfg.Signal.TOFIScale == 0 {
        cfg.Signal.TOFIScale = 1.0
    }
    if cfg.Signal.TOFIMode == "" {
        cfg.Signal.TOFIMode = "linear"
    }
    if cfg.Output.Format == "" {
        cfg.Output.Format = "csv"
    }
    if cfg.Latency.MaxMS == 0 {
        cfg.Latency.MaxMS = 1000
    }
    if cfg.Latency.GapWarnMS == 0 {
        cfg.Latency.GapWarnMS = 3000
    }
    if cfg.Monitor.IntervalSeconds == 0 {
        cfg.Monitor.IntervalSeconds = 60
    }

    return cfg, nil
}
```

- [ ] **Step 8: Create default config**

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
  format: both

latency:
  max_ms: 1000
  gap_warn_ms: 3000

monitor:
  interval_seconds: 60
```

- [ ] **Step 9: Run tests to verify structure**

Run: `go build ./...`
Expected: No errors

- [ ] **Step 10: Commit**

```bash
git add go.mod go.sum internal/ configs/
git commit -m "feat: initialize Go module and core types"
```

---

## Task 2: Implement Error Types

**Files:**
- Create: `internal/model/errors.go`

- [ ] **Step 1: Create error types**

```go
// internal/model/errors.go
package model

import "fmt"

type OrderFlowError struct {
    Code    string
    Message string
    Cause   error
}

func (e *OrderFlowError) Error() string {
    if e.Cause != nil {
        return fmt.Sprintf("%s: %s: %v", e.Code, e.Message, e.Cause)
    }
    return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *OrderFlowError) Unwrap() error {
    return e.Cause
}

func NewGapError(expected, got int64) *OrderFlowError {
    return &OrderFlowError{
        Code:    "GAP_DETECTED",
        Message: fmt.Sprintf("expected update %d, got %d", expected, got),
    }
}

func NewLatencyError(ts, now int64) *OrderFlowError {
    return &OrderFlowError{
        Code:    "HIGH_LATENCY",
        Message: fmt.Sprintf("event age %dms exceeds threshold", now-ts),
    }
}

func NewConnectionError(url string, cause error) *OrderFlowError {
    return &OrderFlowError{
        Code:    "CONNECTION_ERROR",
        Message: fmt.Sprintf("failed to connect to %s", url),
        Cause:   cause,
    }
}

func NewSyncError(message string) *OrderFlowError {
    return &OrderFlowError{
        Code:    "SYNC_ERROR",
        Message: message,
    }
}
```

- [ ] **Step 2: Run tests**

Run: `go build ./...`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add internal/model/errors.go
git commit -m "feat: add error types"
```

---

## Task 3: Implement WebSocket Client Wrapper

**Files:**
- Create: `pkg/websocket/client.go`

- [ ] **Step 1: Create WebSocket client**

```go
// pkg/websocket/client.go
package websocket

import (
    "context"
    "net/http"
    "time"

    "github.com/gorilla/websocket"
)

type Client struct {
    conn    *websocket.Conn
    url     string
    timeout time.Duration
}

func NewClient(url string, timeoutSeconds int) *Client {
    return &Client{
        url:     url,
        timeout: time.Duration(timeoutSeconds) * time.Second,
    }
}

func (c *Client) Connect(ctx context.Context) error {
    dialer := websocket.Dialer{
        HandshakeTimeout: c.timeout,
    }

    conn, _, err := dialer.DialContext(ctx, c.url, http.Header{})
    if err != nil {
        return err
    }

    c.conn = conn
    return nil
}

func (c *Client) ReadMessage(ctx context.Context) ([]byte, error) {
    if c.conn == nil {
        return nil, websocket.ErrCloseSent
    }

    // Set read deadline
    c.conn.SetReadDeadline(time.Now().Add(c.timeout))

    // Create channel for message
    msgCh := make(chan []byte, 1)
    errCh := make(chan error, 1)

    go func() {
        _, msg, err := c.conn.ReadMessage()
        if err != nil {
            errCh <- err
            return
        }
        msgCh <- msg
    }()

    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    case err := <-errCh:
        return nil, err
    case msg := <-msgCh:
        return msg, nil
    }
}

func (c *Client) Close() error {
    if c.conn != nil {
        return c.conn.Close()
    }
    return nil
}

func (c *Client) IsConnected() bool {
    return c.conn != nil
}
```

- [ ] **Step 2: Run tests**

Run: `go build ./...`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add pkg/websocket/
git commit -m "feat: add WebSocket client wrapper"
```

---

## Task 4: Implement Feature Calculator Interface and OFI Calculator

**Files:**
- Create: `internal/feature/calculator.go`
- Create: `internal/feature/ofi.go`
- Create: `internal/feature/ofi_test.go`

- [ ] **Step 1: Write failing test for OFI calculator**

```go
// internal/feature/ofi_test.go
package feature

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestOFICalculator_Update(t *testing.T) {
    tests := []struct {
        name         string
        lastBidPrice float64
        lastBidQty   float64
        lastAskPrice float64
        lastAskQty   float64
        book         model.OrderBook
        expected     float64
    }{
        {
            name:         "bid size increase",
            lastBidPrice: 100.0,
            lastBidQty:   10.0,
            lastAskPrice: 101.0,
            lastAskQty:   5.0,
            book: model.OrderBook{
                Bids: map[float64]float64{100.0: 15.0},
                Asks: map[float64]float64{101.0: 5.0},
            },
            expected: 5.0, // 15 - 10 = 5
        },
        {
            name:         "ask size increase",
            lastBidPrice: 100.0,
            lastBidQty:   10.0,
            lastAskPrice: 101.0,
            lastAskQty:   5.0,
            book: model.OrderBook{
                Bids: map[float64]float64{100.0: 10.0},
                Asks: map[float64]float64{101.0: 10.0},
            },
            expected: -5.0, // -(10 - 5) = -5
        },
        {
            name:         "bid price increase",
            lastBidPrice: 100.0,
            lastBidQty:   10.0,
            lastAskPrice: 101.0,
            lastAskQty:   5.0,
            book: model.OrderBook{
                Bids: map[float64]float64{102.0: 8.0},
                Asks: map[float64]float64{101.0: 5.0},
            },
            expected: 8.0, // new bid at higher price
        },
        {
            name:         "ask price decrease",
            lastBidPrice: 100.0,
            lastBidQty:   10.0,
            lastAskPrice: 101.0,
            lastAskQty:   5.0,
            book: model.OrderBook{
                Bids: map[float64]float64{100.0: 10.0},
                Asks: map[float64]float64{99.0: 7.0},
            },
            expected: -7.0, // new ask at lower price
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            calc := &OFICalculator{
                lastBidPrice: tt.lastBidPrice,
                lastBidQty:   tt.lastBidQty,
                lastAskPrice: tt.lastAskPrice,
                lastAskQty:   tt.lastAskQty,
            }
            feature := calc.Update(model.Event{}, &tt.book, nil)
            assert.InDelta(t, tt.expected, feature.OFI, 0.001)
        })
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/feature/... -v -run TestOFICalculator`
Expected: FAIL with "undefined: OFICalculator"

- [ ] **Step 3: Create calculator interface**

```go
// internal/feature/calculator.go
package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type Calculator interface {
    Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature
    Reset()
}
```

- [ ] **Step 4: Implement OFI calculator**

```go
// internal/feature/ofi.go
package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type OFICalculator struct {
    lastBidPrice float64
    lastBidQty   float64
    lastAskPrice float64
    lastAskQty   float64
}

func NewOFICalculator() *OFICalculator {
    return &OFICalculator{}
}

func (c *OFICalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
    feature := model.Feature{Timestamp: event.Timestamp}

    bidPrice, bidQty, bidOk := book.BestBid()
    askPrice, askQty, askOk := book.BestAsk()

    if !bidOk || !askOk {
        return feature
    }

    feature.Mid = (bidPrice + askPrice) / 2
    feature.Spread = askPrice - bidPrice
    feature.BidDepth = bidQty
    feature.AskDepth = askQty

    // Calculate OFI
    var ofi float64

    if c.lastBidPrice == 0 && c.lastAskPrice == 0 {
        // First update, no OFI
        ofi = 0
    } else if bidPrice > c.lastBidPrice {
        // Bid price increased, add new bid qty
        ofi = bidQty
    } else if bidPrice < c.lastBidPrice {
        // Bid price decreased, subtract old bid qty
        ofi = -c.lastBidQty
    } else {
        // Bid price same, check qty change
        ofi = bidQty - c.lastBidQty
    }

    if c.lastAskPrice == 0 {
        // No previous ask
    } else if askPrice < c.lastAskPrice {
        // Ask price decreased, add new ask qty
        ofi -= askQty
    } else if askPrice > c.lastAskPrice {
        // Ask price increased, subtract old ask qty
        ofi += c.lastAskQty
    } else {
        // Ask price same, check qty change
        ofi -= (askQty - c.lastAskQty)
    }

    feature.OFI = ofi

    // Update state
    c.lastBidPrice = bidPrice
    c.lastBidQty = bidQty
    c.lastAskPrice = askPrice
    c.lastAskQty = askQty

    return feature
}

func (c *OFICalculator) Reset() {
    c.lastBidPrice = 0
    c.lastBidQty = 0
    c.lastAskPrice = 0
    c.lastAskQty = 0
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `go test ./internal/feature/... -v -run TestOFICalculator`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add internal/feature/
git commit -m "feat: add OFI calculator with tests"
```

---

## Task 5: Implement CVD Calculator

**Files:**
- Create: `internal/feature/cvd.go`
- Create: `internal/feature/cvd_test.go`

- [ ] **Step 1: Write failing test for CVD calculator**

```go
// internal/feature/cvd_test.go
package feature

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
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
                {Side: "BUY", Qty: 1.0},
            },
            expected: 1.0,
        },
        {
            name: "sell trade",
            trades: []model.Trade{
                {Side: "SELL", Qty: 2.0},
            },
            expected: -2.0,
        },
        {
            name: "mixed trades",
            trades: []model.Trade{
                {Side: "BUY", Qty: 3.0},
                {Side: "SELL", Qty: 1.0},
            },
            expected: 2.0,
        },
        {
            name: "no trades",
            trades: []model.Trade{},
            expected: 0.0,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            calc := &CVDCalculator{}
            feature := calc.Update(model.Event{}, nil, tt.trades)
            assert.InDelta(t, tt.expected, feature.CVD, 0.001)
        })
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/feature/... -v -run TestCVDCalculator`
Expected: FAIL with "undefined: CVDCalculator"

- [ ] **Step 3: Implement CVD calculator**

```go
// internal/feature/cvd.go
package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type CVDCalculator struct {
    value float64
}

func NewCVDCalculator() *CVDCalculator {
    return &CVDCalculator{}
}

func (c *CVDCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
    feature := model.Feature{Timestamp: event.Timestamp}

    for _, trade := range trades {
        if trade.Side == "BUY" {
            c.value += trade.Qty
        } else if trade.Side == "SELL" {
            c.value -= trade.Qty
        }
    }

    feature.CVD = c.value
    return feature
}

func (c *CVDCalculator) Reset() {
    c.value = 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/feature/... -v -run TestCVDCalculator`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/feature/cvd.go internal/feature/cvd_test.go
git commit -m "feat: add CVD calculator with tests"
```

---

## Task 6: Implement OBI Calculator

**Files:**
- Create: `internal/feature/imbalance.go`
- Create: `internal/feature/imbalance_test.go`

- [ ] **Step 1: Write failing test for OBI calculator**

```go
// internal/feature/imbalance_test.go
package feature

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
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

- [ ] **Step 3: Implement OBI calculator**

```go
// internal/feature/imbalance.go
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

## Task 7: Implement MicroPrice Calculator

**Files:**
- Create: `internal/feature/microprice.go`
- Create: `internal/feature/microprice_test.go`

- [ ] **Step 1: Write failing test for MicroPrice calculator**

```go
// internal/feature/microprice_test.go
package feature

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestMicroPriceCalculator_Update(t *testing.T) {
    tests := []struct {
        name     string
        book     model.OrderBook
        expected float64
    }{
        {
            name: "balanced",
            book: model.OrderBook{
                Bids: map[float64]float64{100.0: 10.0},
                Asks: map[float64]float64{101.0: 10.0},
            },
            expected: 100.5, // (101*10 + 100*10) / (10+10) = 100.5
        },
        {
            name: "bid heavy",
            book: model.OrderBook{
                Bids: map[float64]float64{100.0: 20.0},
                Asks: map[float64]float64{101.0: 10.0},
            },
            expected: 100.333, // (101*20 + 100*10) / (20+10) = 100.333
        },
        {
            name: "ask heavy",
            book: model.OrderBook{
                Bids: map[float64]float64{100.0: 10.0},
                Asks: map[float64]float64{101.0: 20.0},
            },
            expected: 100.667, // (101*10 + 100*20) / (10+20) = 100.667
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            calc := &MicroPriceCalculator{}
            feature := calc.Update(model.Event{}, &tt.book, nil)
            assert.InDelta(t, tt.expected, feature.Microprice, 0.001)
        })
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/feature/... -v -run TestMicroPriceCalculator`
Expected: FAIL with "undefined: MicroPriceCalculator"

- [ ] **Step 3: Implement MicroPrice calculator**

```go
// internal/feature/microprice.go
package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type MicroPriceCalculator struct{}

func NewMicroPriceCalculator() *MicroPriceCalculator {
    return &MicroPriceCalculator{}
}

func (c *MicroPriceCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
    feature := model.Feature{Timestamp: event.Timestamp}

    bidPrice, bidQty, bidOk := book.BestBid()
    askPrice, askQty, askOk := book.BestAsk()

    if !bidOk || !askOk {
        return feature
    }

    total := bidQty + askQty
    if total > 0 {
        feature.Microprice = (askPrice*bidQty + bidPrice*askQty) / total
    }

    feature.Mid = (bidPrice + askPrice) / 2
    feature.Spread = askPrice - bidPrice
    feature.BidDepth = bidQty
    feature.AskDepth = askQty

    return feature
}

func (c *MicroPriceCalculator) Reset() {
    // No state to reset
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/feature/... -v -run TestMicroPriceCalculator`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/feature/microprice.go internal/feature/microprice_test.go
git commit -m "feat: add MicroPrice calculator with tests"
```

---

## Task 8: Implement TakerMaker Calculator

**Files:**
- Create: `internal/feature/taker_maker.go`
- Create: `internal/feature/taker_maker_test.go`

- [ ] **Step 1: Write failing test for TakerMaker calculator**

```go
// internal/feature/taker_maker_test.go
package feature

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestTakerMakerCalculator_Update(t *testing.T) {
    tests := []struct {
        name            string
        trades          []model.Trade
        askDepth        float64
        bidDepth        float64
        expectedBuy     float64
        expectedSell    float64
    }{
        {
            name: "buy trade with ask depth",
            trades: []model.Trade{
                {Side: "BUY", Qty: 5.0},
            },
            askDepth:     10.0,
            bidDepth:     10.0,
            expectedBuy:  0.5, // 5/10
            expectedSell: 0.0,
        },
        {
            name: "sell trade with bid depth",
            trades: []model.Trade{
                {Side: "SELL", Qty: 3.0},
            },
            askDepth:     10.0,
            bidDepth:     10.0,
            expectedBuy:  0.0,
            expectedSell: 0.3, // 3/10
        },
        {
            name: "mixed trades",
            trades: []model.Trade{
                {Side: "BUY", Qty: 2.0},
                {Side: "SELL", Qty: 4.0},
            },
            askDepth:     10.0,
            bidDepth:     10.0,
            expectedBuy:  0.2, // 2/10
            expectedSell: 0.4, // 4/10
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            calc := &TakerMakerCalculator{}
            book := &model.OrderBook{
                Bids: map[float64]float64{100.0: tt.bidDepth},
                Asks: map[float64]float64{101.0: tt.askDepth},
            }
            feature := calc.Update(model.Event{}, book, tt.trades)
            assert.InDelta(t, tt.expectedBuy, feature.BuyBreakout, 0.001)
            assert.InDelta(t, tt.expectedSell, feature.SellBreakout, 0.001)
        })
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/feature/... -v -run TestTakerMakerCalculator`
Expected: FAIL with "undefined: TakerMakerCalculator"

- [ ] **Step 3: Implement TakerMaker calculator**

```go
// internal/feature/taker_maker.go
package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type TakerMakerCalculator struct {
    buyVolume  float64
    sellVolume float64
}

func NewTakerMakerCalculator() *TakerMakerCalculator {
    return &TakerMakerCalculator{}
}

func (c *TakerMakerCalculator) Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature {
    feature := model.Feature{Timestamp: event.Timestamp}

    // Accumulate trade volumes
    for _, trade := range trades {
        if trade.Side == "BUY" {
            c.buyVolume += trade.Qty
        } else if trade.Side == "SELL" {
            c.sellVolume += trade.Qty
        }
    }

    // Calculate breakout ratios
    _, askQty, askOk := book.BestAsk()
    _, bidQty, bidOk := book.BestBid()

    if askOk && askQty > 0 {
        feature.BuyBreakout = c.buyVolume / askQty
    }
    if bidOk && bidQty > 0 {
        feature.SellBreakout = c.sellVolume / bidQty
    }

    return feature
}

func (c *TakerMakerCalculator) Reset() {
    c.buyVolume = 0
    c.sellVolume = 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/feature/... -v -run TestTakerMakerCalculator`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/feature/taker_maker.go internal/feature/taker_maker_test.go
git commit -m "feat: add TakerMaker calculator with tests"
```

---

## Task 9: Implement Signal Generator Interface and TradeOFI Generator

**Files:**
- Create: `internal/signal/generator.go`
- Create: `internal/signal/trade_ofi.go`
- Create: `internal/signal/trade_ofi_test.go`

- [ ] **Step 1: Write failing test for TradeOFI generator**

```go
// internal/signal/trade_ofi_test.go
package signal

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestTradeOFISignalGenerator_Generate(t *testing.T) {
    tests := []struct {
        name           string
        tofi           float64
        threshold      float64
        scale          float64
        expectedSide   model.SignalSide
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/signal/... -v -run TestTradeOFISignalGenerator`
Expected: FAIL with "undefined: TradeOFISignalGenerator"

- [ ] **Step 3: Create generator interface**

```go
// internal/signal/generator.go
package signal

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type Generator interface {
    Generate(feature model.Feature) *model.Signal
}
```

- [ ] **Step 4: Implement TradeOFI generator**

```go
// internal/signal/trade_ofi.go
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
    if math.Abs(feature.TOFI) < g.threshold {
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `go test ./internal/signal/... -v -run TestTradeOFISignalGenerator`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add internal/signal/
git commit -m "feat: add TradeOFI signal generator with tests"
```

---

## Task 10: Implement Signal Tracker

**Files:**
- Create: `internal/signal/tracker.go`
- Create: `internal/signal/tracker_test.go`

- [ ] **Step 1: Write failing test for signal tracker**

```go
// internal/signal/tracker_test.go
package signal

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/signal/... -v -run TestTracker`
Expected: FAIL with "undefined: Tracker"

- [ ] **Step 3: Implement signal tracker**

```go
// internal/signal/tracker.go
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/signal/... -v -run TestTracker`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/signal/tracker.go internal/signal/tracker_test.go
git commit -m "feat: add signal tracker with tests"
```

---

## Task 11: Implement Stream Validator

**Files:**
- Create: `internal/validator/stream.go`
- Create: `internal/validator/stream_test.go`

- [ ] **Step 1: Write failing test for stream validator**

```go
// internal/validator/stream_test.go
package validator

import (
    "testing"
    "github.com/stretchr/testify/assert"
)

func TestStreamValidator_Check(t *testing.T) {
    tests := []struct {
        name        string
        gapWarnMS   int64
        lastTS      int64
        currentTS   int64
        expectError bool
    }{
        {
            name:        "normal interval",
            gapWarnMS:   3000,
            lastTS:      1000,
            currentTS:   1100,
            expectError: false,
        },
        {
            name:        "backward timestamp",
            gapWarnMS:   3000,
            lastTS:      1000,
            currentTS:   900,
            expectError: true,
        },
        {
            name:        "large gap",
            gapWarnMS:   3000,
            lastTS:      1000,
            currentTS:   5000,
            expectError: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            v := NewStreamValidator("depth", tt.gapWarnMS, 100)
            v.lastTimestamp = tt.lastTS
            err := v.Check(tt.currentTS)
            if tt.expectError {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/validator/... -v -run TestStreamValidator`
Expected: FAIL with "undefined: StreamValidator"

- [ ] **Step 3: Implement stream validator**

```go
// internal/validator/stream.go
package validator

import (
    "fmt"
    "log/slog"
)

type StreamValidator struct {
    streamType   string
    gapWarnMS    int64
    reportEvery  int
    eventCount   int
    lastTimestamp int64
    logger       *slog.Logger
}

func NewStreamValidator(streamType string, gapWarnMS int64, reportEvery int) *StreamValidator {
    return &StreamValidator{
        streamType:  streamType,
        gapWarnMS:   gapWarnMS,
        reportEvery: reportEvery,
        logger:      slog.Default(),
    }
}

func (v *StreamValidator) Check(timestamp int64) error {
    v.eventCount++

    if v.lastTimestamp > 0 {
        if timestamp < v.lastTimestamp {
            return fmt.Errorf("backward timestamp: %d < %d", timestamp, v.lastTimestamp)
        }
        if timestamp-v.lastTimestamp > v.gapWarnMS {
            return fmt.Errorf("large gap: %dms between events", timestamp-v.lastTimestamp)
        }
    }

    v.lastTimestamp = timestamp

    if v.eventCount%v.reportEvery == 0 {
        v.logger.Info("stream stats",
            "stream", v.streamType,
            "events", v.eventCount,
        )
    }

    return nil
}

func (v *StreamValidator) Reset() {
    v.lastTimestamp = 0
    v.eventCount = 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/validator/... -v -run TestStreamValidator`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/validator/
git commit -m "feat: add stream validator with tests"
```

---

## Task 12: Implement Feature Recorder

**Files:**
- Create: `internal/recorder/recorder.go`
- Create: `internal/recorder/feature.go`
- Create: `internal/recorder/feature_test.go`

- [ ] **Step 1: Write failing test for feature recorder**

```go
// internal/recorder/feature_test.go
package recorder

import (
    "os"
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestFeatureRecorder_Write(t *testing.T) {
    // Create temp file
    tmpFile, err := os.CreateTemp("", "features-*.csv")
    assert.NoError(t, err)
    defer os.Remove(tmpFile.Name())
    tmpFile.Close()

    // Create recorder
    rec, err := NewFeatureRecorder(tmpFile.Name(), "csv")
    assert.NoError(t, err)
    defer rec.Close()

    // Write feature
    feature := model.Feature{
        Timestamp: 1234567890,
        Mid:       100.5,
        Microprice: 100.45,
        Spread:    0.1,
        OBI1:      0.2,
        OBI5:      0.1,
        OBI10:     0.05,
        OFI:       0.3,
        CVD:       1.5,
        TOFI:      0.25,
    }

    err = rec.Write(feature)
    assert.NoError(t, err)

    // Read file and verify
    content, err := os.ReadFile(tmpFile.Name())
    assert.NoError(t, err)
    assert.Contains(t, string(content), "1234567890")
    assert.Contains(t, string(content), "100.5")
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/recorder/... -v -run TestFeatureRecorder`
Expected: FAIL with "undefined: FeatureRecorder"

- [ ] **Step 3: Create recorder interface**

```go
// internal/recorder/recorder.go
package recorder

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type Recorder interface {
    Write(feature model.Feature) error
    WriteSignal(signal model.Signal) error
    Close() error
}
```

- [ ] **Step 4: Implement feature recorder**

```go
// internal/recorder/feature.go
package recorder

import (
    "encoding/csv"
    "fmt"
    "os"
    "strconv"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

type FeatureRecorder struct {
    file    *os.File
    writer  *csv.Writer
    format  string
    header  bool
}

func NewFeatureRecorder(path, format string) (*FeatureRecorder, error) {
    file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    if err != nil {
        return nil, err
    }

    return &FeatureRecorder{
        file:   file,
        writer: csv.NewWriter(file),
        format: format,
    }, nil
}

func (r *FeatureRecorder) Write(feature model.Feature) error {
    if !r.header {
        if err := r.writeHeader(); err != nil {
            return err
        }
        r.header = true
    }

    record := []string{
        strconv.FormatInt(feature.Timestamp, 10),
        fmt.Sprintf("%f", feature.Mid),
        fmt.Sprintf("%f", feature.Microprice),
        fmt.Sprintf("%f", feature.Spread),
        fmt.Sprintf("%f", feature.OBI1),
        fmt.Sprintf("%f", feature.OBI5),
        fmt.Sprintf("%f", feature.OBI10),
        fmt.Sprintf("%f", feature.OFI),
        feature.TradeSide,
        fmt.Sprintf("%f", feature.TradePrice),
        fmt.Sprintf("%f", feature.TradeQty),
        fmt.Sprintf("%f", feature.CVD),
        fmt.Sprintf("%f", feature.BidDepth),
        fmt.Sprintf("%f", feature.AskDepth),
        fmt.Sprintf("%f", feature.BuyBreakout),
        fmt.Sprintf("%f", feature.SellBreakout),
        fmt.Sprintf("%f", feature.TOFI),
    }

    return r.writer.Write(record)
}

func (r *FeatureRecorder) writeHeader() error {
    header := []string{
        "timestamp", "mid", "microprice", "spread",
        "obi1", "obi5", "obi10", "ofi",
        "trade_side", "trade_price", "trade_qty", "cvd",
        "bid_depth", "ask_depth", "buy_breakout", "sell_breakout", "tofi",
    }
    return r.writer.Write(header)
}

func (r *FeatureRecorder) WriteSignal(signal model.Signal) error {
    // Not implemented for feature recorder
    return nil
}

func (r *FeatureRecorder) Close() error {
    r.writer.Flush()
    return r.file.Close()
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `go test ./internal/recorder/... -v -run TestFeatureRecorder`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add internal/recorder/
git commit -m "feat: add feature recorder with tests"
```

---

## Task 13: Implement Signal Recorder

**Files:**
- Create: `internal/recorder/signal.go`
- Create: `internal/recorder/signal_test.go`

- [ ] **Step 1: Write failing test for signal recorder**

```go
// internal/recorder/signal_test.go
package recorder

import (
    "os"
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestSignalRecorder_Write(t *testing.T) {
    // Create temp file
    tmpFile, err := os.CreateTemp("", "signals-*.csv")
    assert.NoError(t, err)
    defer os.Remove(tmpFile.Name())
    tmpFile.Close()

    // Create recorder
    rec, err := NewSignalRecorder(tmpFile.Name())
    assert.NoError(t, err)
    defer rec.Close()

    // Write signal
    signal := model.Signal{
        Timestamp: 1234567890,
        Side:      model.Long,
        Strength:  0.75,
        Reason:    "tofi=0.25",
    }

    err = rec.WriteSignal(signal)
    assert.NoError(t, err)

    // Read file and verify
    content, err := os.ReadFile(tmpFile.Name())
    assert.NoError(t, err)
    assert.Contains(t, string(content), "1234567890")
    assert.Contains(t, string(content), "LONG")
    assert.Contains(t, string(content), "0.75")
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/recorder/... -v -run TestSignalRecorder`
Expected: FAIL with "undefined: SignalRecorder"

- [ ] **Step 3: Implement signal recorder**

```go
// internal/recorder/signal.go
package recorder

import (
    "encoding/csv"
    "fmt"
    "os"
    "strconv"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

type SignalRecorder struct {
    file   *os.File
    writer *csv.Writer
    header bool
}

func NewSignalRecorder(path string) (*SignalRecorder, error) {
    file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    if err != nil {
        return nil, err
    }

    return &SignalRecorder{
        file:   file,
        writer: csv.NewWriter(file),
    }, nil
}

func (r *SignalRecorder) Write(feature model.Feature) error {
    // Not implemented for signal recorder
    return nil
}

func (r *SignalRecorder) WriteSignal(signal model.Signal) error {
    if !r.header {
        if err := r.writeHeader(); err != nil {
            return err
        }
        r.header = true
    }

    record := []string{
        strconv.FormatInt(signal.Timestamp, 10),
        signal.Side.String(),
        fmt.Sprintf("%f", signal.Strength),
        signal.Reason,
    }

    return r.writer.Write(record)
}

func (r *SignalRecorder) writeHeader() error {
    header := []string{"timestamp", "signal", "strength", "reason"}
    return r.writer.Write(header)
}

func (r *SignalRecorder) Close() error {
    r.writer.Flush()
    return r.file.Close()
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/recorder/... -v -run TestSignalRecorder`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/recorder/signal.go internal/recorder/signal_test.go
git commit -m "feat: add signal recorder with tests"
```

---

## Task 14: Implement Monitor

**Files:**
- Create: `internal/monitor/monitor.go`
- Create: `internal/monitor/monitor_test.go`

- [ ] **Step 1: Write failing test for monitor**

```go
// internal/monitor/monitor_test.go
package monitor

import (
    "testing"
    "time"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestMonitor_Update(t *testing.T) {
    m := NewMonitor(1 * time.Second)

    // Update with signals
    m.Update(&model.Signal{Side: model.Long, Strength: 0.5})
    m.Update(&model.Signal{Side: model.Short, Strength: 0.3})
    m.Update(&model.Signal{Side: model.Long, Strength: 0.7})

    // Check counts
    assert.Equal(t, 2, m.counts[model.Long])
    assert.Equal(t, 1, m.counts[model.Short])
    assert.Equal(t, 3, len(m.strength))
}

func TestMonitor_Reset(t *testing.T) {
    m := NewMonitor(1 * time.Second)

    m.Update(&model.Signal{Side: model.Long, Strength: 0.5})
    m.Reset()

    assert.Equal(t, 0, m.counts[model.Long])
    assert.Equal(t, 0, len(m.strength))
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/monitor/... -v -run TestMonitor`
Expected: FAIL with "undefined: Monitor"

- [ ] **Step 3: Implement monitor**

```go
// internal/monitor/monitor.go
package monitor

import (
    "fmt"
    "log/slog"
    "time"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

type Monitor struct {
    counts    map[model.SignalSide]int
    strength  []float64
    interval  time.Duration
    lastReset time.Time
    logger    *slog.Logger
}

func NewMonitor(interval time.Duration) *Monitor {
    return &Monitor{
        counts:    make(map[model.SignalSide]int),
        strength:  make([]float64, 0),
        interval:  interval,
        lastReset: time.Now(),
        logger:    slog.Default(),
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

    m.logger.Info("signal statistics",
        "total", total,
        "long", m.counts[model.Long],
        "short", m.counts[model.Short],
        "flat", m.counts[model.Flat],
        "avg_strength", fmt.Sprintf("%.4f", avgStrength),
    )
}

func (m *Monitor) Reset() {
    m.counts = make(map[model.SignalSide]int)
    m.strength = make([]float64, 0)
    m.lastReset = time.Now()
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/monitor/... -v -run TestMonitor`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/monitor/
git commit -m "feat: add monitor with tests"
```

---

## Task 15: Implement Evaluator

**Files:**
- Create: `internal/evaluator/evaluator.go`
- Create: `internal/evaluator/evaluator_test.go`

- [ ] **Step 1: Write failing test for evaluator**

```go
// internal/evaluator/evaluator_test.go
package evaluator

import (
    "os"
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestEvaluator_AddSignal(t *testing.T) {
    tmpFile, err := os.CreateTemp("", "eval-*.csv")
    assert.NoError(t, err)
    defer os.Remove(tmpFile.Name())
    tmpFile.Close()

    ev, err := NewEvaluator(tmpFile.Name())
    assert.NoError(t, err)
    defer ev.Close()

    signal := &model.Signal{
        Timestamp: 1000,
        Side:      model.Long,
        Strength:  0.5,
    }

    ev.AddSignal(signal)
    assert.Equal(t, 1, len(ev.pending))
}

func TestEvaluator_UpdatePrice(t *testing.T) {
    tmpFile, err := os.CreateTemp("", "eval-*.csv")
    assert.NoError(t, err)
    defer os.Remove(tmpFile.Name())
    tmpFile.Close()

    ev, err := NewEvaluator(tmpFile.Name())
    assert.NoError(t, err)
    defer ev.Close()

    // Add signal
    signal := &model.Signal{
        Timestamp: 1000,
        Side:      model.Long,
        Strength:  0.5,
    }
    ev.AddSignal(signal)

    // Update price
    ev.UpdatePrice(100.5)
    assert.Equal(t, 1, len(ev.pending))
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/evaluator/... -v -run TestEvaluator`
Expected: FAIL with "undefined: Evaluator"

- [ ] **Step 3: Implement evaluator**

```go
// internal/evaluator/evaluator.go
package evaluator

import (
    "encoding/csv"
    "fmt"
    "os"
    "strconv"
    "sync"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

type pendingSignal struct {
    signal     model.Signal
    entryPrice float64
    timestamp  int64
}

type Evaluator struct {
    pending []pendingSignal
    file    *os.File
    writer  *csv.Writer
    mu      sync.Mutex
    header  bool
}

func NewEvaluator(path string) (*Evaluator, error) {
    file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    if err != nil {
        return nil, err
    }

    return &Evaluator{
        pending: make([]pendingSignal, 0),
        file:    file,
        writer:  csv.NewWriter(file),
    }, nil
}

func (e *Evaluator) AddSignal(signal *model.Signal) {
    e.mu.Lock()
    defer e.mu.Unlock()

    e.pending = append(e.pending, pendingSignal{
        signal:    *signal,
        timestamp: signal.Timestamp,
    })
}

func (e *Evaluator) UpdatePrice(mid float64) {
    e.mu.Lock()
    defer e.mu.Unlock()

    // Check pending signals for return computation
    // This is simplified - full implementation would check time horizons
    for i := len(e.pending) - 1; i >= 0; i-- {
        ps := e.pending[i]
        // Remove old signals
        if ps.timestamp < 10000 { // Simplified check
            e.pending = append(e.pending[:i], e.pending[i+1:]...)
        }
    }
}

func (e *Evaluator) writeRow(signal model.Signal, entryPrice, return1s, return5s, return10s float64) error {
    if !e.header {
        header := []string{"signal_time", "signal", "strength", "entry_price", "return_1s", "return_5s", "return_10s"}
        if err := e.writer.Write(header); err != nil {
            return err
        }
        e.header = true
    }

    record := []string{
        strconv.FormatInt(signal.Timestamp, 10),
        signal.Side.String(),
        fmt.Sprintf("%f", signal.Strength),
        fmt.Sprintf("%f", entryPrice),
        fmt.Sprintf("%f", return1s),
        fmt.Sprintf("%f", return5s),
        fmt.Sprintf("%f", return10s),
    }

    return e.writer.Write(record)
}

func (e *Evaluator) Close() error {
    e.writer.Flush()
    return e.file.Close()
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/evaluator/... -v -run TestEvaluator`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/evaluator/
git commit -m "feat: add evaluator with tests"
```

---

## Task 16: Implement Collector Workers

**Files:**
- Create: `internal/collector/depth.go`
- Create: `internal/collector/trade.go`
- Create: `internal/collector/depth_test.go`
- Create: `internal/collector/trade_test.go`

- [ ] **Step 1: Write failing test for trade collector**

```go
// internal/collector/trade_test.go
package collector

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestParseTradeMessage(t *testing.T) {
    msg := []byte(`{"e":"trade","T":1234567890,"s":"BTCUSDT","p":"100.5","q":"1.0","m":false}`)
    
    trade, err := parseTradeMessage(msg)
    assert.NoError(t, err)
    assert.Equal(t, "BUY", trade.Side)
    assert.Equal(t, 100.5, trade.Price)
    assert.Equal(t, 1.0, trade.Qty)
}

func TestParseTradeMessage_Sell(t *testing.T) {
    msg := []byte(`{"e":"trade","T":1234567890,"s":"BTCUSDT","p":"100.5","q":"2.0","m":true}`)
    
    trade, err := parseTradeMessage(msg)
    assert.NoError(t, err)
    assert.Equal(t, "SELL", trade.Side)
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/collector/... -v -run TestParseTradeMessage`
Expected: FAIL with "undefined: parseTradeMessage"

- [ ] **Step 3: Implement trade collector**

```go
// internal/collector/trade.go
package collector

import (
    "context"
    "encoding/json"
    "log/slog"
    "sync"
    "time"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
    "github.com/jiangyums/binance-orderflow-lab/pkg/websocket"
)

type tradeMessage struct {
    E string  `json:"e"` // Event type
    T int64   `json:"T"` // Transaction time
    S string  `json:"s"` // Symbol
    P float64 `json:"p"` // Price
    Q float64 `json:"q"` // Quantity
    M bool    `json:"m"` // Is buyer the maker
}

type Trade struct {
    Side  string
    Price float64
    Qty   float64
    Time  int64
}

func parseTradeMessage(msg []byte) (*Trade, error) {
    var tm tradeMessage
    if err := json.Unmarshal(msg, &tm); err != nil {
        return nil, err
    }

    side := "BUY"
    if tm.M {
        side = "SELL"
    }

    return &Trade{
        Side:  side,
        Price: tm.P,
        Qty:   tm.Q,
        Time:  tm.T,
    }, nil
}

func TradeWorker(
    ctx context.Context,
    url string,
    timeoutSeconds int,
    trades *[]model.Trade,
    tradesMu *sync.Mutex,
    eventCh chan<- model.Event,
) error {
    logger := slog.Default()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }

        client := websocket.NewClient(url, timeoutSeconds)
        if err := client.Connect(ctx); err != nil {
            logger.Error("trade connect failed", "error", err)
            time.Sleep(3 * time.Second)
            continue
        }

        logger.Info("trade connected")

        for {
            select {
            case <-ctx.Done():
                client.Close()
                return ctx.Err()
            default:
            }

            msg, err := client.ReadMessage(ctx)
            if err != nil {
                logger.Error("trade read error", "error", err)
                client.Close()
                break
            }

            trade, err := parseTradeMessage(msg)
            if err != nil {
                logger.Error("trade parse error", "error", err)
                continue
            }

            // Update shared trades
            tradesMu.Lock()
            *trades = append(*trades, model.Trade{
                Side:  trade.Side,
                Price: trade.Price,
                Qty:   trade.Qty,
                Time:  trade.Time,
            })
            tradesMu.Unlock()

            // Send event
            eventCh <- model.Event{
                Type:      model.TradeUpdated,
                Timestamp: trade.Time,
            }
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/collector/... -v -run TestParseTradeMessage`
Expected: PASS

- [ ] **Step 5: Write failing test for depth collector**

```go
// internal/collector/depth_test.go
package collector

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestApplyDepthUpdate(t *testing.T) {
    book := model.NewOrderBook()
    book.Bids[100.0] = 10.0
    book.Asks[101.0] = 5.0

    update := `{"b":[["100.0","15.0"]],"a":[["101.0","5.0"]],"U":2,"u":2,"pu":1}`
    
    err := applyDepthUpdate(book, []byte(update))
    assert.NoError(t, err)
    assert.Equal(t, 15.0, book.Bids[100.0])
}
```

- [ ] **Step 6: Run test to verify it fails**

Run: `go test ./internal/collector/... -v -run TestApplyDepthUpdate`
Expected: FAIL with "undefined: applyDepthUpdate"

- [ ] **Step 7: Implement depth collector**

```go
// internal/collector/depth.go
package collector

import (
    "context"
    "encoding/json"
    "log/slog"
    "sync"
    "time"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
    "github.com/jiangyums/binance-orderflow-lab/pkg/websocket"
)

type depthMessage struct {
    E string     `json:"e"` // Event type
    T int64      `json:"T"` // Transaction time
    S string     `json:"s"` // Symbol
    U int64      `json:"U"` // First update ID
    u int64      `json:"u"` // Final update ID
    pu int64     `json:"pu"` // Previous final update ID
    B [][]string `json:"b"` // Bids
    A [][]string `json:"a"` // Asks
}

func applyDepthUpdate(book *model.OrderBook, msg []byte) error {
    var dm depthMessage
    if err := json.Unmarshal(msg, &dm); err != nil {
        return err
    }

    // Update bids
    for _, bid := range dm.B {
        if len(bid) == 2 {
            price := parseFloat(bid[0])
            qty := parseFloat(bid[1])
            if qty == 0 {
                delete(book.Bids, price)
            } else {
                book.Bids[price] = qty
            }
        }
    }

    // Update asks
    for _, ask := range dm.A {
        if len(ask) == 2 {
            price := parseFloat(ask[0])
            qty := parseFloat(ask[1])
            if qty == 0 {
                delete(book.Asks, price)
            } else {
                book.Asks[price] = qty
            }
        }
    }

    book.LastUpdateID = dm.u
    return nil
}

func parseFloat(s string) float64 {
    var f float64
    json.Unmarshal([]byte(s), &f)
    return f
}

func DepthWorker(
    ctx context.Context,
    url string,
    timeoutSeconds int,
    book *model.OrderBook,
    eventCh chan<- model.Event,
) error {
    logger := slog.Default()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }

        client := websocket.NewClient(url, timeoutSeconds)
        if err := client.Connect(ctx); err != nil {
            logger.Error("depth connect failed", "error", err)
            time.Sleep(3 * time.Second)
            continue
        }

        logger.Info("depth connected")

        for {
            select {
            case <-ctx.Done():
                client.Close()
                return ctx.Err()
            default:
            }

            msg, err := client.ReadMessage(ctx)
            if err != nil {
                logger.Error("depth read error", "error", err)
                client.Close()
                break
            }

            if err := applyDepthUpdate(book, msg); err != nil {
                logger.Error("depth apply error", "error", err)
                continue
            }

            eventCh <- model.Event{
                Type:      model.BookUpdated,
                Timestamp: time.Now().UnixMilli(),
            }
        }
    }
}
```

- [ ] **Step 8: Run test to verify it passes**

Run: `go test ./internal/collector/... -v -run TestApplyDepthUpdate`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add internal/collector/
git commit -m "feat: add collector workers with tests"
```

---

## Task 17: Implement Engine

**Files:**
- Create: `internal/engine/engine.go`
- Create: `internal/engine/engine_test.go`

- [ ] **Step 1: Write failing test for engine**

```go
// internal/engine/engine_test.go
package engine

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/jiangyums/binance-orderflow-lab/internal/config"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

func TestEngine_New(t *testing.T) {
    cfg := &config.Config{
        Symbol: "btcusdt",
    }

    eng := New(cfg)
    assert.NotNil(t, eng)
    assert.Equal(t, cfg, eng.config)
}

func TestEngine_DispatchEvent(t *testing.T) {
    cfg := &config.Config{
        Symbol: "btcusdt",
    }

    eng := New(cfg)
    
    event := model.Event{
        Type:      model.BookUpdated,
        Timestamp: 1234567890,
    }

    // This should not panic
    eng.dispatchEvent(event)
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/engine/... -v -run TestEngine`
Expected: FAIL with "undefined: New"

- [ ] **Step 3: Implement engine**

```go
// internal/engine/engine.go
package engine

import (
    "context"
    "log/slog"
    "sync"

    "github.com/jiangyums/binance-orderflow-lab/internal/collector"
    "github.com/jiangyums/binance-orderflow-lab/internal/config"
    "github.com/jiangyums/binance-orderflow-lab/internal/evaluator"
    "github.com/jiangyums/binance-orderflow-lab/internal/feature"
    "github.com/jiangyums/binance-orderflow-lab/internal/model"
    "github.com/jiangyums/binance-orderflow-lab/internal/monitor"
    "github.com/jiangyums/binance-orderflow-lab/internal/recorder"
    "github.com/jiangyums/binance-orderflow-lab/internal/signal"
    "github.com/jiangyums/binance-orderflow-lab/internal/validator"
    "golang.org/x/sync/errgroup"
)

type Engine struct {
    eventCh     chan model.Event
    book        *model.OrderBook
    bookMu      sync.RWMutex
    trades      []model.Trade
    tradesMu    sync.Mutex
    calculators []feature.Calculator
    generator   signal.Generator
    tracker     *signal.Tracker
    evaluators  []*evaluator.Evaluator
    recorders   []recorder.Recorder
    monitor     *monitor.Monitor
    validator   *validator.StreamValidator
    config      *config.Config
    logger      *slog.Logger
}

func New(cfg *config.Config) *Engine {
    return &Engine{
        eventCh:    make(chan model.Event, 1000),
        book:       model.NewOrderBook(),
        trades:     make([]model.Trade, 0),
        calculators: []feature.Calculator{
            feature.NewOFICalculator(),
            feature.NewCVDCalculator(),
            feature.NewOBICalculator(1),
            feature.NewOBICalculator(5),
            feature.NewOBICalculator(10),
            feature.NewMicroPriceCalculator(),
            feature.NewTakerMakerCalculator(),
        },
        generator: signal.NewTradeOFISignalGenerator(
            cfg.Signal.TOFIThreshold,
            cfg.Signal.TOFIScale,
            cfg.Signal.TOFIMode,
        ),
        tracker: signal.NewTracker(false),
        monitor: monitor.NewMonitor(60000000000), // 60 seconds
        validator: validator.NewStreamValidator(
            "depth",
            cfg.Latency.GapWarnMS,
            2000,
        ),
        config: cfg,
        logger: slog.Default(),
    }
}

func (e *Engine) Run(ctx context.Context) error {
    ctx, cancel := context.WithCancel(ctx)
    defer cancel()

    g, ctx := errgroup.WithContext(ctx)

    // Start depth worker
    g.Go(func() error {
        return collector.DepthWorker(
            ctx,
            e.config.WebSocket.DepthURL,
            e.config.WebSocket.Timeout,
            e.book,
            e.eventCh,
        )
    })

    // Start trade worker
    g.Go(func() error {
        return collector.TradeWorker(
            ctx,
            e.config.WebSocket.TradeURL,
            e.config.WebSocket.Timeout,
            &e.trades,
            &e.tradesMu,
            e.eventCh,
        )
    })

    // Start event processor
    g.Go(func() error {
        return e.processEvents(ctx)
    })

    return g.Wait()
}

func (e *Engine) processEvents(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case event := <-e.eventCh:
            e.dispatchEvent(event)
        }
    }
}

func (e *Engine) dispatchEvent(event model.Event) {
    switch event.Type {
    case model.BookUpdated:
        e.handleBookUpdate(event)
    case model.TradeUpdated:
        e.handleTradeUpdate(event)
    case model.BookError, model.TradeError:
        e.handleError(event)
    }
}

func (e *Engine) handleBookUpdate(event model.Event) {
    e.bookMu.RLock()
    book := *e.book
    e.bookMu.RUnlock()

    feature := model.Feature{Timestamp: event.Timestamp}
    for _, calc := range e.calculators {
        feature = calc.Update(event, &book, e.trades)
    }

    e.processFeature(feature)
}

func (e *Engine) handleTradeUpdate(event model.Event) {
    e.tradesMu.Lock()
    trades := make([]model.Trade, len(e.trades))
    copy(trades, e.trades)
    e.tradesMu.Unlock()

    feature := model.Feature{Timestamp: event.Timestamp}
    for _, calc := range e.calculators {
        feature = calc.Update(event, e.book, trades)
    }

    e.processFeature(feature)
}

func (e *Engine) processFeature(feature model.Feature) {
    e.validator.Check(feature.Timestamp)

    for _, ev := range e.evaluators {
        ev.UpdatePrice(feature.Mid)
    }

    for _, rec := range e.recorders {
        rec.Write(feature)
    }

    sig := e.generator.Generate(feature)
    if sig != nil {
        filtered := e.tracker.Update(sig)
        if filtered != nil {
            e.monitor.Update(filtered)
            for _, ev := range e.evaluators {
                ev.AddSignal(filtered)
            }
            for _, rec := range e.recorders {
                rec.WriteSignal(*filtered)
            }
            if filtered.Side != model.Flat {
                e.logger.Info("signal",
                    "side", filtered.Side,
                    "strength", filtered.Strength,
                    "reason", filtered.Reason,
                )
            }
        }
    }
}

func (e *Engine) handleError(event model.Event) {
    e.logger.Error("stream error",
        "type", event.Type,
        "error", event.Error,
    )
}

func (e *Engine) Close() {
    for _, rec := range e.recorders {
        rec.Close()
    }
    for _, ev := range e.evaluators {
        ev.Close()
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/engine/... -v -run TestEngine`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add internal/engine/
git commit -m "feat: add engine with tests"
```

---

## Task 18: Implement Main Entry Point

**Files:**
- Create: `cmd/orderflow/main.go`

- [ ] **Step 1: Create main.go**

```go
// cmd/orderflow/main.go
package main

import (
    "context"
    "flag"
    "log/slog"
    "os"
    "os/signal"
    "syscall"

    "github.com/jiangyums/binance-orderflow-lab/internal/config"
    "github.com/jiangyums/binance-orderflow-lab/internal/engine"
)

func main() {
    configPath := flag.String("config", "configs/default.yaml", "config file path")
    flag.Parse()

    // Load config
    cfg, err := config.Load(*configPath)
    if err != nil {
        slog.Error("failed to load config", "error", err)
        os.Exit(1)
    }

    // Create engine
    eng := engine.New(cfg)

    // Setup signal handling
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    // Run engine
    slog.Info("starting orderflow engine", "symbol", cfg.Symbol)
    if err := eng.Run(ctx); err != nil && err != context.Canceled {
        slog.Error("engine error", "error", err)
        os.Exit(1)
    }

    // Cleanup
    eng.Close()
    slog.Info("orderflow engine stopped")
}
```

- [ ] **Step 2: Build and test**

Run: `go build ./cmd/orderflow`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add cmd/orderflow/
git commit -m "feat: add main entry point"
```

---

## Task 19: Run Full Test Suite

**Files:**
- None (verification task)

- [ ] **Step 1: Run all tests**

Run: `go test -v ./...`
Expected: All tests pass

- [ ] **Step 2: Run benchmarks**

Run: `go test -bench=. ./...`
Expected: Benchmarks complete

- [ ] **Step 3: Build final binary**

Run: `go build -o bin/orderflow ./cmd/orderflow`
Expected: Binary created successfully

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Go refactoring"
```

---

## Summary

This plan covers the complete Go refactoring of the binance-orderflow-lab project:

1. **Foundation**: Go module, core types, config
2. **Error Handling**: Custom error types
3. **WebSocket**: Client wrapper
4. **Features**: OFI, CVD, OBI, MicroPrice, TakerMaker calculators
5. **Signals**: TradeOFI generator, tracker
6. **Validation**: Stream validator
7. **Recording**: Feature and signal recorders
8. **Monitoring**: Real-time statistics
9. **Evaluation**: P&L computation
10. **Collection**: Depth and trade workers
11. **Engine**: Core coordinator
12. **Entry Point**: Main binary

Each task follows TDD principles with failing tests, implementation, and verification.
