# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 20:17:53 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_6h/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_6h/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=68, median=88, 95th=115.
- Maximum magnitude across each simulation: median `M=5.12`, 95th percentile `M=6.28`.
- Indirect triggering share (`Gen>=2`) has median `2.3%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.784`, lon `174.223` with rate `0.3899`.

## Threshold Comparison

- `M>=3.0`: simulated mean `89.64`, simulated 5th/50th/95th `68/88/115`, summary expected `432.16`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `9.04`, simulated 5th/50th/95th `4/9/15`, summary expected `43.22`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `0.91`, simulated 5th/50th/95th `0/1/3`, summary expected `4.32`, simulated P(N>=1) `59.8%`, summary P(N>=1) `59.5%`.
- `M>=6.0`: simulated mean `0.10`, simulated 5th/50th/95th `0/0/1`, summary expected `0.43`, simulated P(N>=1) `9.3%`, summary P(N>=1) `9.3%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `79.3%` (simulated `89.64` vs summary `432.16`).
  - `M>=4.0` count mean differs by `79.1%` (simulated `9.04` vs summary `43.22`).
  - `M>=5.0` count mean differs by `79.0%` (simulated `0.91` vs summary `4.32`).
  - `M>=6.0` count mean differs by `77.3%` (simulated `0.10` vs summary `0.43`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
