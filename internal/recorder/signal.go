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