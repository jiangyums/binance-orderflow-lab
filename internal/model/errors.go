package model

import "fmt"

type OrderFlowError struct {
    Code    string
    Message string
    Cause   error
}

func (e *OrderFlowError) Error() string {
    if e.Cause != nil {
        return fmt.Sprintf("%s: %s: %v", e.Code, e.Message, e.Cause)
    }
    return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *OrderFlowError) Unwrap() error {
    return e.Cause
}

func NewGapError(expected, got int64) *OrderFlowError {
    return &OrderFlowError{
        Code:    "GAP_DETECTED",
        Message: fmt.Sprintf("expected update %d, got %d", expected, got),
    }
}

func NewLatencyError(ts, now int64) *OrderFlowError {
    return &OrderFlowError{
        Code:    "HIGH_LATENCY",
        Message: fmt.Sprintf("event age %dms exceeds threshold", now-ts),
    }
}

func NewConnectionError(url string, cause error) *OrderFlowError {
    return &OrderFlowError{
        Code:    "CONNECTION_ERROR",
        Message: fmt.Sprintf("failed to connect to %s", url),
        Cause:   cause,
    }
}

func NewSyncError(message string) *OrderFlowError {
    return &OrderFlowError{
        Code:    "SYNC_ERROR",
        Message: message,
    }
}