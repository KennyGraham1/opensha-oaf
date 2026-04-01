#!/usr/bin/env python3
"""Build publication-grade diagnostic figures for the NZ ETAS issue-time study."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
    for patch in bp["boxes"]:
        patch.set_facecolor("#cfe8ff")
        patch.set_edgecolor("#2b6cb0")
    for median in bp["medians"]:
        median.set_color("#1a202c")
        median.set_linewidth(2)
    n_obs = rows[0]["n_obs"] if rows else None
    if n_obs is not None:
        ax.axhline(float(n_obs), color="#111111", linestyle="--", linewidth=1.5, label=f"Observed N={int(n_obs)}")
    ax.set_title("A) Empirical Count Distributions by Issue Time")
    ax.set_ylabel("Catalog event count (M≥3, NZ region)")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")
    if n_obs is not None:
        ax.legend(loc="upper left", fontsize=9)

    # Panel B: count ratio and N-test classification
    ax = axes[0, 1]
    ratio = np.array([float(row["ensemble_median"]) / float(row["n_obs"]) for row in rows])
    lo = np.array([float(row["n_p05"]) / float(row["n_obs"]) for row in rows])
    hi = np.array([float(row["n_p95"]) / float(row["n_obs"]) for row in rows])
    class_color = {"underpredict": "#d73027", "overpredict": "#4575b4", "pass": "#1a9850", "fail-both": "#762a83", "unknown": "#777777"}
    colors = [class_color[classify_n_test(row["n_q_lo"], row["n_q_hi"])] for row in rows]
    ax.errorbar(x, ratio, yerr=np.vstack([ratio - lo, hi - ratio]), fmt="none", ecolor="#666666", alpha=0.9, capsize=4)
    ax.scatter(x, ratio, c=colors, s=80, zorder=3)
    ax.axhline(1.0, color="#1a9850", linestyle="--", linewidth=1.5)
    ax.axvline(4.5, color="#aaaaaa", linestyle=":", linewidth=1.2)
    ax.axvline(6.5, color="#aaaaaa", linestyle=":", linewidth=1.2)
    ax.text(2.0, max(hi) * 0.95, "Regime 1", color="#555555", ha="center", fontsize=9)
    ax.text(5.5, max(hi) * 0.95, "Regime 2", color="#555555", ha="center", fontsize=9)
    ax.text(7.0, max(hi) * 0.95, "Regime 3", color="#555555", ha="center", fontsize=9)
    ax.set_title("B) Count Bias Ratio with 5th–95th Range")
    ax.set_ylabel("Median / observed count")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.grid(alpha=0.3, linestyle=":")

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
        lines.append(
            f"- {row['label']}: median/obs={ratio:.3f}, N-test=({float(row['n_q_lo']):.3f},{float(row['n_q_hi']):.3f}), "
            f"rolling p={float(row['rolling_p']):.3g}, E[N]/pyCSEP-mean={float(row['expected_to_py_mean']):.2f}, "
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


def make_daily_decomposition_figure(root: Path, rows: list[dict], output_path: Path, output_csv: Path) -> None:
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

    fig, axes = plt.subplots(2, 2, figsize=(16, 12), constrained_layout=True)
    fig.suptitle(
        "Daily Decomposition of Fixed-Horizon ETAS Skill (days 7–14)\n"
        "Issue-time-specific temporal allocation diagnostics",
        fontsize=14,
        fontweight="bold",
    )

    # A) observed vs median forecast trajectories
    ax = axes[0, 0]
    x = np.arange(7)
    ax.plot(x, observed_counts, color="#111111", linewidth=2.5, marker="o", label="Observed")
    for idx, row in enumerate(rows):
        if row["key"] in {"2h", "2d", "7d", "premainshock"}:
            ax.plot(x, medians[idx], linewidth=1.8, marker="o", label=str(row["label"]))
            ax.fill_between(x, p10[idx], p90[idx], alpha=0.15)
    ax.set_xticks(x, day_labels)
    ax.set_ylabel("Daily event count (M≥3)")
    ax.set_title("A) Daily Count Trajectories (observed vs forecast median)")
    ax.grid(alpha=0.3, linestyle=":")
    ax.legend(loc="upper right", fontsize=8)

    # B) standardized residual heatmap
    ax = axes[0, 1]
    im = ax.imshow(z, cmap="RdBu_r", aspect="auto", vmin=-3, vmax=3)
    ax.set_yticks(np.arange(len(rows)), [str(r["label"]) for r in rows])
    ax.set_xticks(np.arange(7), day_labels)
    ax.set_title("B) Standardized Residual Z = (Obs - Mean) / SD")
    plt.colorbar(im, ax=ax, label="Z-score")

    # C) PIT-like empirical CDF at observed
    ax = axes[1, 0]
    im2 = ax.imshow(pit, cmap="coolwarm", aspect="auto", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(rows)), [str(r["label"]) for r in rows])
    ax.set_xticks(np.arange(7), day_labels)
    ax.set_title("C) Empirical CDF at Observed (daily)")
    ax.set_xlabel("Day bin after mainshock (days)")
    plt.colorbar(im2, ax=ax, label="P(N_sim ≤ N_obs)")

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
    make_regime_figure(rows, output_dir / "publication_regime_diagnostics.png")
    write_metrics(
        rows,
        output_dir / "publication_regime_metrics.csv",
        output_dir / "publication_diagnostics_summary.md",
    )
    make_daily_decomposition_figure(
        root,
        rows,
        output_dir / "publication_daily_decomposition.png",
        output_dir / "publication_daily_metrics.csv",
    )
    print(f"Wrote {output_dir / 'publication_regime_diagnostics.png'}")
    print(f"Wrote {output_dir / 'publication_regime_metrics.csv'}")
    print(f"Wrote {output_dir / 'publication_diagnostics_summary.md'}")
    print(f"Wrote {output_dir / 'publication_daily_decomposition.png'}")
    print(f"Wrote {output_dir / 'publication_daily_metrics.csv'}")


if __name__ == "__main__":
    main()
