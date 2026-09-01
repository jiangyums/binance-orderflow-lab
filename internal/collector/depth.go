package collector

import (
	"context"
	"encoding/json"
	"log"
	"strconv"
	"sync"
	"time"

	"github.com/jiangyums/binance-orderflow-lab/internal/model"
	"github.com/jiangyums/binance-orderflow-lab/pkg/websocket"
)

// depthMessage 是 Binance depth@100ms WebSocket 推送的增量更新消息。
type depthMessage struct {
	E  string      `json:"e"` // 事件类型 "depthUpdate"
	E2 int64       `json:"E"` // 事件时间
	S  string      `json:"s"` // 交易对
	U  int64       `json:"U"` // 首个更新 ID
	U2 int64       `json:"u"` // 末尾更新 ID
	PU int64       `json:"pu"`// 上一次末尾更新 ID
	B  [][]string  `json:"b"` // 买盘 [["价格","数量"],...]
	A  [][]string  `json:"a"` // 卖盘 [["价格","数量"],...]
}

// readResult 是消息读取的结果。
type readResult struct {
	msg []byte
	err error
}

// depthState 管理深度流的状态。
type depthState struct {
	book       *model.OrderBook
	ready      *bool
	readyMu    *sync.RWMutex
	pending    [][]byte
	lastID     int64
	synced     bool
}

// DepthWorker 实现 Binance 深度流同步协议。
func DepthWorker(
	ctx context.Context,
	url string,
	timeoutSeconds int,
	book *model.OrderBook,
	ready *bool,
	readyMu *sync.RWMutex,
	snapshotURL string,
	symbol string,
	depthLimit int,
	eventCh chan<- model.Event,
) error {
	b := newBackoff(3*time.Second, 60*time.Second)

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		client := websocket.NewClient(url, timeoutSeconds)
		if err := client.Connect(ctx); err != nil {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			log.Printf("depth connect failed: %v", err)
			if err := sleepCtx(ctx, b.next()); err != nil {
				return ctx.Err()
			}
			continue
		}
		b.reset()
		log.Println("depth connected")

		err := runDepthSession(ctx, client, book, ready, readyMu, snapshotURL, symbol, depthLimit, eventCh)
		client.Close()

		if ctx.Err() != nil {
			return ctx.Err()
		}
		if err != nil {
			log.Printf("depth session error: %v, reconnecting...", err)
			if err := sleepCtx(ctx, b.next()); err != nil {
				return ctx.Err()
			}
		}
	}
}

// runDepthSession 执行一次完整的深度流会话。
func runDepthSession(
	ctx context.Context,
	client *websocket.Client,
	book *model.OrderBook,
	ready *bool,
	readyMu *sync.RWMutex,
	snapshotURL string,
	symbol string,
	depthLimit int,
	eventCh chan<- model.Event,
) error {
	readCh := make(chan readResult, 256)
	snapReq := make(chan struct{}, 1)
	snapResp := make(chan *DepthSnapshot, 1)

	go readMessageLoop(ctx, client, readCh)
	go snapshotLoop(ctx, snapshotURL, symbol, depthLimit, snapReq, snapResp)

	return runDepthLoop(ctx, &depthState{
		book: book, ready: ready, readyMu: readyMu,
	}, readCh, snapResp, snapReq, eventCh)
}

// readMessageLoop 持续从WebSocket读取消息。
func readMessageLoop(ctx context.Context, client *websocket.Client, out chan<- readResult) {
	defer close(out)
	for {
		client.SetReadDeadline(time.Now().Add(30 * time.Second))
		msg, err := client.ReadMessage(ctx)
		if err != nil {
			select {
			case out <- readResult{err: err}:
			case <-ctx.Done():
			}
			return
		}
		select {
		case out <- readResult{msg: msg}:
		case <-ctx.Done():
			return
		}
	}
}

// snapshotLoop 等待请求信号, 拉取快照。
func snapshotLoop(ctx context.Context, url, symbol string, limit int, req <-chan struct{}, out chan<- *DepthSnapshot) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-req:
			snap, err := fetchSnapshotWithRetry(ctx, url, symbol, limit)
			if err != nil {
				if ctx.Err() != nil {
					return
				}
				continue
			}
			select {
			case out <- snap:
			case <-ctx.Done():
				return
			}
		}
	}
}

// runDepthLoop 是主循环, 调度消息处理。
func runDepthLoop(
	ctx context.Context,
	s *depthState,
	readCh <-chan readResult,
	snapResp <-chan *DepthSnapshot,
	snapReq chan<- struct{},
	eventCh chan<- model.Event,
) error {
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()

		case r, ok := <-readCh:
			if !ok {
				return errConnectionClosed
			}
			if err := handleReadMsg(ctx, s, r, snapReq, eventCh); err != nil {
				return err
			}

		case snap, ok := <-snapResp:
			if ok && !s.synced {
				handleSnapshot(s, snap)
			}
		}
	}
}

