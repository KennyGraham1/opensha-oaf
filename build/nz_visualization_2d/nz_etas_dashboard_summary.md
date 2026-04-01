# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Tue Mar 31 22:26:02 NZDT 2026`
- Forecast window: `2.0` to `14.5` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2d/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2d/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=1161, median=1403, 95th=1926.
- Maximum magnitude across each simulation: median `M=6.28`, 95th percentile `M=7.47`.
- Indirect triggering share (`Gen>=2`) has median `40.5%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.719`, lon `174.280` with rate `7.776`.

## Threshold Comparison

- `M>=3.0`: simulated mean `1453.13`, simulated 5th/50th/95th `1161/1403/1926`, summary expected `1136.16`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `145.69`, simulated 5th/50th/95th `104/142/199`, summary expected `113.62`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `14.60`, simulated 5th/50th/95th `7/14/24`, summary expected `11.36`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=6.0`: simulated mean `1.44`, simulated 5th/50th/95th `0/1/4`, summary expected `1.14`, simulated P(N>=1) `73.1%`, summary P(N>=1) `72.9%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `27.9%` (simulated `1453.13` vs summary `1136.16`).
  - `M>=4.0` count mean differs by `28.2%` (simulated `145.69` vs summary `113.62`).
  - `M>=5.0` count mean differs by `28.5%` (simulated `14.60` vs summary `11.36`).
  - `M>=6.0` count mean differs by `26.8%` (simulated `1.44` vs summary `1.14`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
