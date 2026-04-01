# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 20:15:54 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_3d/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_3d/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=434, median=513, 95th=677.
- Maximum magnitude across each simulation: median `M=5.83`, 95th percentile `M=7.03`.
- Indirect triggering share (`Gen>=2`) has median `30.9%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.723`, lon `174.279` with rate `2.804`.

## Threshold Comparison

- `M>=3.0`: simulated mean `526.98`, simulated 5th/50th/95th `434/513/677`, summary expected `417.46`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `52.48`, simulated 5th/50th/95th `35/51/74`, summary expected `41.75`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `5.22`, simulated 5th/50th/95th `1/5/10`, summary expected `4.17`, simulated P(N>=1) `99.0%`, summary P(N>=1) `98.9%`.
- `M>=6.0`: simulated mean `0.48`, simulated 5th/50th/95th `0/0/2`, summary expected `0.42`, simulated P(N>=1) `35.9%`, summary P(N>=1) `35.6%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `26.2%` (simulated `526.98` vs summary `417.46`).
  - `M>=4.0` count mean differs by `25.7%` (simulated `52.48` vs summary `41.75`).
  - `M>=5.0` count mean differs by `24.9%` (simulated `5.22` vs summary `4.17`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
