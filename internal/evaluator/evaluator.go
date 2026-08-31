package evaluator

import (
	"encoding/csv"
	"os"
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

	for i := len(e.pending) - 1; i >= 0; i-- {
		ps := e.pending[i]
		if ps.timestamp < 10000 {
			e.pending = append(e.pending[:i], e.pending[i+1:]...)
		}
	}
}

func (e *Evaluator) Close() error {
	e.writer.Flush()
	return e.file.Close()
}
