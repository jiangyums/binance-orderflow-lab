package model

type EventType int

const (
	BookUpdated EventType = iota
	TradeUpdated
	BookError
	TradeError
)

type Event struct {
	Type      EventType
	Timestamp int64
	Error     error
}
