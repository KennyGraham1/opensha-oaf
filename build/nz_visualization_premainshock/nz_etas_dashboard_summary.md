# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Tue Mar 31 20:16:10 NZDT 2026`
- Forecast window: `0.5` to `14.5` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_premainshock/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_premainshock/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=109, median=218, 95th=516.
- Maximum magnitude across each simulation: median `M=5.48`, 95th percentile `M=6.64`.
- Indirect triggering share (`Gen>=2`) has median `10.5%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.795`, lon `174.221` with rate `1.03`.

## Threshold Comparison

- `M>=3.0`: simulated mean `254.33`, simulated 5th/50th/95th `109/218/516`, summary expected `801.69`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `25.40`, simulated 5th/50th/95th `9/22/54`, summary expected `80.17`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `2.44`, simulated 5th/50th/95th `0/2/6`, summary expected `8.02`, simulated P(N>=1) `85.0%`, summary P(N>=1) `84.6%`.
- `M>=6.0`: simulated mean `0.26`, simulated 5th/50th/95th `0/0/1`, summary expected `0.80`, simulated P(N>=1) `21.1%`, summary P(N>=1) `20.8%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `68.3%` (simulated `254.33` vs summary `801.69`).
  - `M>=4.0` count mean differs by `68.3%` (simulated `25.40` vs summary `80.17`).
  - `M>=5.0` count mean differs by `69.5%` (simulated `2.44` vs summary `8.02`).
  - `M>=6.0` count mean differs by `68.1%` (simulated `0.26` vs summary `0.80`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
