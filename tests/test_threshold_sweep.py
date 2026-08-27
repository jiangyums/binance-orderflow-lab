from src.orderflow.signal.engine import SignalEngine
from src.orderflow.signal.signal import SignalSide


THRESHOLDS = [
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
]



def evaluate(
    signals,
    threshold
):

    engine = SignalEngine(
        threshold=threshold
    )


    results = []


    for feature in signals:


        signal = engine.generate(
            feature
        )


        if signal is None:
            continue


        if signal.side == SignalSide.FLAT:
            continue


        results.append(
            signal
        )


    return results





def main():


    #
    # TODO:
    # 替换成你的历史feature数据读取
    #
    features = load_features()



    print(
        "===== Threshold Sweep ====="
    )


    for threshold in THRESHOLDS:


        signals = evaluate(
            features,
            threshold
        )


        print(
            f"\nthreshold={threshold}"
        )


        print(
            f"samples={len(signals)}"
        )


        if len(signals)==0:
            continue


        evaluator = SignalEvaluator()

        result = evaluator.evaluate(
            signals,
            features
        )


        print(
            result
        )




if __name__ == "__main__":
    main()