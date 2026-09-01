package collector

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

// DepthSnapshot 是 REST /fapi/v1/depth 返回的订单簿快照。
type DepthSnapshot struct {
	LastUpdateID int64      `json:"lastUpdateId"`
	Bids         [][]string `json:"bids"`
	Asks         [][]string `json:"asks"`
}

// fetchSnapshotWithRetry 拉取快照, 失败时按退避重试, 直到成功或 ctx 取消。
func fetchSnapshotWithRetry(ctx context.Context, snapshotURL, symbol string, depthLimit int) (*DepthSnapshot, error) {
	b := newBackoff(500*time.Millisecond, 5*time.Second)
	for {
		snap, err := fetchSnapshot(ctx, snapshotURL, symbol, depthLimit)
		if err == nil {
			return snap, nil
		}
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		log.Printf("depth snapshot fetch failed: %v", err)
		if err := sleepCtx(ctx, b.next()); err != nil {
			return nil, ctx.Err()
		}
	}
}

// fetchSnapshot 通过 REST 拉取一次订单簿快照。
func fetchSnapshot(ctx context.Context, snapshotURL, symbol string, depthLimit int) (*DepthSnapshot, error) {
	u, err := url.Parse(snapshotURL)
	if err != nil {
		return nil, fmt.Errorf("invalid snapshot url: %w", err)
	}
	q := u.Query()
	q.Set("symbol", strings.ToUpper(symbol))
	q.Set("limit", strconv.Itoa(depthLimit))
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return nil, err
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("snapshot http status %d", resp.StatusCode)
	}

	var snap DepthSnapshot
	if err := json.NewDecoder(resp.Body).Decode(&snap); err != nil {
		return nil, fmt.Errorf("decode snapshot: %w", err)
	}
	if snap.LastUpdateID == 0 || len(snap.Bids) == 0 || len(snap.Asks) == 0 {
		return nil, fmt.Errorf("invalid snapshot payload")
	}
	return &snap, nil
}
