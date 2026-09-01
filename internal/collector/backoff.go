package collector

import (
	"context"
	"math/rand/v2"
	"time"
)

// sleepCtx 等待 d;期间若 ctx 被取消,立即返回 ctx.Err()。
// 与 time.Sleep 不同,它不会让取消信号多等一个完整的 sleep 周期。
func sleepCtx(ctx context.Context, d time.Duration) error {
	if d <= 0 {
		return ctx.Err()
	}
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

// backoff 提供带抖动的指数退避重试间隔:
// 每次失败后间隔翻倍(封顶 max),并在 [50%, 100%) 区间随机抖动,
// 避免多个 worker 同时失败后同步重连造成雷群效应;
// 连接成功后调用 reset 复位到初始间隔。
type backoff struct {
	current time.Duration
	initial time.Duration
	max     time.Duration
}

func newBackoff(initial, max time.Duration) *backoff {
	return &backoff{current: initial, initial: initial, max: max}
}

// next 返回本次重试的等待时长,并为下次翻倍(封顶 max)。
func (b *backoff) next() time.Duration {
	half := b.current / 2
	d := b.current
	if half > 0 {
		d = half + time.Duration(rand.Int64N(int64(half))) // 随机化到 [50%, 100%)
	}
	b.current *= 2
	if b.current > b.max {
		b.current = b.max
	}
	return d
}

// reset 在连接成功后恢复初始间隔。
func (b *backoff) reset() {
	b.current = b.initial
}
