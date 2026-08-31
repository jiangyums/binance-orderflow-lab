package collector

import (
	"context"
	"encoding/json"
	"log"
	"time"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/jiangyums/binance-orderflow-lab/pkg/websocket"
)

type depthMessage struct {
	E  string     `json:"e"`
	T  int64      `json:"T"`
	S  string     `json:"s"`
	U  int64      `json:"U"`
	U2 int64      `json:"u"`
	PU int64      `json:"pu"`
	B  [][]string `json:"b"`
	A  [][]string `json:"a"`
}

func applyDepthUpdate(book *model.OrderBook, msg []byte) error {
	var dm depthMessage
	if err := json.Unmarshal(msg, &dm); err != nil {
		return err
	}

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

	book.LastUpdateID = dm.U2
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
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		client := websocket.NewClient(url, timeoutSeconds)
		if err := client.Connect(ctx); err != nil {
			log.Printf("depth connect failed: %v", err)
			time.Sleep(3 * time.Second)
			continue
		}

		log.Println("depth connected")

		for {
			select {
			case <-ctx.Done():
				client.Close()
				return ctx.Err()
			default:
			}

			msg, err := client.ReadMessage(ctx)
			if err != nil {
				log.Printf("depth read error: %v", err)
				client.Close()
				break
			}

			if err := applyDepthUpdate(book, msg); err != nil {
				log.Printf("depth apply error: %v", err)
				continue
			}

			eventCh <- model.Event{
				Type:      model.BookUpdated,
				Timestamp: time.Now().UnixMilli(),
			}
		}
	}
}
