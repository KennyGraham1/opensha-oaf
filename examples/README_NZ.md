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
*   **Network**: Unrestricted HTTPS access to `service.geonet.org.nz`.

### Running the Demo
Navigate to the project root and execute:

```bash
./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ
```

### Output Files
The script generates results in the project root directory:

1.  **`nz_etas_simulations.txt`**: A summary report containing:
    *   **Analysis Metadata**: Date, $M_c$, Number of simulations.
    *   **Fitted Parameters**: The calculated $a, p, c$ values.
    *   **Forecast Table**: Expected counts for probabilities of $M \ge 3.0, 4.0, 5.0$.

2.  **`simulated_catalogs/`**: A directory containing 100 separate text files (e.g., `sim_0001.txt`).
    *   These represent 100 possible "future timelines".
    *   **Format**:
        ```text
        # RelativeTime(days)  Magnitude  Generation
        7.123                 4.5        1
        8.441                 3.2        2
        ```
    *   **Generation**: `1` = direct aftershock of mainshock, `2` = aftershock of an aftershock, etc.

---

## 4. Configuration

To modify the analysis, you must edit `src/main/java/org/opensha/oaf/etas/examples/ETAS_Demo_NZ.java`. Key variables include:

### Event Selection
*   **`EVENT_ID`** (Line ~20): The GeoNet Public ID of the mainshock (e.g., `2016p858000` for Kaikōura).
    *   *Find IDs at [quakesearch.geonet.org.nz](https://quakesearch.geonet.org.nz/)*.

### Model Parameters
*   **`magComplete`** (Line ~80): The magnitude below which the catalog is considered incomplete.
    *   *Default*: `3.0` (Conservative for NZ).
    *   *Effect*: Lowering this (e.g., to 2.5) adds more recommended data but risks bias if the network missed small events.
*   **`forecastMinDays`** / **`forecastMaxDays`** (Line ~40): The start and end time (in days relative to mainshock) for the forecast.
    *   *Example*: `7.0` to `14.0` forecasts the second week.

### Simulation Settings
*   **`nSims`** (Line ~45): Number of stochastic simulations to run.
    *   *Default*: `100`. Increase to `1000+` for publication-quality statistics.

---

## 5. Troubleshooting

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

## 6. License & Credits
*   **Engine**: OpenSHA (USGS)
*   **Data**: GeoNet / GNS Science (CC BY 3.0 NZ)
*   **Implementation**: Adapted for NZ usage by the opensha-oaf team.
