from typing import Optional

from .signal import Signal, SignalSide


class SignalStateTracker:
    """
    Signal状态过滤器

    作用：
    - 去除连续重复信号
    - 只输出状态变化
    - 过滤FLAT噪声

    示例:

    输入:
        FLAT
        FLAT
        SHORT
        SHORT
        LONG
        FLAT

    输出:
        SHORT
        LONG
        FLAT
    """

    def __init__(self, emit_flat=False):

        #
        # 上一次有效signal
        #
        self.last_signal: Optional[SignalSide] = None

        #
        # 是否输出FLAT变化
        #
        self.emit_flat = emit_flat

    def update(self, signal: Signal) -> Optional[Signal]:

        if signal is None:

            return None

        current = signal.side

        #
        # FLAT处理
        #
        if current == SignalSide.FLAT:

            if not self.emit_flat:

                return None

        #
        # 第一次信号
        #
        if self.last_signal is None:

            self.last_signal = current

            return signal

        #
        # 没有变化
        #
        if current == self.last_signal:

            return None

        #
        # 状态改变
        #
        self.last_signal = current

        return signal

    def reset(self):

        self.last_signal = None
