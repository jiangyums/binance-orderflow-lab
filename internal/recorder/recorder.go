package recorder

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

type Recorder interface {
    Write(feature model.Feature) error
    WriteSignal(signal model.Signal) error
    Close() error
}