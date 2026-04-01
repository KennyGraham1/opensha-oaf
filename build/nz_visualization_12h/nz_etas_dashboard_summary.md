# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 20:09:05 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_12h/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_12h/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=70, median=88, 95th=121.
- Maximum magnitude across each simulation: median `M=5.11`, 95th percentile `M=6.16`.
- Indirect triggering share (`Gen>=2`) has median `2.6%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.795`, lon `174.221` with rate `0.417`.

## Threshold Comparison

- `M>=3.0`: simulated mean `91.47`, simulated 5th/50th/95th `70/88/121`, summary expected `921.27`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `9.32`, simulated 5th/50th/95th `4/9/15`, summary expected `92.13`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `0.90`, simulated 5th/50th/95th `0/1/3`, summary expected `9.21`, simulated P(N>=1) `59.9%`, summary P(N>=1) `59.5%`.
- `M>=6.0`: simulated mean `0.08`, simulated 5th/50th/95th `0/0/1`, summary expected `0.92`, simulated P(N>=1) `7.6%`, summary P(N>=1) `7.6%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `90.1%` (simulated `91.47` vs summary `921.27`).
  - `M>=4.0` count mean differs by `89.9%` (simulated `9.32` vs summary `92.13`).
  - `M>=5.0` count mean differs by `90.2%` (simulated `0.90` vs summary `9.21`).
  - `M>=6.0` count mean differs by `91.6%` (simulated `0.08` vs summary `0.92`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
