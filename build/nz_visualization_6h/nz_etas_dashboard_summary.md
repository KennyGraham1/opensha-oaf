# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 19:50:06 NZDT 2026`
- Forecast window: `0.2` to `14.5` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_6h/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_6h/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=221, median=397, 95th=747.
- Maximum magnitude across each simulation: median `M=5.73`, 95th percentile `M=6.88`.
- Indirect triggering share (`Gen>=2`) has median `17.2%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.784`, lon `174.223` with rate `1.752`.

## Threshold Comparison

- `M>=3.0`: simulated mean `436.34`, simulated 5th/50th/95th `221/397/747`, summary expected `758.62`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `43.82`, simulated 5th/50th/95th `20/40/79`, summary expected `75.86`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `4.30`, simulated 5th/50th/95th `1/4/9`, summary expected `7.59`, simulated P(N>=1) `96.5%`, summary P(N>=1) `96.4%`.
- `M>=6.0`: simulated mean `0.42`, simulated 5th/50th/95th `0/0/2`, summary expected `0.76`, simulated P(N>=1) `33.2%`, summary P(N>=1) `32.9%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `42.5%` (simulated `436.34` vs summary `758.62`).
  - `M>=4.0` count mean differs by `42.2%` (simulated `43.82` vs summary `75.86`).
  - `M>=5.0` count mean differs by `43.4%` (simulated `4.30` vs summary `7.59`).
  - `M>=6.0` count mean differs by `44.8%` (simulated `0.42` vs summary `0.76`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
