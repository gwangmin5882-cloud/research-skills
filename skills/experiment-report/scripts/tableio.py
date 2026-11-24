"""
tableio.py - shared helpers for experiment-report scripts.

Reads CSV/TSV/XLSX, detects numeric columns, computes descriptive statistics,
Welch's t-test and Holm correction. Standard library only (openpyxl for .xlsx).
"""

import csv
import io
import math
import os
import re
import statistics

MISSING = {"", "na", "n/a", "nan", "null", "none", "-", "--", "?", "#n/a", "#value!", "#div/0!"}


# ---------------------------------------------------------------- reading

def read_table(path, sheet=None):
    """Return (header, rows, info). rows: list of dicts with '_row' = spreadsheet row number."""
    ext = os.path.splitext(path)[1].lower()
    info = {"file": os.path.basename(path)}
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("Reading .xlsx needs openpyxl (pip install openpyxl), or save the sheet as CSV.")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb[sheet] if sheet else wb.worksheets[0]
        info["sheet"] = ws.title
        info["sheets"] = wb.sheetnames
        raw_rows = [["" if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]
    else:
        raw = open(path, "rb").read()
        text = None
        for enc in ("utf-8-sig", "cp949", "euc-kr", "latin-1"):
            try:
                text = raw.decode(enc)
                info["encoding"] = enc
                break
            except UnicodeDecodeError:
                continue
        try:
            dialect = csv.Sniffer().sniff(text[:8000], delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel_tab if ext in (".tsv", ".tab") else csv.excel
        info["delimiter"] = getattr(dialect, "delimiter", ",")
        raw_rows = list(csv.reader(io.StringIO(text), dialect))

    # keep spreadsheet row numbers (1-based, header = row 1)
    numbered = [(i + 1, r) for i, r in enumerate(raw_rows) if any(str(c).strip() for c in r)]
    if not numbered:
        raise SystemExit("The table is empty.")
    _, head = numbered[0]
    header, seen = [], {}
    for i, h in enumerate(head):
        h = str(h).strip() or f"col{i + 1}"
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 1
        header.append(h)
    rows = []
    for rownum, r in numbered[1:]:
        r = list(r) + [""] * (len(header) - len(r))
        d = {h: str(r[i]).strip() for i, h in enumerate(header)}
        d["_row"] = rownum
        rows.append(d)
    info["rows"] = len(rows)
    return header, rows, info


def parse_number(s):
    """'1,234.5' -> 1234.5 ; '85%' -> 85.0 ; missing/non-numeric -> None."""
    if s is None:
        return None
    s = str(s).strip()
    if s.lower() in MISSING:
        return None
    pct = s.endswith("%")
    if pct:
        s = s[:-1].strip()
    if re.fullmatch(r"[-+]?\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def is_missing(s):
    return s is None or str(s).strip().lower() in MISSING


def profile_columns(header, rows):
    prof = []
    for h in header:
        vals = [r[h] for r in rows]
        present = [v for v in vals if not is_missing(v)]
        nums = [parse_number(v) for v in present]
        n_num = sum(1 for v in nums if v is not None)
        numeric = bool(present) and n_num / len(present) >= 0.9
        examples = []
        for v in present:
            if v not in examples:
                examples.append(v)
            if len(examples) == 3:
                break
        prof.append({
            "name": h,
            "type": "numeric" if numeric else "text",
            "non_missing": len(present),
            "missing": len(vals) - len(present),
            "unique": len(set(present)),
            "non_numeric_values": (len(present) - n_num) if numeric else None,
            "examples": examples,
        })
    return prof


ID_LIKE = re.compile(r"^(id|idx|index|seed|run|run_id|trial|rep|repeat|replicate|fold|no|#|번호|시드|반복)$", re.I)


def exclude_rows(rows, spec):
    """spec: '15,22' -> drop rows with those spreadsheet row numbers (header = row 1)."""
    if not spec:
        return rows, []
    drop = {int(x) for x in re.split(r"[,\s]+", str(spec).strip()) if x}
    return [r for r in rows if r["_row"] not in drop], sorted(drop)


def decimals_for(values):
    """One number of decimals per metric, from its magnitude (about 4 significant digits)."""
    vals = [abs(v) for v in values if v is not None and v != 0]
    if not vals:
        return 2
    return max(0, min(8, 3 - math.floor(math.log10(max(vals)))))


def fmt_d(x, d):
    if x is None:
        return "-"
    return f"{x:,.{d}f}" if abs(x) >= 1000 else f"{x:.{d}f}"


def apply_filters(rows, filters):
    """filters: list of 'col=value' or 'col!=value'."""
    out = rows
    for f in filters or []:
        if "!=" in f:
            col, val = f.split("!=", 1)
            out = [r for r in out if r.get(col.strip()) != val.strip()]
        elif "=" in f:
            col, val = f.split("=", 1)
            out = [r for r in out if r.get(col.strip()) == val.strip()]
    return out


def group_label(row, group_cols):
    return " / ".join(row[c] if not is_missing(row[c]) else "(missing)" for c in group_cols) if group_cols else "all"


def ordered_groups(rows, group_cols, order=None):
    labels = []
    for r in rows:
        g = group_label(r, group_cols)
        if g not in labels:
            labels.append(g)
    if order:
        pref = [o for o in order if o in labels]
        labels = pref + [g for g in labels if g not in pref]
    return labels


# ---------------------------------------------------------------- statistics

def _betacf(a, b, x, maxit=500, eps=3e-14):
    fpmin = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fpmin else fpmin)
    h = d
    for m in range(1, maxit + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    bt = math.exp(lbt)
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_p_two_sided(t, df):
    if df <= 0 or t is None or math.isnan(t):
        return None
    return betainc(df / 2.0, 0.5, df / (df + t * t))


def t_crit(df, alpha=0.05):
    """Two-sided critical value of Student's t."""
    lo, hi = 0.0, 1e4
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_p_two_sided(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def describe(values):
    v = [x for x in values if x is not None]
    n = len(v)
    out = {"n": n}
    if n == 0:
        return out
    mean = statistics.fmean(v)
    out.update({"mean": mean, "min": min(v), "max": max(v), "median": statistics.median(v)})
    if n >= 2:
        sd = statistics.stdev(v)
        sem = sd / math.sqrt(n)
        tc = t_crit(n - 1)
        out.update({"sd": sd, "sem": sem, "ci95": [mean - tc * sem, mean + tc * sem]})
    if n >= 4:
        q1, _, q3 = statistics.quantiles(v, n=4, method="inclusive")
        out.update({"q1": q1, "q3": q3})
    return out


def robust_outliers(pairs, alpha=0.01):
    """pairs: [(row, value)] -> the most extreme value if Grubbs' test rejects it at `alpha`
    (two-sided). Quartile- and MAD-based rules flag ordinary spread in the tiny samples typical
    of experiments (e.g. 5 seeds); Grubbs' test accounts for n, so it only flags values that
    are far from everything else, such as a crashed or mis-logged run."""
    vals = [v for _, v in pairs]
    n = len(vals)
    if n < 4:
        return []
    mean = statistics.fmean(vals)
    sd = statistics.stdev(vals)
    if sd == 0:
        return []
    r_ext, v_ext = max(pairs, key=lambda p: abs(p[1] - mean))
    g = abs(v_ext - mean) / sd
    t = t_crit(n - 2, alpha / n)           # upper alpha/(2n) point of t(n-2)
    g_crit = (n - 1) / math.sqrt(n) * math.sqrt(t * t / (n - 2 + t * t))
    if g > g_crit:
        return [{"row": r_ext, "value": v_ext, "grubbs_g": g, "g_critical": g_crit}]
    return []


def welch(a, b):
    """Welch's t-test of a vs b (a - b)."""
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    se2 = va / na + vb / nb
    diff = ma - mb
    if se2 == 0:
        return {"mean_diff": diff, "t": None, "df": None, "p": None, "ci95_diff": None,
                "cohen_d": None, "note": "zero variance in both groups"}
    se = math.sqrt(se2)
    t = diff / se
    df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    tc = t_crit(df)
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)) if (na + nb - 2) > 0 else 0
    d = diff / pooled if pooled > 0 else None
    return {"mean_diff": diff, "t": t, "df": df, "p": t_p_two_sided(t, df),
            "ci95_diff": [diff - tc * se, diff + tc * se], "cohen_d": d, "note": None}


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (None stays None)."""
    idx = [i for i, p in enumerate(pvals) if p is not None]
    m = len(idx)
    adj = [None] * len(pvals)
    running = 0.0
    for rank, i in enumerate(sorted(idx, key=lambda k: pvals[k])):
        val = min(1.0, (m - rank) * pvals[i])
        running = max(running, val)
        adj[i] = running
    return adj


def fmt(x, digits=None):
    """Readable number for reports (full precision stays in JSON)."""
    if x is None:
        return "-"
    if isinstance(x, int):
        return f"{x:,}"
    ax = abs(x)
    if digits is not None:
        return f"{x:.{digits}f}"
    if ax == 0:
        return "0"
    if ax >= 1000:
        return f"{x:,.1f}"
    if ax >= 1:
        return f"{x:.3f}".rstrip("0").rstrip(".") if ax < 100 else f"{x:.2f}"
    if ax >= 0.001:
        return f"{x:.4f}"
    return f"{x:.2e}"


def fmt_p(p):
    if p is None:
        return "-"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"
