#!/usr/bin/env python3
"""Render a professional ensemble dashboard for NZ ETAS outputs."""

from __future__ import annotations

import argparse
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.ticker import MaxNLocator
from scipy.ndimage import gaussian_filter


PARAM_PATTERN = re.compile(r"^([acbp]-value|ams-value):\s+([-+]?\d*\.?\d+)$")
COUNT_PATTERN = re.compile(r"^\s*M>=(\d+(?:\.\d+)?)\s*:\s*([-+]?\d*\.?\d+)$")
PROB_PATTERN = re.compile(r"^\s*M>=(\d+(?:\.\d+)?)\s*:\s*([-+]?\d*\.?\d+)%$")
PCTL_PATTERN = re.compile(
    r"^\s*M>=(\d+(?:\.\d+)?)\s*:\s*5th=(\d+)\s+Median=(\d+)\s+95th=(\d+)$"
)
WINDOW_PATTERN = re.compile(r"--- Forecast \(Days ([0-9.]+)-([0-9.]+)\) ---")


@dataclass
class SummaryInfo:
    event_id: str
    analysis_date: str
    mag_complete: float
    n_sims: int
    forecast_start: float
    forecast_end: float
    thresholds: list[float]
    expected_counts: dict[float, float]
    probabilities: dict[float, float]
    percentiles: dict[float, tuple[int, int, int]]
    fitted_params: dict[str, float]


@dataclass
class EnsembleMetrics:
    catalog_paths: list[Path]
    time_edges: np.ndarray
    time_centers: np.ndarray
    daily_counts: np.ndarray
    cumulative_counts: np.ndarray
    threshold_counts: np.ndarray
    generation_counts: np.ndarray
    max_magnitudes: np.ndarray
    spatial_lats: np.ndarray | None
    spatial_lons: np.ndarray | None
    large_lats: np.ndarray | None
    large_lons: np.ndarray | None
    large_mags: np.ndarray | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a publication-style dashboard from NZ ETAS output files."
    )
    parser.add_argument(
        "--summary",
        default="nz_etas_simulations.txt",
        help="Path to the ETAS summary file.",
    )
    parser.add_argument(
        "--catalog-dir",
        default="simulated_catalogs",
        help="Directory containing sim_*.txt catalog files.",
    )
    parser.add_argument(
        "--spatial-rate",
        default="spatial_rate_map.csv",
        help="Optional spatial rate map CSV. Ignored if missing.",
    )
    parser.add_argument(
        "--output-stem",
        default="build/nz_visualization/nz_etas_dashboard",
        help="Output stem; the script writes .png, .pdf, and _summary.md.",
    )
    parser.add_argument(
        "--time-bin-days",
        type=float,
        default=0.5,
        help="Time bin width in days for the ensemble rate panels.",
    )
    parser.add_argument(
        "--spatial-mag",
        type=float,
        default=None,
        help="Magnitude threshold used for spatial density contours.",
    )
    parser.add_argument(
        "--overlay-mag",
        type=float,
        default=None,
        help="Magnitude threshold used for highlighted point overlays.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=220,
        help="PNG resolution.",
    )
    return parser.parse_args()


