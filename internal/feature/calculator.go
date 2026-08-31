package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type Calculator interface {
	Update(event model.Event, book *model.OrderBook, trades []model.Trade) model.Feature
	Reset()
}
