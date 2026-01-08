# ETAS Codebase Implementation Guide

This document provides a deep technical dive into the Java implementation of the ETAS model within the `opensha-oaf` project. It maps the mathematical concepts to specific classes, methods, and variables in the source code.

## 1. Class Hierarchy

The core logic resides in the `org.opensha.oaf.etas` package.

### Key Classes
| Class | Role | Key Responsibility |
| :--- | :--- | :--- |
| **`ETAS_AftershockModel`** | **Abstract Base** | Defines the data structures (lists of events) and generic ETAS parameters (`a`, `p`, `c`). |
| **`ETAS_AftershockModel_SequenceSpecific`** | **Implementation** | Implements the **Maximum Likelihood Estimation (MLE)** to fit parameters to a specific sequence. This is the main class used in the NZ demo. |
| **`ETAScatalog`** | **Simulation** | Represents a stochastic future. Generates synthetic catalogs using Monte Carlo simulation. |
| **`ETAS_StatsCalc`** | **Math Utility** | Static methods for Omori Law integration, branching ratios, and spatial centroid calculations. |

---

## 2. Mathematical to Code Mapping

The model assumes the standard ETAS conditional intensity function:
$$ \lambda(t) = \mu + \sum_{t_i < t} K \cdot 10^{\alpha(M_i - M_c)} \cdot (t - t_i + c)^{-p} $$

### A. Parameters
| Math Symbol | Code Variable | Location (`ETAS_AftershockModel`) |
| :--- | :--- | :--- |
| **$\mu$** | `mu` | Background rate (usually ignored/zero for aftershock sequences). |
| **$K$** | `Math.pow(10, a)` | Productivity ($a$ is the log-productivity). |
| **$\alpha$** | `alpha` | Scaling of productivity with magnitude. Fixed at 1.0. |
| **$c$** | `c` | Time offset parameter. |
| **$p$** | `p` | Omori decay exponent. |
| **$M_c$** | `magComplete` | The completeness magnitude of the catalog. |

---

## 3. Critical Workflows

### A. Parameter Fitting (MLE)
**Class**: `ETAS_AftershockModel_SequenceSpecific`
**Method**: `getLikelihoodMatrixGridFastMc()`

The code finds optimal parameters by performing a grid search:
1.  **Grid Initialization**: The constructor accepts arrays defining the search space for `a`, `p`, and `c`.
2.  **Likelihood Calculation**:
    *   It iterates through every combination of `p` and `c`.
    *   For each event $i$, it computes the intensity contribution from the Mainshock (`timeDecayMS`) and all previous aftershocks (`timeDecayAS`).
    *   **Optimization**: The intense inner loops (calculating the sum of past events) are optimized to avoid re-calculating constant terms.
3.  **Selection**: The combination with the highest Log-Likelihood is stored in `max_a_index`, `max_p_index`, etc.

### B. Stochastic Simulation (Forecasting)
**Class**: `ETAScatalog`
**Method**: `getNewETAScatalog()` -> `getChildren()`

The forecasting is done by simulating future event trees:
1.  **Seeding**: Starts with the observed Mainshock and Aftershocks as "Gen 0" parents.
2.  **Recursion (`getChildren`)**:
    *   Calculates the **productivity** (expected number of children) for a parent event using:
        `calculateProductivity(...)` -> Integral of Omori law over the forecast window.
    *   Draws a random number of children from a **Poisson distribution** (`assignNumberOfOffspring`).
    *   Assigns **Times** to children (inverse transform sampling of Omori law).
    *   Assigns **Magnitudes** to children (inverse transform sampling of Gutenberg-Richter).
3.  **Iteration**: The simulation repeats for `nSims` (100) times to build a probabilistic distribution.

### C. Forecast Quantification
**Class**: `ETAS_AftershockModel`
**Method**: `getExpectedNumEvents()`

