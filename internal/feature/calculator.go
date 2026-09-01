package feature

import "github.com/jiangyums/binance-orderflow-lab/internal/model"

// Calculator 计算一组特征并原地写入 feat。
// feat 由调用方初始化(Timestamp 已填),各实现只填充自己负责的字段;
// 禁止新建 Feature 返回——那会覆盖其他 calculator 已写入的结果。
type Calculator interface {
	Update(event model.Event, book *model.OrderBook, trades []model.Trade, feat *model.Feature)
	Reset()
}
