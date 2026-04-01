# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Tue Mar 31 22:29:38 NZDT 2026`
- Forecast window: `3.0` to `14.5` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_3d/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_3d/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=984, median=1150, 95th=1391.
- Maximum magnitude across each simulation: median `M=6.20`, 95th percentile `M=7.38`.
- Indirect triggering share (`Gen>=2`) has median `38.8%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.723`, lon `174.279` with rate `6.316`.

## Threshold Comparison

- `M>=3.0`: simulated mean `1159.39`, simulated 5th/50th/95th `984/1150/1391`, summary expected `939.96`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `116.15`, simulated 5th/50th/95th `88/115/147`, summary expected `94.00`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `11.57`, simulated 5th/50th/95th `5/11/19`, summary expected `9.40`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=6.0`: simulated mean `1.14`, simulated 5th/50th/95th `0/1/3`, summary expected `0.94`, simulated P(N>=1) `66.2%`, summary P(N>=1) `65.7%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `23.3%` (simulated `1159.39` vs summary `939.96`).
  - `M>=4.0` count mean differs by `23.6%` (simulated `116.15` vs summary `94.00`).
  - `M>=5.0` count mean differs by `23.1%` (simulated `11.57` vs summary `9.40`).
  - `M>=6.0` count mean differs by `21.7%` (simulated `1.14` vs summary `0.94`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
