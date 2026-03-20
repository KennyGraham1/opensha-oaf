# Operational Aftershock Forecasting (OAF) Server Code and Desktop Applications.

> **Fork Information**: This repository is a fork of [USGS/opensha-oaf](https://code.usgs.gov/esc/oaf/opensha-oaf).

## Key Changes & Enhancements

This fork introduces significant improvements to the ETAS modeling capabilities and developer experience:

*   **Configurable ETAS Runner**:
    *   Replaced hardcoded parameters with a flexible JSON-based configuration system (`ETASConfig`).
    *   Simulations can now be driven by `etas_config.json`, allowing control over duration, number of simulations, and magnitude thresholds without recompiling.
*   **Spatial Rate Maps**:
    *   Added 2D spatial forecasting via `ETAS_RateModel2D`, producing grid-based rate maps of expected aftershock locations.
    *   Outputs both CSV (lat/lon/rate) and KML (contour map for Google Earth) formats.
    *   Controlled via the `spatial` block in `etas_config.json`. Disabled by default.
*   **Reproducibility**:
    *   Added support for random seeds in simulations, ensuring that results can be strictly reproduced for debugging and verification.
*   **Simulated Catalogs**:
    *   Integrated new simulated catalog examples, including specific scenarios for New Zealand (NZ).
*   **Codebase Cleanliness**:
    *   Removed accidental binary commits (class files) to reduce repository bloat.

## Setup

This software depends on the [upstream OpenSHA](https://github.com/opensha/opensha) project. Both repositories must live in the **same parent directory**:

```bash
mkdir ~/opensha && cd ~/opensha
git clone https://github.com/opensha/opensha
git clone https://github.com/KennyGraham1/opensha-oaf
cd opensha-oaf
```

**Requirements**: Java 11 or higher. Gradle is included via the wrapper — no separate install needed.

## Running the NZ Demo

For full configuration details, output interpretation, and the spatial forecasting extension, see [docs/README_NZ.md](docs/README_NZ.md).

### 1. Create `etas_config.json`

Place this file in the project root (edit the `eventId` and windows to suit your event):

```json
{
    "eventId": "2016p858000",
    "dataSource": "geonet",
    "dataWindow":     { "minDays": 0, "maxDays": 7  },
    "forecastWindow": { "minDays": 7, "maxDays": 14 },
    "region": { "radiusKm": 200, "minDepth": -10, "maxDepth": 100 },
    "catalog": { "magComplete": 3.0, "forecastMagnitudes": [3.0, 4.0, 5.0] },
    "simulation": { "nSims": 100, "seed": 12345 },
    "output": { "summaryFile": "nz_etas_simulations.txt", "catalogDir": "simulated_catalogs" }
}
```

### 2. Run the demo

```bash
./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ --args="--config etas_config.json"
```

Or with positional arguments (event ID, data end day, forecast end day):

```bash
./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ --args="2016p858000 7 14"
```

### 3. Check the output

| File | Contents |
| :--- | :--- |
| `nz_etas_simulations.txt` | Fitted parameters and forecast table |
| `simulated_catalogs/sim_NNNN.txt` | One synthetic catalog per simulation |

The first run will download Gradle dependencies and compile — subsequent runs are faster.

## About the Original USGS Project

The upstream project was developed by:
- Michael Barall, USGS Earthquake Science Center, Moffett Field, CA.
- Nicholas van der Elst, USGS Earthquake Science Center, Pasadena, CA.
- Kevin Milner, USGS Geologic Hazards Science Center, Pasadena, CA.

The original OAF server runs continuously in the cloud, monitoring the USGS ComCat earthquake catalog and automatically generating aftershock forecasts. This fork focuses on the configurable ETAS forecasting capabilities for research and analysis.


## Citations

For the OAF server and analyst utilities:

Barall, M., and van der Elst, N. (2025), Operational Aftershock Forecasting,
USGS Software Release, [https://doi.org/10.5066/P1FJSYVJ](https://doi.org/10.5066/P1FJSYVJ).

For Aftershock Forecaster:

van der Elst, N., Barall, M., and Milner, K. (2025), Aftershock Forecaster,
USGS Software Release, [https://doi.org/10.5066/P1LG6ZQS](https://doi.org/10.5066/P1LG6ZQS).