def parse_summary(path: Path) -> SummaryInfo:
    if not path.exists():
        raise FileNotFoundError(f"Summary file not found: {path}")

    event_id = ""
    analysis_date = ""
    mag_complete = math.nan
    n_sims = 0
    forecast_start = math.nan
    forecast_end = math.nan
    expected_counts: dict[float, float] = {}
    probabilities: dict[float, float] = {}
    percentiles: dict[float, tuple[int, int, int]] = {}
    fitted_params: dict[str, float] = {}
    section = ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Event:"):
            event_id = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Analysis Date:"):
            analysis_date = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Mag Complete (Mc):"):
            mag_complete = float(line.split(":", 1)[1].strip())
            continue
        if line.startswith("Num Simulations:"):
            n_sims = int(float(line.split(":", 1)[1].strip()))
            continue

        match = WINDOW_PATTERN.search(raw_line)
        if match:
            forecast_start = float(match.group(1))
            forecast_end = float(match.group(2))
            section = "expected"
            continue

        if line == "Probability of >=1 Event:":
            section = "probabilities"
            continue
        if line.startswith("--- Uncertainty"):
            section = "uncertainty"
            continue
        if line.startswith("--- Fitted Parameters ---"):
            section = "params"
            continue
        if line.startswith("---"):
            section = ""
            continue

        match = PARAM_PATTERN.match(line)
        if match:
            fitted_params[match.group(1).replace("-value", "")] = float(match.group(2))
            continue

        if section == "expected":
            match = COUNT_PATTERN.match(line)
            if match:
                expected_counts[float(match.group(1))] = float(match.group(2))
            continue
        if section == "probabilities":
            match = PROB_PATTERN.match(line)
            if match:
                probabilities[float(match.group(1))] = float(match.group(2)) / 100.0
            continue
        if section == "uncertainty":
            match = PCTL_PATTERN.match(line)
            if match:
                percentiles[float(match.group(1))] = (
                    int(match.group(2)),
                    int(match.group(3)),
                    int(match.group(4)),
                )

    thresholds = sorted(expected_counts)
    if not thresholds:
        raise ValueError(f"Could not parse magnitude thresholds from {path}")

    return SummaryInfo(
        event_id=event_id,
        analysis_date=analysis_date,
        mag_complete=mag_complete,
        n_sims=n_sims,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
        thresholds=thresholds,
        expected_counts=expected_counts,
        probabilities=probabilities,
        percentiles=percentiles,
        fitted_params=fitted_params,
    )


