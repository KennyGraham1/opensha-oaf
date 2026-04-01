# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 20:20:56 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_premainshock/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_premainshock/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=73, median=104, 95th=186.
- Maximum magnitude across each simulation: median `M=5.16`, 95th percentile `M=6.30`.
- Indirect triggering share (`Gen>=2`) has median `8.1%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.795`, lon `174.221` with rate `0.4937`.

## Threshold Comparison

- `M>=3.0`: simulated mean `113.80`, simulated 5th/50th/95th `73/104/186`, summary expected `144.97`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `11.47`, simulated 5th/50th/95th `5/11/21`, summary expected `14.50`, simulated P(N>=1) `99.9%`, summary P(N>=1) `99.9%`.
- `M>=5.0`: simulated mean `1.09`, simulated 5th/50th/95th `0/1/3`, summary expected `1.45`, simulated P(N>=1) `62.7%`, summary P(N>=1) `62.6%`.
- `M>=6.0`: simulated mean `0.10`, simulated 5th/50th/95th `0/0/1`, summary expected `0.14`, simulated P(N>=1) `9.7%`, summary P(N>=1) `9.7%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `21.5%` (simulated `113.80` vs summary `144.97`).
  - `M>=4.0` count mean differs by `20.9%` (simulated `11.47` vs summary `14.50`).
  - `M>=5.0` count mean differs by `24.8%` (simulated `1.09` vs summary `1.45`).
  - `M>=6.0` count mean differs by `29.0%` (simulated `0.10` vs summary `0.14`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
