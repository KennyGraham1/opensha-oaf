# Codebase Analysis & Stripping Strategy Report

**Date:** 2026-01-08
**Project:** opensha-oaf (Operational Aftershock Forecasting)
**Objective:** Create a stripped-down, self-contained codebase for ETAS and GR workflows.

## 1. Codebase Structure Analysis

The project acts as a thin layer of specialized OAF code on top of a massive seismic hazard library (OpenSHA).

### Core Components
| Component | Location | Status |
|-----------|----------|--------|
| **ETAS Engine** | `src/main/java/org/opensha/oaf/etas` | **Primary Target**. Contains logic for ETAS models, stochastic simulation, and forecasting. |
| **Common Utils** | `src/main/java/org/opensha/oaf/util` | **Required**. Specialized geospatial tools (SphRegion) and array utilities. |
| **RJ Model** | `src/main/java/org/opensha/oaf/rj` | **Optional**. Reasenberg-Jones model logic. Can be excluded if only ETAS is needed. |
| **Server/GUI** | `src/main/java/org/opensha/oaf/{aafs,gui,oetas}` | **Exclude**. Legacy GUI and heavy server infrastructure code not needed for modern deployment. |

### Dependency Analysis (The "Iceberg" Problem)
The ETAS engine is tightly coupled to the upstream OpenSHA library (`opensha_local`), which accounts for ~90% of the code volume.

*   **Direct Dependencies:**
    *   `ObsEqkRupture`: The core event object.
    *   `Location`: Geospatial logic.
    *   `DiscretizedFunc`: Mathematical functions for hazard curves.
    *   `EqkRupture`: Parent class for seismic events.
    *   `TectonicRegime`: Metadata for seismic regions.

*   **Implication:** You cannot simply "copy-paste" the `etas` folder. It essentially requires the entire OpenSHA `commons` and `sha` packages to compile.

## 2. Strategies for "Stripping Down"

We identified three distinct approaches to achieving the objective, ranging from "Quick & Robust" to "Lean & Risky".

### Approach A: The "Fat JAR" (Recommended for Stability)
Use the existing Gradle build system to compile a single executable JAR that includes *only* the classes actually used at runtime.
*   **Mechanism:** The `shadowJar` or custom `FatJar` task traverses the dependency tree and includes only referenced compiled bytecode.
*   **Pros:**
    *   Zero code changes required.
    *   Guaranteed to match the production logic exactly.
    *   Time to deliver: < 2 hours.
*   **Cons:**
    *   Resulting JAR is ~50-100MB (includes unused but referenced transitive dependencies).

### Approach B: Source-Level Extraction (Recommended for Minimalism)
Create a new `opensha-lite` repository and manually copy *only* the required source files, modifying them to remove unused imports.
*   **Mechanism:** recursively find dependencies and copy `.java` files, creating dummy stubs for complex classes that are only lightly used.
*   **Pros:**
    *   Smallest possible codebase (maybe <5MB source).
    *   Total understanding of every line of code.
*   **Cons:**
    *   Extremely labor-intensive (days of work).
    *   High risk of introducing subtle bugs by breaking hidden dependencies.
    *   Maintenance nightmare (hard to pull updates from upstream).

### Approach C: Containerized Production Wrapper (Best for Modern Ops)
Keep the "Fat JAR" but wrap it in a lightweight Docker container with a simplified API.
*   **Mechanism:**
    1.  Build the JAR.
    2.  Create a Docker image (Distroless or Alpine Java).
    3.  Expose the functionality via a simple CLI or REST wrapper.
*   **Pros:**
    *   "Self-contained" from an infrastructure perspective (just run the container).
    *   Clean separation of concerns.
*   **Cons:**
    *   Requires Docker runtime.

## 3. Recommendation

**Adopt Approach C (Hybrid)**.

1.  **Do not** attempt to manually slice the `opensha_local` source code. The ROI is negative due to complexity.
2.  Instead, create a **Targeted Build Task** `appETASRunner` that produces a specialized JAR.
3.  Deploy this JAR with a clear **Configuration Interface** (JSON config) and **Docker** wrapper.

This satisfies the requirement of being "self-contained" and "ready for production" without incurring the technical debt of a forked partial codebase.

## 4. Next Steps Implementation Checklist

1. [ ] **Build Optimization**: Add `appETASRunner` task to `build.gradle` to produce the specialized artifact.
2. [ ] **Runner Implementation**: Create `ETASRunner_Headless.java` to execute forecasts without any GUI dependencies.
3. [ ] **Dockerization**: Create `Dockerfile` to package the runner + Java 11 runtime.
4. [ ] **Config**: Standardize the `etas_config.json` structure for inputs/outputs.