// handleReadMsg 处理收到的增量消息, 返回error表示需要重连。
func handleReadMsg(ctx context.Context, s *depthState, r readResult, snapReq chan<- struct{}, eventCh chan<- model.Event) error {
	if r.err != nil {
		return r.err
	}

	var dm depthMessage
	if err := json.Unmarshal(r.msg, &dm); err != nil {
		log.Printf("depth parse error: %v", err)
		return nil
	}

	// 未同步: 缓存diff
	if !s.synced {
		s.pending = append(s.pending, r.msg)
		if len(s.pending) == 1 {
			requestSnapshot(snapReq)
		}
		if len(s.pending) > 5000 {
			return errSnapshotTimeout
		}
		return nil
	}

	// 已同步: 校验pu连续性
	if dm.PU != s.lastID && dm.U != s.lastID+1 {
		log.Printf("depth sequence break: pu=%d last=%d", dm.PU, s.lastID)
		resetState(s)
		requestSnapshot(snapReq)
		return nil
	}

	// 应用增量更新
	applyDiff(s.book, &dm)
	s.lastID = dm.U2
	sendBookEvent(ctx, eventCh)
	return nil
}

// handleSnapshot 处理快照合并。
func handleSnapshot(s *depthState, snap *DepthSnapshot) {
	bids, asks := snapshotToMaps(snap)

	// 回放缓冲的diff
	for _, raw := range s.pending {
		var dm depthMessage
		if err := json.Unmarshal(raw, &dm); err != nil {
			continue
		}
		if dm.U > snap.LastUpdateID {
			applyDiffToMaps(bids, asks, &dm)
			s.lastID = dm.U2
		}
	}

	// 原子替换OrderBook
	s.book.Lock()
	s.book.Bids = bids
	s.book.Asks = asks
	s.book.LastUpdateID = snap.LastUpdateID
	s.book.Unlock()

	s.readyMu.Lock()
	*s.ready = true
	s.readyMu.Unlock()

	log.Printf("depth synced: snapshot=%d buffered=%d", snap.LastUpdateID, len(s.pending))
	s.pending = nil
	s.synced = true
}

// snapshotToMaps 将快照转换为map。
func snapshotToMaps(snap *DepthSnapshot) (bids, asks map[float64]float64) {
	bids = make(map[float64]float64, len(snap.Bids))
	asks = make(map[float64]float64, len(snap.Asks))
	for _, b := range snap.Bids {
		if len(b) == 2 {
			price, _ := strconv.ParseFloat(b[0], 64)
			qty, _ := strconv.ParseFloat(b[1], 64)
			if qty > 0 {
				bids[price] = qty
			}
		}
	}
	for _, a := range snap.Asks {
		if len(a) == 2 {
			price, _ := strconv.ParseFloat(a[0], 64)
			qty, _ := strconv.ParseFloat(a[1], 64)
			if qty > 0 {
				asks[price] = qty
			}
		}
	}
	return
}

// applyDiffToMaps 将diff应用到map (不加锁)。
func applyDiffToMaps(bids, asks map[float64]float64, dm *depthMessage) {
	for _, b := range dm.B {
		if len(b) == 2 {
			price, _ := strconv.ParseFloat(b[0], 64)
			qty, _ := strconv.ParseFloat(b[1], 64)
			if qty == 0 {
				delete(bids, price)
			} else {
				bids[price] = qty
			}
		}
	}
	for _, a := range dm.A {
		if len(a) == 2 {
			price, _ := strconv.ParseFloat(a[0], 64)
			qty, _ := strconv.ParseFloat(a[1], 64)
			if qty == 0 {
				delete(asks, price)
			} else {
				asks[price] = qty
			}
		}
	}
}

// applyDiff 将增量更新应用到OrderBook (加锁)。
func applyDiff(book *model.OrderBook, dm *depthMessage) {
	book.Lock()
	applyDiffToMaps(book.Bids, book.Asks, dm)
	book.LastUpdateID = dm.U2
	book.Unlock()
}

// resetState 重置所有状态, 准备重新同步。
func resetState(s *depthState) {
	s.book.Lock()
	s.book.Bids = make(map[float64]float64)
	s.book.Asks = make(map[float64]float64)
	s.book.LastUpdateID = 0
	s.book.Unlock()

	s.readyMu.Lock()
	*s.ready = false
	s.readyMu.Unlock()

	s.pending = nil
	s.synced = false
	s.lastID = 0
}

// requestSnapshot 请求快照 (非阻塞)。
func requestSnapshot(ch chan<- struct{}) {
	select {
	case ch <- struct{}{}:
	default:
	}
}

// sendBookEvent 发送BookUpdated事件 (非阻塞)。
func sendBookEvent(ctx context.Context, ch chan<- model.Event) {
	select {
	case ch <- model.Event{Type: model.BookUpdated, Timestamp: time.Now().UnixMilli()}:
	default:
	}
}

var (
	errSnapshotTimeout  = &syncError{"snapshot not ready: buffer overflow"}
	errConnectionClosed = &syncError{"connection closed"}
)

type syncError struct{ msg string }

func (e *syncError) Error() string { return e.msg }
