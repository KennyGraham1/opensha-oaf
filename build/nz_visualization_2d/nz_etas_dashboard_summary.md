# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 20:12:15 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2d/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2d/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=426, median=519, 95th=781.
- Maximum magnitude across each simulation: median `M=5.84`, 95th percentile `M=7.02`.
- Indirect triggering share (`Gen>=2`) has median `30.6%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.719`, lon `174.280` with rate `2.84`.

## Threshold Comparison

- `M>=3.0`: simulated mean `556.99`, simulated 5th/50th/95th `426/519/781`, summary expected `403.53`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `55.85`, simulated 5th/50th/95th `35/53/83`, summary expected `40.35`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `5.55`, simulated 5th/50th/95th `2/5/11`, summary expected `4.04`, simulated P(N>=1) `99.5%`, summary P(N>=1) `99.5%`.
- `M>=6.0`: simulated mean `0.52`, simulated 5th/50th/95th `0/0/2`, summary expected `0.40`, simulated P(N>=1) `38.8%`, summary P(N>=1) `38.5%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `38.0%` (simulated `556.99` vs summary `403.53`).
  - `M>=4.0` count mean differs by `38.4%` (simulated `55.85` vs summary `40.35`).
  - `M>=5.0` count mean differs by `37.5%` (simulated `5.55` vs summary `4.04`).
  - `M>=6.0` count mean differs by `29.6%` (simulated `0.52` vs summary `0.40`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
