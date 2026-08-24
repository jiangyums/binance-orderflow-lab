from .obi_signal import OBISignal
from .ofi_signal import OFISignal


from .signal import (
    Signal,
    SignalSide
)



class SignalEngine:


    def __init__(
        self,
        obi_weight=0.6,
        ofi_weight=0.4,
        threshold=0.8
    ):


        self.obi = OBISignal()

        self.ofi = OFISignal()



        #
        # Signal权重
        #
        self.obi_weight = obi_weight

        self.ofi_weight = ofi_weight



        #
        # 触发阈值
        #
        self.threshold = threshold





    def generate(
        self,
        feature
    ):



        obi_signal = (
            self.obi.generate(feature)
        )



        ofi_signal = (
            self.ofi.generate(feature)
        )



        score = 0.0





        #
        # OBI贡献
        #
        if obi_signal.side == SignalSide.LONG:


            score += (
                obi_signal.strength
                *
                self.obi_weight
            )


        elif obi_signal.side == SignalSide.SHORT:


            score -= (
                obi_signal.strength
                *
                self.obi_weight
            )






        #
        # OFI贡献
        #
        if ofi_signal.side == SignalSide.LONG:


            score += (
                ofi_signal.strength
                *
                self.ofi_weight
            )


        elif ofi_signal.side == SignalSide.SHORT:


            score -= (
                ofi_signal.strength
                *
                self.ofi_weight
            )







        #
        # LONG
        #
        if score > self.threshold:


            return Signal(


                feature["timestamp"],


                SignalSide.LONG,


                score,


                "OBI+OFI"


            )






        #
        # SHORT
        #
        elif score < -self.threshold:


            return Signal(


                feature["timestamp"],


                SignalSide.SHORT,


                abs(score),


                "OBI+OFI"


            )







        #
        # FLAT
        #
        return Signal(


            feature["timestamp"],


            SignalSide.FLAT,


            abs(score),


            "Weak"


        )