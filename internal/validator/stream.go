package validator

import (
    "fmt"
    "log"
)

type StreamValidator struct {
    streamType   string
    gapWarnMS    int64
    reportEvery  int
    eventCount   int
    lastTimestamp int64
}

func NewStreamValidator(streamType string, gapWarnMS int64, reportEvery int) *StreamValidator {
    return &StreamValidator{
        streamType:  streamType,
        gapWarnMS:   gapWarnMS,
        reportEvery: reportEvery,
    }
}

func (v *StreamValidator) Check(timestamp int64) error {
    v.eventCount++

    if v.lastTimestamp > 0 {
        if timestamp < v.lastTimestamp {
            return fmt.Errorf("backward timestamp: %d < %d", timestamp, v.lastTimestamp)
        }
        if timestamp-v.lastTimestamp > v.gapWarnMS {
            return fmt.Errorf("large gap: %dms between events", timestamp-v.lastTimestamp)
        }
    }

    v.lastTimestamp = timestamp

    if v.eventCount%v.reportEvery == 0 {
        log.Printf("stream stats stream=%s events=%d", v.streamType, v.eventCount)
    }

    return nil
}

func (v *StreamValidator) Reset() {
    v.lastTimestamp = 0
    v.eventCount = 0
}