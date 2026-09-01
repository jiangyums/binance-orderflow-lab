package collector

import (
	"context"
	"encoding/json"
	"log"
	"strconv"
	"sync"
	"time"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/jiangyums/binance-orderflow-lab/pkg/websocket"
)

type tradeMessage struct {
	E  interface{} `json:"e"`
	E2 int64       `json:"E"`
	S  string      `json:"s"`
	T  int64       `json:"t"`
	T2 int64       `json:"T"`
	P  string      `json:"p"`
	Q  string      `json:"q"`
	M  bool        `json:"m"`
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

	price, _ := strconv.ParseFloat(tm.P, 64)
	qty, _ := strconv.ParseFloat(tm.Q, 64)

	return &Trade{
		Side:  side,
		Price: price,
		Qty:   qty,
		Time:  tm.T2,
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
	b := newBackoff(3*time.Second, 60*time.Second)
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		client := websocket.NewClient(url, timeoutSeconds)
		if err := client.Connect(ctx); err != nil {
			// Connect 内部走 DialContext,ctx 取消时会立即返回;
			// 这里让重试等待本身也可被 ctx 打断,并做指数退避。
			if ctx.Err() != nil {
				return ctx.Err()
			}
			log.Printf("trade connect failed: %v", err)
			if err := sleepCtx(ctx, b.next()); err != nil {
				return ctx.Err()
			}
			continue
		}
		b.reset()

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
				Side:      trade.Side,
				Price:     trade.Price,
				Quantity:  trade.Qty,
				Timestamp: trade.Time,
			})
			tradesMu.Unlock()

			select {
			case <-ctx.Done():
				return ctx.Err()
			case eventCh <- model.Event{
				Type:      model.TradeUpdated,
				Timestamp: trade.Time,
			}:
			}
		}
	}
}
