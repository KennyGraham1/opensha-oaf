# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Wed Apr 01 20:14:12 NZDT 2026`
- Forecast window: `7.0` to `14.0` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2h/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_2h/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=67, median=86, 95th=117.
- Maximum magnitude across each simulation: median `M=5.08`, 95th percentile `M=6.19`.
- Indirect triggering share (`Gen>=2`) has median `3.7%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-42.204`, lon `173.612` with rate `0.3354`.

## Threshold Comparison

- `M>=3.0`: simulated mean `88.48`, simulated 5th/50th/95th `67/86/117`, summary expected `252.55`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `8.96`, simulated 5th/50th/95th `4/9/15`, summary expected `25.26`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `0.83`, simulated 5th/50th/95th `0/1/3`, summary expected `2.53`, simulated P(N>=1) `55.8%`, summary P(N>=1) `55.6%`.
- `M>=6.0`: simulated mean `0.07`, simulated 5th/50th/95th `0/0/1`, summary expected `0.25`, simulated P(N>=1) `6.8%`, summary P(N>=1) `6.8%`.

## Notes

- The dashboard is driven by the simulated catalogs themselves. The summary-file expected counts do not match the catalog-derived ensemble means at some thresholds:
  - `M>=3.0` count mean differs by `65.0%` (simulated `88.48` vs summary `252.55`).
  - `M>=4.0` count mean differs by `64.5%` (simulated `8.96` vs summary `25.26`).
  - `M>=5.0` count mean differs by `67.3%` (simulated `0.83` vs summary `2.53`).
  - `M>=6.0` count mean differs by `71.5%` (simulated `0.07` vs summary `0.25`).
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