*   **Logic**: Calculates the expected rate by integrating the fitted intensity function.
*   **Important Note**: This method returns the rate of events **$\ge M_c$**.
*   **Scaling**: To get the rate for a different magnitude (e.g., $M \ge 4.0$), the code must manually apply the Gutenberg-Richter scaling factor:
    $$ N(\ge M) = N(\ge M_c) \times 10^{-b(M - M_c)} $$
    *(This explicit scaling was added to `ETAS_Demo_NZ.java` during the implementation).*

---

## 4. Advanced Topics

### A. Generic vs. Sequence-Specific Models
The codebase supports two primary modeling approaches, distinct in their origin of parameters.

#### 1. `ETAS_AftershockModel_Generic`
*   **Philosophy**: "Bayesian Prior Driven". It presumes the sequence behaves like the *average* sequence for that tectonic region until proven otherwise.
*   **Initialization**: 
    *   Constructed using `GenericETAS_Parameters` (defaults: $p \approx 1.0, c \approx 0.01$).
    *   It defines a Gaussian distribution for $a$-values ($mean \pm 3\sigma$) and typically holds $p$ and $c$ constant or within a narrow prior range.
*   **Fitting**: It does **NOT** perform a free parameter search.
    *   Calculates `epiLikelihood` (Likelihood of the sequence given the prior parameters).
    *   Updates the weights of the parameter grid based on the data (Bayesian update), but does not move the grid itself.
*   **Use Case**: First minutes/hours after a mainshock when the catalog is incomplete or empty.

#### 2. `ETAS_AftershockModel_SequenceSpecific` (Used in Demo)
*   **Philosophy**: "Data Driven". It acknowledges that every sequence is unique and fits parameters ($a, p, c$) directly to the observed aftershocks.
*   **Initialization**: 
    *   Takes raw `ObsEqkRupList` and defines a wide search grid for $a, p, c$.
*   **Fitting (`getLikelihoodMatrixGridFastMc`)**:
    *   **Grid Search**: Iterates over thousands of ($a, p, c$) combinations.
    *   **Maximum Likelihood**: Calculates $\log L(\theta | Data) = \sum \log \lambda(t_i) - \int \lambda(t) dt$.
    *   **Optimization**: Returns the specific parameters that maximize this likelihood.
*   **Use Case**: Mature sequences (days/weeks) where enough data exists to constrain the Omori decay ($p$) and productivity ($a$).

### B. Spatial Capabilities (`ETAS_RateModel2D`)
While the primary forecasting loop is 0-Dimensional, the package contains **unused** spatial capabilities in `ETAS_RateModel2D.java`.

*   **Functionality**: Can generate a 2D grid of expected rates (`GriddedGeoDataSet`).
*   **Method**: `calculateRateModel(...)`
*   **Spatial Kernel**: It employs a spatial decay function for rate estimation:
    $$ S(r) \propto \frac{H}{(d^2 + r^2)^{1.5}} $$
    Where:
    *   $r$: Distance from source.
    *   $d$: Source radius (function of magnitude).
    *   $H$: Seismogenic depth.

**Note**: This 2D model is a *post-processing* or *visualization* step in this library, not the core engine for the stochastic event count forecasting used in the demo.

### C. Parameter Management
All parameters are encapsulated in the **`GenericETAS_Parameters`** class.
*   **Role**: A Serializable container for mean values, sigmas, and covariance matrices of model parameters.
*   **Defaults**: If instantiated empty, it defaults to global average tectonic parameters:
    *   $a \approx -2.4$
    *   $p \approx 0.966$
    *   $c \approx 0.003$ days
    *   $\alpha = 1.0, b = 1.0$

## 5. Data Flow Summary
1.  **Input**: `ETAS_Demo_NZ` fetches QuakeML $\rightarrow$ parses to `ObsEqkRupList`.
2.  **Model Selection**: Instantiates `ETAS_AftershockModel_SequenceSpecific`.
3.  **Fitting**: `SequenceSpecific` runs `getLikelihoodMatrixGridFastMc` to find best fit `a,p,c`.
4.  **Simulation**: Calls `getNewETAScatalog()` $N$ times.
    *   Recursively generates offspring implementation in `ETAScatalog`.
