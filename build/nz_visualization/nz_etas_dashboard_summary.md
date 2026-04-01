# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Mon Mar 30 16:18:07 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `build/nz_visualization/nz_etas_dashboard.png` and `build/nz_visualization/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=277, median=345, 95th=495.
- Maximum magnitude across each simulation: median `M=5.65`, 95th percentile `M=6.80`.
- Indirect triggering share (`Gen>=2`) has median `32.6%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.785`, lon `174.254` with rate `1.718`.

## Threshold Comparison

- `M>=3.0`: simulated mean `360.34`, simulated 5th/50th/95th `277/345/495`, summary expected `265.71`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `36.19`, simulated 5th/50th/95th `23/34/56`, summary expected `26.57`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `3.64`, simulated 5th/50th/95th `1/3/8`, summary expected `2.66`, simulated P(N>=1) `95.8%`, summary P(N>=1) `95.4%`.
- `M>=6.0`: simulated mean `0.35`, simulated 5th/50th/95th `0/0/2`, summary expected `0.27`, simulated P(N>=1) `27.1%`, summary P(N>=1) `26.8%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `35.6%` (simulated `360.34` vs summary `265.71`).
  - `M>=4.0` count mean differs by `36.2%` (simulated `36.19` vs summary `26.57`).
  - `M>=5.0` count mean differs by `37.0%` (simulated `3.64` vs summary `2.66`).
  - `M>=6.0` count mean differs by `30.2%` (simulated `0.35` vs summary `0.27`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
