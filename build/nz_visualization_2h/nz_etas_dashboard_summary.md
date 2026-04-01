# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Tue Mar 31 22:17:19 NZDT 2026`
- Forecast window: `0.1` to `14.5` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2h/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2h/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=116, median=232, 95th=572.
- Maximum magnitude across each simulation: median `M=5.52`, 95th percentile `M=6.61`.
- Indirect triggering share (`Gen>=2`) has median `9.5%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-42.204`, lon `173.612` with rate `0.8917`.

## Threshold Comparison

- `M>=3.0`: simulated mean `267.91`, simulated 5th/50th/95th `116/232/572`, summary expected `586.31`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `26.83`, simulated 5th/50th/95th `10/23/57`, summary expected `58.63`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `2.68`, simulated 5th/50th/95th `0/2/7`, summary expected `5.86`, simulated P(N>=1) `87.3%`, summary P(N>=1) `87.2%`.
- `M>=6.0`: simulated mean `0.27`, simulated 5th/50th/95th `0/0/1`, summary expected `0.59`, simulated P(N>=1) `21.2%`, summary P(N>=1) `20.6%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `54.3%` (simulated `267.91` vs summary `586.31`).
  - `M>=4.0` count mean differs by `54.2%` (simulated `26.83` vs summary `58.63`).
  - `M>=5.0` count mean differs by `54.2%` (simulated `2.68` vs summary `5.86`).
  - `M>=6.0` count mean differs by `54.6%` (simulated `0.27` vs summary `0.59`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
