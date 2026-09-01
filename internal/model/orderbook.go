package model

import "sync"

type OrderBook struct {
	Bids         map[float64]float64
	Asks         map[float64]float64
	LastUpdateID int64
	mu           sync.RWMutex
}

func NewOrderBook() *OrderBook {
	return &OrderBook{
		Bids: make(map[float64]float64),
		Asks: make(map[float64]float64),
	}
}

func (ob *OrderBook) Lock() {
	ob.mu.Lock()
}

func (ob *OrderBook) Unlock() {
	ob.mu.Unlock()
}

func (ob *OrderBook) RLock() {
	ob.mu.RLock()
}

func (ob *OrderBook) RUnlock() {
	ob.mu.RUnlock()
}

func (ob *OrderBook) Reset() {
	ob.mu.Lock()
	defer ob.mu.Unlock()
	ob.Bids = make(map[float64]float64)
	ob.Asks = make(map[float64]float64)
	ob.LastUpdateID = 0
}

func (ob *OrderBook) BestBid() (float64, float64, bool) {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	var bestPrice float64
	var bestQty float64
	found := false

	for price, qty := range ob.Bids {
		if !found || price > bestPrice {
			bestPrice = price
			bestQty = qty
			found = true
		}
	}
	return bestPrice, bestQty, found
}

func (ob *OrderBook) BestAsk() (float64, float64, bool) {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	var bestPrice float64
	var bestQty float64
	found := false

	for price, qty := range ob.Asks {
		if !found || price < bestPrice {
			bestPrice = price
			bestQty = qty
			found = true
		}
	}
	return bestPrice, bestQty, found
}

func (ob *OrderBook) MidPrice() float64 {
	bid, _, _ := ob.BestBid()
	ask, _, _ := ob.BestAsk()
	if bid == 0 || ask == 0 {
		return 0
	}
	return (bid + ask) / 2
}

func (ob *OrderBook) Spread() float64 {
	bid, _, _ := ob.BestBid()
	ask, _, _ := ob.BestAsk()
	return ask - bid
}

func (ob *OrderBook) BidVolume(levels int) float64 {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	var total float64
	count := 0
	for _, qty := range ob.Bids {
		total += qty
		count++
		if count >= levels {
			break
		}
	}
	return total
}

func (ob *OrderBook) AskVolume(levels int) float64 {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	var total float64
	count := 0
	for _, qty := range ob.Asks {
		total += qty
		count++
		if count >= levels {
			break
		}
	}
	return total
}