def load_catalog_rows(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    times: list[float] = []
    mags: list[float] = []
    gens: list[int] = []
    lats: list[float] = []
    lons: list[float] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("Time "):
                continue
            fields = line.split()
            if len(fields) < 3:
                continue
            times.append(float(fields[0]))
            mags.append(float(fields[1]))
            gens.append(int(float(fields[2])))
            if len(fields) >= 5:
                lats.append(float(fields[3]))
                lons.append(float(fields[4]))

    time_arr = np.asarray(times, dtype=float)
    mag_arr = np.asarray(mags, dtype=float)
    gen_arr = np.asarray(gens, dtype=int)
    lat_arr = np.asarray(lats, dtype=float) if lats else None
    lon_arr = np.asarray(lons, dtype=float) if lons else None
    return time_arr, mag_arr, gen_arr, lat_arr, lon_arr


def build_time_edges(start: float, end: float, bin_width: float) -> np.ndarray:
    if bin_width <= 0:
        raise ValueError("--time-bin-days must be positive")
    count = max(1, int(math.ceil((end - start) / bin_width)))
    edges = start + np.arange(count + 1, dtype=float) * bin_width
    edges[-1] = end
    if edges[-2] >= end:
        edges = np.array([start, end], dtype=float)
    return edges


def compute_ensemble_metrics(
    catalog_paths: list[Path],
    summary: SummaryInfo,
    time_bin_days: float,
    spatial_mag: float,
    overlay_mag: float,
) -> EnsembleMetrics:
    time_edges = build_time_edges(summary.forecast_start, summary.forecast_end, time_bin_days)
    time_centers = 0.5 * (time_edges[:-1] + time_edges[1:])
    n_bins = len(time_centers)
    n_sims = len(catalog_paths)
    n_thresholds = len(summary.thresholds)
    generation_labels = 4

    daily_counts = np.zeros((n_sims, n_bins), dtype=int)
    threshold_counts = np.zeros((n_sims, n_thresholds), dtype=int)
    generation_counts = np.zeros((n_sims, generation_labels), dtype=int)
    max_magnitudes = np.full(n_sims, np.nan, dtype=float)

    spatial_lat_chunks: list[np.ndarray] = []
    spatial_lon_chunks: list[np.ndarray] = []
    large_lat_chunks: list[np.ndarray] = []
    large_lon_chunks: list[np.ndarray] = []
    large_mag_chunks: list[np.ndarray] = []

    for index, path in enumerate(catalog_paths):
        times, mags, gens, lats, lons = load_catalog_rows(path)

        if mags.size:
            max_magnitudes[index] = float(np.max(mags))

        if mags.size:
            for threshold_index, threshold in enumerate(summary.thresholds):
                threshold_counts[index, threshold_index] = int(np.count_nonzero(mags >= threshold))

        mc_mask = mags >= summary.mag_complete
        if mc_mask.any():
            daily_counts[index] = np.histogram(times[mc_mask], bins=time_edges)[0]
            generation_counts[index, 0] = int(np.count_nonzero(mc_mask & (gens == 1)))
            generation_counts[index, 1] = int(np.count_nonzero(mc_mask & (gens == 2)))
            generation_counts[index, 2] = int(np.count_nonzero(mc_mask & (gens == 3)))
            generation_counts[index, 3] = int(np.count_nonzero(mc_mask & (gens >= 4)))

        if lats is not None and lons is not None and mags.size:
            spatial_mask = mags >= spatial_mag
            if np.any(spatial_mask):
                spatial_lat_chunks.append(lats[spatial_mask])
                spatial_lon_chunks.append(lons[spatial_mask])

            large_mask = mags >= overlay_mag
            if np.any(large_mask):
                large_lat_chunks.append(lats[large_mask])
                large_lon_chunks.append(lons[large_mask])
                large_mag_chunks.append(mags[large_mask])

    cumulative_counts = np.cumsum(daily_counts, axis=1)

    spatial_lats = np.concatenate(spatial_lat_chunks) if spatial_lat_chunks else None
    spatial_lons = np.concatenate(spatial_lon_chunks) if spatial_lon_chunks else None
    large_lats = np.concatenate(large_lat_chunks) if large_lat_chunks else None
    large_lons = np.concatenate(large_lon_chunks) if large_lon_chunks else None
    large_mags = np.concatenate(large_mag_chunks) if large_mag_chunks else None

    return EnsembleMetrics(
        catalog_paths=catalog_paths,
        time_edges=time_edges,
        time_centers=time_centers,
        daily_counts=daily_counts,
        cumulative_counts=cumulative_counts,
        threshold_counts=threshold_counts,
        generation_counts=generation_counts,
        max_magnitudes=max_magnitudes,
        spatial_lats=spatial_lats,
        spatial_lons=spatial_lons,
        large_lats=large_lats,
        large_lons=large_lons,
        large_mags=large_mags,
    )


def load_spatial_rate_grid(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    if not path.exists():
        return None

    rows: list[tuple[float, float, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [item.strip() for item in line.split(",")]
            if len(parts) != 3:
                continue
            rows.append((float(parts[0]), float(parts[1]), float(parts[2])))

    if not rows:
        return None

    array = np.asarray(rows, dtype=float)
    lats = np.unique(array[:, 0])
    lons = np.unique(array[:, 1])
    grid = np.full((lats.size, lons.size), np.nan, dtype=float)
    lat_index = {value: idx for idx, value in enumerate(lats)}
    lon_index = {value: idx for idx, value in enumerate(lons)}

    for lat, lon, rate in array:
        grid[lat_index[lat], lon_index[lon]] = rate

    return lats, lons, grid


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#F6F3EE",
            "axes.facecolor": "#FCFAF7",
            "axes.edgecolor": "#433D3A",
            "axes.labelcolor": "#2F2A28",
            "axes.titleweight": "bold",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "font.size": 10,
            "grid.color": "#D8D0C7",
            "grid.linewidth": 0.8,
            "grid.alpha": 0.65,
            "axes.grid": True,
            "savefig.facecolor": "#F6F3EE",
            "xtick.color": "#3A3431",
            "ytick.color": "#3A3431",
        }
    )


def quantiles(array: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return tuple(np.percentile(array, [5, 50, 95], axis=0))


def configure_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=4, color="#4A4440")


def draw_temporal_panels(
    ax_rate: plt.Axes,
    ax_cumulative: plt.Axes,
    metrics: EnsembleMetrics,
    summary: SummaryInfo,
) -> None:
    rate_q05, rate_q50, rate_q95 = quantiles(metrics.daily_counts)
    cum_q05, cum_q50, cum_q95 = quantiles(metrics.cumulative_counts)
    mean_rate = metrics.daily_counts.mean(axis=0)
    mean_cumulative = metrics.cumulative_counts.mean(axis=0)
    centers = metrics.time_centers
    width = np.diff(metrics.time_edges)

    band_color = "#9CC5D9"
    median_color = "#0D3B66"
    mean_color = "#C8553D"

    ax_rate.fill_between(centers, rate_q05, rate_q95, color=band_color, alpha=0.65, label="5th-95th percentile")
    ax_rate.step(centers, rate_q50, where="mid", color=median_color, linewidth=2.3, label="Median")
    ax_rate.step(centers, mean_rate, where="mid", color=mean_color, linewidth=1.8, linestyle="--", label="Mean")
    ax_rate.set_title(f"Temporal Rate Decay (M>={summary.mag_complete:.1f})")
    ax_rate.set_ylabel(f"Events per {width[0]:.2f}-day bin")
    ax_rate.set_xlim(metrics.time_edges[0], metrics.time_edges[-1])
    ax_rate.set_xlabel("Relative time (days)")
    ax_rate.legend(frameon=False, loc="upper right")
    configure_axes(ax_rate)

    ax_cumulative.fill_between(
        centers,
        cum_q05,
        cum_q95,
        color=band_color,
        alpha=0.65,
        label="5th-95th percentile",
    )
    ax_cumulative.plot(centers, cum_q50, color=median_color, linewidth=2.3, label="Median")
    ax_cumulative.plot(centers, mean_cumulative, color=mean_color, linewidth=1.8, linestyle="--", label="Mean")
    ax_cumulative.set_title(f"Cumulative Ensemble Counts (M>={summary.mag_complete:.1f})")
    ax_cumulative.set_ylabel("Cumulative events")
    ax_cumulative.set_xlim(metrics.time_edges[0], metrics.time_edges[-1])
    ax_cumulative.set_xlabel("Relative time (days)")
    ax_cumulative.legend(frameon=False, loc="upper left")
    configure_axes(ax_cumulative)


def draw_threshold_panel(ax: plt.Axes, metrics: EnsembleMetrics, summary: SummaryInfo) -> None:
    thresholds = np.asarray(summary.thresholds, dtype=float)
    q05, q50, q95 = quantiles(metrics.threshold_counts)
    means = metrics.threshold_counts.mean(axis=0)
    analytic = np.asarray([summary.expected_counts[threshold] for threshold in thresholds], dtype=float)
    probs = np.asarray(
        [100.0 * float(np.mean(metrics.threshold_counts[:, idx] > 0)) for idx in range(len(thresholds))],
        dtype=float,
    )

    for idx, threshold in enumerate(thresholds):
        ax.vlines(threshold, q05[idx], q95[idx], color="#2A6F97", linewidth=7, alpha=0.9)
        ax.scatter(threshold, q50[idx], s=60, color="#0D3B66", zorder=3)
        ax.scatter(threshold + 0.04, means[idx], s=40, marker="D", color="#C8553D", zorder=3)
        ax.scatter(
            threshold - 0.04,
            analytic[idx],
            s=70,
            facecolors="#FCFAF7",
            edgecolors="#7A1F1F",
            linewidths=1.6,
            zorder=3,
        )
        label_y = max(q95[idx], analytic[idx], means[idx]) + max(1.5, 0.04 * max(q95[idx], 1.0))
        ax.text(threshold, label_y, f"{probs[idx]:.1f}%", ha="center", va="bottom", fontsize=9, color="#473F39")

    ax.set_title("Count Uncertainty by Magnitude Threshold")
    ax.set_xlabel("Magnitude threshold")
    ax.set_ylabel("Forecast count in days %.1f-%.1f" % (summary.forecast_start, summary.forecast_end))
    ax.set_xticks(thresholds)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    legend_lines = [
        plt.Line2D([0], [0], color="#2A6F97", linewidth=7, label="Simulated 5th-95th percentile"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="#0D3B66", markeredgecolor="#0D3B66", label="Simulated median"),
        plt.Line2D([0], [0], marker="D", color="none", markerfacecolor="#C8553D", markeredgecolor="#C8553D", label="Simulated mean"),
        plt.Line2D([0], [0], marker="o", color="#7A1F1F", markerfacecolor="#FCFAF7", markeredgewidth=1.6, label="Summary expected"),
    ]
    ax.legend(handles=legend_lines, frameon=False, loc="upper right")
    ax.text(
        0.02,
        0.02,
        "Labels show P(N>=1) from the simulated catalogs.",
        transform=ax.transAxes,
        fontsize=9,
        color="#4B4642",
        ha="left",
        va="bottom",
    )
    configure_axes(ax)


def draw_max_magnitude_panel(ax: plt.Axes, metrics: EnsembleMetrics, summary: SummaryInfo) -> None:
    finite_max = metrics.max_magnitudes[np.isfinite(metrics.max_magnitudes)]
    if finite_max.size == 0:
        ax.text(0.5, 0.5, "No simulated events found.", ha="center", va="center")
        configure_axes(ax)
        return

    lower = math.floor(min(summary.mag_complete, finite_max.min()) * 2.0) / 2.0
    upper = math.ceil(finite_max.max() * 10.0) / 10.0
    grid = np.arange(lower, upper + 0.101, 0.1)
    exceedance = np.asarray([np.mean(finite_max >= value) for value in grid], dtype=float)
    ax.step(grid, 100.0 * exceedance, where="post", color="#0D3B66", linewidth=2.3)

    for threshold in summary.thresholds:
        probability = 100.0 * float(np.mean(finite_max >= threshold))
        ax.scatter(threshold, probability, s=46, color="#C8553D", zorder=3)
        ax.text(threshold + 0.05, probability + 1.5, f"M≥{threshold:.1f}: {probability:.1f}%", fontsize=9, color="#473F39")

    median_max, p95_max = np.percentile(finite_max, [50, 95])
    ax.axvline(median_max, color="#6A994E", linestyle="--", linewidth=1.6)
    ax.axvline(p95_max, color="#BC4B51", linestyle=":", linewidth=1.8)
    ax.text(median_max, 8, f"Median max M={median_max:.2f}", rotation=90, va="bottom", ha="right", color="#456431")
    ax.text(p95_max, 8, f"95th pct max M={p95_max:.2f}", rotation=90, va="bottom", ha="left", color="#8A3034")
    ax.set_ylim(0, 105)
    ax.set_title("Maximum Magnitude Exceedance")
    ax.set_xlabel("Magnitude")
    ax.set_ylabel("P(max magnitude ≥ M) [%]")
    configure_axes(ax)


def draw_generation_panel(ax: plt.Axes, metrics: EnsembleMetrics) -> None:
    labels = ["Gen 1", "Gen 2", "Gen 3", "Gen 4+"]
    x = np.arange(len(labels))
    q05, q50, q95 = quantiles(metrics.generation_counts)
    means = metrics.generation_counts.mean(axis=0)
    colors = ["#0D3B66", "#2A6F97", "#7AAE7A", "#F4A259"]

    ax.bar(x, means, color=colors, width=0.7, alpha=0.85)
    ax.vlines(x, q05, q95, color="#473F39", linewidth=2.0)
    ax.scatter(x, q50, color="#7A1F1F", s=46, zorder=3)
    ax.set_xticks(x, labels)
    ax.set_title("Trigger Cascade Structure (M>=Mc)")
    ax.set_ylabel("Count per simulation")
    total = np.maximum(metrics.generation_counts.sum(axis=1), 1)
    indirect_share = metrics.generation_counts[:, 1:].sum(axis=1) / total
    ax.text(
        0.02,
        0.98,
        "Median indirect share (Gen>=2): %.1f%%" % (100.0 * float(np.median(indirect_share))),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#473F39",
        bbox={"facecolor": "#F6F3EE", "edgecolor": "none", "pad": 3.0, "alpha": 0.9},
    )
    legend_items = [
        plt.Line2D([0], [0], color="#473F39", linewidth=2.0, label="5th-95th percentile"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="#7A1F1F", markeredgecolor="#7A1F1F", label="Median"),
        plt.Rectangle((0, 0), 1, 1, color="#2A6F97", alpha=0.85, label="Mean"),
    ]
    ax.legend(handles=legend_items, frameon=False, loc="upper right")
    configure_axes(ax)


def draw_spatial_panel(
    ax: plt.Axes,
    rate_grid: tuple[np.ndarray, np.ndarray, np.ndarray] | None,
    metrics: EnsembleMetrics,
    spatial_mag: float,
    overlay_mag: float,
) -> None:
    heatmap_cmap = LinearSegmentedColormap.from_list(
        "etas_heat",
        ["#F8F4E8", "#E9C46A", "#F4A259", "#E76F51", "#9D2A2B"],
    )

    if rate_grid is None and (metrics.spatial_lats is None or metrics.spatial_lons is None):
        ax.text(0.5, 0.5, "Spatial columns or rate grid not available.", ha="center", va="center")
        ax.set_axis_off()
        return

    lat_limits = None
    lon_limits = None
    if rate_grid is not None:
        lats, lons, grid = rate_grid
        valid = grid[np.isfinite(grid) & (grid > 0)]
        norm = LogNorm(vmin=max(float(np.nanpercentile(valid, 5)), 1e-5), vmax=float(np.nanmax(valid))) if valid.size else None
        mesh = ax.pcolormesh(lons, lats, grid, shading="auto", cmap=heatmap_cmap, norm=norm)
        colorbar = plt.colorbar(mesh, ax=ax, fraction=0.045, pad=0.02)
        colorbar.set_label("Expected rate")
        lat_limits = (float(lats.min()), float(lats.max()))
        lon_limits = (float(lons.min()), float(lons.max()))

    if metrics.spatial_lats is not None and metrics.spatial_lons is not None:
        lat_data = metrics.spatial_lats
        lon_data = metrics.spatial_lons
        if lat_limits is not None and lon_limits is not None:
            in_bounds = (
                (lat_data >= lat_limits[0])
                & (lat_data <= lat_limits[1])
                & (lon_data >= lon_limits[0])
                & (lon_data <= lon_limits[1])
            )
            lat_data = lat_data[in_bounds]
            lon_data = lon_data[in_bounds]
        if lat_data.size and lon_data.size:
            if lat_limits is None:
                lat_limits = (float(np.min(lat_data)), float(np.max(lat_data)))
                lon_limits = (float(np.min(lon_data)), float(np.max(lon_data)))
            bins_lat = np.linspace(lat_limits[0], lat_limits[1], 55)
            bins_lon = np.linspace(lon_limits[0], lon_limits[1], 55)
            density, lat_edges, lon_edges = np.histogram2d(lat_data, lon_data, bins=[bins_lat, bins_lon])
            density = gaussian_filter(density, sigma=1.0)
            positive = density[density > 0]
            if positive.size:
                levels = np.quantile(positive, [0.70, 0.85, 0.95])
                levels = np.unique(levels)
                if levels.size:
                    lat_centers = 0.5 * (lat_edges[:-1] + lat_edges[1:])
                    lon_centers = 0.5 * (lon_edges[:-1] + lon_edges[1:])
                    ax.contour(
                        lon_centers,
                        lat_centers,
                        density,
                        levels=levels,
                        colors="#113A5D",
                        linewidths=1.2,
                        alpha=0.9,
                    )

    if metrics.large_lats is not None and metrics.large_lons is not None and metrics.large_mags is not None:
        lat_data = metrics.large_lats
        lon_data = metrics.large_lons
        mags = metrics.large_mags
        if lat_limits is not None and lon_limits is not None:
            in_bounds = (
                (lat_data >= lat_limits[0])
                & (lat_data <= lat_limits[1])
                & (lon_data >= lon_limits[0])
                & (lon_data <= lon_limits[1])
            )
            lat_data = lat_data[in_bounds]
            lon_data = lon_data[in_bounds]
            mags = mags[in_bounds]
        if lat_data.size:
            sizes = 8.0 + np.square(np.clip(mags - overlay_mag + 0.3, 0.3, None)) * 8.0
            ax.scatter(
                lon_data,
                lat_data,
                s=sizes,
                color="#FCFAF7",
                edgecolor="#7A1F1F",
                linewidth=0.5,
                alpha=0.18,
            )

    ax.set_title("Spatial Rate Field and Realized Event Density")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.text(
        0.02,
        0.02,
        "Contours: density of simulated M≥%.1f events\nPoints: simulated M≥%.1f events"
        % (spatial_mag, overlay_mag),
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
        color="#473F39",
        bbox={"facecolor": "#F6F3EE", "edgecolor": "none", "pad": 3.0, "alpha": 0.9},
    )
    configure_axes(ax)


def build_dashboard(
    summary: SummaryInfo,
    metrics: EnsembleMetrics,
    output_stem: Path,
    rate_grid: tuple[np.ndarray, np.ndarray, np.ndarray] | None,
    spatial_mag: float,
    overlay_mag: float,
    dpi: int,
) -> tuple[Path, Path]:
    set_plot_style()
    fig = plt.figure(figsize=(15.5, 11.5), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 1.05])

    ax_rate = fig.add_subplot(grid[0, 0])
    ax_cumulative = fig.add_subplot(grid[0, 1])
    ax_thresholds = fig.add_subplot(grid[1, 0])
    ax_maxmag = fig.add_subplot(grid[1, 1])
    ax_generation = fig.add_subplot(grid[2, 0])
    ax_spatial = fig.add_subplot(grid[2, 1])

    draw_temporal_panels(ax_rate, ax_cumulative, metrics, summary)
    draw_threshold_panel(ax_thresholds, metrics, summary)
    draw_max_magnitude_panel(ax_maxmag, metrics, summary)
    draw_generation_panel(ax_generation, metrics)
    draw_spatial_panel(ax_spatial, rate_grid, metrics, spatial_mag, overlay_mag)

    params_order = ["ams", "a", "p", "c", "b"]
    params_text = "  ".join(
        f"{name}={summary.fitted_params[name]:.2f}"
        for name in params_order
        if name in summary.fitted_params
    )
    fig.suptitle(
        f"NZ ETAS Ensemble Diagnostic Dashboard | Event {summary.event_id}",
        fontsize=17,
        fontweight="bold",
        color="#2E2A27",
    )
    fig.text(
        0.5,
        0.965,
        (
            f"Forecast days {summary.forecast_start:.1f}-{summary.forecast_end:.1f} | "
            f"Mc={summary.mag_complete:.1f} | {len(metrics.catalog_paths)} simulations processed | "
            f"{params_text}"
        ),
        ha="center",
        fontsize=10.5,
        color="#4B4642",
    )
    fig.text(
        0.5,
        0.008,
        (
            "Shaded bands and intervals are empirical 5th-95th percentiles from the simulated catalogs. "
            "Hollow markers in the threshold panel show the summary-file expected counts for comparison."
        ),
        ha="center",
        fontsize=9,
        color="#4B4642",
    )

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    fig.savefig(png_path, dpi=dpi, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, pdf_path


def peak_rate_location(rate_grid: tuple[np.ndarray, np.ndarray, np.ndarray] | None) -> tuple[float, float, float] | None:
    if rate_grid is None:
        return None
    lats, lons, grid = rate_grid
    if not np.isfinite(grid).any():
        return None
    index = np.nanargmax(grid)
    lat_idx, lon_idx = np.unravel_index(index, grid.shape)
    return float(lats[lat_idx]), float(lons[lon_idx]), float(grid[lat_idx, lon_idx])


def write_summary_markdown(
    summary: SummaryInfo,
    metrics: EnsembleMetrics,
    rate_grid: tuple[np.ndarray, np.ndarray, np.ndarray] | None,
    output_stem: Path,
    png_path: Path,
    pdf_path: Path,
    spatial_mag: float,
    overlay_mag: float,
) -> Path:
    thresholds = np.asarray(summary.thresholds, dtype=float)
    count_q05, count_q50, count_q95 = quantiles(metrics.threshold_counts)
    count_mean = metrics.threshold_counts.mean(axis=0)
    cumulative_final = metrics.cumulative_counts[:, -1]
    cum_q05, cum_q50, cum_q95 = np.percentile(cumulative_final, [5, 50, 95])
    finite_max = metrics.max_magnitudes[np.isfinite(metrics.max_magnitudes)]
    max_q50, max_q95 = np.percentile(finite_max, [50, 95]) if finite_max.size else (math.nan, math.nan)
    total = np.maximum(metrics.generation_counts.sum(axis=1), 1)
    indirect_share = metrics.generation_counts[:, 1:].sum(axis=1) / total
    rate_peak = peak_rate_location(rate_grid)

    lines = [
        "# NZ ETAS Visualization Summary",
        "",
        f"- Event: `{summary.event_id}`",
        f"- Analysis date: `{summary.analysis_date}`",
        f"- Forecast window: `{summary.forecast_start:.1f}` to `{summary.forecast_end:.1f}` days",
        f"- Magnitude of completeness: `Mc={summary.mag_complete:.1f}`",
        f"- Catalogs processed: `{len(metrics.catalog_paths)}`",
        f"- Dashboard files: `{png_path}` and `{pdf_path}`",
        "",
        "## Ensemble Diagnostics",
        "",
        (
            f"- Final cumulative `M>={summary.mag_complete:.1f}` count across the forecast window: "
            f"5th={cum_q05:.0f}, median={cum_q50:.0f}, 95th={cum_q95:.0f}."
        ),
        (
            f"- Maximum magnitude across each simulation: median `M={max_q50:.2f}`, "
            f"95th percentile `M={max_q95:.2f}`."
        ),
        (
            f"- Indirect triggering share (`Gen>=2`) has median `{100.0 * np.median(indirect_share):.1f}%` "
            f"of all `M>=Mc` events."
        ),
        (
            f"- Spatial contours summarize simulated `M>={spatial_mag:.1f}` events; "
            f"point overlays summarize `M>={overlay_mag:.1f}` events."
        ),
    ]

    if rate_peak is not None:
        lines.append(
            f"- Peak deterministic spatial rate is near lat `{rate_peak[0]:.3f}`, lon `{rate_peak[1]:.3f}` "
            f"with rate `{rate_peak[2]:.4g}`."
        )

    lines.extend(["", "## Threshold Comparison", ""])

    for idx, threshold in enumerate(thresholds):
        simulated_probability = float(np.mean(metrics.threshold_counts[:, idx] > 0))
        summary_probability = summary.probabilities.get(float(threshold), float("nan"))
        lines.append(
            (
                f"- `M>={threshold:.1f}`: simulated mean `{count_mean[idx]:.2f}`, "
                f"simulated 5th/50th/95th `{count_q05[idx]:.0f}/{count_q50[idx]:.0f}/{count_q95[idx]:.0f}`, "
                f"summary expected `{summary.expected_counts[float(threshold)]:.2f}`, "
                f"simulated P(N>=1) `{100.0 * simulated_probability:.1f}%`, "
                f"summary P(N>=1) `{100.0 * summary_probability:.1f}%`."
            )
        )

    discrepancies: list[str] = []
    for idx, threshold in enumerate(thresholds):
        expected = summary.expected_counts[float(threshold)]
        simulated = float(count_mean[idx])
        if expected > 0:
            relative_diff = abs(simulated - expected) / expected
            if relative_diff >= 0.15:
                discrepancies.append(
                    f"`M>={threshold:.1f}` count mean differs by `{100.0 * relative_diff:.1f}%` "
                    f"(simulated `{simulated:.2f}` vs summary `{expected:.2f}`)."
                )

    lines.extend(["", "## Notes", ""])
    if discrepancies:
        lines.append(
            "- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:"
        )
        lines.extend([f"  - {item}" for item in discrepancies])
    else:
        lines.append("- Summary-file expected counts are broadly consistent with the catalog-derived ensemble means.")
    lines.append(
        "- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior."
    )

    summary_path = output_stem.parent / f"{output_stem.name}_summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary)
    catalog_dir = Path(args.catalog_dir)
    spatial_rate_path = Path(args.spatial_rate)
    output_stem = Path(args.output_stem)

    summary = parse_summary(summary_path)
    catalog_paths = sorted(catalog_dir.glob("sim_*.txt"))
    if not catalog_paths:
        raise FileNotFoundError(f"No simulated catalogs found in {catalog_dir}")

    spatial_mag = (
        max(summary.mag_complete, args.spatial_mag)
        if args.spatial_mag is not None
        else max(summary.mag_complete, summary.thresholds[1] if len(summary.thresholds) > 1 else summary.thresholds[0])
    )
    overlay_mag = (
        max(spatial_mag, args.overlay_mag)
        if args.overlay_mag is not None
        else max(spatial_mag, summary.thresholds[2] if len(summary.thresholds) > 2 else spatial_mag)
    )

    metrics = compute_ensemble_metrics(
        catalog_paths=catalog_paths,
        summary=summary,
        time_bin_days=args.time_bin_days,
        spatial_mag=spatial_mag,
        overlay_mag=overlay_mag,
    )
    rate_grid = load_spatial_rate_grid(spatial_rate_path)
    png_path, pdf_path = build_dashboard(
        summary=summary,
        metrics=metrics,
        output_stem=output_stem,
        rate_grid=rate_grid,
        spatial_mag=spatial_mag,
        overlay_mag=overlay_mag,
        dpi=args.dpi,
    )
    summary_md = write_summary_markdown(
        summary=summary,
        metrics=metrics,
        rate_grid=rate_grid,
        output_stem=output_stem,
        png_path=png_path,
        pdf_path=pdf_path,
        spatial_mag=spatial_mag,
        overlay_mag=overlay_mag,
    )

    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    print(f"Wrote {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
