# New Zealand ETAS Forecast Demo Documentation

This document provides a comprehensive guide to the **New Zealand ETAS (Epidemic Type Aftershock Sequence)** demonstration within the `opensha-oaf` project. It details the system architecture, mathematical model, configuration options, and usage instructions for forecasting aftershocks using GeoNet data.

---

## 1. Overview

The `ETAS_Demo_NZ.java` application allows researchers and analysts to retrieve real-time earthquake data from New Zealand's **GeoNet** agency and generate probabilistic aftershock forecasts using a sequence-specific ETAS model.

### Key Features
*   **Automated Data Retrieval**: Directly queries GeoNet's FDSN web services for the mainshock and associated aftershocks.
*   **Custom Parsing**: Handles GeoNet-specific QuakeML formats via `ETAS_GeoNetAccessor`.
*   **Sequence-Specific Fitting**: Estimates ETAS parameters ($a, p, c$) tailored specifically to the fetched sequence using Constant-Likelihood grid search.
*   **Stochastic Forecasting**: Generates thousands of synthetic future catalogs (Monte Carlo simulation) to estimate aftershock probabilities.
*   **Detailed Output**: Exports both summary statistics and individual stochastic catalogs for further analysis.

---

## 2. Technical Architecture

### A. Data Source
*   **Provider**: GeoNet (New Zealand)
*   **Protocol**: FDSN Event Web Service (`https://service.geonet.org.nz/fdsnws/event/1/`)
*   **Format**: QuakeML (XML)
*   **Filtering**:
    *   **Spatial**: Events within a defined radius (default: 1.8°) of the mainshock.
    *   **Temporal**: Events occurring between the mainshock time and the current "now" (or simulation end time).
    *   **Depth**: Shallow crustal events (Depth < 100km).

### B. The ETAS Model
The model usually implemented is a **0-Dimensional (Temporal-Magnitude)** ETAS model.

$$ \lambda(t) = \mu + \sum_{i:t_i<t} K \cdot 10^{\alpha(M_i-M_c)} \cdot (t-t_i+c)^{-p} $$

