#!/usr/bin/env python3
"""Use pyCSEP to evaluate and visualize NZ ETAS simulated catalogs."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import csep
from csep import plots
from csep.core import catalog_evaluations, poisson_evaluations, regions
from csep.core.catalogs import CSEPCatalog
from csep.core.forecasts import CatalogForecast, GriddedForecast
from csep.core.repositories import write_json
from csep.utils.time_utils import datetime_to_utc_epoch


WINDOW_PATTERN = re.compile(r"--- Forecast \(Days ([0-9.]+)-([0-9.]+)\) ---")
GEONET_EVENT_URL = "https://service.geonet.org.nz/fdsnws/event/1/query?eventid={event_id}"
MILLIS_PER_DAY = 86_400_000.0


@dataclass
class SummaryInfo:
    event_id: str
    analysis_date: str
    mag_complete: float
    forecast_start: float
    forecast_end: float


@dataclass
class ConfigInfo:
    event_id: str
    mag_complete: float
    forecast_start: float
    forecast_end: float
    min_depth: float
    max_depth: float


@dataclass
class ForecastContext:
    event_id: str
    analysis_date: str
    mag_complete: float
    forecast_start: float
    forecast_end: float
    min_depth: float
    max_depth: float


@dataclass
class MainshockInfo:
    event_id: str
    origin_time: datetime
    latitude: float = math.nan
    longitude: float = math.nan
    depth_km: float = math.nan
    magnitude: float = math.nan
    source: str = ""


@dataclass
class CatalogBuildStats:
    raw_count: int
    kept_magnitude_count: int
    kept_spatial_count: int


@dataclass
class CatalogTestDiagnostics:
    observed_event_count: int
    observed_events_in_zero_spatial_rate_cells: int
    observed_nonzero_spatial_cells_with_zero_rate: int
    observed_events_in_zero_space_magnitude_bins: int
    total_spatial_cells: int
    zero_spatial_rate_cells: int


@dataclass
class CatalogArrays:
    name: str
    relative_days: np.ndarray
    magnitudes: np.ndarray
    generations: np.ndarray
    latitudes: np.ndarray
    longitudes: np.ndarray
    raw_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert NZ ETAS simulated catalogs into pyCSEP objects, formal tests, and figures."
    )
    parser.add_argument("--summary", default="nz_etas_simulations.txt", help="Path to ETAS summary file.")
    parser.add_argument("--config", default="etas_config.json", help="Path to ETAS configuration JSON.")
    parser.add_argument("--catalog-dir", default="simulated_catalogs", help="Directory containing sim_*.txt files.")
    parser.add_argument(
        "--output-dir",
        default="build/pycsep",
        help="Directory for generated pyCSEP plots, cached GeoNet data, and summaries.",
    )
    parser.add_argument(
        "--mainshock-time",
        default=None,
        help="Optional ISO-8601 UTC time for the mainshock. Overrides GeoNet event lookup.",
    )
    parser.add_argument(
        "--reference-time",
        default=None,
        help="Legacy absolute anchor used only if GeoNet event lookup is unavailable.",
    )
    parser.add_argument(
        "--observed-catalog",
        default=None,
        help="Optional pyCSEP ASCII observed catalog to use instead of downloading from GeoNet.",
    )
    parser.add_argument(
        "--skip-observed",
        action="store_true",
        help="Skip GeoNet observed-catalog download and observation-based pyCSEP tests.",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Optional directory for cached GeoNet mainshock and observed catalog files.",
    )
    parser.add_argument(
        "--rolling-window-days",
        type=float,
        default=1.0,
        help="Width of rolling sub-windows in days for within-forecast number-test diagnostics.",
    )
    parser.add_argument(
        "--max-catalogs",
        type=int,
        default=None,
        help="Optional cap on the number of simulated catalogs to load.",
    )
    return parser.parse_args()


def parse_datetime(raw_value: str) -> datetime:
    value = raw_value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_summary(path: Path) -> SummaryInfo:
    event_id = ""
    analysis_date = ""
    mag_complete = math.nan
    forecast_start = math.nan
    forecast_end = math.nan

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("Event:"):
            event_id = line.split(":", 1)[1].strip()
        elif line.startswith("Analysis Date:"):
            analysis_date = line.split(":", 1)[1].strip()
        elif line.startswith("Mag Complete (Mc):"):
            mag_complete = float(line.split(":", 1)[1].strip())
        else:
            match = WINDOW_PATTERN.search(raw_line)
            if match:
                forecast_start = float(match.group(1))
                forecast_end = float(match.group(2))

    if not math.isfinite(mag_complete) or not math.isfinite(forecast_start) or not math.isfinite(forecast_end):
        raise ValueError(f"Could not parse required ETAS metadata from {path}")

    return SummaryInfo(
        event_id=event_id,
        analysis_date=analysis_date,
        mag_complete=mag_complete,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
    )


def parse_config(path: Path) -> ConfigInfo:
    if not path.exists():
        return ConfigInfo(
            event_id="",
            mag_complete=math.nan,
            forecast_start=math.nan,
            forecast_end=math.nan,
            min_depth=-10.0,
            max_depth=100.0,
        )
    config = json.loads(path.read_text(encoding="utf-8"))
    return ConfigInfo(
        event_id=str(config.get("eventId", "")).strip(),
        mag_complete=float(config.get("catalog", {}).get("magComplete", math.nan)),
        forecast_start=float(config.get("forecastWindow", {}).get("minDays", math.nan)),
        forecast_end=float(config.get("forecastWindow", {}).get("maxDays", math.nan)),
        min_depth=float(config.get("region", {}).get("minDepth", -10.0)),
        max_depth=float(config.get("region", {}).get("maxDepth", 100.0)),
    )


def merge_metadata(summary: SummaryInfo, config: ConfigInfo) -> ForecastContext:
    event_id = summary.event_id or config.event_id
    mag_complete = summary.mag_complete if math.isfinite(summary.mag_complete) else config.mag_complete
    forecast_start = summary.forecast_start if math.isfinite(summary.forecast_start) else config.forecast_start
    forecast_end = summary.forecast_end if math.isfinite(summary.forecast_end) else config.forecast_end
    if not event_id or not math.isfinite(mag_complete) or not math.isfinite(forecast_start) or not math.isfinite(forecast_end):
        raise ValueError("Insufficient ETAS metadata. Ensure the summary and config files contain the event, Mc, and forecast window.")
    return ForecastContext(
        event_id=event_id,
        analysis_date=summary.analysis_date,
        mag_complete=mag_complete,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
        min_depth=config.min_depth,
        max_depth=config.max_depth,
    )


def load_etas_catalog(path: Path, mag_complete: float) -> CatalogArrays:
    relative_days: list[float] = []
    magnitudes: list[float] = []
    generations: list[int] = []
    latitudes: list[float] = []
    longitudes: list[float] = []
    raw_count = 0

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("Time "):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            raw_count += 1
            magnitude = float(parts[1])
            if magnitude < mag_complete:
                continue
            relative_days.append(float(parts[0]))
            magnitudes.append(magnitude)
            generations.append(int(parts[2]))
            latitudes.append(float(parts[3]))
            longitudes.append(float(parts[4]))

    arrays = CatalogArrays(
        name=path.stem,
        relative_days=np.asarray(relative_days, dtype=float),
        magnitudes=np.asarray(magnitudes, dtype=float),
        generations=np.asarray(generations, dtype=int),
        latitudes=np.asarray(latitudes, dtype=float),
        longitudes=np.asarray(longitudes, dtype=float),
        raw_count=raw_count,
    )

    if arrays.relative_days.size > 1 and np.any(arrays.relative_days[:-1] > arrays.relative_days[1:]):
        order = np.argsort(arrays.relative_days, kind="mergesort")
        arrays.relative_days = arrays.relative_days[order]
        arrays.magnitudes = arrays.magnitudes[order]
        arrays.generations = arrays.generations[order]
        arrays.latitudes = arrays.latitudes[order]
        arrays.longitudes = arrays.longitudes[order]

    return arrays


def build_region(context: ForecastContext, max_mag: float):
    max_mag_edge = max(context.mag_complete + 0.1, math.ceil(max_mag * 10.0) / 10.0 + 0.1)
    magnitudes = regions.magnitude_bins(context.mag_complete, max_mag_edge, 0.1)
    return regions.create_space_magnitude_region(regions.nz_csep_region(), magnitudes)


def build_catalog(
    arrays: CatalogArrays,
    catalog_id: int,
    mainshock_time: datetime,
    region,
) -> tuple[CSEPCatalog, CatalogBuildStats]:
    epoch_origin = datetime_to_utc_epoch(mainshock_time)
    event_count = arrays.relative_days.size
    data = np.empty(event_count, dtype=CSEPCatalog.dtype)
    if event_count:
        data["id"] = np.asarray([f"{arrays.name}_{idx:06d}".encode("utf-8") for idx in range(event_count)], dtype="S256")
        data["origin_time"] = np.rint(epoch_origin + arrays.relative_days * MILLIS_PER_DAY).astype(np.int64)
        data["latitude"] = arrays.latitudes
        data["longitude"] = arrays.longitudes
        data["depth"] = 0.0
        data["magnitude"] = arrays.magnitudes

    catalog = CSEPCatalog(data=data, catalog_id=catalog_id, name=arrays.name)
    catalog.region = region
    catalog = catalog.filter_spatial(region=region, in_place=False)

    stats = CatalogBuildStats(
        raw_count=arrays.raw_count,
        kept_magnitude_count=event_count,
        kept_spatial_count=catalog.event_count,
    )
    return catalog, stats


def representative_catalog(catalogs: list[CSEPCatalog]) -> CSEPCatalog:
    counts = np.asarray([catalog.event_count for catalog in catalogs], dtype=int)
    median_count = float(np.median(counts))
    representative_index = int(np.argmin(np.abs(counts - median_count)))
    return catalogs[representative_index]


def sanitize_token(value: str) -> str:
    return value.replace(".", "p").replace("-", "m")


def cache_paths(cache_dir: Path, context: ForecastContext) -> tuple[Path, Path]:
    window_token = f"d{sanitize_token(f'{context.forecast_start:g}')}_{sanitize_token(f'{context.forecast_end:g}')}"
    mc_token = f"mc{sanitize_token(f'{context.mag_complete:g}')}"
    mainshock_path = cache_dir / f"{context.event_id}_mainshock.json"
    observed_path = cache_dir / f"{context.event_id}_{window_token}_{mc_token}_observed.csv"
    return mainshock_path, observed_path


def save_mainshock_cache(path: Path, mainshock: MainshockInfo) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event_id": mainshock.event_id,
        "origin_time": mainshock.origin_time.isoformat(),
        "latitude": mainshock.latitude,
        "longitude": mainshock.longitude,
        "depth_km": mainshock.depth_km,
        "magnitude": mainshock.magnitude,
        "source": mainshock.source,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_mainshock_cache(path: Path) -> Optional[MainshockInfo]:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return MainshockInfo(
        event_id=str(payload["event_id"]),
        origin_time=parse_datetime(str(payload["origin_time"])),
        latitude=float(payload.get("latitude", math.nan)),
        longitude=float(payload.get("longitude", math.nan)),
        depth_km=float(payload.get("depth_km", math.nan)),
        magnitude=float(payload.get("magnitude", math.nan)),
        source=str(payload.get("source", "cache")),
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_first_descendant(element: ET.Element, name: str) -> Optional[ET.Element]:
    for descendant in element.iter():
        if _local_name(descendant.tag) == name:
            return descendant
    return None


def _find_matching_descendant(element: ET.Element, name: str, public_id: str) -> Optional[ET.Element]:
    for descendant in element.iter():
        if _local_name(descendant.tag) == name and descendant.attrib.get("publicID") == public_id:
            return descendant
    return None


def _text_at_path(element: Optional[ET.Element], *path: str) -> Optional[str]:
    current = element
    for component in path:
        if current is None:
            return None
        current = _find_first_descendant(current, component)
    if current is None or current.text is None:
        return None
    return current.text.strip()


def fetch_geonet_mainshock(event_id: str) -> MainshockInfo:
    url = GEONET_EVENT_URL.format(event_id=event_id)
    with urllib.request.urlopen(url, timeout=60) as response:
        xml_payload = response.read()
    root = ET.fromstring(xml_payload)
    event = _find_first_descendant(root, "event")
    if event is None:
        raise RuntimeError(f"GeoNet event lookup returned no <event> for {event_id}")

    preferred_origin_id = _text_at_path(event, "preferredOriginID")
    preferred_magnitude_id = _text_at_path(event, "preferredMagnitudeID")
    origin = _find_matching_descendant(event, "origin", preferred_origin_id) if preferred_origin_id else None
    magnitude = _find_matching_descendant(event, "magnitude", preferred_magnitude_id) if preferred_magnitude_id else None
    origin = origin or _find_first_descendant(event, "origin")
    magnitude = magnitude or _find_first_descendant(event, "magnitude")
    if origin is None or magnitude is None:
        raise RuntimeError(f"GeoNet event lookup for {event_id} did not contain a usable origin and magnitude.")

    origin_time_text = _text_at_path(origin, "time", "value")
    latitude_text = _text_at_path(origin, "latitude", "value")
    longitude_text = _text_at_path(origin, "longitude", "value")
    depth_text = _text_at_path(origin, "depth", "value")
    magnitude_text = _text_at_path(magnitude, "mag", "value")
    if not origin_time_text or not latitude_text or not longitude_text or not depth_text or not magnitude_text:
        raise RuntimeError(f"GeoNet event lookup for {event_id} was missing one or more required fields.")

    public_id = event.attrib.get("publicID", event_id)
    clean_id = public_id.rsplit("/", 1)[-1]
    return MainshockInfo(
        event_id=clean_id,
        origin_time=parse_datetime(origin_time_text),
        latitude=float(latitude_text),
        longitude=float(longitude_text),
        depth_km=float(depth_text) / 1000.0,
        magnitude=float(magnitude_text),
        source="GeoNet FDSN event service",
    )


def resolve_mainshock(
    context: ForecastContext,
    override_time: Optional[str],
    fallback_time: Optional[str],
    cache_path: Path,
) -> MainshockInfo:
    cached = load_mainshock_cache(cache_path)
    if override_time:
        mainshock = MainshockInfo(
            event_id=context.event_id,
            origin_time=parse_datetime(override_time),
            source="--mainshock-time",
        )
        if cached and math.isfinite(cached.latitude):
            mainshock.latitude = cached.latitude
            mainshock.longitude = cached.longitude
            mainshock.depth_km = cached.depth_km
            mainshock.magnitude = cached.magnitude
        save_mainshock_cache(cache_path, mainshock)
        return mainshock
    if cached is not None and cached.source != "--reference-time":
        return cached
    try:
        mainshock = fetch_geonet_mainshock(context.event_id)
    except Exception:
        if cached is not None:
            return cached
        if fallback_time:
            mainshock = MainshockInfo(
                event_id=context.event_id,
                origin_time=parse_datetime(fallback_time),
                source="--reference-time",
            )
        else:
            raise
    save_mainshock_cache(cache_path, mainshock)
    return mainshock


def observed_catalog_name(context: ForecastContext) -> str:
    return f"GeoNet observed {context.event_id} days {context.forecast_start:.1f}-{context.forecast_end:.1f}"


def window_datetimes(mainshock: MainshockInfo, context: ForecastContext) -> tuple[datetime, datetime]:
    return (
        mainshock.origin_time + timedelta(days=context.forecast_start),
        mainshock.origin_time + timedelta(days=context.forecast_end),
    )


def load_cached_observed_catalog(path: Path, region, context: ForecastContext) -> Optional[CSEPCatalog]:
    if not path.exists():
        return None
    catalog = CSEPCatalog.load_catalog(filename=str(path), name=observed_catalog_name(context), region=region)
    catalog.region = region
    return catalog


def filter_catalog_absolute_window(catalog: CSEPCatalog, start_time: datetime, end_time: datetime) -> CSEPCatalog:
    start_epoch = datetime_to_utc_epoch(start_time)
    end_epoch = datetime_to_utc_epoch(end_time)
    return catalog.filter(
        [f"origin_time >= {start_epoch}", f"origin_time < {end_epoch}"],
        in_place=False,
    )


def load_or_query_observed_catalog(
    context: ForecastContext,
    mainshock: MainshockInfo,
    region,
    observed_path: Path,
    observed_override: Optional[str],
    skip_observed: bool,
) -> Optional[CSEPCatalog]:
    if observed_override:
        catalog = CSEPCatalog.load_catalog(filename=str(observed_override), name=observed_catalog_name(context), region=region)
        catalog.region = region
        return catalog.filter_spatial(region=region, in_place=False)

    cached = load_cached_observed_catalog(observed_path, region=region, context=context)
    if cached is not None:
        return cached
    if skip_observed:
        return None

    start_time, end_time = window_datetimes(mainshock, context)
    lon_min, lon_max, lat_min, lat_max = regions.nz_csep_region().get_bbox()
    observed = csep.query_gns(
        start_time=start_time,
        end_time=end_time,
        min_magnitude=context.mag_complete,
        min_latitude=float(lat_min),
        max_latitude=float(lat_max),
        min_longitude=float(lon_min),
        max_longitude=float(lon_max),
        max_depth=context.max_depth,
        verbose=False,
    )
    filters = [
        f"magnitude >= {context.mag_complete}",
        f"depth >= {context.min_depth}",
        f"depth <= {context.max_depth}",
        f"origin_time >= {datetime_to_utc_epoch(start_time)}",
        f"origin_time < {datetime_to_utc_epoch(end_time)}",
    ]
    observed = observed.filter(filters, in_place=False)
    observed.region = region
    observed = observed.filter_spatial(region=region, in_place=False)
    observed.name = observed_catalog_name(context)
    observed_path.parent.mkdir(parents=True, exist_ok=True)
    observed.write_ascii(str(observed_path))
    return observed


def save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def save_axis(ax: plt.Axes, path: Path) -> None:
    save_figure(ax.figure, path)


def remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def build_uniform_benchmark(expected_rates: GriddedForecast) -> GriddedForecast:
    benchmark_data = np.zeros_like(expected_rates.data)
    magnitude_totals = expected_rates.magnitude_counts()
    num_nodes = benchmark_data.shape[0]
    if num_nodes > 0:
        benchmark_data[:] = magnitude_totals / num_nodes
    return GriddedForecast(
        start_time=expected_rates.start_time,
        end_time=expected_rates.end_time,
        data=benchmark_data,
        region=expected_rates.region,
        magnitudes=expected_rates.magnitudes,
        name="Uniform-space benchmark",
    )


def compute_catalog_test_diagnostics(
    expected_rates: GriddedForecast,
    observed_catalog: CSEPCatalog,
) -> CatalogTestDiagnostics:
    expected_spatial = expected_rates.spatial_counts()
    observed_spatial = observed_catalog.spatial_counts()
    zero_spatial_rate_mask = expected_spatial <= 0.0
    observed_in_zero_spatial_cells = (observed_spatial > 0) & zero_spatial_rate_mask
    target_rates, _ = expected_rates.target_event_rates(observed_catalog)
    return CatalogTestDiagnostics(
        observed_event_count=int(observed_catalog.event_count),
        observed_events_in_zero_spatial_rate_cells=int(np.sum(observed_spatial[observed_in_zero_spatial_cells])),
        observed_nonzero_spatial_cells_with_zero_rate=int(np.count_nonzero(observed_in_zero_spatial_cells)),
        observed_events_in_zero_space_magnitude_bins=int(np.count_nonzero(target_rates <= 0.0)),
        total_spatial_cells=int(expected_spatial.size),
        zero_spatial_rate_cells=int(np.count_nonzero(zero_spatial_rate_mask)),
    )


def _run_catalog_test_with_captured_stdout(callback):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = callback()
    return result, buffer.getvalue().strip()


def run_catalog_based_consistency_tests(
    forecast: CatalogForecast,
    observed_catalog: CSEPCatalog,
) -> tuple[dict[str, object], list[str]]:
    results: dict[str, object] = {}
    messages: list[str] = []

    results["catalog_number_test"] = catalog_evaluations.number_test(forecast, observed_catalog, verbose=False)
    results["catalog_magnitude_test"] = catalog_evaluations.magnitude_test(forecast, observed_catalog, verbose=False)

    spatial_result, spatial_stdout = _run_catalog_test_with_captured_stdout(
        lambda: catalog_evaluations.spatial_test(forecast, observed_catalog, verbose=False)
    )
    results["catalog_spatial_test"] = spatial_result
    if spatial_stdout:
        messages.append(spatial_stdout)

    pseudolikelihood_result, pseudolikelihood_stdout = _run_catalog_test_with_captured_stdout(
        lambda: catalog_evaluations.pseudolikelihood_test(forecast, observed_catalog, verbose=False)
    )
    results["catalog_pseudolikelihood_test"] = pseudolikelihood_result
    if pseudolikelihood_stdout and pseudolikelihood_stdout != spatial_stdout:
        messages.append(pseudolikelihood_stdout)

    results["catalog_resampled_magnitude_test"] = catalog_evaluations.resampled_magnitude_test(
        forecast, observed_catalog, verbose=False, seed=12345
    )
    results["catalog_mll_magnitude_test"] = catalog_evaluations.MLL_magnitude_test(
        forecast, observed_catalog, verbose=False, seed=12345
    )
    return results, messages


def compute_indirect_fraction_percent(catalog_arrays: list[CatalogArrays]) -> np.ndarray:
    fractions = []
    for arrays in catalog_arrays:
        if arrays.generations.size == 0:
            fractions.append(0.0)
        else:
            fractions.append(100.0 * np.mean(arrays.generations >= 2))
    return np.asarray(fractions, dtype=float)


def plot_generation_resolved_cumulative(
    path: Path,
    catalog_arrays: list[CatalogArrays],
    context: ForecastContext,
) -> None:
    time_grid = np.linspace(context.forecast_start, context.forecast_end, 240)
    categories = [
        ("All M>=Mc", lambda arrays: np.ones(arrays.relative_days.shape, dtype=bool), "#1b4965"),
        ("Generation 1", lambda arrays: arrays.generations == 1, "#2a9d8f"),
        ("Generation >=2", lambda arrays: arrays.generations >= 2, "#e76f51"),
    ]

    fig, ax = plt.subplots(figsize=(11, 7))
    for label, selector, color in categories:
        ensemble_counts = np.zeros((len(catalog_arrays), time_grid.size), dtype=float)
        for idx, arrays in enumerate(catalog_arrays):
            mask = selector(arrays)
            times = arrays.relative_days[mask]
            ensemble_counts[idx, :] = np.searchsorted(times, time_grid, side="right")
        q05, q50, q95 = np.quantile(ensemble_counts, [0.05, 0.5, 0.95], axis=0)
        ax.fill_between(time_grid, q05, q95, color=color, alpha=0.14)
        ax.plot(time_grid, q50, color=color, linewidth=2.0, label=f"{label} median")

    ax.set_title("Generation-resolved ETAS cumulative counts")
    ax.set_xlabel("Days since mainshock")
    ax.set_ylabel("Cumulative event count")
    ax.grid(alpha=0.3)
    ax.legend()
    save_figure(fig, path)


def selected_exceedance_windows(context: ForecastContext) -> list[tuple[str, float, float]]:
    duration = context.forecast_end - context.forecast_start
    candidate_lengths = sorted({duration, min(duration, 1.0), min(duration, 3.0), min(duration, 5.0)})
    windows = []
    for length in candidate_lengths:
        if length <= 0:
            continue
        end_day = context.forecast_start + length
        windows.append((f"Days {context.forecast_start:.1f}-{end_day:.1f}", context.forecast_start, end_day))
    windows.sort(key=lambda item: item[2])
    return windows


def window_maximum_magnitude(arrays: CatalogArrays, start_day: float, end_day: float) -> float:
    mask = (arrays.relative_days >= start_day) & (arrays.relative_days < end_day)
    if not np.any(mask):
        return -np.inf
    return float(np.max(arrays.magnitudes[mask]))


def observed_window_maximum(observed_catalog: Optional[CSEPCatalog], start_time: datetime, end_time: datetime) -> float:
    if observed_catalog is None:
        return math.nan
    subcatalog = filter_catalog_absolute_window(observed_catalog, start_time, end_time)
    if subcatalog.event_count == 0:
        return math.nan
    return float(np.max(subcatalog.get_magnitudes()))


def plot_maximum_magnitude_exceedance(
    path: Path,
    catalog_arrays: list[CatalogArrays],
    context: ForecastContext,
    mainshock: MainshockInfo,
    observed_catalog: Optional[CSEPCatalog],
) -> None:
    global_max = max(
        [context.mag_complete]
        + [float(np.max(arrays.magnitudes)) for arrays in catalog_arrays if arrays.magnitudes.size]
    )
    magnitude_grid = np.arange(context.mag_complete, math.ceil(global_max * 10.0) / 10.0 + 0.11, 0.1)
    colors = ["#003049", "#669bbc", "#f77f00", "#d62828"]

    fig, ax = plt.subplots(figsize=(11, 7))
    for color, (label, start_day, end_day) in zip(colors, selected_exceedance_windows(context)):
        maxima = np.asarray(
            [window_maximum_magnitude(arrays, start_day, end_day) for arrays in catalog_arrays],
            dtype=float,
        )
        exceedance = np.mean(maxima[:, None] >= magnitude_grid[None, :], axis=0)
        obs_max = observed_window_maximum(
            observed_catalog,
            mainshock.origin_time + timedelta(days=start_day),
            mainshock.origin_time + timedelta(days=end_day),
        )
        curve_label = label if not math.isfinite(obs_max) else f"{label} (obs max {obs_max:.2f})"
        ax.plot(magnitude_grid, exceedance, linewidth=2.0, color=color, label=curve_label)

    ax.set_title("ETAS maximum-magnitude exceedance by forecast sub-window")
    ax.set_xlabel("Magnitude threshold")
    ax.set_ylabel("P(Max magnitude >= threshold)")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.3)
    ax.legend()
    save_figure(fig, path)


def plot_spatial_residuals(path: Path, expected_rates: GriddedForecast, observed_catalog: CSEPCatalog) -> None:
    observed_counts = observed_catalog.spatial_counts()
    expected_counts = expected_rates.spatial_counts()
    residuals = (observed_counts - expected_counts) / np.sqrt(np.maximum(expected_counts, 1.0e-6))
    residual_grid = expected_rates.region.get_cartesian(residuals)
    clim = float(np.max(np.abs(residuals))) if residuals.size else 1.0
    clim = max(clim, 1.0)
    ax = plots.plot_gridded_dataset(
        residual_grid,
        expected_rates.region,
        basemap=None,
        colormap="RdBu_r",
        clim=(-clim, clim),
        clabel="(Observed - expected) / sqrt(expected)",
        title="Spatial residual map against GeoNet observations",
        show=False,
    )
    save_axis(ax, path)


def build_rolling_windows(context: ForecastContext, window_days: float) -> list[tuple[float, float]]:
    width = context.forecast_end - context.forecast_start
    if width <= 0:
        return []
    step = max(min(window_days, width), min(width, 0.25))
    edges = [context.forecast_start]
    current = context.forecast_start
    while current < context.forecast_end - 1.0e-9:
        current = min(current + step, context.forecast_end)
        edges.append(current)
    return [(edges[idx], edges[idx + 1]) for idx in range(len(edges) - 1)]


def build_subforecast(
    forecast: CatalogForecast,
    start_time: datetime,
    end_time: datetime,
    label: str,
) -> CatalogForecast:
    subcatalogs = [filter_catalog_absolute_window(catalog, start_time, end_time) for catalog in forecast.catalogs]
    return CatalogForecast(
        catalogs=subcatalogs,
        start_time=start_time,
        end_time=end_time,
        region=forecast.region,
        n_cat=len(subcatalogs),
        name=label,
    )


def run_rolling_number_tests(
    forecast: CatalogForecast,
    observed_catalog: CSEPCatalog,
    context: ForecastContext,
    mainshock: MainshockInfo,
    window_days: float,
) -> tuple[list, Optional[object]]:
    results = []
    for start_day, end_day in build_rolling_windows(context, window_days):
        start_time = mainshock.origin_time + timedelta(days=start_day)
        end_time = mainshock.origin_time + timedelta(days=end_day)
        label = f"Days {start_day:.1f}-{end_day:.1f}"
        subforecast = build_subforecast(forecast, start_time, end_time, label)
        subobserved = filter_catalog_absolute_window(observed_catalog, start_time, end_time)
        subobserved.region = forecast.region
        result = catalog_evaluations.number_test(subforecast, subobserved, verbose=False)
        result.sim_name = label
        result.obs_name = observed_catalog.name
        results.append(result)
    calibration_result = None
    if len(results) >= 2:
        calibration_result = catalog_evaluations.calibration_test(results)
    return results, calibration_result


def write_summary(
    path: Path,
    context: ForecastContext,
    mainshock: MainshockInfo,
    forecast: CatalogForecast,
    representative: CSEPCatalog,
    stats: list[CatalogBuildStats],
    observed_catalog: Optional[CSEPCatalog],
    observed_path: Optional[Path],
    catalog_test_diagnostics: Optional[CatalogTestDiagnostics],
    catalog_test_messages: list[str],
    evaluation_results: dict[str, object],
    rolling_results: list,
    calibration_result: Optional[object],
    output_files: list[Path],
    indirect_fraction_percent: np.ndarray,
) -> None:
    def format_scalar(value: object) -> str:
        if value is None:
            return "None"
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        if isinstance(value, (float, np.floating)):
            value = float(value)
            if math.isnan(value):
                return "nan"
            if math.isinf(value):
                return "-inf" if value < 0 else "inf"
            return f"{value:.6g}"
        return str(value)

    def format_quantile(value: object) -> str:
        if isinstance(value, (tuple, list)):
            return "(" + ", ".join(format_scalar(item) for item in value) + ")"
        return format_scalar(value)

    raw_total = sum(item.raw_count for item in stats)
    magnitude_total = sum(item.kept_magnitude_count for item in stats)
    spatial_total = sum(item.kept_spatial_count for item in stats)
    counts = np.asarray([catalog.event_count for catalog in forecast.catalogs], dtype=float)
    lines = [
        "# pyCSEP NZ ETAS Summary",
        "",
        f"- pyCSEP version: `{getattr(csep, '__version__', 'unknown')}`",
        f"- pyCSEP source: `{csep.__file__}`",
        f"- Event: `{context.event_id}`",
        f"- Analysis date: `{context.analysis_date}`",
        f"- Mainshock origin time: `{mainshock.origin_time.isoformat()}`",
        f"- Mainshock metadata source: `{mainshock.source}`",
        f"- Mainshock magnitude: `{mainshock.magnitude:.2f}`" if math.isfinite(mainshock.magnitude) else "- Mainshock magnitude: unavailable",
        f"- Forecast window: `{context.forecast_start:.1f}` to `{context.forecast_end:.1f}` days",
        f"- Forecast absolute window: `{forecast.start_time.isoformat()}` to `{forecast.end_time.isoformat()}`",
        f"- Catalogs loaded into pyCSEP: `{forecast.n_cat}`",
        f"- Raw ETAS rows read: `{raw_total}`",
        f"- Events kept after `M>=Mc` filtering: `{magnitude_total}`",
        f"- Events kept after NZ pyCSEP region filtering: `{spatial_total}`",
        f"- Representative catalog: `{representative.name}` with `{representative.event_count}` events",
        f"- Ensemble event-count median: `{np.median(counts):.0f}`",
        f"- Median indirect (`Gen>=2`) share of `M>=Mc` events: `{np.median(indirect_fraction_percent):.1f}%`",
        "",
        "## Observed Catalog",
        "",
    ]
    if observed_catalog is None:
        lines.extend(
            [
                "- No observed GeoNet catalog was available. Observation-based pyCSEP tests were skipped.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"- Observed catalog: `{observed_catalog.name}`",
                f"- Observed event count in testing region: `{observed_catalog.event_count}`",
                f"- Observed catalog cache: `{observed_path}`" if observed_path is not None else "- Observed catalog cache: unavailable",
                "",
            ]
        )
        if catalog_test_diagnostics is not None:
            lines.extend(
                [
                    "## Catalog-Test Diagnostics",
                    "",
                    f"- Observed events in zero ETAS spatial-rate cells: `{catalog_test_diagnostics.observed_events_in_zero_spatial_rate_cells}` across `{catalog_test_diagnostics.observed_nonzero_spatial_cells_with_zero_rate}` spatial cells",
                    f"- Observed events in zero ETAS space-magnitude bins: `{catalog_test_diagnostics.observed_events_in_zero_space_magnitude_bins}`",
                    f"- Zero-rate ETAS spatial cells in testing region: `{catalog_test_diagnostics.zero_spatial_rate_cells}` of `{catalog_test_diagnostics.total_spatial_cells}`",
                    "",
                ]
            )

    if evaluation_results:
        lines.extend(["## Evaluation Results", ""])
        for key, result in evaluation_results.items():
            if result is None:
                continue
            quantile = getattr(result, "quantile", None)
            observed_statistic = getattr(result, "observed_statistic", None)
            status = getattr(result, "status", "unknown")
            lines.append(
                f"- `{key}`: observed statistic `{format_scalar(observed_statistic)}`, quantile `{format_quantile(quantile)}`, status `{status}`"
            )
        lines.append("")

    if rolling_results:
        lines.extend(
            [
                "## Rolling Diagnostics",
                "",
                f"- Rolling number-test sub-windows: `{len(rolling_results)}`",
            ]
        )
        if calibration_result is not None:
            lines.append(
                f"- Rolling calibration KS statistic: `{calibration_result.observed_statistic}` with p-value `{calibration_result.quantile}`"
            )
        lines.append("")

    lines.extend(["## Generated Files", ""])
    lines.extend([f"- `{output_file}`" for output_file in sorted(output_files)])
    lines.append("")
    lines.extend(
        [
            "## Notes",
            "",
            "- The cumulative and histogram plots use GeoNet observations when available; otherwise they fall back to a representative simulation.",
            "- The rolling-window calibration test is a within-forecast diagnostic built from daily sub-window number tests inside the current ETAS horizon.",
        ]
    )
    if "paired_t_test_vs_uniform" in evaluation_results or "w_test_vs_uniform" in evaluation_results:
        lines.append("- The benchmark comparison uses a uniform-in-space forecast that preserves the ETAS expected magnitude totals.")
    if catalog_test_messages:
        lines.append("- pyCSEP emitted undersampling notices for the spatial/pseudolikelihood tests; these were captured and summarized here instead of relying on raw stdout.")
    if catalog_test_diagnostics is not None and catalog_test_diagnostics.observed_events_in_zero_spatial_rate_cells > 0:
        lines.append("- In pyCSEP, `status=undersampled` for the spatial and pseudolikelihood tests means observed events occurred in cells where the forecast had zero spatial support, so those events were removed before recomputing the score.")
    if catalog_test_diagnostics is not None and catalog_test_diagnostics.observed_events_in_zero_space_magnitude_bins > 0:
        lines.append("- The Poisson paired T/W comparison tests were skipped because pyCSEP comparison scores require positive target rates for all observed events, which is not true here.")
    lines.append("- The catalog number test uses the empirical distribution of synthetic catalog sizes; the catalog magnitude tests compare the observed magnitude histogram against the union of all synthetic catalogs scaled to the observed event count.")
    if any(
        isinstance(getattr(result, "observed_statistic", None), (float, np.floating))
        and math.isinf(float(getattr(result, "observed_statistic")))
        for result in evaluation_results.values()
        if result is not None
    ):
        lines.append(
            "- Infinite comparison-test statistics indicate observed events fell in ETAS cells with zero expected rate, which pyCSEP treats as a hard failure for that score."
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary = parse_summary(Path(args.summary))
    config = parse_config(Path(args.config))
    context = merge_metadata(summary, config)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir) if args.cache_dir else output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mainshock_cache_path, observed_cache_path = cache_paths(cache_dir, context)

    mainshock = resolve_mainshock(
        context=context,
        override_time=args.mainshock_time,
        fallback_time=args.reference_time,
        cache_path=mainshock_cache_path,
    )

    catalog_paths = sorted(Path(args.catalog_dir).glob("sim_*.txt"))
    if args.max_catalogs is not None:
        catalog_paths = catalog_paths[: args.max_catalogs]
    if not catalog_paths:
        raise FileNotFoundError(f"No ETAS simulated catalogs found in {args.catalog_dir}")

    catalog_arrays = [load_etas_catalog(path, context.mag_complete) for path in catalog_paths]
    max_mag = max(
        [context.mag_complete]
        + [float(np.max(arrays.magnitudes)) for arrays in catalog_arrays if arrays.magnitudes.size]
    )
    region = build_region(context, max_mag=max_mag)

    catalogs: list[CSEPCatalog] = []
    stats: list[CatalogBuildStats] = []
    for catalog_id, arrays in enumerate(catalog_arrays):
        catalog, catalog_stats = build_catalog(
            arrays=arrays,
            catalog_id=catalog_id,
            mainshock_time=mainshock.origin_time,
            region=region,
        )
        catalogs.append(catalog)
        stats.append(catalog_stats)

    forecast = CatalogForecast(
        catalogs=catalogs,
        start_time=mainshock.origin_time + timedelta(days=context.forecast_start),
        end_time=mainshock.origin_time + timedelta(days=context.forecast_end),
        region=region,
        n_cat=len(catalogs),
        name=f"NZ ETAS {context.event_id}".strip(),
    )
    representative = representative_catalog(catalogs)
    expected_rates = forecast.get_expected_rates(verbose=False)
    indirect_fraction_percent = compute_indirect_fraction_percent(catalog_arrays)

    observed_catalog = None
    try:
        observed_catalog = load_or_query_observed_catalog(
            context=context,
            mainshock=mainshock,
            region=region,
            observed_path=observed_cache_path,
            observed_override=args.observed_catalog,
            skip_observed=args.skip_observed,
        )
    except Exception as exc:
        if not args.skip_observed:
            print(f"Observed GeoNet catalog unavailable: {exc}")

    cumulative_path = output_dir / "nz_etas_pycsep_cumulative.png"
    histogram_path = output_dir / "nz_etas_pycsep_histogram.png"
    mag_time_path = output_dir / "nz_etas_pycsep_magnitude_time.png"
    rate_path = output_dir / "nz_etas_pycsep_expected_rates.png"
    observed_map_path = output_dir / "nz_etas_pycsep_observed_catalog.png"
    evaluation_path = output_dir / "nz_etas_pycsep_evaluation_distributions.png"
    comparison_path = output_dir / "nz_etas_pycsep_benchmark_comparison.png"
    skill_path = output_dir / "nz_etas_pycsep_skill_diagrams.png"
    residual_path = output_dir / "nz_etas_pycsep_spatial_residuals.png"
    generation_path = output_dir / "nz_etas_pycsep_generation_cumulative.png"
    max_mag_path = output_dir / "nz_etas_pycsep_max_magnitude_exceedance.png"
    rolling_consistency_path = output_dir / "nz_etas_pycsep_rolling_number_consistency.png"
    calibration_path = output_dir / "nz_etas_pycsep_rolling_calibration.png"
    summary_path = output_dir / "nz_etas_pycsep_summary.md"
    json_dir = output_dir / "evaluation_json"
    json_dir.mkdir(parents=True, exist_ok=True)
    comparison_json_paths = [
        json_dir / "paired_t_test_vs_uniform.json",
        json_dir / "w_test_vs_uniform.json",
    ]

    comparison_catalog = observed_catalog if observed_catalog is not None else representative
    comparison_label = comparison_catalog.name
    ax = plots.plot_cumulative_events_versus_time(
        forecast,
        comparison_catalog,
        time_axis="days",
        sim_label="ETAS ensemble",
        obs_label=comparison_label,
        show=False,
        title="pyCSEP cumulative counts for NZ ETAS ensemble",
    )
    save_axis(ax, cumulative_path)

    ax = plots.plot_magnitude_histogram(
        forecast,
        comparison_catalog,
        log_scale=False,
        normalize=False,
        show=False,
        title="pyCSEP magnitude histogram for NZ ETAS ensemble",
    )
    save_axis(ax, histogram_path)

    ax = plots.plot_magnitude_versus_time(
        representative,
        reset_times=True,
        show=False,
        title=f"pyCSEP magnitude-time view: {representative.name}",
    )
    save_axis(ax, mag_time_path)

    ax = expected_rates.plot(
        show=False,
        basemap=None,
        title="pyCSEP expected rates for NZ ETAS ensemble",
        figsize=(10, 8),
    )
    save_axis(ax, rate_path)

    plot_generation_resolved_cumulative(generation_path, catalog_arrays, context)
    plot_maximum_magnitude_exceedance(max_mag_path, catalog_arrays, context, mainshock, observed_catalog)

    evaluation_results: dict[str, object] = {}
    rolling_results = []
    calibration_result = None
    catalog_test_diagnostics = None
    catalog_test_messages: list[str] = []
    output_files = [
        cumulative_path,
        histogram_path,
        mag_time_path,
        rate_path,
        generation_path,
        max_mag_path,
        summary_path,
        mainshock_cache_path,
    ]

    if observed_catalog is not None:
        observed_catalog.region = region
        observed_catalog.name = observed_catalog_name(context)
        output_files.append(observed_cache_path)

        ax = plots.plot_catalog(
            observed_catalog,
            basemap=None,
            plot_region=True,
            title="GeoNet observed catalog in pyCSEP NZ testing region",
            show=False,
        )
        save_axis(ax, observed_map_path)
        output_files.append(observed_map_path)

        plot_spatial_residuals(residual_path, expected_rates, observed_catalog)
        output_files.append(residual_path)

        catalog_test_diagnostics = compute_catalog_test_diagnostics(expected_rates, observed_catalog)
        if catalog_test_diagnostics.observed_events_in_zero_spatial_rate_cells > 0:
            print(
                "Catalog-test diagnostic: "
                f"{catalog_test_diagnostics.observed_events_in_zero_spatial_rate_cells}/"
                f"{catalog_test_diagnostics.observed_event_count} observed events fall in zero ETAS spatial-rate cells."
            )
        if catalog_test_diagnostics.observed_events_in_zero_space_magnitude_bins > 0:
            print(
                "Catalog-test diagnostic: "
                f"{catalog_test_diagnostics.observed_events_in_zero_space_magnitude_bins}/"
                f"{catalog_test_diagnostics.observed_event_count} observed events fall in zero ETAS space-magnitude bins."
            )

        evaluation_results, catalog_test_messages = run_catalog_based_consistency_tests(
            forecast, observed_catalog
        )
        if catalog_test_messages:
            print(
                "pyCSEP catalog spatial tests marked the forecast as undersampled and recomputed the score after excluding unsupported observed events."
            )

        for key, result in evaluation_results.items():
            if result is not None:
                json_path = json_dir / f"{key}.json"
                write_json(result, str(json_path))
                output_files.append(json_path)

        distribution_results = [
            evaluation_results["catalog_number_test"],
            evaluation_results["catalog_magnitude_test"],
            evaluation_results["catalog_spatial_test"],
            evaluation_results["catalog_pseudolikelihood_test"],
            evaluation_results["catalog_resampled_magnitude_test"],
            evaluation_results["catalog_mll_magnitude_test"],
        ]
        distribution_titles = [
            "Number test",
            "Magnitude test",
            "Spatial test",
            "Pseudolikelihood test",
            "Resampled magnitude test",
            "MLL magnitude test",
        ]
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        for ax, title, result in zip(axes.flat, distribution_titles, distribution_results):
            if result is None:
                ax.axis("off")
                ax.set_title(f"{title} unavailable")
                continue
            plots.plot_test_distribution(result, ax=ax, show=False)
            ax.set_title(title)
        fig.suptitle("pyCSEP catalog-based evaluation distributions", y=1.02)
        fig.tight_layout()
        save_figure(fig, evaluation_path)
        output_files.append(evaluation_path)

        per_test_plot_specs = [
            ("catalog_number_test", output_dir / "nz_etas_pycsep_catalog_number_test.png", "Catalog N-Test"),
            ("catalog_magnitude_test", output_dir / "nz_etas_pycsep_catalog_magnitude_test.png", "Catalog M-Test"),
            ("catalog_spatial_test", output_dir / "nz_etas_pycsep_catalog_spatial_test.png", "Catalog S-Test"),
            ("catalog_pseudolikelihood_test", output_dir / "nz_etas_pycsep_catalog_pseudolikelihood_test.png", "Catalog PL-Test"),
            ("catalog_resampled_magnitude_test", output_dir / "nz_etas_pycsep_catalog_resampled_magnitude_test.png", "Catalog Resampled M-Test"),
            ("catalog_mll_magnitude_test", output_dir / "nz_etas_pycsep_catalog_mll_magnitude_test.png", "Catalog MLL M-Test"),
        ]
        for result_key, plot_path, title in per_test_plot_specs:
            result = evaluation_results.get(result_key)
            if result is None:
                continue
            ax = result.plot(show=False)
            ax.set_title(title)
            save_axis(ax, plot_path)
            output_files.append(plot_path)

        if catalog_test_diagnostics.observed_events_in_zero_space_magnitude_bins == 0:
            benchmark = build_uniform_benchmark(expected_rates)
            t_result = poisson_evaluations.paired_t_test(expected_rates, benchmark, observed_catalog)
            w_result = poisson_evaluations.w_test(expected_rates, benchmark, observed_catalog)
            evaluation_results["paired_t_test_vs_uniform"] = t_result
            evaluation_results["w_test_vs_uniform"] = w_result
            write_json(t_result, str(json_dir / "paired_t_test_vs_uniform.json"))
            write_json(w_result, str(json_dir / "w_test_vs_uniform.json"))
            output_files.extend([json_dir / "paired_t_test_vs_uniform.json", json_dir / "w_test_vs_uniform.json"])

            ax = plots.plot_comparison_test(
                results_t=t_result,
                results_w=w_result,
                show=False,
                title="ETAS vs uniform-space benchmark",
            )
            save_axis(ax, comparison_path)
            output_files.append(comparison_path)
        else:
            print(
                "Skipping pyCSEP paired T/W comparison tests because observed events fall in zero ETAS space-magnitude bins."
            )
            remove_if_exists(comparison_path)
            for stale_path in comparison_json_paths:
                remove_if_exists(stale_path)

        fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
        plots.plot_concentration_ROC_diagram(
            expected_rates,
            observed_catalog,
            ax=axes[0],
            show=False,
            title="Concentration ROC",
        )
        plots.plot_ROC_diagram(
            expected_rates,
            observed_catalog,
            ax=axes[1],
            show=False,
            title="ROC",
        )
        plots.plot_Molchan_diagram(
            expected_rates,
            observed_catalog,
            ax=axes[2],
            show=False,
            title="Molchan",
        )
        fig.tight_layout()
        save_figure(fig, skill_path)
        output_files.append(skill_path)

        rolling_results, calibration_result = run_rolling_number_tests(
            forecast=forecast,
            observed_catalog=observed_catalog,
            context=context,
            mainshock=mainshock,
            window_days=args.rolling_window_days,
        )
        if rolling_results:
            ax = plots.plot_consistency_test(
                rolling_results,
                plot_mean=True,
                show=False,
                title=f"Rolling number-test consistency ({args.rolling_window_days:g}-day windows)",
            )
            save_axis(ax, rolling_consistency_path)
            output_files.append(rolling_consistency_path)

        if calibration_result is not None:
            write_json(calibration_result, str(json_dir / "rolling_number_calibration.json"))
            output_files.append(json_dir / "rolling_number_calibration.json")
            ax = calibration_result.plot(show=False)
            ax.set_title("Rolling number-test calibration")
            save_axis(ax, calibration_path)
            output_files.append(calibration_path)

    write_summary(
        path=summary_path,
        context=context,
        mainshock=mainshock,
        forecast=forecast,
        representative=representative,
        stats=stats,
        observed_catalog=observed_catalog,
        observed_path=observed_cache_path if observed_catalog is not None else None,
        catalog_test_diagnostics=catalog_test_diagnostics,
        catalog_test_messages=catalog_test_messages,
        evaluation_results=evaluation_results,
        rolling_results=rolling_results,
        calibration_result=calibration_result,
        output_files=output_files,
        indirect_fraction_percent=indirect_fraction_percent,
    )

    unique_output_files = list(dict.fromkeys(output_files))
    print(f"Using pyCSEP {getattr(csep, '__version__', 'unknown')} from {csep.__file__}")
    print(f"Wrote {summary_path}")
    for output_file in unique_output_files:
        if output_file == summary_path:
            continue
        print(f"Wrote {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
