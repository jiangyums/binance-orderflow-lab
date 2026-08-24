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
        # 报告用强度：两分量强度之和（范围 0~2），可超过 1.0，
        # 使 1-2 / >2 强度桶有意义；与加权 score（仅用于阈值判断）解耦
        #
        strength = (
            obi_signal.strength
            +
            ofi_signal.strength
        )

        #
        # LONG
        #
        if score > self.threshold:


            return Signal(


                feature["timestamp"],


                SignalSide.LONG,


                strength,


                "OBI+OFI"


            )






        #
        # SHORT
        #
        elif score < -self.threshold:


            return Signal(


                feature["timestamp"],


                SignalSide.SHORT,


                strength,


                "OBI+OFI"


            )







        #
        # FLAT
        #
        return Signal(


            feature["timestamp"],


            SignalSide.FLAT,


            strength,


            "Weak"


        )