import numpy as np

def compute_mir(prices: np.ndarray) -> float:
    prices = np.asarray(prices, dtype=np.float64)
    if len(prices) < 2:
        return 0.0
    if np.any(prices <= 0):
        # per spec: if min or max <=0 return 0
        if float(np.min(prices)) <= 0:
            return 0.0
    # Brute-force MIR per Wu et al. 2013: R(j,k)=P_k/P_j-1, MIR=max|R| with j<k
    # Optimized v-pattern check first for O(n) fast path, with tie handling
    # Fall back to brute-force scan to ensure correctness for duplicate extrema
    n = len(prices)
    best = 0.0
    best_abs = 0.0
    for j in range(n - 1):
        pj = float(prices[j])
        if pj <= 0:
            continue
        for k in range(j + 1, n):
            pk = float(prices[k])
            if pk <= 0:
                continue
            r = pk / pj - 1.0
            ar = abs(r)
            if ar > best_abs:
                best_abs = ar
                best = r
    return float(best)

def compute_mir_batch(prices: np.ndarray, window_size: int) -> np.ndarray:
    prices = np.asarray(prices, dtype=np.float64)
    out = np.full(len(prices), np.nan, dtype=np.float64)
    for i in range(window_size, len(prices)+1):
        out[i-1] = compute_mir(prices[i-window_size:i])
    return out
