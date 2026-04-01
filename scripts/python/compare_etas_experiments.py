#!/usr/bin/env python3
"""
compare_etas_experiments.py — Compare ETAS forecast experiments across data windows.

For each experiment this script reads:
  - nz_etas_simulations_<label>.txt   : fitted parameters, expected counts, percentiles
  - build/pycsep_<label>/nz_etas_pycsep_summary.md : pyCSEP evaluation statistics
  - build/pycsep_<label>/evaluation_json/*.json      : raw test results

It produces:
  1. A console table comparing all experiments
  2. A multi-panel comparison figure (PNG)
  3. A markdown report (compare_experiments_report.md)

Usage:
  python3 scripts/python/compare_etas_experiments.py
  python3 scripts/python/compare_etas_experiments.py --root /path/to/opensha-oaf
  python3 scripts/python/compare_etas_experiments.py --output-dir build/comparison
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


# ---------------------------------------------------------------------------
# Experiment registry — add new experiments here in chronological order
# ---------------------------------------------------------------------------

@dataclass
class ExperimentDef:
    label: str                   # short label, e.g. "premainshock"
    data_days: float             # length of MLE data window in days
    forecast_start: float        # forecast start (days post-mainshock)
    forecast_end: float          # forecast end   (days post-mainshock)
    model_type: str              # "generic" or "sequence-specific"
    summary_file: str            # relative to root
    pycsep_dir: str              # relative to root


EXPERIMENTS: list[ExperimentDef] = [
    ExperimentDef(
        label="generic\n(0 h data)",
        data_days=0.0,
        forecast_start=0.5,
        forecast_end=14.5,
        model_type="generic",
        summary_file="nz_etas_simulations_premainshock.txt",
        pycsep_dir="build/pycsep_premainshock",
    ),
    ExperimentDef(
        label="2 h data",
        data_days=2/24,
        forecast_start=2/24,
        forecast_end=14.5,
        model_type="sequence-specific",
        summary_file="nz_etas_simulations_2h.txt",
        pycsep_dir="build/pycsep_2h",
    ),
    ExperimentDef(
        label="6 h data",
        data_days=6/24,
        forecast_start=6/24,
        forecast_end=14.5,
        model_type="sequence-specific",
        summary_file="nz_etas_simulations_6h.txt",
        pycsep_dir="build/pycsep_6h",
    ),
    ExperimentDef(
        label="12 h data",
        data_days=0.5,
        forecast_start=0.5,
        forecast_end=14.5,
        model_type="sequence-specific",
        summary_file="nz_etas_simulations_12h.txt",
        pycsep_dir="build/pycsep_12h",
    ),
    ExperimentDef(
        label="1 day data",
        data_days=1.0,
        forecast_start=1.0,
        forecast_end=14.5,
        model_type="sequence-specific",
        summary_file="nz_etas_simulations_1d.txt",
        pycsep_dir="build/pycsep_1d",
    ),
    ExperimentDef(
        label="2 day data",
        data_days=2.0,
        forecast_start=2.0,
        forecast_end=14.5,
        model_type="sequence-specific",
        summary_file="nz_etas_simulations_2d.txt",
        pycsep_dir="build/pycsep_2d",
    ),
    ExperimentDef(
        label="3 day data",
        data_days=3.0,
        forecast_start=3.0,
        forecast_end=14.5,
        model_type="sequence-specific",
        summary_file="nz_etas_simulations_3d.txt",
        pycsep_dir="build/pycsep_3d",
    ),
    ExperimentDef(
        label="7 day data\n(reference)",
        data_days=7.0,
        forecast_start=7.0,
        forecast_end=14.0,
        model_type="sequence-specific",
        summary_file="nz_etas_simulations.txt",
        pycsep_dir="build/pycsep",
    ),
]


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class FittedParams:
    ams: Optional[float] = None
    a: Optional[float] = None
    p: Optional[float] = None
    c: Optional[float] = None
    b: Optional[float] = None


@dataclass
class ForecastStats:
    """From the simulation summary text file."""
    params: FittedParams = field(default_factory=FittedParams)
    expected_m3: Optional[float] = None
    median_m3: Optional[int] = None
    p5_m3: Optional[int] = None
    p95_m3: Optional[int] = None


@dataclass
class PyCSEPStats:
    """From the pyCSEP summary markdown and JSON files."""
    n_obs: Optional[int] = None
    ensemble_median: Optional[int] = None
    n_test_q_lo: Optional[float] = None
    n_test_q_hi: Optional[float] = None
    n_test_stat: Optional[int] = None
    m_test_q_lo: Optional[float] = None
    s_test_q_hi: Optional[float] = None
    pl_test_q_hi: Optional[float] = None
    rolling_ks_p: Optional[float] = None
    indirect_share: Optional[float] = None
    n_test_dist: Optional[list] = None   # full distribution for CDF plot


@dataclass
class ExperimentResult:
    defn: ExperimentDef
    forecast: ForecastStats = field(default_factory=ForecastStats)
    pycsep: PyCSEPStats = field(default_factory=PyCSEPStats)
    available: bool = False


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_summary_file(path: Path) -> ForecastStats:
    stats = ForecastStats()
    if not path.exists():
        return stats
    text = path.read_text()

    def _float(pattern: str) -> Optional[float]:
        m = re.search(pattern, text)
        return float(m.group(1)) if m else None

    def _int(pattern: str) -> Optional[int]:
        m = re.search(pattern, text)
        return int(m.group(1)) if m else None

    stats.params.ams = _float(r"ams-value:\s*([-\d.]+)")
    stats.params.a   = _float(r"a-value:\s*([-\d.]+)")
    stats.params.p   = _float(r"p-value:\s*([-\d.]+)")
    stats.params.c   = _float(r"c-value:\s*([-\d.]+)")
    stats.params.b   = _float(r"b-value:\s*([-\d.]+)")
    stats.expected_m3 = _float(r"M>=3\.0:\s*([\d.]+)\s*$")
    # percentile line: "  M>=3.0:  5th=NNN  Median=NNN  95th=NNN"
    m = re.search(r"M>=3\.0:\s+5th=(\d+)\s+Median=(\d+)\s+95th=(\d+)", text)
    if m:
        stats.p5_m3     = int(m.group(1))
        stats.median_m3 = int(m.group(2))
        stats.p95_m3    = int(m.group(3))
    return stats


def parse_pycsep_summary(md_path: Path) -> PyCSEPStats:
    stats = PyCSEPStats()
    if not md_path.exists():
        return stats
    text = md_path.read_text()

    def _float(pattern: str) -> Optional[float]:
        m = re.search(pattern, text)
        return float(m.group(1)) if m else None

    def _int(pattern: str) -> Optional[int]:
        m = re.search(pattern, text)
        return int(m.group(1)) if m else None

    stats.n_obs           = _int(r"Observed event count in testing region:\s*`?(\d+)`?")
    stats.ensemble_median = _int(r"Ensemble event-count median:\s*`?(\d+)`?")
    stats.indirect_share  = _float(r"Median indirect.*share of.*events:\s*`?([\d.]+)`?%")

    # N-test: quantile `(q_lo, q_hi)`
    m = re.search(r"catalog_number_test.*?quantile\s+`\(([\d.]+),\s*([\d.]+)\)`", text)
    if m:
        stats.n_test_q_lo = float(m.group(1))
        stats.n_test_q_hi = float(m.group(2))
    m = re.search(r"catalog_number_test.*?observed statistic\s+`?(\d+)`?", text)
    if m:
        stats.n_test_stat = int(m.group(1))

    # M-test
    m = re.search(r"catalog_magnitude_test.*?quantile\s+`\(([\d.]+),\s*([\d.]+)\)`", text)
    if m:
        stats.m_test_q_lo = float(m.group(1))

    # S-test (q_hi is the relevant tail)
    m = re.search(r"catalog_spatial_test.*?quantile\s+`\(([\d.]+),\s*([\d.]+)\)`", text)
    if m:
        stats.s_test_q_hi = float(m.group(2))

    # PL-test
    m = re.search(r"catalog_pseudolikelihood_test.*?quantile\s+`\(([\d.]+),\s*([\d.]+)\)`", text)
    if m:
        stats.pl_test_q_hi = float(m.group(2))

    # Rolling KS p-value
    m = re.search(r"Rolling calibration KS statistic.*?p-value\s+`?([\d.e+\-]+)`?", text)
    if m:
        stats.rolling_ks_p = float(m.group(1))

    return stats


def parse_n_test_json(json_path: Path) -> Optional[list]:
    if not json_path.exists():
        return None
    try:
        data = json.loads(json_path.read_text())
        return data.get("test_distribution")
    except Exception:
        return None


def load_experiment(root: Path, defn: ExperimentDef) -> ExperimentResult:
    result = ExperimentResult(defn=defn)
    summary_path = root / defn.summary_file
    pycsep_dir   = root / defn.pycsep_dir
    md_path      = pycsep_dir / "nz_etas_pycsep_summary.md"
    n_test_json  = pycsep_dir / "evaluation_json" / "catalog_number_test.json"

    result.forecast = parse_summary_file(summary_path)
    result.pycsep   = parse_pycsep_summary(md_path)
    result.pycsep.n_test_dist = parse_n_test_json(n_test_json)
    result.available = summary_path.exists() or md_path.exists()
    return result


# ---------------------------------------------------------------------------
# Console table
# ---------------------------------------------------------------------------

def _fmt(v, fmt=".3f", missing="—"):
    return format(v, fmt) if v is not None else missing


def _pass_fail(q: Optional[float], threshold=0.025, reverse=False) -> str:
    """Return PASS/FAIL/MARGINAL symbol."""
    if q is None:
        return "?"
    if reverse:
        # for q_hi tests (S, PL) pass means q_hi > 0.05
        if q > 0.05:
            return "✓"
        elif q > 0.025:
            return "~"
        else:
            return "✗"
    else:
        # for N-test delta values pass means > 0.025
        if q > 0.025:
            return "✓"
        elif q > 0.010:
            return "~"
        else:
            return "✗"


def print_table(results: list[ExperimentResult]) -> None:
    w = 14
    sep = "-" * (w * 10 + 9)

    def row(*cols):
        print("  ".join(str(c).ljust(w) for c in cols))

    print("\n" + "=" * len(sep))
    print("ETAS EXPERIMENT COMPARISON — 2016 Kaikōura M7.82")
    print("=" * len(sep))

    # Header
    labels = [r.defn.label.replace("\n", " ") for r in results]
    print("\n--- A: Fitted Parameters ---")
    row("Parameter", *labels)
    print(sep)
    row("ams",     *[_fmt(r.forecast.params.ams) for r in results])
    row("a",       *[_fmt(r.forecast.params.a)   for r in results])
    row("p",       *[_fmt(r.forecast.params.p)   for r in results])
    row("c (days)",*[_fmt(r.forecast.params.c)   for r in results])

    print("\n--- B: Forecast vs Observed (M≥3) ---")
    row("Metric", *labels)
    print(sep)
    row("N_obs (pyCSEP)",  *[_fmt(r.pycsep.n_obs,       ".0f") for r in results])
    row("Ensemble median", *[_fmt(r.pycsep.ensemble_median, ".0f") for r in results])
    row("Sim median (txt)",*[_fmt(r.forecast.median_m3,  ".0f") for r in results])
    row("5th pctile",      *[_fmt(r.forecast.p5_m3,     ".0f") for r in results])
    row("95th pctile",     *[_fmt(r.forecast.p95_m3,    ".0f") for r in results])
    row("Expected (anal)", *[_fmt(r.forecast.expected_m3,".1f") for r in results])

    print("\n--- C: pyCSEP Evaluation Results ---")
    row("Test", *labels)
    print(sep)
    row("N-test δ₁ (q_lo)", *[_fmt(r.pycsep.n_test_q_lo) for r in results])
    row("N-test δ₂ (q_hi)", *[_fmt(r.pycsep.n_test_q_hi) for r in results])
    row("N-test pass?",      *[_pass_fail(r.pycsep.n_test_q_lo) + "/" +
                                _pass_fail(r.pycsep.n_test_q_hi) for r in results])
    row("M-test q_lo",       *[_fmt(r.pycsep.m_test_q_lo)  for r in results])
    row("S-test q_hi",       *[_fmt(r.pycsep.s_test_q_hi)  for r in results])
    row("PL-test q_hi",      *[_fmt(r.pycsep.pl_test_q_hi) for r in results])
    row("Rolling KS p",      *[_fmt(r.pycsep.rolling_ks_p) for r in results])
    row("Indirect share %",  *[_fmt(r.pycsep.indirect_share,".1f") for r in results])

    print()


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

PASS_GREEN    = "#2ca02c"
MARGINAL_ORG  = "#ff7f0e"
FAIL_RED      = "#d62728"
PRIOR_BLUE    = "#1f77b4"

def _x_positions(results: list[ExperimentResult]) -> np.ndarray:
    """X positions: data window length in hours for plotting."""
    hours = []
    for r in results:
        h = r.defn.data_days * 24
        hours.append(h)
    return np.array(hours)


def _color_n_test(q_lo: Optional[float], q_hi: Optional[float]) -> str:
    if q_lo is None or q_hi is None:
        return "grey"
    if min(q_lo, q_hi) < 0.025:
        return FAIL_RED
    if min(q_lo, q_hi) < 0.05:
        return MARGINAL_ORG
    return PASS_GREEN


def _color_q_hi(q_hi: Optional[float]) -> str:
    if q_hi is None:
        return "grey"
    if q_hi < 0.05:
        return FAIL_RED
    if q_hi < 0.1:
        return MARGINAL_ORG
    return PASS_GREEN


def make_figure(results: list[ExperimentResult], output_path: Path) -> None:
    available = [r for r in results if r.available]
    if not available:
        print("No results available to plot.")
        return

    fig = plt.figure(figsize=(18, 22))
    fig.suptitle(
        "ETAS Experiment Comparison — 2016 Kaikōura M7.82\n"
        "How forecast skill changes with length of early data window used for MLE fitting",
        fontsize=14, fontweight="bold", y=0.98,
    )

    gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.45, wspace=0.38)

    ax_ams   = fig.add_subplot(gs[0, 0])
    ax_p     = fig.add_subplot(gs[0, 1])
    ax_c     = fig.add_subplot(gs[0, 2])
    ax_nobs  = fig.add_subplot(gs[1, 0:2])
    ax_ratio = fig.add_subplot(gs[1, 2])
    ax_ntest = fig.add_subplot(gs[2, 0])
    ax_mtest = fig.add_subplot(gs[2, 1])
    ax_spl   = fig.add_subplot(gs[2, 2])
    ax_ks    = fig.add_subplot(gs[3, 0])
    ax_indir = fig.add_subplot(gs[3, 1])
    ax_cdfs  = fig.add_subplot(gs[3, 2])

    hours  = _x_positions(available)
    labels = [r.defn.label.replace("\n", " ") for r in available]
    x_ticks = hours
    x_labels = [f"{h:.1f} h" if h < 24 else f"{h/24:.0f} d" for h in hours]

    def _setup_ax(ax, title, ylabel, xlabel="Data window used for MLE fitting"):
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xlabel(xlabel, fontsize=8)
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, fontsize=7, rotation=30, ha="right")
        ax.grid(True, alpha=0.3, linestyle="--")

    def _scatter(ax, values, color_fn=None, default_color=PRIOR_BLUE, marker="o", size=60):
        for i, (h, v) in enumerate(zip(hours, values)):
            if v is None:
                continue
            c = color_fn(i) if color_fn else default_color
            ax.scatter(h, v, color=c, s=size, zorder=3, marker=marker)
        # connect available points
        pts = [(h, v) for h, v in zip(hours, values) if v is not None]
        if len(pts) > 1:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color="grey", linewidth=1, linestyle="--", alpha=0.5, zorder=2)

    # ── Panel A: ams convergence ──────────────────────────────────────────────
    ams_vals = [r.forecast.params.ams for r in available]
    _scatter(ax_ams, ams_vals)
    ax_ams.axhline(-2.423, color="red", linestyle=":", linewidth=1.2, label="Generic prior (−2.423)")
    ax_ams.legend(fontsize=7)
    _setup_ax(ax_ams, "ams Convergence", "MLE ams value")

    # ── Panel B: p convergence ────────────────────────────────────────────────
    p_vals = [r.forecast.params.p for r in available]
    _scatter(ax_p, p_vals)
    ax_p.axhline(1.08, color="red", linestyle=":", linewidth=1.2, label="Prior p̄ = 1.08")
    ax_p.legend(fontsize=7)
    _setup_ax(ax_p, "p-value Convergence", "MLE p value")

    # ── Panel C: c convergence ────────────────────────────────────────────────
    c_vals = [r.forecast.params.c for r in available]
    _scatter(ax_c, c_vals)
    ax_c.axhline(0.01, color="red", linestyle=":", linewidth=1.2, label="Prior c = 0.01")
    ax_c.legend(fontsize=7)
    _setup_ax(ax_c, "c-value Convergence", "MLE c value (days)")

    # ── Panel D: Ensemble median vs N_obs ─────────────────────────────────────
    medians = [r.pycsep.ensemble_median for r in available]
    n_obs   = [r.pycsep.n_obs           for r in available]
    p5s     = [r.forecast.p5_m3         for r in available]
    p95s    = [r.forecast.p95_m3        for r in available]

    for i, r in enumerate(available):
        h = hours[i]
        med = medians[i]
        obs = n_obs[i]
        p5  = p5s[i]
        p95 = p95s[i]
        if med is not None:
            ax_nobs.scatter(h, med, color=PRIOR_BLUE, s=60, zorder=3, label="Ensemble median" if i == 0 else "")
        if obs is not None:
            ax_nobs.scatter(h, obs, color="black", marker="*", s=100, zorder=4, label="Observed N" if i == 0 else "")
        if p5 is not None and p95 is not None:
            ax_nobs.vlines(h, p5, p95, color=PRIOR_BLUE, alpha=0.4, linewidth=3, label="5th–95th pctile" if i == 0 else "")

    ax_nobs.legend(fontsize=8)
    _setup_ax(ax_nobs, "Ensemble Median vs Observed Count (M≥3)", "Event count")

    # ── Panel E: Ratio median/N_obs ───────────────────────────────────────────
    ratios = []
    for r in available:
        if r.pycsep.ensemble_median and r.pycsep.n_obs:
            ratios.append(r.pycsep.ensemble_median / r.pycsep.n_obs)
        else:
            ratios.append(None)
    _scatter(ax_ratio, ratios)
    ax_ratio.axhline(1.0, color="green", linestyle="-", linewidth=1.5, label="Perfect (ratio=1)")
    ax_ratio.set_ylim(0, max((v for v in ratios if v is not None), default=2) * 1.2)
    ax_ratio.legend(fontsize=7)
    _setup_ax(ax_ratio, "Forecast Bias: Median / N_obs", "Ratio (1 = unbiased)")

    # ── Panel F: N-test quantiles ─────────────────────────────────────────────
    q_lo = [r.pycsep.n_test_q_lo for r in available]
    q_hi = [r.pycsep.n_test_q_hi for r in available]

    for i, (h, qlo, qhi) in enumerate(zip(hours, q_lo, q_hi)):
        c = _color_n_test(qlo, qhi)
        if qlo is not None:
            ax_ntest.scatter(h, qlo, color=c, s=60, marker="o", zorder=3,
                             label="δ₁ (q_lo)" if i == 0 else "")
        if qhi is not None:
            ax_ntest.scatter(h, qhi, color=c, s=60, marker="s", zorder=3,
                             label="δ₂ (q_hi)" if i == 0 else "")

    ax_ntest.axhline(0.025, color="red", linestyle="--", linewidth=1, label="Threshold 0.025")
    ax_ntest.set_ylim(-0.05, 1.05)
    ax_ntest.legend(fontsize=7)
    _setup_ax(ax_ntest, "N-test Quantiles\n(both must be >0.025 to pass)", "Quantile")

    # ── Panel G: M-test q_lo ─────────────────────────────────────────────────
    m_q = [r.pycsep.m_test_q_lo for r in available]

    def _m_color(i):
        q = m_q[i]
        if q is None:
            return "grey"
        return PASS_GREEN if q > 0.05 else (MARGINAL_ORG if q > 0.025 else FAIL_RED)

    _scatter(ax_mtest, m_q, color_fn=_m_color)
    ax_mtest.axhline(0.05, color="red", linestyle="--", linewidth=1, label="Threshold 0.05")
    ax_mtest.set_ylim(-0.05, 1.05)
    ax_mtest.legend(fontsize=7)
    _setup_ax(ax_mtest, "M-test q_lo\n(magnitude distribution)", "q_lo")

    # ── Panel H: S-test and PL-test q_hi ─────────────────────────────────────
    s_q  = [r.pycsep.s_test_q_hi  for r in available]
    pl_q = [r.pycsep.pl_test_q_hi for r in available]

    for i, h in enumerate(hours):
        sq  = s_q[i]
        plq = pl_q[i]
        if sq is not None:
            ax_spl.scatter(h, sq, color=_color_q_hi(sq), s=60, marker="o", zorder=3,
                           label="S-test q_hi" if i == 0 else "")
        if plq is not None:
            ax_spl.scatter(h, plq, color=_color_q_hi(plq), s=60, marker="^", zorder=3,
                           label="PL-test q_hi" if i == 0 else "")

    ax_spl.axhline(0.05, color="red", linestyle="--", linewidth=1, label="Threshold 0.05")
    ax_spl.set_ylim(-0.05, 1.05)
    ax_spl.legend(fontsize=7)
    _setup_ax(ax_spl, "S-test & PL-test q_hi\n(spatial; >0.05 = pass)", "q_hi")

    # ── Panel I: Rolling KS p-value ───────────────────────────────────────────
    ks_vals = [r.pycsep.rolling_ks_p for r in available]

    def _ks_color(i):
        v = ks_vals[i]
        if v is None:
            return "grey"
        return PASS_GREEN if v > 0.05 else FAIL_RED

    _scatter(ax_ks, ks_vals, color_fn=_ks_color)
    ax_ks.axhline(0.05, color="red", linestyle="--", linewidth=1, label="p = 0.05")
    ax_ks.set_ylim(-0.05, 1.05)
    ax_ks.legend(fontsize=7)
    _setup_ax(ax_ks, "Rolling Calibration KS p-value\n(temporal bias check; >0.05 = pass)", "p-value")

    # ── Panel J: Indirect share ───────────────────────────────────────────────
    indir = [r.pycsep.indirect_share for r in available]
    _scatter(ax_indir, indir, default_color=PRIOR_BLUE)
    _setup_ax(ax_indir, "Median Indirect (Gen≥2) Share %\n(ETAS branching activity)", "% of events from branching")

    # ── Panel K: N-test distribution CDFs ────────────────────────────────────
    cmap = plt.cm.viridis(np.linspace(0.1, 0.9, len(available)))
    for i, r in enumerate(available):
        dist = r.pycsep.n_test_dist
        if not dist:
            continue
        arr = np.sort(dist)
        cdf = np.arange(1, len(arr) + 1) / len(arr)
        lbl = r.defn.label.replace("\n", " ")
        ax_cdfs.plot(arr, cdf, color=cmap[i], linewidth=1.5, label=lbl)
        # mark observed N
        n_obs_val = r.pycsep.n_obs
        if n_obs_val is not None:
            ax_cdfs.axvline(n_obs_val, color=cmap[i], linestyle=":", alpha=0.7)

    ax_cdfs.set_xlabel("Simulated catalog size (M≥3)", fontsize=8)
    ax_cdfs.set_ylabel("CDF", fontsize=9)
    ax_cdfs.set_title("N-test: CDF of simulated counts\n(dotted vertical = N_obs for each experiment)", fontsize=10, fontweight="bold")
    ax_cdfs.legend(fontsize=6, loc="upper left")
    ax_cdfs.grid(True, alpha=0.3, linestyle="--")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure saved: {output_path}")


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _status(q_lo: Optional[float], q_hi: Optional[float] = None, mode="n_test") -> str:
    if mode == "n_test":
        if q_lo is None or q_hi is None:
            return "?"
        if min(q_lo, q_hi) >= 0.025:
            return "**Pass**"
        return "**FAIL**"
    elif mode == "q_hi":
        if q_lo is None:
            return "?"
        if q_lo >= 0.05:
            return "**Pass**"
        if q_lo >= 0.025:
            return "**Marginal**"
        return "**FAIL**"
    elif mode == "ks":
        if q_lo is None:
            return "?"
        return "**Pass**" if q_lo >= 0.05 else "**FAIL**"
    return "?"


def write_report(results: list[ExperimentResult], output_path: Path) -> None:
    lines = []
    a = lines.append

    a("# ETAS Experiment Comparison Report")
    a("")
    a("## Event: 2016 Kaikōura M7.82 (GeoNet `2016p858000`)")
    a("")
    a("This report compares ETAS forecasts fitted on progressively longer early aftershock")
    a("data windows, from a pure generic prior (0 data) to a fully fitted 7-day model.")
    a("The key question: **how quickly does sequence-specific MLE fitting correct the generic")
    a("prior's underprediction of this highly productive sequence?**")
    a("")
    a("---")
    a("")
    a("## A. Fitted ETAS Parameters")
    a("")
    a("The generic prior means are: ams = −2.423, p = 1.08, c = 0.01 days.")
    a("")

    headers = ["Experiment", "Data window", "Model", "ams", "a", "p", "c (days)"]
    a("| " + " | ".join(headers) + " |")
    a("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in results:
        if not r.available:
            continue
        fp = r.forecast.params
        row = [
            r.defn.label.replace("\n", " "),
            f"{r.defn.data_days*24:.1f} h" if r.defn.data_days < 1 else f"{r.defn.data_days:.0f} d",
            r.defn.model_type,
            _fmt(fp.ams), _fmt(fp.a), _fmt(fp.p), _fmt(fp.c),
        ]
        a("| " + " | ".join(row) + " |")

    a("")
    a("**Key observation**: watch how `ams` changes as more data is used.")
    a("The generic prior starts at −2.423. With real aftershock data the MLE should push")
    a("`ams` higher (less negative = more productive), converging toward the 7-day estimate.")
    a("")
    a("---")
    a("")
    a("## B. Forecast vs Observed (M≥3)")
    a("")
    a("Note: each experiment has a *different* forecast window and therefore a *different*")
    a("observed count N_obs — the observed catalog is queried for exactly that window.")
    a("The ratio median/N_obs measures forecast bias (1.0 = unbiased).")
    a("")

    headers = ["Experiment", "Forecast window", "N_obs", "Ensemble median", "5th pctile", "95th pctile", "Median/N_obs"]
    a("| " + " | ".join(headers) + " |")
    a("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in results:
        if not r.available:
            continue
        n_obs = r.pycsep.n_obs
        med   = r.pycsep.ensemble_median
        ratio = f"{med/n_obs:.2f}" if med and n_obs else "—"
        row = [
            r.defn.label.replace("\n", " "),
            f"{r.defn.forecast_start:.3g}–{r.defn.forecast_end:.4g} days",
            str(n_obs) if n_obs else "—",
            str(med) if med else "—",
            str(r.forecast.p5_m3)  if r.forecast.p5_m3  else "—",
            str(r.forecast.p95_m3) if r.forecast.p95_m3 else "—",
            ratio,
        ]
        a("| " + " | ".join(row) + " |")

    a("")
    a("---")
    a("")
    a("## C. pyCSEP Evaluation Results")
    a("")
    a("Threshold: N-test both δ values > 0.025; M-test q_lo > 0.05; S/PL q_hi > 0.05;")
    a("rolling KS p > 0.05.")
    a("")

    headers = ["Experiment", "N-test δ₁", "N-test δ₂", "N-test", "M-test q_lo", "S-test q_hi", "PL-test q_hi", "Rolling KS p", "Status"]
    a("| " + " | ".join(headers) + " |")
    a("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in results:
        if not r.available:
            continue
        p = r.pycsep
        overall = _status(p.n_test_q_lo, p.n_test_q_hi, "n_test")
        row = [
            r.defn.label.replace("\n", " "),
            _fmt(p.n_test_q_lo),
            _fmt(p.n_test_q_hi),
            overall,
            _fmt(p.m_test_q_lo),
            _fmt(p.s_test_q_hi),
            _fmt(p.pl_test_q_hi),
            f"{p.rolling_ks_p:.3e}" if p.rolling_ks_p is not None else "—",
            _status(p.rolling_ks_p, mode="ks"),
        ]
        a("| " + " | ".join(row) + " |")

    a("")
    a("---")
    a("")
    a("## D. Interpretation")
    a("")
    a("### Why the generic (0 h) forecast fails")
    a("")
    a("The generic ETAS prior is calibrated on *average* active-shallow-crust sequences")
    a("from the global ISC catalog (2,099 sequences, 1960–2019). The 2016 Kaikōura M7.82")
    a("was far more productive than average, so the generic prior systematically")
    a("underestimates the event count by a large factor.")
    a("")
    a("### What happens as data is added")
    a("")
    a("Each additional hour of aftershock observation allows the MLE to push `ams` upward,")
    a("increasing the predicted productivity. The N-test quantile measures how well the")
    a("model's count distribution contains the observed count.")
    a("")
    a("### Comparison caveat")
    a("")
    a("The forecast windows are not identical across experiments — longer data windows")
    a("mean shorter remaining forecast windows, and fewer observed events to predict.")
    a("The 7-day reference model forecasts a quieter period (days 7–14) than the")
    a("early-window models (which must predict the Omori peak). This is an intrinsically")
    a("harder problem for the early-window models even if `ams` converges correctly.")
    a("")
    a("---")
    a("")
    a("*Generated by `scripts/python/compare_etas_experiments.py`*")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"Report saved: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="Root directory of the opensha-oaf project")
    p.add_argument("--output-dir", default="build/comparison", help="Directory for output files")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    out  = root / args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    print(f"Root      : {root}")
    print(f"Output dir: {out}")
    print()

    results = []
    for defn in EXPERIMENTS:
        r = load_experiment(root, defn)
        results.append(r)
        status = "OK" if r.available else "MISSING"
        label = defn.label.replace("\n", " ")
        print(f"  [{status:7s}] {label:25s}  summary={defn.summary_file}")

    available = [r for r in results if r.available]
    if not available:
        print("\nNo experiment results found. Run the pipeline for each config first:")
        for defn in EXPERIMENTS:
            print(f"  ./run_etas_pipeline.sh etas_config_{defn.pycsep_dir.split('_', 2)[-1].replace('pycsep/', '')}.json")
        sys.exit(1)

    print(f"\n{len(available)}/{len(results)} experiments available.\n")

    print_table(available)

    figure_path = out / "etas_experiment_comparison.png"
    make_figure(available, figure_path)

    report_path = out / "compare_experiments_report.md"
    write_report(available, report_path)

    print(f"\nAll outputs in: {out}/")


if __name__ == "__main__":
    main()
