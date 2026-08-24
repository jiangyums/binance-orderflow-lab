class SignalStateTracker:

    def __init__(self):
        self.last_signal = None


    def update(self, signal):

        if signal.side == self.last_signal:
            return None


        self.last_signal = signal.side

        return signal