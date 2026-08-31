package collector

import (
	"context"
	"encoding/json"
	"log"
	"sync"
	"time"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/jiangyums/binance-orderflow-lab/pkg/websocket"
)

type tradeMessage struct {
	E string  `json:"e"`
	T int64   `json:"T"`
	S string  `json:"s"`
	P float64 `json:"p"`
	Q float64 `json:"q"`
	M bool    `json:"m"`
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
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		client := websocket.NewClient(url, timeoutSeconds)
		if err := client.Connect(ctx); err != nil {
			log.Printf("trade connect failed: %v", err)
			time.Sleep(3 * time.Second)
			continue
		}

		log.Println("trade connected")

		for {
			select {
			case <-ctx.Done():
				client.Close()
				return ctx.Err()
			default:
			}

			msg, err := client.ReadMessage(ctx)
			if err != nil {
				log.Printf("trade read error: %v", err)
				client.Close()
				break
			}

			trade, err := parseTradeMessage(msg)
			if err != nil {
				log.Printf("trade parse error: %v", err)
				continue
			}

			tradesMu.Lock()
			*trades = append(*trades, model.Trade{
				Side:     trade.Side,
				Price:    trade.Price,
				Quantity: trade.Qty,
				Timestamp: trade.Time,
			})
			tradesMu.Unlock()

			eventCh <- model.Event{
				Type:      model.TradeUpdated,
				Timestamp: trade.Time,
			}
		}
	}
}