5.  **Output**: `ETAS_Demo_NZ` reads `simulatedCatalog` lists and writes to `simulated_catalogs/*.txt`.

## 6. Advanced Physics & Hazards

### A. Time-Dependent Completeness ($M_c(t)$)
The code (`ETAS_AftershockModel`) has specific logic to handle **Time-Dependent Completeness**, a critical phenomenon where the detection of small aftershocks is temporarily blinded by the coda of large events.

*   **Flag**: `timeDependentMc` (Boolean).
*   **Mechanism**:
    *   It adjusts the lower bound of the time integral in the rate equation.
    *   Instead of integrating from $t_{min}$, it effectively uses a dynamic start time based on the magnitude of the parent event.
    *   **Formula Logic**: The parameter `ac` implies a short-term productivity/detection threshold. The code calculates a modified offset `cms`:
        $$ c_{ms} = c \cdot (k \cdot k_c)^{1/p} $$
        This essentially models the recovery of the network's detection capability following a large energy release.
## 7. Parameter Estimation Deep Dive
The heart of the `SequenceSpecific` model is `getLikelihoodMatrixGridFastMc()`. Here is the step-by-step algorithmic breakdown:

### A. The Optimization Strategy
Instead of calculating the full likelihood for every combination of $(a, p, c)$, the code exploits the structure of the ETAS equation to separate the **shape** (controlled by $p, c$) from the **scale** (controlled by $a$).

### B. Outer Loops ($p, c$)
1.  Iterate over all possible values of $p$ and $c$.
2.  **Pre-calculate Shapes**:
    *   Calculate `timeDecayMS[i]`: The decay value at time $t_i$ from the mainshock.
    *   Calculate `timeDecayAS[i]`: The summed decay values at time $t_i$ from all previous aftershocks.
    *   *Note*: These values are "normalized" (they sum to 1 or are unscaled by productivity $a$).
3.  **Pre-calculate Integrals**:
    *   Compute the integral of the Omori law (expected number of events) over the data window.
    *   This is the $-\int \lambda(t) dt$ term in the likelihood equation.

### C. Inner Loops ($a, \mu$)
1.  Iterate over all possible values of $a$ (aftershock productivity) and $ams$ (mainshock productivity).
2.  **Scale and Sum**:
    *   Combine the pre-calculated shapes with the current $a$-values:
        $$ \lambda(t_i) = 10^{ams} \cdot \text{DecayMS}_i + 10^a \cdot \text{DecayAS}_i $$
    *   Sum the Log-Likelihood:
        $$ \log L = \sum_{i} \log(\lambda(t_i)) - N_{expected} $$
3.  **Bayesian Prior**: Add the log-probability from the `priorLikelihood` matrix.

### D. Result
The grid cell with the highest final `logLike` is selected as the **Maximum Likelihood Estimate (MLE)**. This approach reduces a 4D complexity problem into a nested 2D problem, making the fit extremely fast (~seconds).

### B. Downstream Integration: Shaking Forecasts
The `org.opensha.oaf.etas` package is designed to feed directly into **Probabilistic Seismic Hazard Analysis (PSHA)**.

*   **Class**: `ETAS_ShakingForecastCalc`
*   **Workflow**:
    1.  **Rate Model**: Takes a spatial `rateModel` (from `ETAS_RateModel2D`).
    2.  **ERF Creation**: Wraps the rates into a `GriddedForecast` (an OpenSHA `AbstractERF`). This treats every grid cell as a `PointSourceNshm`.
    3.  **GMPE Calculation**: Uses **Ground Motion Prediction Equations** (e.g., via `ScalarIMR`) to calculate the probability of exceeding specific ground motions (PGA, MMI).
    4.  **Hazard Curves**: Outputs `DiscretizedFunc[]`, representing the probability of exceedance at every grid point.

This architecture proves that the ETAS module is not just a statistical toy but a fully integrated component of a **Short-Term Hazard Forecasting** system.
