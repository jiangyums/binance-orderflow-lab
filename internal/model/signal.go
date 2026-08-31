package model

type SignalSide int

const (
	Long SignalSide = iota
	Short
	Flat
)

func (s SignalSide) String() string {
	switch s {
	case Long:
		return "LONG"
	case Short:
		return "SHORT"
	case Flat:
		return "FLAT"
	default:
		return "UNKNOWN"
	}
}

type Signal struct {
	Timestamp int64
	Side      SignalSide
	Strength  float64
	Reason    string
}
