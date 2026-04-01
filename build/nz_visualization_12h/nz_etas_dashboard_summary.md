# NZ ETAS Visualization Summary

- Event: `2016p858000`
- Analysis date: `Tue Mar 31 22:19:35 NZDT 2026`
- Forecast window: `0.5` to `14.5` days
- Magnitude of completeness: `Mc=3.0`
- Catalogs processed: `1000`
- Dashboard files: `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_12h/nz_etas_dashboard.png` and `/home/kennyg/projects/ETASModels/opensha-oaf/build/nz_visualization_12h/nz_etas_dashboard.pdf`

## Ensemble Diagnostics

- Final cumulative `M>=3.0` count across the forecast window: 5th=737, median=1201, 95th=1597.
- Maximum magnitude across each simulation: median `M=6.17`, 95th percentile `M=7.38`.
- Indirect triggering share (`Gen>=2`) has median `38.9%` of all `M>=Mc` events.
- Spatial contours summarize simulated `M>=4.0` events; point overlays summarize `M>=5.0` events.
- Peak deterministic spatial rate is near lat `-41.795`, lon `174.221` with rate `5.694`.

## Threshold Comparison

- `M>=3.0`: simulated mean `1141.74`, simulated 5th/50th/95th `737/1201/1597`, summary expected `1188.25`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=4.0`: simulated mean `114.60`, simulated 5th/50th/95th `67/117/164`, summary expected `118.83`, simulated P(N>=1) `100.0%`, summary P(N>=1) `100.0%`.
- `M>=5.0`: simulated mean `11.45`, simulated 5th/50th/95th `4/11/21`, summary expected `11.88`, simulated P(N>=1) `99.9%`, summary P(N>=1) `99.9%`.
- `M>=6.0`: simulated mean `1.17`, simulated 5th/50th/95th `0/1/3`, summary expected `1.19`, simulated P(N>=1) `65.2%`, summary P(N>=1) `64.7%`.

## Notes

- Summary-file expected counts are broadly consistent with the catalog-derived ensemble means.
- In a branching ETAS forecast, the empirical catalog ensemble is the safer object to visualize than a single expected-count column because it preserves overdispersion, cascade depth, and magnitude exceedance behavior.
