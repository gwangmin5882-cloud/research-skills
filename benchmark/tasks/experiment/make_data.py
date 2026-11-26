"""
Generates the experiment-task inputs and the answer key (deterministic).

results.csv  - 3 methods x 2 datasets x 5 seeds, Korean headers, saved in CP949
               (the encoding Korean Excel uses), with one missing value and one
               crashed run planted.
train_log.csv - validation accuracy per epoch; the baseline overfits after its peak.
answer_key.json - the facts a correct report must contain, computed independently
                  of the skill's scripts (statistics module only).
"""
import csv
import json
import math
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, "input")
os.makedirs(INP, exist_ok=True)
rng = random.Random(2026)

METHODS = ["기준모델", "제안A", "제안B"]
TRUE_ACC = {("데이터1", "기준모델"): 0.800, ("데이터1", "제안A"): 0.822, ("데이터1", "제안B"): 0.835,
            ("데이터2", "기준모델"): 0.760, ("데이터2", "제안A"): 0.762, ("데이터2", "제안B"): 0.790}
TRUE_LAT = {"기준모델": 12.0, "제안A": 13.0, "제안B": 31.0}
CRASH = ("제안B", "데이터2", 4)       # crashed run: accuracy collapses
MISSING = ("제안A", "데이터1", 2)     # accuracy not logged

rows = []
for ds in ["데이터1", "데이터2"]:
    for m in METHODS:
        for seed in range(1, 6):
            acc = TRUE_ACC[(ds, m)] + rng.gauss(0, 0.008)
            lat = TRUE_LAT[m] + rng.gauss(0, 0.8)
            acc_s = f"{acc:.4f}"
            if (m, ds, seed) == CRASH:
                acc_s = "0.1021"
            if (m, ds, seed) == MISSING:
                acc_s = ""
            rows.append([m, ds, seed, acc_s, f"{lat:.2f}"])

header = ["방법", "데이터셋", "시드", "정확도", "지연시간_ms"]
with open(os.path.join(INP, "results.csv"), "w", newline="", encoding="cp949") as fh:
    w = csv.writer(fh)
    w.writerow(header)
    w.writerows(rows)

# learning curves: baseline peaks around epoch 17 then declines (overfitting)
log = []
for m in METHODS:
    for seed in range(1, 4):
        for ep in range(1, 31):
            if m == "기준모델":
                v = 0.80 - 0.45 * math.exp(-ep / 4.5) - 0.0016 * max(0, ep - 17) ** 1.3
            elif m == "제안A":
                v = 0.823 - 0.45 * math.exp(-ep / 5.0)
            else:
                v = 0.836 - 0.48 * math.exp(-ep / 5.5)
            v += rng.gauss(0, 0.004)
            log.append([m, seed, ep, f"{v:.4f}"])
with open(os.path.join(INP, "train_log.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["방법", "시드", "에폭", "검증정확도"])
    w.writerows(log)


# ---------------------------------------------------------------- answer key
def tcrit(df):
    # two-sided 95% critical t via bisection on the regularized incomplete beta (independent of the skill)
    def betacf(a, b, x):
        qab, qap, qam = a + b, a + 1, a - 1
        c, d = 1.0, 1 - qab * x / qap
        d = 1 / d
        h = d
        for k in range(1, 300):
            m2 = 2 * k
            aa = k * (b - k) * x / ((qam + m2) * (a + m2))
            d = 1 / (1 + aa * d); c = 1 + aa / c; h *= d * c
            aa = -(a + k) * (qab + k) * x / ((a + m2) * (qap + m2))
            d = 1 / (1 + aa * d); c = 1 + aa / c; h *= d * c
        return h

    def ibeta(a, b, x):
        bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
        return bt * betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * betacf(b, a, 1 - x) / b

    lo, hi = 0.0, 100.0
    for _ in range(100):
        mid = (lo + hi) / 2
        p = ibeta(df / 2, 0.5, df / (df + mid * mid))
        lo, hi = (mid, hi) if p > 0.05 else (lo, mid)
    return lo


def vals(m, ds, col, drop_crash=False):
    out = []
    for (mm, dd, seed, acc, lat) in rows:
        if mm == m and dd == ds:
            if drop_crash and (mm, dd, seed) == CRASH:
                continue
            v = acc if col == "acc" else lat
            if v != "":
                out.append(float(v))
    return out


def welch(a, b):
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    se2 = va / len(a) + vb / len(b)
    df = se2 ** 2 / ((va / len(a)) ** 2 / (len(a) - 1) + (vb / len(b)) ** 2 / (len(b) - 1))
    t = tcrit(df)
    d = ma - mb
    return {"diff": d, "ci95": [d - t * math.sqrt(se2), d + t * math.sqrt(se2)], "n": [len(a), len(b)]}


def row_of(key):
    for i, (mm, dd, seed, *_ ) in enumerate(rows):
        if (mm, dd, seed) == key:
            return i + 2   # spreadsheet row (header = 1)


key = {
    "A_vs_base_data1": welch(vals("제안A", "데이터1", "acc"), vals("기준모델", "데이터1", "acc")),
    "A_vs_base_data2": welch(vals("제안A", "데이터2", "acc"), vals("기준모델", "데이터2", "acc")),
    "B_vs_base_data1": welch(vals("제안B", "데이터1", "acc"), vals("기준모델", "데이터1", "acc")),
    "B_vs_base_data2_with_crash": welch(vals("제안B", "데이터2", "acc"), vals("기준모델", "데이터2", "acc")),
    "B_vs_base_data2_without_crash": welch(vals("제안B", "데이터2", "acc", True), vals("기준모델", "데이터2", "acc")),
    "crash": {"row": row_of(CRASH), "method": CRASH[0], "dataset": CRASH[1], "seed": CRASH[2], "accuracy": 0.1021},
    "missing": {"row": row_of(MISSING), "method": MISSING[0], "dataset": MISSING[1], "seed": MISSING[2]},
    "latency_mean_ms": {m: statistics.fmean(vals(m, "데이터1", "lat") + vals(m, "데이터2", "lat")) for m in METHODS},
}
curve = {}
for m in METHODS:
    by_ep = {}
    for mm, seed, ep, v in log:
        if mm == m:
            by_ep.setdefault(ep, []).append(float(v))
    means = {ep: statistics.fmean(v) for ep, v in by_ep.items()}
    best_ep = max(means, key=means.get)
    curve[m] = {"best_epoch": best_ep, "best_mean": means[best_ep], "final_mean_epoch30": means[30]}
key["learning_curve"] = curve
with open(os.path.join(HERE, "answer_key.json"), "w", encoding="utf-8") as fh:
    json.dump(key, fh, ensure_ascii=False, indent=2)
print(json.dumps(key, ensure_ascii=False, indent=1))
