package model

type Feature struct {
	Timestamp    int64
	Mid          float64
	Microprice   float64
	Spread       float64
	OBI1         float64
	OBI5         float64
	OBI10        float64
	OFI          float64
	TradeSide    string
	TradePrice   float64
	TradeQty     float64
	CVD          float64
	BidDepth     float64
	AskDepth     float64
	BuyBreakout  float64
	SellBreakout float64
	TOFI         float64
}
