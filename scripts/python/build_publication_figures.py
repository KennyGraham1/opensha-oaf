#!/usr/bin/env python3
"""Build publication-grade diagnostic figures for the NZ ETAS issue-time study."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass
class Experiment:
    key: str
    label: str
    summary_file: str
    pycsep_dir: str
    issue_hours: float


EXPERIMENTS: list[Experiment] = [
    Experiment("premainshock", "Generic", "nz_etas_simulations_premainshock.txt", "build/pycsep_premainshock", 0.0),
    Experiment("2h", "2 h", "nz_etas_simulations_2h.txt", "build/pycsep_2h", 2.0),
    Experiment("6h", "6 h", "nz_etas_simulations_6h.txt", "build/pycsep_6h", 6.0),
    Experiment("12h", "12 h", "nz_etas_simulations_12h.txt", "build/pycsep_12h", 12.0),
    Experiment("1d", "1 d", "nz_etas_simulations_1d.txt", "build/pycsep_1d", 24.0),
    Experiment("2d", "2 d", "nz_etas_simulations_2d.txt", "build/pycsep_2d", 48.0),
    Experiment("3d", "3 d", "nz_etas_simulations_3d.txt", "build/pycsep_3d", 72.0),
    Experiment("7d", "7 d", "nz_etas_simulations.txt", "build/pycsep", 168.0),
]


# ── Regime colour / style encoding ──────────────────────────────────────────
# Regime 1 (STAI + branching-identifiability failure): generic, 2h – 1d
# Regime 2 (Omori underestimation): 2d – 3d
# Regime 3 (calibrated): 7d only
REGIME_COLORS: dict[str, str] = {
    "premainshock": "#8B0000",  # dark red     – Regime 1
    "2h":           "#DC143C",  # crimson      – Regime 1
    "6h":           "#FF6347",  # tomato       – Regime 1
    "12h":          "#FF8C00",  # dark orange  – Regime 1
    "1d":           "#DAA520",  # goldenrod    – Regime 1
    "2d":           "#4169E1",  # royal blue   – Regime 2
    "3d":           "#00008B",  # dark blue    – Regime 2
    "7d":           "#1B7837",  # forest green – Regime 3
}
REGIME_LINESTYLES: dict[str, str] = {
    "premainshock": "--",
    "2h":           "-",
    "6h":           "--",
    "12h":          "-.",
    "1d":           ":",
    "2d":           "-",
    "3d":           "--",
    "7d":           "-",
}
REGIME_MARKERS: dict[str, str] = {
    "premainshock": "D",
    "2h":           "o",
    "6h":           "^",
    "12h":          "s",
    "1d":           "v",
    "2d":           "P",
    "3d":           "h",
    "7d":           "*",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_float(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text, re.MULTILINE)
    return float(m.group(1)) if m else None


def _parse_int(text: str, pattern: str) -> int | None:
    m = re.search(pattern, text, re.MULTILINE)
    return int(m.group(1)) if m else None


def parse_summary(path: Path) -> dict[str, float | int | None]:
    text = _read(path)
    expected = _parse_float(text, r"Expected Number of Events:\s*\n\s*M>=3\.0:\s*([\d.]+)")
    m = re.search(r"M>=3\.0:\s+5th=(\d+)\s+Median=(\d+)\s+95th=(\d+)", text)
    p5 = int(m.group(1)) if m else None
    median = int(m.group(2)) if m else None
    p95 = int(m.group(3)) if m else None
    ams = _parse_float(text, r"ams-value:\s*([-\d.]+)")
    a_val = _parse_float(text, r"a-value:\s*([-\d.]+)")
    p_val = _parse_float(text, r"p-value:\s*([-\d.]+)")
    c_val = _parse_float(text, r"c-value:\s*([-\d.]+)")
    return {
        "expected_m3": expected,
        "summary_p5": p5,
        "summary_median": median,
        "summary_p95": p95,
        "ams": ams,
        "a": a_val,
        "p": p_val,
        "c": c_val,
    }


def parse_pycsep_summary(path: Path) -> dict[str, float | int | None]:
    text = _read(path)
    n_obs = _parse_int(text, r"Observed event count in testing region:\s*`?(\d+)`?")
    ensemble_median = _parse_int(text, r"Ensemble event-count median:\s*`?(\d+)`?")
    indirect_share = _parse_float(text, r"Median indirect \(`Gen>=2`\) share of `M>=Mc` events:\s*`?([\d.]+)`?%")
    q_match = re.search(r"catalog_number_test.*?quantile\s+`\(([-\d.e+]+),\s*([-\d.e+]+)\)`", text)
    n_q_lo = float(q_match.group(1)) if q_match else None
    n_q_hi = float(q_match.group(2)) if q_match else None
    zero_spatial_events = _parse_int(text, r"Observed events in zero ETAS spatial-rate cells:\s*`?(\d+)`?")
    zero_sm_events = _parse_int(text, r"Observed events in zero ETAS space-magnitude bins:\s*`?(\d+)`?")
    zero_cells_match = re.search(
        r"Zero-rate ETAS spatial cells in testing region:\s*`?(\d+)`? of `?(\d+)`?",
        text,
    )
    zero_cells = int(zero_cells_match.group(1)) if zero_cells_match else None
    total_cells = int(zero_cells_match.group(2)) if zero_cells_match else None
    rolling_p = _parse_float(text, r"Rolling calibration KS statistic:.*?p-value\s+`?([-\d.e+]+)`?")
    return {
        "n_obs": n_obs,
        "ensemble_median": ensemble_median,
        "indirect_share": indirect_share,
        "n_q_lo": n_q_lo,
        "n_q_hi": n_q_hi,
        "zero_spatial_events": zero_spatial_events,
        "zero_sm_events": zero_sm_events,
        "zero_cells": zero_cells,
        "total_cells": total_cells,
        "rolling_p": rolling_p,
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_dataset(root: Path) -> list[dict]:
    rows: list[dict] = []
    for exp in EXPERIMENTS:
        summary = parse_summary(root / exp.summary_file)
        py_summary = parse_pycsep_summary(root / exp.pycsep_dir / "nz_etas_pycsep_summary.md")
        n_test = load_json(root / exp.pycsep_dir / "evaluation_json" / "catalog_number_test.json")
        rolling = load_json(root / exp.pycsep_dir / "evaluation_json" / "rolling_number_calibration.json")

        n_dist = np.asarray(n_test["test_distribution"], dtype=float)
        rolling_dist = np.asarray(rolling.get("test_distribution", []), dtype=float)

        row = {
            "key": exp.key,
            "label": exp.label,
            "issue_hours": exp.issue_hours,
            **summary,
            **py_summary,
            "n_dist": n_dist,
            "n_mean": float(np.mean(n_dist)),
            "n_p05": float(np.percentile(n_dist, 5.0)),
            "n_p95": float(np.percentile(n_dist, 95.0)),
            "n_max": float(np.max(n_dist)),
            "rolling_dist": rolling_dist,
            "rolling_stat": float(rolling.get("observed_statistic", np.nan)),
        }
        if row["expected_m3"] and row["ensemble_median"]:
            row["expected_to_py_median"] = float(row["expected_m3"] / row["ensemble_median"])
        else:
            row["expected_to_py_median"] = np.nan
        if row["expected_m3"] and row["n_mean"]:
            row["expected_to_py_mean"] = float(row["expected_m3"] / row["n_mean"])
        else:
            row["expected_to_py_mean"] = np.nan
        rows.append(row)
    return rows


def classify_n_test(q_lo: float | None, q_hi: float | None) -> str:
    if q_lo is None or q_hi is None:
        return "unknown"
    if q_lo < 0.025 and q_hi >= 0.025:
        return "underpredict"
    if q_hi < 0.025 and q_lo >= 0.025:
        return "overpredict"
    if q_lo >= 0.025 and q_hi >= 0.025:
        return "pass"
    return "fail-both"


def _ensemble_crps(samples: np.ndarray, observed: float) -> float:
    x = np.asarray(samples, dtype=float).ravel()
    # Ensemble CRPS: E|X-y| - 0.5 E|X-X'|, with O(n log n) second term.
    first = np.mean(np.abs(x - observed))
    x_sorted = np.sort(x)
    n = x_sorted.size
    coeff = (2 * np.arange(1, n + 1) - n - 1).astype(float)
    pairwise_mean_abs = 2.0 * np.sum(coeff * x_sorted) / (n * n)
    second = 0.5 * pairwise_mean_abs
    return float(first - second)


def _interval_score(samples: np.ndarray, observed: float, alpha: float = 0.1) -> tuple[float, float, float, int]:
    x = np.asarray(samples, dtype=float).ravel()
    low = float(np.quantile(x, alpha / 2.0))
    high = float(np.quantile(x, 1.0 - alpha / 2.0))
    score = high - low
    if observed < low:
        score += (2.0 / alpha) * (low - observed)
    elif observed > high:
        score += (2.0 / alpha) * (observed - high)
    covered = int(low <= observed <= high)
    return float(score), low, high, covered


def _empirical_pmf_int(samples: np.ndarray) -> np.ndarray:
    x = np.asarray(samples, dtype=int).ravel()
    if x.size == 0:
        return np.zeros(1, dtype=float)
    counts = np.bincount(x, minlength=int(np.max(x)) + 1).astype(float)
    total = float(np.sum(counts))
    if total <= 0:
        return np.zeros_like(counts)
    return counts / total


def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    length = max(len(p), len(q))
    if len(p) < length:
        p = np.pad(p, (0, length - len(p)))
    if len(q) < length:
        q = np.pad(q, (0, length - len(q)))
    m = 0.5 * (p + q)
    p_mask = (p > 0) & (m > 0)
    q_mask = (q > 0) & (m > 0)
    kl_pm = np.sum(p[p_mask] * np.log2(p[p_mask] / m[p_mask]))
    kl_qm = np.sum(q[q_mask] * np.log2(q[q_mask] / m[q_mask]))
    return float(0.5 * (kl_pm + kl_qm))


def _js_from_samples_int(a: np.ndarray, b: np.ndarray) -> float:
    return _js_divergence(_empirical_pmf_int(a), _empirical_pmf_int(b))


def _bootstrap_ci(values: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float).ravel()
    return float(np.quantile(arr, alpha / 2.0)), float(np.quantile(arr, 1.0 - alpha / 2.0))


def _bootstrap_metric_distribution_1d(
    samples: np.ndarray,
    stat_fn: Any,
    rng: np.random.Generator,
    n_boot: int = 1000,
) -> np.ndarray:
    x = np.asarray(samples, dtype=float).ravel()
    n = x.size
    out = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        out[i] = float(stat_fn(x[idx]))
    return out


def _bootstrap_metric_distribution_daily(
    daily_samples: np.ndarray,
    stat_fn: Any,
    rng: np.random.Generator,
    n_boot: int = 1000,
) -> np.ndarray:
    x = np.asarray(daily_samples, dtype=float)
    n = x.shape[0]
    out = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        out[i] = float(stat_fn(x[idx, :]))
    return out


def _sse_segment_mean(y: np.ndarray, start: int, end: int) -> float:
    seg = y[start:end]
    mu = np.mean(seg)
    return float(np.sum((seg - mu) ** 2))


def _fit_best_breaks(y: np.ndarray, min_seg: int = 2) -> dict[str, Any]:
    n = len(y)
    # Null (one segment)
    sse0 = _sse_segment_mean(y, 0, n)
    # One-break model
    best1 = {"sse": np.inf, "b1": None}
    for b1 in range(min_seg, n - min_seg + 1):
        sse = _sse_segment_mean(y, 0, b1) + _sse_segment_mean(y, b1, n)
        if sse < best1["sse"]:
            best1 = {"sse": sse, "b1": b1}
    # Two-break model
    best2 = {"sse": np.inf, "b1": None, "b2": None}
    for b1 in range(min_seg, n - 2 * min_seg + 1):
        for b2 in range(b1 + min_seg, n - min_seg + 1):
            sse = (
                _sse_segment_mean(y, 0, b1)
                + _sse_segment_mean(y, b1, b2)
                + _sse_segment_mean(y, b2, n)
            )
            if sse < best2["sse"]:
                best2 = {"sse": sse, "b1": b1, "b2": b2}
    return {"null": {"sse": sse0}, "one_break": best1, "two_break": best2}


def _bic_from_sse(sse: float, n: int, k: int) -> float:
    sse_adj = max(sse, 1.0e-12)
    return float(n * np.log(sse_adj / n) + k * np.log(n))


def _run_change_point_analysis(
    rows: list[dict],
    probabilistic_metrics: list[dict[str, Any]],
    output_csv: Path,
    output_md: Path,
    output_png: Path,
) -> None:
    # x is ordered by issue time in EXPERIMENTS registry already.
    issue = np.array([float(r["issue_hours"]) for r in rows], dtype=float)
    labels = [str(r["label"]) for r in rows]
    count_ratio = np.array([float(r["ensemble_median"]) / float(r["n_obs"]) for r in rows], dtype=float)
    weekly_crps = np.array([float(m["weekly_crps"]) for m in probabilistic_metrics], dtype=float)
    log10_weekly_crps = np.log10(np.maximum(weekly_crps, 1.0e-12))

    # bootstrap distributions already attached to probabilistic_metrics for uncertainty propagation
    ratio_boot = [np.asarray(r["count_ratio_boot"], dtype=float) for r in rows]
    crps_boot = [np.asarray(m["weekly_crps_boot"], dtype=float) for m in probabilistic_metrics]
    log_crps_boot = [np.log10(np.maximum(np.asarray(m["weekly_crps_boot"], dtype=float), 1.0e-12)) for m in probabilistic_metrics]

    rng = np.random.default_rng(20260402)
    results: list[dict[str, Any]] = []
    plot_payload: dict[str, Any] = {}

    for metric_name, y, boot_list in [
        ("count_ratio", count_ratio, ratio_boot),
        ("log10_weekly_crps", log10_weekly_crps, log_crps_boot),
    ]:
        fit = _fit_best_breaks(y, min_seg=2)
        n = len(y)
        sse0 = float(fit["null"]["sse"])
        sse1 = float(fit["one_break"]["sse"])
        sse2 = float(fit["two_break"]["sse"])
        b1_one = int(fit["one_break"]["b1"])
        b1 = int(fit["two_break"]["b1"])
        b2 = int(fit["two_break"]["b2"])

        # Permutation tests for one-break and two-break improvements.
        n_perm = 10000
        observed_delta1 = sse0 - sse1
        observed_delta = sse0 - sse2
        observed_delta21 = sse1 - sse2
        perm_delta1 = np.empty(n_perm, dtype=float)
        perm_deltas = np.empty(n_perm, dtype=float)
        perm_delta21 = np.empty(n_perm, dtype=float)
        for i in range(n_perm):
            yp = rng.permutation(y)
            fp = _fit_best_breaks(yp, min_seg=2)
            perm_delta1[i] = float(fp["null"]["sse"] - fp["one_break"]["sse"])
            perm_deltas[i] = float(fp["null"]["sse"] - fp["two_break"]["sse"])
            perm_delta21[i] = float(fp["one_break"]["sse"] - fp["two_break"]["sse"])
        p_perm1 = float((1.0 + np.sum(perm_delta1 >= observed_delta1)) / (n_perm + 1.0))
        p_perm = float((1.0 + np.sum(perm_deltas >= observed_delta)) / (n_perm + 1.0))
        p_perm21 = float((1.0 + np.sum(perm_delta21 >= observed_delta21)) / (n_perm + 1.0))

        # Bootstrap breakpoint support by sampling one draw per run from each run-specific bootstrap distribution.
        n_boot_break = 5000
        b1_counts: dict[int, int] = {}
        b2_counts: dict[int, int] = {}
        for _ in range(n_boot_break):
            yb = np.array([boot[rng.integers(0, boot.size)] for boot in boot_list], dtype=float)
            fb = _fit_best_breaks(yb, min_seg=2)
            bb1 = int(fb["two_break"]["b1"])
            bb2 = int(fb["two_break"]["b2"])
            b1_counts[bb1] = b1_counts.get(bb1, 0) + 1
            b2_counts[bb2] = b2_counts.get(bb2, 0) + 1

        b1_support = 100.0 * b1_counts.get(b1, 0) / n_boot_break
        b2_support = 100.0 * b2_counts.get(b2, 0) / n_boot_break

        result = {
            "metric": metric_name,
            "n_points": n,
            "best_one_break_index": b1_one,
            "one_break_after_label": labels[b1_one - 1],
            "one_break_before_label": labels[b1_one],
            "one_break_after_issue_hours": issue[b1_one - 1],
            "one_break_after_issue_days": issue[b1_one - 1] / 24.0,
            "best_break1_index": b1,
            "best_break2_index": b2,
            "break1_after_label": labels[b1 - 1],
            "break1_before_label": labels[b1],
            "break2_after_label": labels[b2 - 1],
            "break2_before_label": labels[b2],
            "break1_after_issue_hours": issue[b1 - 1],
            "break2_after_issue_hours": issue[b2 - 1],
            "break1_after_issue_days": issue[b1 - 1] / 24.0,
            "break2_after_issue_days": issue[b2 - 1] / 24.0,
            "sse_null": sse0,
            "sse_one_break": sse1,
            "sse_two_break": sse2,
            "delta_sse_one_vs_null": observed_delta1,
            "delta_sse_two_vs_null": observed_delta,
            "delta_sse_two_vs_one": observed_delta21,
            "bic_null": _bic_from_sse(sse0, n, 1),
            "bic_one_break": _bic_from_sse(sse1, n, 2),
            "bic_two_break": _bic_from_sse(sse2, n, 3),
            "perm_p_one_vs_null": p_perm1,
            "perm_p_two_vs_null": p_perm,
            "perm_p_two_vs_one": p_perm21,
            "break1_bootstrap_support_percent": b1_support,
            "break2_bootstrap_support_percent": b2_support,
        }
        results.append(result)
        plot_payload[metric_name] = {"y": y, "b1": b1, "b2": b2, "perm_p": p_perm}

    # CSV
    headers = list(results[0].keys())
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for r in results:
            f.write(",".join(str(r[h]) for h in headers) + "\n")

    # Summary markdown
    lines = [
        "# Change-Point / Segmented Analysis Summary",
        "",
        "- Model family: piecewise-constant mean with 0, 1, or 2 breakpoints.",
        "- Minimum segment size: 2 issue-time points.",
        "- Significance: permutation test (10,000 permutations) for two-break model vs null.",
        "- Breakpoint support: bootstrap resampling from run-specific metric distributions (5,000 replicates).",
        "",
    ]
    for r in results:
        lines.append(
            f"- **{r['metric']}**: one-break at {r['one_break_after_label']} ({float(r['one_break_after_issue_days']):.2f} d; "
            f"p={float(r['perm_p_one_vs_null']):.4f}); two-breaks after {r['break1_after_label']} "
            f"({float(r['break1_after_issue_days']):.2f} d) and {r['break2_after_label']} ({float(r['break2_after_issue_days']):.2f} d), "
            f"p(two vs null)={float(r['perm_p_two_vs_null']):.4f}, p(two vs one)={float(r['perm_p_two_vs_one']):.4f}, "
            f"support=({float(r['break1_bootstrap_support_percent']):.1f}%, "
            f"{float(r['break2_bootstrap_support_percent']):.1f}%)."
        )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Figure
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    fig.suptitle("Segmented Change-Point Diagnostics by Issue Time", fontsize=13, fontweight="bold")
    for ax, metric_name, y_label in [
        (axes[0], "count_ratio", "Median / observed count"),
        (axes[1], "log10_weekly_crps", "log10(weekly CRPS)"),
    ]:
        payload = plot_payload[metric_name]
        y = np.asarray(payload["y"], dtype=float)
        b1 = int(payload["b1"])
        b2 = int(payload["b2"])
        ax.plot(issue, y, marker="o", linewidth=1.8, color="#1f78b4")
        # Segment means
        means = [np.mean(y[:b1]), np.mean(y[b1:b2]), np.mean(y[b2:])]
        seg_edges = [(0, b1), (b1, b2), (b2, len(y))]
        for (s, e), mu in zip(seg_edges, means):
            ax.hlines(mu, issue[s], issue[e - 1], colors="#e31a1c", linewidth=2.2)
        ax.axvline(issue[b1 - 1], color="#555555", linestyle="--", linewidth=1.2)
        ax.axvline(issue[b2 - 1], color="#555555", linestyle="--", linewidth=1.2)
        ax.set_xscale("log")
        ax.set_xticks([2, 6, 12, 24, 48, 72, 168], ["2h", "6h", "12h", "1d", "2d", "3d", "7d"])
        ax.set_xlabel("Issue time")
        ax.set_ylabel(y_label)
        ax.grid(alpha=0.3, linestyle=":")
        ax.set_title(f"{metric_name}: p={payload['perm_p']:.4f}")
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_regime_figure(rows: list[dict], output_path: Path) -> None:
    x = np.arange(len(rows))
    labels = [row["label"] for row in rows]

    fig, axes = plt.subplots(3, 2, figsize=(16, 15), constrained_layout=True)
    fig.suptitle(
        "Kaikōura ETAS Fixed-Horizon Diagnostics (days 7–14)\n"
        "Issue-time sensitivity across count, support, and calibration metrics",
        fontsize=14,
        fontweight="bold",
    )

    # Panel A: count distributions (N-test empirical)
    ax = axes[0, 0]
    dists = [row["n_dist"] for row in rows]
    bp = ax.boxplot(dists, positions=x, patch_artist=True, whis=(5, 95), showfliers=False)
    for patch, row in zip(bp["boxes"], rows):
        patch.set_facecolor(REGIME_COLORS.get(str(row["key"]), "#cfe8ff"))
        patch.set_alpha(0.75)
        patch.set_edgecolor("#333333")
        patch.set_linewidth(1.2)
    for median in bp["medians"]:
        median.set_color("#111111")
        median.set_linewidth(2.2)
    n_obs = rows[0]["n_obs"] if rows else None
    if n_obs is not None:
        ax.axhline(float(n_obs), color="#111111", linestyle="--", linewidth=1.5, label=f"Observed N={int(n_obs)}")
    ax.set_title("A) Empirical Count Distributions by Issue Time")
    ax.set_ylabel("Catalog event count (M≥3, NZ region)")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")
    if n_obs is not None:
        ax.legend(loc="upper left", fontsize=9)

    # Panel B: count ratio with 5th–95th ensemble range and bootstrap 95% CI
    ax = axes[0, 1]
    ratio = np.array([float(row["ensemble_median"]) / float(row["n_obs"]) for row in rows])
    lo = np.array([float(row["n_p05"]) / float(row["n_obs"]) for row in rows])
    hi = np.array([float(row["n_p95"]) / float(row["n_obs"]) for row in rows])
    # Bootstrap 95% CI on median/observed ratio
    _rng_b = np.random.default_rng(20260402)
    ci_lows_b = np.empty(len(rows))
    ci_highs_b = np.empty(len(rows))
    for _bi, _row in enumerate(rows):
        _n_obs_v = float(_row["n_obs"])
        _boot = _bootstrap_metric_distribution_1d(
            np.asarray(_row["n_dist"], dtype=float),
            lambda _x, _n=_n_obs_v: float(np.median(_x) / _n),
            rng=_rng_b,
            n_boot=1000,
        )
        ci_lows_b[_bi], ci_highs_b[_bi] = _bootstrap_ci(_boot, alpha=0.05)
    class_color = {"underpredict": "#d73027", "overpredict": "#4575b4", "pass": "#1a9850", "fail-both": "#762a83", "unknown": "#777777"}
    colors = [class_color[classify_n_test(row["n_q_lo"], row["n_q_hi"])] for row in rows]
    # Ensemble 5th–95th range (light whiskers)
    ax.errorbar(x, ratio, yerr=np.vstack([ratio - lo, hi - ratio]),
                fmt="none", ecolor="#aaaaaa", alpha=0.55, capsize=3, linewidth=1.0, label="Ensemble 5–95%")
    # Bootstrap 95% CI on median ratio (thick, dark)
    ax.errorbar(x, ratio, yerr=np.vstack([ratio - ci_lows_b, ci_highs_b - ratio]),
                fmt="none", ecolor="#333333", alpha=0.9, capsize=5, linewidth=2.0, label="Bootstrap 95% CI")
    ax.scatter(x, ratio, c=colors, s=100, zorder=4, edgecolor="#111111", linewidth=0.8)
    ax.axhline(1.0, color="#1a9850", linestyle="--", linewidth=1.5, label="Unbiased (ratio = 1)")
    ax.axvline(4.5, color="#aaaaaa", linestyle=":", linewidth=1.2)
    ax.axvline(6.5, color="#aaaaaa", linestyle=":", linewidth=1.2)
    ax.text(2.0, max(hi) * 0.95, "Regime 1", color="#555555", ha="center", fontsize=9)
    ax.text(5.5, max(hi) * 0.95, "Regime 2", color="#555555", ha="center", fontsize=9)
    ax.text(7.0, max(hi) * 0.95, "Regime 3", color="#555555", ha="center", fontsize=9)
    ax.set_title("B) Count Bias Ratio  (5–95% ensemble range + bootstrap 95% CI)")
    ax.set_ylabel("Median / observed count")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")
    ax.legend(loc="upper right", fontsize=8)

    # Panel C: p-value and indirect share
    ax = axes[1, 0]
    p_values = np.array([float(row["p"]) for row in rows])
    indirect = np.array([float(row["indirect_share"]) for row in rows])
    ax.plot(x, p_values, marker="o", color="#7b3294", linewidth=2, label="MLE p-value")
    ax.set_ylabel("MLE p-value", color="#7b3294")
    ax.tick_params(axis="y", labelcolor="#7b3294")
    ax.set_ylim(0.82, 1.16)
    ax2 = ax.twinx()
    ax2.plot(x, indirect, marker="s", color="#008837", linewidth=2, label="Indirect share (%)")
    ax2.set_ylabel("Indirect generation≥2 share (%)", color="#008837")
    ax2.tick_params(axis="y", labelcolor="#008837")
    ax2.set_ylim(0, 40)
    ax.axvline(4.5, color="#aaaaaa", linestyle=":", linewidth=1.2)
    ax.axvline(6.5, color="#aaaaaa", linestyle=":", linewidth=1.2)
    ax.set_title("C) Parameter-Regime Shift: Omori p and Branching Share")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")

    # Panel D: support limitations
    ax = axes[1, 1]
    zero_spatial = np.array([float(row["zero_spatial_events"]) for row in rows])
    zero_sm = np.array([float(row["zero_sm_events"]) for row in rows])
    zero_cells_frac = np.array([float(row["zero_cells"]) / float(row["total_cells"]) for row in rows])
    ax.plot(x, zero_spatial, marker="o", linewidth=2, color="#e66101", label="Observed in zero spatial cells")
    ax.plot(x, zero_sm, marker="^", linewidth=2, color="#b2182b", label="Observed in zero space-mag bins")
    ax.set_ylabel("Observed events")
    ax2 = ax.twinx()
    ax2.plot(x, 100 * zero_cells_frac, marker="s", linewidth=2, color="#4d4d4d", label="Zero-rate cell fraction")
    ax2.set_ylabel("Zero-rate cells (%)")
    ax.set_title("D) Spatial-Support Diagnostics")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], loc="upper left", fontsize=8)

    # Panel E: analytical vs empirical consistency
    ax = axes[2, 0]
    expected = np.array([float(row["expected_m3"]) for row in rows])
    py_mean = np.array([float(row["n_mean"]) for row in rows])
    py_median = np.array([float(row["ensemble_median"]) for row in rows])
    summary_median = np.array([float(row["summary_median"]) for row in rows])
    ax.plot(x, expected, marker="o", color="#d73027", linewidth=2, label="Analytical expected E[N] (summary)")
    ax.plot(x, py_mean, marker="s", color="#4575b4", linewidth=2, label="Empirical mean (pyCSEP N-dist)")
    ax.plot(x, py_median, marker="^", color="#1a9850", linewidth=2, label="Empirical median (pyCSEP)")
    ax.plot(x, summary_median, marker="D", color="#984ea3", linewidth=2, label="Empirical median (summary)")
    ax.set_yscale("log")
    ax.set_ylabel("Count (log scale)")
    ax.set_title("E) Analytical-vs-Empirical Count Consistency Check")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")
    ax.legend(loc="upper left", fontsize=8)

    # Panel F: rolling sub-window diagnostics
    ax = axes[2, 1]
    for idx, row in enumerate(rows):
        vals = np.asarray(row["rolling_dist"], dtype=float)
        if vals.size:
            jitter = np.linspace(-0.15, 0.15, vals.size)
            ax.scatter(np.full(vals.size, idx) + jitter, vals, color="#8c8c8c", s=25, alpha=0.85)
    rolling_p = np.array([float(row["rolling_p"]) for row in rows])
    ax.plot(x, rolling_p, marker="o", color="#08519c", linewidth=2.2, label="Rolling calibration KS p-value")
    ax.axhline(0.05, color="#d73027", linestyle="--", linewidth=1.2, label="p=0.05 threshold")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("F) Rolling Sub-window Consistency and Calibration")
    ax.set_ylabel("Calibration metric")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")
    ax.legend(loc="upper left", fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_metrics(rows: list[dict], output_csv: Path, output_md: Path) -> None:
    rng = np.random.default_rng(20260402)
    headers = [
        "key",
        "label",
        "issue_hours",
        "n_obs",
        "pycsep_median",
        "pycsep_mean",
        "pycsep_p05",
        "pycsep_p95",
        "pycsep_max",
        "median_ratio",
        "median_ratio_boot_ci95_low",
        "median_ratio_boot_ci95_high",
        "analytical_expected",
        "expected_to_py_mean",
        "expected_to_py_median",
        "n_q_lo",
        "n_q_hi",
        "rolling_p",
        "indirect_share_percent",
        "p_value",
        "zero_spatial_events",
        "zero_space_mag_events",
        "zero_cell_fraction_percent",
    ]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for row in rows:
            n_obs = float(row["n_obs"])
            n_dist = np.asarray(row["n_dist"], dtype=float)
            ratio_boot = _bootstrap_metric_distribution_1d(
                n_dist,
                lambda x: float(np.median(x) / n_obs),
                rng=rng,
                n_boot=2000,
            )
            ratio_ci_low, ratio_ci_high = _bootstrap_ci(ratio_boot, alpha=0.05)
            row["count_ratio_boot"] = ratio_boot
            values = [
                row["key"],
                row["label"],
                f"{row['issue_hours']:.1f}",
                f"{int(row['n_obs'])}",
                f"{int(row['ensemble_median'])}",
                f"{row['n_mean']:.3f}",
                f"{row['n_p05']:.3f}",
                f"{row['n_p95']:.3f}",
                f"{row['n_max']:.3f}",
                f"{float(row['ensemble_median']) / n_obs:.6f}",
                f"{ratio_ci_low:.6f}",
                f"{ratio_ci_high:.6f}",
                f"{float(row['expected_m3']):.3f}",
                f"{float(row['expected_to_py_mean']):.3f}",
                f"{float(row['expected_to_py_median']):.3f}",
                f"{float(row['n_q_lo']):.6f}",
                f"{float(row['n_q_hi']):.6f}",
                f"{float(row['rolling_p']):.6g}",
                f"{float(row['indirect_share']):.2f}",
                f"{float(row['p']):.3f}",
                f"{int(row['zero_spatial_events'])}",
                f"{int(row['zero_sm_events'])}",
                f"{100.0 * float(row['zero_cells']) / float(row['total_cells']):.3f}",
            ]
            f.write(",".join(values) + "\n")

    lines = [
        "# Publication Diagnostics Summary",
        "",
        "- Source: fixed-horizon Kaikōura rerun outputs (`build/pycsep*`, `nz_etas_simulations*.txt`).",
        "- Figure: `build/comparison/publication_regime_diagnostics.png`.",
        "- CSV table: `build/comparison/publication_regime_metrics.csv`.",
        "",
        "## Key Diagnostics",
        "",
    ]
    for row in rows:
        ratio = float(row["ensemble_median"]) / float(row["n_obs"])
        ci_low, ci_high = _bootstrap_ci(np.asarray(row["count_ratio_boot"], dtype=float), alpha=0.05)
        lines.append(
            f"- {row['label']}: median/obs={ratio:.3f}, N-test=({float(row['n_q_lo']):.3f},{float(row['n_q_hi']):.3f}), "
            f"95% CI=({ci_low:.3f},{ci_high:.3f}), rolling p={float(row['rolling_p']):.3g}, "
            f"E[N]/pyCSEP-mean={float(row['expected_to_py_mean']):.2f}, "
            f"indirect={float(row['indirect_share']):.1f}%."
        )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_mainshock_time(path: Path) -> datetime:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload["origin_time"]
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_observed_daily_counts(observed_csv: Path, mainshock_time: datetime) -> np.ndarray:
    bins = np.arange(7.0, 15.0, 1.0)
    counts = np.zeros(7, dtype=int)
    with observed_csv.open("r", encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        try:
            idx = header.index("time_string")
        except ValueError as exc:
            raise RuntimeError(f"time_string column not found in {observed_csv}") from exc
        for line in f:
            parts = line.strip().split(",")
            if len(parts) <= idx:
                continue
            raw = parts[idx]
            if not raw:
                continue
            dt = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
            rel_days = (dt - mainshock_time).total_seconds() / 86400.0
            if 7.0 <= rel_days < 14.0:
                day = int(np.floor(rel_days)) - 7
                if 0 <= day < 7:
                    counts[day] += 1
    return counts


def _sim_dir_for_key(root: Path, key: str) -> Path:
    if key == "7d":
        return root / "simulated_catalogs"
    return root / f"simulated_catalogs_{key}"


def _load_daily_sim_counts(sim_dir: Path, mag_min: float = 3.0) -> np.ndarray:
    bins = np.arange(7.0, 15.0, 1.0)
    all_counts: list[np.ndarray] = []
    for path in sorted(sim_dir.glob("sim_*.txt")):
        day_counts = np.zeros(7, dtype=int)
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("Time "):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                t = float(parts[0])
                m = float(parts[1])
                if m < mag_min or t < 7.0 or t >= 14.0:
                    continue
                idx = int(np.floor(t)) - 7
                if 0 <= idx < 7:
                    day_counts[idx] += 1
        all_counts.append(day_counts)
    if not all_counts:
        raise RuntimeError(f"No simulated catalogs found in {sim_dir}")
    return np.asarray(all_counts, dtype=float)


def compute_daily_diagnostics(root: Path, rows: list[dict]) -> dict[str, Any]:
    mainshock = _parse_mainshock_time(root / "build/pycsep/cache/2016p858000_mainshock.json")
    observed_counts = _parse_observed_daily_counts(
        root / "build/pycsep/cache/2016p858000_d7_14_mc3_observed.csv",
        mainshock,
    )
    day_labels = [f"{d}-{d+1}" for d in range(7, 14)]

    sim_arrays: list[np.ndarray] = []
    for row in rows:
        sim_dir = _sim_dir_for_key(root, str(row["key"]))
        sim_arrays.append(_load_daily_sim_counts(sim_dir))

    means = np.vstack([arr.mean(axis=0) for arr in sim_arrays])
    medians = np.vstack([np.median(arr, axis=0) for arr in sim_arrays])
    p10 = np.vstack([np.percentile(arr, 10, axis=0) for arr in sim_arrays])
    p90 = np.vstack([np.percentile(arr, 90, axis=0) for arr in sim_arrays])
    stds = np.vstack([arr.std(axis=0, ddof=1) for arr in sim_arrays])
    z = (observed_counts[None, :] - means) / np.maximum(stds, 1.0e-6)
    pit = np.vstack([(arr <= observed_counts[None, :]).mean(axis=0) for arr in sim_arrays])
    return {
        "observed_counts": observed_counts,
        "day_labels": day_labels,
        "sim_arrays": sim_arrays,
        "means": means,
        "medians": medians,
        "p10": p10,
        "p90": p90,
        "stds": stds,
        "z": z,
        "pit": pit,
    }


def make_daily_decomposition_figure(
    rows: list[dict],
    daily: dict[str, Any],
    output_path: Path,
    output_csv: Path,
) -> None:
    observed_counts = np.asarray(daily["observed_counts"], dtype=float)
    day_labels = list(daily["day_labels"])
    sim_arrays = list(daily["sim_arrays"])
    means = np.asarray(daily["means"], dtype=float)
    medians = np.asarray(daily["medians"], dtype=float)
    p10 = np.asarray(daily["p10"], dtype=float)
    p90 = np.asarray(daily["p90"], dtype=float)
    stds = np.asarray(daily["stds"], dtype=float)
    z = np.asarray(daily["z"], dtype=float)
    pit = np.asarray(daily["pit"], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12), constrained_layout=True)
    fig.suptitle(
        "Daily Decomposition of Fixed-Horizon ETAS Skill (days 7–14)\n"
        "Issue-time-specific temporal allocation diagnostics",
        fontsize=14,
        fontweight="bold",
    )

    # A) observed vs median forecast trajectories — all 8 runs
    ax = axes[0, 0]
    x = np.arange(7)
    ax.plot(x, observed_counts, color="#111111", linewidth=2.8, marker="*",
            markersize=10, label="Observed", zorder=10)
    for idx, row in enumerate(rows):
        key = str(row["key"])
        color = REGIME_COLORS.get(key, "#888888")
        ls = REGIME_LINESTYLES.get(key, "-")
        mk = REGIME_MARKERS.get(key, "o")
        lw = 2.5 if key == "7d" else 1.4
        ms = 8 if key == "7d" else 5
        ax.plot(x, medians[idx], linewidth=lw, linestyle=ls, marker=mk, markersize=ms,
                color=color, label=str(row["label"]))
        ax.fill_between(x, p10[idx], p90[idx], alpha=0.08, color=color)
    ax.set_xticks(x, day_labels)
    ax.set_ylabel("Daily event count (M≥3)")
    ax.set_title("A) Daily Forecast Trajectories — All 8 Issue Times\n"
                 "(10–90% shaded; observed = black stars; colours = regime)")
    ax.grid(alpha=0.3, linestyle=":")
    ax.legend(loc="upper right", fontsize=7, ncol=2)

    # B) standardized residual heatmap (clipped ±5, cell-annotated)
    ax = axes[0, 1]
    z_clipped = np.clip(z, -5, 5)
    im = ax.imshow(z_clipped, cmap="RdBu_r", aspect="auto", vmin=-5, vmax=5)
    ax.set_yticks(np.arange(len(rows)), [str(r["label"]) for r in rows])
    ax.set_xticks(np.arange(7), day_labels)
    ax.set_title("B) Standardised Residual  Z = (Obs − Mean) / SD  [clipped ±5]")
    plt.colorbar(im, ax=ax, label="Z-score (clipped ±5)")
    for _i in range(z.shape[0]):
        for _j in range(z.shape[1]):
            _val = z[_i, _j]
            _txt_color = "white" if abs(z_clipped[_i, _j]) > 2.5 else "#111111"
            ax.text(_j, _i, f"{_val:.1f}", ha="center", va="center",
                    fontsize=7, color=_txt_color)

    # C) PIT-like empirical CDF at observed (annotated)
    ax = axes[1, 0]
    im2 = ax.imshow(pit, cmap="coolwarm", aspect="auto", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(rows)), [str(r["label"]) for r in rows])
    ax.set_xticks(np.arange(7), day_labels)
    ax.set_title("C) Empirical CDF at Observed  P(N_sim ≤ N_obs) — daily")
    ax.set_xlabel("Day bin after mainshock (days)")
    plt.colorbar(im2, ax=ax, label="PIT  (0 = over-predict, 1 = under-predict)")
    for _i in range(pit.shape[0]):
        for _j in range(pit.shape[1]):
            _pval = pit[_i, _j]
            _txt_color = "white" if (_pval < 0.15 or _pval > 0.85) else "#111111"
            ax.text(_j, _i, f"{_pval:.2f}", ha="center", va="center",
                    fontsize=7, color=_txt_color)

    # D) average absolute daily error and sharpness
    ax = axes[1, 1]
    mae_daily = np.mean(np.abs(medians - observed_counts[None, :]), axis=1)
    sharpness = np.mean(p90 - p10, axis=1)
    issue = np.array([float(row["issue_hours"]) for row in rows])
    ax.plot(issue, mae_daily, marker="o", linewidth=2.0, color="#e66101", label="Mean absolute daily error")
    ax2 = ax.twinx()
    ax2.plot(issue, sharpness, marker="s", linewidth=2.0, color="#5e3c99", label="Mean daily 10–90 width")
    ax.set_xscale("log")
    ax.set_xticks([2, 6, 12, 24, 48, 72, 168], ["2h", "6h", "12h", "1d", "2d", "3d", "7d"])
    ax.set_xlabel("Issue time")
    ax.set_ylabel("Mean absolute daily error")
    ax2.set_ylabel("Mean daily 10–90 interval width")
    ax.set_title("D) Daily Accuracy vs Sharpness Trade-off")
    ax.grid(alpha=0.3, linestyle=":")
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], loc="upper right", fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    # export daily matrix stats
    headers = [
        "run",
        "issue_hours",
        "day_bin",
        "observed",
        "sim_mean",
        "sim_median",
        "sim_p10",
        "sim_p90",
        "sim_std",
        "z_score",
        "pit_cdf",
    ]
    with output_csv.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for i, row in enumerate(rows):
            for d in range(7):
                values = [
                    str(row["key"]),
                    f"{float(row['issue_hours']):.1f}",
                    f"{7+d}-{8+d}",
                    str(int(observed_counts[d])),
                    f"{means[i, d]:.6f}",
                    f"{medians[i, d]:.6f}",
                    f"{p10[i, d]:.6f}",
                    f"{p90[i, d]:.6f}",
                    f"{stds[i, d]:.6f}",
                    f"{z[i, d]:.6f}",
                    f"{pit[i, d]:.6f}",
                ]
                f.write(",".join(values) + "\n")


def make_probabilistic_scores_figure(
    rows: list[dict],
    daily: dict[str, Any],
    output_path: Path,
    output_csv: Path,
    output_md: Path,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(20260402)
    observed_counts = np.asarray(daily["observed_counts"], dtype=float)
    sim_arrays = [np.asarray(arr, dtype=float) for arr in daily["sim_arrays"]]
    pit = np.asarray(daily["pit"], dtype=float)
    z = np.asarray(daily["z"], dtype=float)

    ref_idx = next((i for i, row in enumerate(rows) if str(row["key"]) == "7d"), len(rows) - 1)
    ref_weekly = np.asarray(rows[ref_idx]["n_dist"], dtype=int)
    ref_daily = sim_arrays[ref_idx]

    metrics: list[dict[str, float | str]] = []
    for idx, row in enumerate(rows):
        n_obs = float(row["n_obs"])
        weekly_dist = np.asarray(row["n_dist"], dtype=float)
        weekly_crps = _ensemble_crps(weekly_dist, n_obs)
        weekly_is90, w_low, w_high, w_cover = _interval_score(weekly_dist, n_obs, alpha=0.1)
        weekly_width90 = w_high - w_low
        weekly_dispersion = float(np.var(weekly_dist, ddof=1) / max(np.mean(weekly_dist), 1.0e-9))
        weekly_js_ref = _js_from_samples_int(weekly_dist, ref_weekly)
        weekly_pit = float(np.mean(weekly_dist <= n_obs))
        weekly_abs_pit_dev = abs(weekly_pit - 0.5)

        daily_dist = sim_arrays[idx]
        daily_crps_vals = [_ensemble_crps(daily_dist[:, d], observed_counts[d]) for d in range(7)]
        daily_is_vals = []
        daily_width_vals = []
        daily_cov_vals = []
        for d in range(7):
            score, d_low, d_high, d_cover = _interval_score(daily_dist[:, d], observed_counts[d], alpha=0.1)
            daily_is_vals.append(score)
            daily_width_vals.append(d_high - d_low)
            daily_cov_vals.append(d_cover)

        daily_js_ref = float(
            np.mean(
                [
                    _js_from_samples_int(daily_dist[:, d], ref_daily[:, d])
                    for d in range(7)
                ]
            )
        )
        daily_abs_pit_dev = float(np.mean(np.abs(pit[idx] - 0.5)))
        daily_extreme_pit_frac = float(np.mean((pit[idx] < 0.05) | (pit[idx] > 0.95)))
        daily_abs_z = float(np.mean(np.abs(z[idx])))

        weekly_crps_boot = _bootstrap_metric_distribution_1d(
            weekly_dist,
            lambda x: _ensemble_crps(x, n_obs),
            rng=rng,
            n_boot=1500,
        )
        daily_crps_boot = _bootstrap_metric_distribution_daily(
            daily_dist,
            lambda m: float(np.mean([_ensemble_crps(m[:, d], observed_counts[d]) for d in range(7)])),
            rng=rng,
            n_boot=1500,
        )
        weekly_crps_ci_low, weekly_crps_ci_high = _bootstrap_ci(weekly_crps_boot, alpha=0.05)
        daily_crps_ci_low, daily_crps_ci_high = _bootstrap_ci(daily_crps_boot, alpha=0.05)

        metrics.append(
            {
                "key": str(row["key"]),
                "label": str(row["label"]),
                "issue_hours": float(row["issue_hours"]),
                "n_test_class": classify_n_test(row["n_q_lo"], row["n_q_hi"]),
                "weekly_crps": weekly_crps,
                "weekly_crps_ci95_low": weekly_crps_ci_low,
                "weekly_crps_ci95_high": weekly_crps_ci_high,
                "weekly_interval_score_90": weekly_is90,
                "weekly_interval_width_90": weekly_width90,
                "weekly_coverage_90": float(w_cover),
                "weekly_dispersion_index": weekly_dispersion,
                "weekly_pit": weekly_pit,
                "weekly_abs_pit_dev": weekly_abs_pit_dev,
                "weekly_js_to_7d": weekly_js_ref,
                "daily_mean_crps": float(np.mean(daily_crps_vals)),
                "daily_mean_crps_ci95_low": daily_crps_ci_low,
                "daily_mean_crps_ci95_high": daily_crps_ci_high,
                "daily_mean_interval_score_90": float(np.mean(daily_is_vals)),
                "daily_mean_interval_width_90": float(np.mean(daily_width_vals)),
                "daily_coverage_90": float(np.mean(daily_cov_vals)),
                "daily_abs_pit_dev": daily_abs_pit_dev,
                "daily_extreme_pit_frac": daily_extreme_pit_frac,
                "daily_abs_z": daily_abs_z,
                "daily_js_to_7d": daily_js_ref,
                "weekly_crps_boot": weekly_crps_boot,
                "daily_mean_crps_boot": daily_crps_boot,
            }
        )

    x = np.arange(len(metrics))
    labels = [str(m["label"]) for m in metrics]
    issue = np.array([float(m["issue_hours"]) for m in metrics])
    weekly_crps = np.array([float(m["weekly_crps"]) for m in metrics])
    weekly_crps_ci_lo = np.array([float(m["weekly_crps_ci95_low"]) for m in metrics])
    weekly_crps_ci_hi = np.array([float(m["weekly_crps_ci95_high"]) for m in metrics])
    weekly_is = np.array([float(m["weekly_interval_score_90"]) for m in metrics])
    daily_crps = np.array([float(m["daily_mean_crps"]) for m in metrics])
    daily_crps_ci_lo = np.array([float(m["daily_mean_crps_ci95_low"]) for m in metrics])
    daily_crps_ci_hi = np.array([float(m["daily_mean_crps_ci95_high"]) for m in metrics])
    daily_is = np.array([float(m["daily_mean_interval_score_90"]) for m in metrics])
    daily_abs_pit = np.array([float(m["daily_abs_pit_dev"]) for m in metrics])
    daily_width = np.array([float(m["daily_mean_interval_width_90"]) for m in metrics])
    weekly_js = np.array([float(m["weekly_js_to_7d"]) for m in metrics])
    daily_js = np.array([float(m["daily_js_to_7d"]) for m in metrics])
    # Coverage data for the overconfidence panel (Panel E)
    n_obs_cov = float(rows[0]["n_obs"])
    cov_p05 = np.array([float(r["n_p05"]) for r in rows])
    cov_p95 = np.array([float(r["n_p95"]) for r in rows])
    cov_med = np.array([float(r["ensemble_median"]) for r in rows])

    regime_bar_colors = [REGIME_COLORS.get(str(m["key"]), "#888888") for m in metrics]

    fig, axd = plt.subplot_mosaic(
        [["A", "B"],
         ["C", "D"],
         ["E", "E"]],
        figsize=(16, 18),
        constrained_layout=True,
    )
    fig.suptitle(
        "Probabilistic Forecast Skill Diagnostics (Fixed Horizon, days 7–14)\n"
        "Proper scores, calibration-sharpness, distributional distance, and coverage by issue time",
        fontsize=14,
        fontweight="bold",
    )

    # A) Weekly CRPS with bootstrap 95% CI
    ax = axd["A"]
    ax.bar(x, weekly_crps, color=regime_bar_colors, edgecolor="#333333", linewidth=0.8, alpha=0.82)
    ax.errorbar(x, weekly_crps,
                yerr=np.vstack([weekly_crps - weekly_crps_ci_lo, weekly_crps_ci_hi - weekly_crps]),
                fmt="none", ecolor="#111111", capsize=5, linewidth=1.8, zorder=5)
    ax.set_title("A) Weekly CRPS with 95% Bootstrap CI\n(lower = better; colours = regime)", fontsize=10)
    ax.set_ylabel("CRPS")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":", axis="y")
    leg_patches = [
        matplotlib.patches.Patch(color="#8B0000", label="Regime 1 (STAI + branching)"),
        matplotlib.patches.Patch(color="#4169E1", label="Regime 2 (Omori underest.)"),
        matplotlib.patches.Patch(color="#1B7837", label="Regime 3 (calibrated, 7d)"),
    ]
    ax.legend(handles=leg_patches, fontsize=8, loc="upper right")

    # B) Daily mean CRPS with bootstrap 95% CI
    ax = axd["B"]
    ax.bar(x, daily_crps, color=regime_bar_colors, edgecolor="#333333", linewidth=0.8, alpha=0.82)
    ax.errorbar(x, daily_crps,
                yerr=np.vstack([daily_crps - daily_crps_ci_lo, daily_crps_ci_hi - daily_crps]),
                fmt="none", ecolor="#111111", capsize=5, linewidth=1.8, zorder=5)
    ax.set_title("B) Daily Mean CRPS with 95% Bootstrap CI\n(lower = better; colours = regime)", fontsize=10)
    ax.set_ylabel("Daily mean CRPS")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":", axis="y")

    # C) Calibration-sharpness frontier with chronological trajectory
    ax = axd["C"]
    # Dashed trajectory line connecting issue times in chronological order
    ax.plot(daily_abs_pit, daily_width, color="#aaaaaa", linewidth=1.2,
            linestyle="--", zorder=1, alpha=0.7)
    for i, m in enumerate(metrics):
        ax.scatter(
            daily_abs_pit[i],
            daily_width[i],
            s=80 + 25 * np.log10(max(issue[i], 1.0)),
            color=REGIME_COLORS.get(str(m["key"]), "#888888"),
            edgecolor="#111111",
            linewidth=0.7,
            alpha=0.95,
            zorder=3,
        )
        ax.text(daily_abs_pit[i] + 0.005, daily_width[i] + 0.20, str(m["label"]), fontsize=8)
    # Arrow indicating direction: second-to-last → last-but-one transition
    if len(metrics) >= 3:
        ax.annotate(
            "",
            xy=(daily_abs_pit[-2], daily_width[-2]),
            xytext=(daily_abs_pit[-3], daily_width[-3]),
            arrowprops=dict(arrowstyle="->", color="#555555", lw=1.4),
        )
    ax.axvline(0.0, color="#555555", linestyle=":", linewidth=1.0)
    ax.set_xlabel("Mean |daily PIT − 0.5|  (calibration error; 0 = perfect)")
    ax.set_ylabel("Mean 90% prediction interval width  (sharpness)")
    ax.set_title("C) Daily Calibration-Sharpness Frontier\n"
                 "(dashed = trajectory early → late; arrow = last-step direction)", fontsize=10)
    ax.grid(alpha=0.3, linestyle=":")

    # D) Distributional distance from 7d reference
    ax = axd["D"]
    ax.bar(x - 0.18, weekly_js, width=0.35, color="#8da0cb", edgecolor="#253494", label="Weekly JS to 7d")
    ax.bar(x + 0.18, daily_js, width=0.35, color="#fc8d62", edgecolor="#b15928", label="Daily JS to 7d")
    ax.set_ylim(0, 1.05)
    ax.set_title("D) Distributional Distance to 7d Reference  (0 = identical, 1 = max)")
    ax.set_ylabel("Jensen-Shannon divergence (bits)")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")
    ax.legend(loc="upper right", fontsize=8)

    # E) 90% Predictive Interval Coverage vs Observed N — the double-failure panel
    ax = axd["E"]
    for i, row in enumerate(rows):
        p05_v = float(row["n_p05"])
        p95_v = float(row["n_p95"])
        med_v = float(row["ensemble_median"])
        covered = p05_v <= n_obs_cov <= p95_v
        col = "#1a9850" if covered else "#d73027"
        ax.barh(i, p95_v - p05_v, left=p05_v, height=0.65,
                color=col, alpha=0.50, edgecolor=col, linewidth=1.5)
        ax.plot(med_v, i, marker="D", color=col, markersize=8, zorder=4)
        ax.text(
            max(p95_v, n_obs_cov) + 20, i,
            f"[{int(p05_v)}, {int(p95_v)}]",
            va="center", fontsize=8, color="#444444",
        )
    ax.axvline(n_obs_cov, color="#111111", linestyle="--", linewidth=2.2,
               label=f"Observed N = {int(n_obs_cov)}")
    ax.set_yticks(range(len(rows)), [str(r["label"]) for r in rows], fontsize=10)
    ax.set_xlabel("Simulated event count (M≥3, days 7–14)", fontsize=10)
    ax.set_title(
        "E) 90% Predictive Interval Coverage  "
        "(green = N_obs inside interval; red = outside → double failure)",
        fontsize=10,
    )
    ax.grid(alpha=0.3, linestyle=":", axis="x")
    ax.legend(loc="lower right", fontsize=9)
    n_covered = sum(1 for r in rows if float(r["n_p05"]) <= n_obs_cov <= float(r["n_p95"]))
    ax.text(
        0.98, 0.03,
        f"Coverage: {n_covered}/{len(rows)} runs  ({100 * n_covered / len(rows):.0f}%)",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#cccccc"),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "key",
        "label",
        "issue_hours",
        "n_test_class",
        "weekly_crps",
        "weekly_crps_ci95_low",
        "weekly_crps_ci95_high",
        "weekly_interval_score_90",
        "weekly_interval_width_90",
        "weekly_coverage_90",
        "weekly_dispersion_index",
        "weekly_pit",
        "weekly_abs_pit_dev",
        "weekly_js_to_7d",
        "daily_mean_crps",
        "daily_mean_crps_ci95_low",
        "daily_mean_crps_ci95_high",
        "daily_mean_interval_score_90",
        "daily_mean_interval_width_90",
        "daily_coverage_90",
        "daily_abs_pit_dev",
        "daily_extreme_pit_frac",
        "daily_abs_z",
        "daily_js_to_7d",
    ]
    with output_csv.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for m in metrics:
            row = [
                str(m["key"]),
                str(m["label"]),
                f"{float(m['issue_hours']):.1f}",
                str(m["n_test_class"]),
                f"{float(m['weekly_crps']):.6f}",
                f"{float(m['weekly_crps_ci95_low']):.6f}",
                f"{float(m['weekly_crps_ci95_high']):.6f}",
                f"{float(m['weekly_interval_score_90']):.6f}",
                f"{float(m['weekly_interval_width_90']):.6f}",
                f"{float(m['weekly_coverage_90']):.6f}",
                f"{float(m['weekly_dispersion_index']):.6f}",
                f"{float(m['weekly_pit']):.6f}",
                f"{float(m['weekly_abs_pit_dev']):.6f}",
                f"{float(m['weekly_js_to_7d']):.6f}",
                f"{float(m['daily_mean_crps']):.6f}",
                f"{float(m['daily_mean_crps_ci95_low']):.6f}",
                f"{float(m['daily_mean_crps_ci95_high']):.6f}",
                f"{float(m['daily_mean_interval_score_90']):.6f}",
                f"{float(m['daily_mean_interval_width_90']):.6f}",
                f"{float(m['daily_coverage_90']):.6f}",
                f"{float(m['daily_abs_pit_dev']):.6f}",
                f"{float(m['daily_extreme_pit_frac']):.6f}",
                f"{float(m['daily_abs_z']):.6f}",
                f"{float(m['daily_js_to_7d']):.6f}",
            ]
            f.write(",".join(row) + "\n")

    best_weekly = min(metrics, key=lambda m: float(m["weekly_crps"]))
    best_daily = min(metrics, key=lambda m: float(m["daily_mean_crps"]))
    worst_daily = max(metrics, key=lambda m: float(m["daily_mean_crps"]))
    lines = [
        "# Probabilistic Skill Summary",
        "",
        "- Figure: `build/comparison/publication_probabilistic_scores.png`.",
        "- CSV table: `build/comparison/publication_probabilistic_scores.csv`.",
        "",
        "## Highlights",
        "",
        f"- Best weekly CRPS: **{best_weekly['label']}** ({float(best_weekly['weekly_crps']):.2f}).",
        f"- Best daily mean CRPS: **{best_daily['label']}** ({float(best_daily['daily_mean_crps']):.2f}).",
        f"- Worst daily mean CRPS: **{worst_daily['label']}** ({float(worst_daily['daily_mean_crps']):.2f}).",
        "- Early runs (generic to 1d) show extreme daily PIT concentration near 1.0, confirming one-sided underprediction.",
        "- Intermediate runs (2d, 3d) reduce score penalties but remain one-sided overpredictive in daily bins.",
        "- The 7d run uniquely minimizes both score penalties and distributional divergence to the calibrated reference.",
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8")
    return metrics


def _safe_cmd(cmd: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return "unknown"


def write_reproducibility_metadata(root: Path, output_md: Path) -> None:
    import sys

    commit = _safe_cmd(["git", "rev-parse", "HEAD"], root)
    pycsep_version = "unknown"
    try:
        import csep  # type: ignore

        pycsep_version = getattr(csep, "__version__", "unknown")
    except Exception:
        pass

    lines = [
        "# Reproducibility Metadata",
        "",
        f"- Git commit: `{commit}`",
        f"- UTC generation time: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Python: `{sys.version.split()[0]}`",
        f"- NumPy: `{np.__version__}`",
        f"- Matplotlib: `{matplotlib.__version__}`",
        f"- pyCSEP: `{pycsep_version}`",
        "- Bootstrap RNG seed (publication diagnostics): `20260402`",
        "- Change-point permutation RNG seed: `20260402`",
        "- Change-point permutations: `10000`",
        "- Breakpoint bootstrap replicates: `5000`",
        "",
        "## Run Order (fixed-horizon issue-time set)",
        "",
        "1. `./run_etas_pipeline.sh etas_config_premainshock.json`",
        "2. `./run_etas_pipeline.sh etas_config_2h.json`",
        "3. `./run_etas_pipeline.sh etas_config_6h.json`",
        "4. `./run_etas_pipeline.sh etas_config_12h.json`",
        "5. `./run_etas_pipeline.sh etas_config_1d.json`",
        "6. `./run_etas_pipeline.sh etas_config_2d.json`",
        "7. `./run_etas_pipeline.sh etas_config_3d.json`",
        "8. `./run_etas_pipeline.sh etas_config.json`",
        "9. `python3 scripts/python/compare_etas_experiments.py`",
        "10. `python3 scripts/python/build_publication_figures.py`",
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root directory.")
    parser.add_argument("--output-dir", default="build/comparison", help="Output directory for figures and tables.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    output_dir = root / args.output_dir
    rows = build_dataset(root)
    daily = compute_daily_diagnostics(root, rows)
    make_regime_figure(rows, output_dir / "publication_regime_diagnostics.png")
    write_metrics(
        rows,
        output_dir / "publication_regime_metrics.csv",
        output_dir / "publication_diagnostics_summary.md",
    )
    make_daily_decomposition_figure(
        rows,
        daily,
        output_dir / "publication_daily_decomposition.png",
        output_dir / "publication_daily_metrics.csv",
    )
    probabilistic_metrics = make_probabilistic_scores_figure(
        rows,
        daily,
        output_dir / "publication_probabilistic_scores.png",
        output_dir / "publication_probabilistic_scores.csv",
        output_dir / "publication_probabilistic_summary.md",
    )
    _run_change_point_analysis(
        rows,
        probabilistic_metrics,
        output_dir / "publication_change_point_analysis.csv",
        output_dir / "publication_change_point_summary.md",
        output_dir / "publication_change_points.png",
    )
    write_reproducibility_metadata(
        root,
        output_dir / "publication_reproducibility_metadata.md",
    )
    print(f"Wrote {output_dir / 'publication_regime_diagnostics.png'}")
    print(f"Wrote {output_dir / 'publication_regime_metrics.csv'}")
    print(f"Wrote {output_dir / 'publication_diagnostics_summary.md'}")
    print(f"Wrote {output_dir / 'publication_daily_decomposition.png'}")
    print(f"Wrote {output_dir / 'publication_daily_metrics.csv'}")
    print(f"Wrote {output_dir / 'publication_probabilistic_scores.png'}")
    print(f"Wrote {output_dir / 'publication_probabilistic_scores.csv'}")
    print(f"Wrote {output_dir / 'publication_probabilistic_summary.md'}")
    print(f"Wrote {output_dir / 'publication_change_point_analysis.csv'}")
    print(f"Wrote {output_dir / 'publication_change_point_summary.md'}")
    print(f"Wrote {output_dir / 'publication_change_points.png'}")
    print(f"Wrote {output_dir / 'publication_reproducibility_metadata.md'}")


if __name__ == "__main__":
    main()
