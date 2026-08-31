package model

type Trade struct {
	Timestamp int64
	Symbol    string
	Side      string
	Price     float64
	Quantity  float64
}