Where:
*   $\lambda(t)$: The instantaneous rate of earthquakes at time $t$.
*   $a$ (Productivity): Log-productivity of the sequence ($K = 10^a$). High values mean more aftershocks.
*   $p$ (Decay): The rate at which aftershock activity dies off (Omori's Law). Typically $\approx 1.0$.
*   $c$ (Offset): A small time constant to avoid singularity at $t=0$. Typically $\approx 0.01$ days.
*   $b$ (Magnitude): The Gutenberg-Richter slope (fixed at 1.0).
*   $\alpha$ (Triggering): Assessing how much more productive larger quakes are (fixed at 1.0).

### C. Fitting Process
1.  **Selection**: Selects all events with Magnitude $\ge M_c$ (Completeness Magnitude).
2.  **Estimation**: Uses **Maximum Likelihood Estimation (MLE)** to find the combination of ($a, p, c$) that best explains the observed timing of events.
3.  **Priors**: Uses Bayesian priors derived from **Active Shallow Crust (ANSR)** tectonic regions to constrain the fit.

---

## 3. Usage Guide

### Prerequisites
*   **Java**: Version 11 or higher.
*   **Gradle**: Included via the wrapper (`./gradlew`) — no separate install needed.
*   **Network**: Unrestricted HTTPS access to `service.geonet.org.nz`.

---

### Step 1 — Clone the repositories

The project depends on the upstream OpenSHA library. Both repositories must be cloned into the **same parent directory**.

```bash
mkdir ~/opensha && cd ~/opensha
git clone https://github.com/opensha/opensha
git clone https://github.com/KennyGraham1/opensha-oaf
cd opensha-oaf
```

Then create the required symlink so Gradle can find the OpenSHA source:

```bash
ln -s ../opensha opensha_local
```

---

### Step 2 — Compile

Gradle manages compilation. The wrapper (`./gradlew`) is included — no separate Gradle install needed.

**Option A — compile and run in one step** (development workflow):

```bash
./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ --args="--config etas_config.json"
```

Gradle will compile everything automatically before running.

**Option B — build a standalone fat jar** (recommended for repeated use):

```bash
./gradlew appNZDemoJar
```

This produces `build/libs/ETAS_Demo_NZ.jar` — a self-contained jar with all dependencies bundled. After this, you can run with plain `java` and never need Gradle again unless the code changes.

> **When to recompile**: only after editing `.java` source files. Config changes (`etas_config.json`) take effect immediately without recompiling.

---

### Step 3 — Create your config file

Copy the example below into a file named `etas_config.json` in the project root. This runs a hindcast for the 2016 M7.8 Kaikōura earthquake, training on the first 7 days of aftershocks and forecasting days 7–14.

```json
{
    "eventId": "2016p858000",
    "dataSource": "geonet",
    "dataWindow":     { "minDays": 0, "maxDays": 7  },
    "forecastWindow": { "minDays": 7, "maxDays": 14 },
    "region": {
        "radiusKm": 200,
        "minDepth": -10,
        "maxDepth": 100
    },
    "catalog": {
        "magComplete": 3.0,
        "forecastMagnitudes": [3.0, 4.0, 5.0]
    },
    "priors": {
        "aMean": -2.423, "aSigma": 0.395,
        "pMean": 1.08,   "pSigma": 0.2,
        "cMean": 0.01,   "logcSigma": 0.7,
        "alpha": 1.0, "b": 1.0, "refMag": 4.5
    },
    "gridSearch": {
        "amsMin": -4.0, "amsMax": 1.0, "amsN": 21,
        "aMin": -3.5,   "aMax": -0.5,  "aN": 21,
        "pMin": 0.5,    "pMax": 2.0,   "pN": 16,
        "cMin": 1e-4,   "cMax": 1e-1,  "cN": 16
    },
    "simulation": {
        "nSims": 100,
        "maxGenerations": 10,
        "maxMag": 9.5,
        "timeDependentMc": false,
        "fitMSProductivity": true,
        "seed": 12345
    },
    "output": {
        "summaryFile": "nz_etas_simulations.txt",
        "catalogDir":  "simulated_catalogs"
    }
}
```

> To also generate a spatial rate map, add a `"spatial"` block — see [Section 5](#5-spatial-forecasting).

---

### Step 4 — Run the demo

**Option A — via Gradle** (compiles and runs in one step):

```bash
./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ --args="--config etas_config.json"
```

The first run will download Gradle dependencies and compile the project. Subsequent runs are faster.

**Option B — via pre-built fat jar** (recommended for repeated use — no Gradle overhead after initial build):

```bash
# Build once (only needed after code changes)
./gradlew appNZDemoJar

# Run using the convenience script
./run_nz_demo.sh                         # picks up etas_config.json automatically
./run_nz_demo.sh path/to/config.json     # custom config path

# Or directly with java
java -jar build/libs/ETAS_Demo_NZ.jar --config etas_config.json
```

You can also pass **positional arguments** (event ID, data end day, forecast end day) with either approach:

```bash
./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ --args="2016p858000 7 14"
# or
./run_nz_demo.sh 2016p858000 7 14
```

This uses hardcoded defaults for everything except the three arguments — less flexible, but useful for quick checks.

---

### Step 5 — Check the console output

A successful run produces output like the following:

```
ETAS Demo (NZ): Config-Driven Runner
Loading config from: etas_config.json

--- Configuration ---
Event ID: 2016p858000
Data Window: Day 0.0 to Day 7.0
Forecast Window: Day 7.0 to Day 14.0
Mag Complete: 3.0
Simulations: 100
Random Seed: 12345

Fetching mainshock metadata for 2016p858000...
Mainshock: M7.8 at Mon Nov 14 00:02:56 NZDT 2016
Location: [Latitude=-42.6932, Longitude=172.9994, Depth=15.0]

Fetching aftershocks for data window...
Fetched 312 aftershocks.
Aftershocks >= Mc(3.0): 289

Computing sequence-specific ETAS model...

--- ETAS Results ---
ams-value (Mainshock Productivity): -1.2341
a-value (Aftershock Productivity): -2.1053
p-value: 1.0800
c-value: 0.0100
b-value: 1.0000

Forecast (Days 7.0-14.0):
M>=3.0: 47.2311
M>=4.0: 4.7231
M>=5.0: 0.4723

Probability of >=1 event:
M>=3.0: 100.0000%
M>=4.0: 99.1200%
M>=5.0: 37.8900%

--- Observed Aftershocks ---
Observed M>=3.0: 53
Observed M>=4.0: 6
Observed M>=5.0: 1

Summary saved to: /path/to/opensha-oaf/nz_etas_simulations.txt
Writing 100 simulation files...
Done.
```

> Exact numbers will vary depending on the aftershocks returned by GeoNet at the time of the query. If a `seed` is set, the stochastic simulation output is reproducible — but the observed aftershock count and fitted parameters depend on live data.

---

### Step 6 — Inspect the output files

| File | What it contains |
| :--- | :--- |
| `nz_etas_simulations.txt` | Summary: fitted parameters, expected counts, percentile uncertainty table |
| `simulated_catalogs/sim_0001.txt` … `sim_NNNN.txt` | One file per Monte Carlo simulation |
| `spatial_rate_map.csv` | Grid of expected aftershock rates — only written when `spatial.enabled: true` |
| `spatial_rate_map.kml` | Contour map for Google Earth — only written when `spatial.enabled: true` |

**Simulated catalog format (spatial disabled):**

```text
# Simulation 1
# RelativeTime(days) Magnitude Generation
Time Mag Gen
7.123    4.5    1
8.441    3.2    2
9.870    3.1    3
```

**Simulated catalog format (spatial enabled):**

```text
# Simulation 1
# RelativeTime(days) Magnitude Generation Latitude Longitude
Time Mag Gen Lat Lon
7.129    5.91    1    -42.0265    173.6600
7.748    4.85    2    -41.9469    173.6572
10.097   6.04    1    -41.7435    174.1773
```

`Generation` indicates how many steps removed from the mainshock: `1` = direct aftershock, `2` = aftershock of an aftershock, etc. Each event's lat/lon is sampled from the spatial kernel centred on its **parent event**, so spatial clustering propagates through the aftershock tree.

### Step 7 — Render an ensemble diagnostic dashboard

For a compact, research-grade view of the forecast ensemble, render the simulated catalogs into a single statistical dashboard:

```bash
python3 scripts/python/visualize_nz_etas_output.py
```

By default this reads:

* `nz_etas_simulations.txt`
* `simulated_catalogs/sim_*.txt`
* `spatial_rate_map.csv` (when present)

and writes:

* `build/nz_visualization/nz_etas_dashboard.png`
* `build/nz_visualization/nz_etas_dashboard.pdf`
* `build/nz_visualization/nz_etas_dashboard_summary.md`

The dashboard is designed to answer the questions a statistical seismologist usually asks first:

* How quickly does the ensemble rate decay through the forecast window?
* What is the empirical 5th/50th/95th count range for each magnitude threshold?
* How often does the ensemble produce an event at or above a given magnitude?
* How much of the forecast is direct triggering versus higher-generation cascade growth?
* Where do the deterministic rate field and realized Monte Carlo event density agree spatially?

It uses the **simulated catalogs themselves** as the primary source for uncertainty bands and exceedance curves. That is generally more informative than a single expected-count column because ETAS branching produces strongly overdispersed count distributions.

### Step 8 — Use pyCSEP on the ETAS ensemble

If you want to inspect the same ETAS catalogs with the `pyCSEP` toolkit, clone and install it from source:

```bash
git clone https://github.com/SCECcode/pycsep.git vendor/pycsep
python3 -m pip install --user -e vendor/pycsep
```

Run a quick package smoke test:

```bash
MPLCONFIGDIR=/tmp/matplotlib python3 -m pytest -q vendor/pycsep/tests/test_catalog.py
```

Then render pyCSEP-based plots from the NZ ETAS output:

```bash
python3 scripts/python/visualize_nz_etas_with_pycsep.py
```

By default the script:

* resolves the mainshock origin time from the GeoNet FDSN event service and caches it
* downloads the matching GeoNet observed catalog for the ETAS forecast window and `Mc`
* converts the ETAS `sim_*.txt` files into `CSEPCatalog` objects and builds a `CatalogForecast`
* runs pyCSEP catalog-based tests plus ETAS-specific diagnostics

This writes:

* `build/pycsep/nz_etas_pycsep_cumulative.png`
* `build/pycsep/nz_etas_pycsep_histogram.png`
* `build/pycsep/nz_etas_pycsep_magnitude_time.png`
* `build/pycsep/nz_etas_pycsep_expected_rates.png`
* `build/pycsep/nz_etas_pycsep_observed_catalog.png`
* `build/pycsep/nz_etas_pycsep_spatial_residuals.png`
* `build/pycsep/nz_etas_pycsep_skill_diagrams.png`
* `build/pycsep/nz_etas_pycsep_evaluation_distributions.png`
* `build/pycsep/nz_etas_pycsep_benchmark_comparison.png`
* `build/pycsep/nz_etas_pycsep_generation_cumulative.png`
* `build/pycsep/nz_etas_pycsep_max_magnitude_exceedance.png`
* `build/pycsep/nz_etas_pycsep_rolling_number_consistency.png`
* `build/pycsep/nz_etas_pycsep_rolling_calibration.png`
* `build/pycsep/evaluation_json/*.json`
* `build/pycsep/nz_etas_pycsep_summary.md`

The observation-backed workflow now runs:

* catalog `number`, `magnitude`, `spatial`, `pseudolikelihood`, resampled-magnitude, and MLL-magnitude tests
* ETAS versus a uniform-space benchmark with pyCSEP comparison plots when all observed events fall inside non-zero ETAS support
* concentration ROC, ROC, and Molchan diagrams
* spatial residual maps, generation-resolved cumulative curves, maximum-magnitude exceedance curves, and rolling-window number-test diagnostics

When GeoNet observations are available, the cumulative and histogram plots use the **observed GeoNet catalog** as the comparison catalog. If you want forecast-only diagnostics or you are offline, use:

```bash
python3 scripts/python/visualize_nz_etas_with_pycsep.py \
  --skip-observed \
  --reference-time 2016-11-13T11:02:56+00:00
```

---

## 4. Configuration (`etas_config.json`)

You can edit `etas_config.json` to customize the run. Key sections include:

### Simulation vs. Reporting Parameters
A common confusion is the difference between `maxMag` and `forecastMagnitudes`.

| Parameter | Section | Description |
| :--- | :--- | :--- |
| **`maxMag`** | `"simulation"` | **Physics Limit.** This is the maximum magnitude the updated model *can* generate during its stochastic simulations. It acts as a physical upper bound (e.g., set to 9.5 to allow for M9+ events, but prevent infinite energy). |
| **`forecastMagnitudes`** | `"catalog"` | **Reporting Filter.** This controls what you *see* in the output text. It does not affect the simulation itself, only the summary statistics. |

**In short:**
*   `maxMag` = **Physics limit** (what the model *can* produce)
*   `forecastMagnitudes` = **Reporting filter** (what you *want to see* in the output)

**Example:**
If you set:
```json
"simulation": { "maxMag": 9.5 },
"catalog": { "forecastMagnitudes": [4.0, 5.0] }
```
The model will simulate all events up to M9.5, but the console output and summary file will only calculate and show the rates/probabilities for **M≥4.0** and **M≥5.0**. (No M≥3.0 or M≥6.0 rows, even though those events exist in the simulation.)

### Other Key Settings
*   **`eventId`**: The GeoNet Event ID (e.g., `2016p858000`).
*   **`dataWindow`**: The period used to *train* the model (e.g., Days 0 to 7).
*   **`forecastWindow`**: The period you want to *predict* (e.g., Days 7 to 14).
*   **`priors`**: The initial "Generic" parameters used to stabilize the fit before data takes over.

### How Uncertainty is Calculated
The output file includes **5th, Median (50th), and 95th percentiles** for event counts. Here's how they're derived:

1.  **Monte Carlo Simulation**: The model generates `nSims` (default: 1000) stochastic "future catalogs". Each represents a possible outcome given the fitted ETAS parameters.
2.  **Counting**: For each magnitude threshold (e.g., M≥4.0), the code counts how many events occurred in the forecast window across all simulations.
3.  **Fractiles**: The built-in `getFractileNumEvents()` method sorts these counts and extracts percentiles.

**Interpretation:**
*   **5th percentile**: Lower bound (90% of simulations had *more* events than this).
*   **Median**: Typical outcome.
*   **95th percentile**: Upper bound (only 5% of simulations had *more* events than this).

This captures **aleatory uncertainty** (inherent randomness in earthquake triggering), not epistemic uncertainty (parameter fitting errors).

### Reproducibility with Random Seed
By default, each run produces **different** stochastic catalogs due to Monte Carlo randomness. To get **reproducible** results (e.g., for controlled experiments comparing different parameters), set a seed in the config:

```json
"simulation": {
    "nSims": 1000,
    "seed": 12345
}
```

**Behavior:**
*   **Same seed** → Identical catalogs every run
*   **Remove `seed`** or set to `null` → Random results each run

This allows you to isolate the effect of parameter changes (e.g., compare `p=1.0` vs `p=1.1`) while keeping the stochastic component fixed.

---

## 5. Spatial Forecasting

In addition to the temporal count forecasts, enabling `spatial` does two things:

1. **2D rate map** — a deterministic grid of expected aftershock rates (`spatial_rate_map.csv` / `.kml`)
2. **Per-event locations** — each synthetic event in the Monte Carlo catalogs is assigned a lat/lon by sampling from the spatial kernel, adding `Latitude` and `Longitude` columns to every `sim_NNNN.txt` file

Both are controlled by the `spatial` block in `etas_config.json` and are disabled by default.

### How It Works

The spatial kernel distributes the total expected aftershock count across a grid of geographic points. Each source event (mainshock and observed aftershocks) contributes a spatially decaying rate at every grid point using:

$$S(r) \propto \frac{H}{(d^2 + r^2) \cdot \sqrt{H^2/4 + r^2 + d^2}}$$

Where:
- $r$ = horizontal distance from source to grid point (km)
- $d$ = source radius, scaled by magnitude and stress drop
- $H$ = seismogenic depth (10 km)

The mainshock is treated as a **finite fault source** (a line of points along the rupture), while aftershocks are treated as **point sources**. The final map is normalized so its total integrates to the median event count from the temporal model — keeping both forecasts internally consistent.

### Enabling Spatial Output

Add the following block to your `etas_config.json`:

```json
"spatial": {
    "enabled": true,
    "spacing": 0.05,
    "scale": 5.0,
    "stressDrop": 3.0,
    "fitType": "aftershocks",
    "plotDuration": 7.0,
    "outputCsvFile": "spatial_rate_map.csv",
    "outputKmlFile": "spatial_rate_map.kml"
}
```

### Configuration Parameters

| Parameter | Description | Default |
| :--- | :--- | :--- |
| `enabled` | Turn spatial output on or off | `false` |
| `spacing` | Grid resolution in degrees (smaller = finer grid, slower) | `0.05` |
| `scale` | Map extent as a multiple of the rupture radius | `5.0` |
| `stressDrop` | Stress drop in MPa — controls source radius ($d$). Higher = smaller, more compact source | `3.0` |
| `fitType` | How to model the mainshock geometry. See options below. | `"aftershocks"` |
| `plotDuration` | Length of the spatial forecast window in days | `7.0` |
| `outputCsvFile` | Path for the CSV rate grid output | `"spatial_rate_map.csv"` |
| `outputKmlFile` | Path for the KML contour map output | `"spatial_rate_map.kml"` |

### Mainshock Geometry (`fitType`)

The mainshock rupture geometry significantly affects the spatial pattern, especially for large events. Three options are available:

| `fitType` | Description |
| :--- | :--- |
| `"aftershocks"` | Fits a line source to the early aftershock cloud to infer the rupture orientation. Recommended when enough early aftershocks are available (≥3). |
| `"shakemap"` | Uses a fault trace from ShakeMap source geometry. Requires passing a `FaultTrace` programmatically (not yet exposed in config). |
| `"point"` | Falls back to a point source centered on the mainshock hypocenter. Use when the sequence is too sparse to constrain geometry. |

For the Kaikōura 2016 sequence, `"aftershocks"` works well as the sequence is dense and the rupture orientation is well-constrained.

### Output Files

**`spatial_rate_map.csv`**

A flat table of the rate grid, one row per grid cell:

```
# Header
lat, lon, rate
-42.05, 173.95, 0.0431
-42.05, 174.00, 0.0612
...
```

Each `rate` value is the expected number of $M \ge M_c$ events in that grid cell during the forecast window.

**`spatial_rate_map.kml`**

A contour map of the rate grid that can be opened directly in **Google Earth** or any KML viewer. Contours are coloured blue (low rate) through red (high rate) with labeled isolines.

### Interpreting the Map

- **High-rate areas** (red/orange contours) indicate zones where aftershock activity is most likely concentrated — typically near the mainshock rupture and major aftershock clusters.
- **The total volume under the map** integrates to the median forecast count from the temporal model. The map does not change the *how many* answer — it answers *where*.
- Grid cells far from any source will approach zero rate, so the map naturally focuses on the active zone.

### Performance Note

Spatial computation scales as `O(N_sources × N_grid_cells)`. For a dense sequence and fine grid:
- `spacing=0.05°` over a 200 km × 200 km area ≈ 1600 grid cells
- With 100 aftershocks as sources → ~160,000 kernel evaluations

This typically runs in a few seconds to a minute. If it is too slow, increase `spacing` (e.g., `0.1`) or reduce `scale`.

---

## 6. Troubleshooting

### "Read timed out" or Connection Errors
*   **Cause**: GeoNet API might be slow or blocking requests.
*   **Fix**: Check your internet connection. Retry the script. If persistent, the `timeout` settings in `ETAS_GeoNetAccessor.java` may need increasing.

### "Zero events found"
*   **Cause**: Incorrect `EVENT_ID` or search radius.
*   **Fix**: Verify the Event ID on the GeoNet website. Ensure `magComplete` isn't set higher than the mainshock.

### Forecast is too high/low
*   **High Forecast**: Often due to setting `magComplete` too low (fitting on incomplete data) or an unusually productive sequence (high $a$-value).
*   **Low Forecast**: Check if the date range covers the actual activity. The Kaikōura sequence was complex; verify if `p-value` fitting is stable (~1.0).

---

## 7. License & Credits
*   **Engine**: OpenSHA (USGS)
*   **Data**: GeoNet / GNS Science (CC BY 3.0 NZ)
*   **Implementation**: Adapted for NZ usage by the opensha-oaf team.
