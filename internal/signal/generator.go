package signal

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type Generator interface {
    Generate(feature model.Feature) *model.Signal
}
