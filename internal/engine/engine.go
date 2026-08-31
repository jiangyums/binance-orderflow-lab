package engine

import (
	"context"
	"log"
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
	mon         *monitor.Monitor
	validator   *validator.StreamValidator
	config      *config.Config
}

func New(cfg *config.Config) *Engine {
	return &Engine{
		eventCh: make(chan model.Event, 1000),
		book:    model.NewOrderBook(),
		trades:  make([]model.Trade, 0),
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
		tracker:   signal.NewTracker(false),
		mon:       monitor.NewMonitor(60000000000),
		validator: validator.NewStreamValidator("depth", cfg.Latency.GapWarnMS, 2000),
		config:    cfg,
	}
}

func (e *Engine) Run(ctx context.Context) error {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	g, ctx := errgroup.WithContext(ctx)

	g.Go(func() error {
		return collector.DepthWorker(ctx, e.config.WebSocket.DepthURL, e.config.WebSocket.Timeout, e.book, e.eventCh)
	})

	g.Go(func() error {
		return collector.TradeWorker(ctx, e.config.WebSocket.TradeURL, e.config.WebSocket.Timeout, &e.trades, &e.tradesMu, e.eventCh)
	})

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

	feat := model.Feature{Timestamp: event.Timestamp}
	for _, calc := range e.calculators {
		feat = calc.Update(event, &book, e.trades)
	}

	e.processFeature(feat)
}

func (e *Engine) handleTradeUpdate(event model.Event) {
	e.tradesMu.Lock()
	trades := make([]model.Trade, len(e.trades))
	copy(trades, e.trades)
	e.tradesMu.Unlock()

	feat := model.Feature{Timestamp: event.Timestamp}
	for _, calc := range e.calculators {
		feat = calc.Update(event, e.book, trades)
	}

	e.processFeature(feat)
}

func (e *Engine) processFeature(feat model.Feature) {
	e.validator.Check(feat.Timestamp)

	for _, ev := range e.evaluators {
		ev.UpdatePrice(feat.Mid)
	}

	for _, rec := range e.recorders {
		rec.Write(feat)
	}

	sig := e.generator.Generate(feat)
	if sig != nil {
		filtered := e.tracker.Update(sig)
		if filtered != nil {
			e.mon.Update(filtered)
			for _, ev := range e.evaluators {
				ev.AddSignal(filtered)
			}
			for _, rec := range e.recorders {
				rec.WriteSignal(*filtered)
			}
			if filtered.Side != model.Flat {
				log.Printf("signal: side=%s strength=%.4f reason=%s", filtered.Side, filtered.Strength, filtered.Reason)
			}
		}
	}
}

func (e *Engine) handleError(event model.Event) {
	log.Printf("stream error: type=%d error=%v", event.Type, event.Error)
}

func (e *Engine) Close() {
	for _, rec := range e.recorders {
		rec.Close()
	}
	for _, ev := range e.evaluators {
		ev.Close()
	}
}
