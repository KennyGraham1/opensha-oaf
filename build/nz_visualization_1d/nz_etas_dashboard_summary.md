# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 20:10:40 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_1d/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_1d/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=73, median=95, 95th=127.
- Maximum magnitude across each simulation: median `M=5.11`, 95th percentile `M=6.28`.
- Indirect triggering share (`Gen>=2`) has median `3.9%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.802`, lon `174.233` with rate `0.4613`.

## Threshold Comparison

- `M>=3.0`: simulated mean `97.12`, simulated 5th/50th/95th `73/95/127`, summary expected `928.74`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `9.80`, simulated 5th/50th/95th `4/10/16`, summary expected `92.87`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `0.95`, simulated 5th/50th/95th `0/1/3`, summary expected `9.29`, simulated P(N>=1) `58.6%`, summary P(N>=1) `58.4%`.
- `M>=6.0`: simulated mean `0.10`, simulated 5th/50th/95th `0/0/1`, summary expected `0.93`, simulated P(N>=1) `9.9%`, summary P(N>=1) `9.9%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `89.5%` (simulated `97.12` vs summary `928.74`).
  - `M>=4.0` count mean differs by `89.4%` (simulated `9.80` vs summary `92.87`).
  - `M>=5.0` count mean differs by `89.7%` (simulated `0.95` vs summary `9.29`).
  - `M>=6.0` count mean differs by `88.9%` (simulated `0.10` vs summary `0.93`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
