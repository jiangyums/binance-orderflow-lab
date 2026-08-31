package recorder

import (
    "encoding/csv"
    "fmt"
    "os"
    "strconv"

    "github.com/jiangyums/binance-orderflow-lab/internal/model"
)

type FeatureRecorder struct {
    file   *os.File
    writer *csv.Writer
    header bool
}

func NewFeatureRecorder(path string) (*FeatureRecorder, error) {
    file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    if err != nil {
        return nil, err
    }

    return &FeatureRecorder{
        file:   file,
        writer: csv.NewWriter(file),
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
    return nil
}

func (r *FeatureRecorder) Close() error {
    r.writer.Flush()
    return r.file.Close()
}