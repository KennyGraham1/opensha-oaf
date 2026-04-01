# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Tue Mar 31 22:22:33 NZDT 2026`
- Forecast window: `1.0` to `14.5` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_1d/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_1d/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=893, median=1483, 95th=1928.
- Maximum magnitude across each simulation: median `M=6.29`, 95th percentile `M=7.37`.
- Indirect triggering share (`Gen>=2`) has median `40.9%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.802`, lon `174.233` with rate `7.19`.

## Threshold Comparison

- `M>=3.0`: simulated mean `1470.13`, simulated 5th/50th/95th `893/1483/1928`, summary expected `1320.22`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `147.55`, simulated 5th/50th/95th `88/148/199`, summary expected `132.02`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `14.70`, simulated 5th/50th/95th `7/14/25`, summary expected `13.20`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=6.0`: simulated mean `1.46`, simulated 5th/50th/95th `0/1/4`, summary expected `1.32`, simulated P(N>=1) `73.9%`, summary P(N>=1) `73.7%`.

## Notes

- Summary-file expected counts are broadly consistent with the catalog-derived ensemble means.
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
