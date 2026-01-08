# Operational Aftershock Forecasting (OAF) Server Code and Desktop Applications.

> **Fork Information**: This repository is a fork of [USGS/opensha-oaf](https://code.usgs.gov/esc/oaf/opensha-oaf).

## Key Changes & Enhancements

This fork introduces significant improvements to the ETAS modeling capabilities and developer experience:

*   **Configurable ETAS Runner**:
    *   Replaced hardcoded parameters with a flexible JSON-based configuration system (`ETASConfig`).
    *   Simulations can now be driven by `etas_config.json`, allowing control over duration, number of simulations, and magnitude thresholds without recompiling.
*   **Reproducibility**:
    *   Added support for random seeds in simulations, ensuring that results can be strictly reproduced for debugging and verification.
*   **Simulated Catalogs**:
    *   Integrated new simulated catalog examples, including specific scenarios for New Zealand (NZ).
*   **Codebase Cleanliness**:
    *   Removed accidental binary commits (class files) to reduce repository bloat.

## Running the NZ Example

For a complete guide on running the New Zealand ETAS demonstration, including configuration details and output interpretation, please refer to [docs/README_NZ.md](docs/README_NZ.md).

Quick start command:

```bash
./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ --args="--config etas_config.json"
```

## Setup

This software depends on the [upstream OpenSHA](https://github.com/opensha/opensha) project which should be cloned into the same directory:

```bash
cd ~/opensha    # or whatever directory you choose
git clone https://github.com/opensha/opensha
git clone https://github.com/KennyGraham1/opensha-oaf
```

**Requirements**: Java version 11 or higher.

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

