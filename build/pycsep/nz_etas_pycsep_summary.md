# pyCSEP NZ ETAS Summary

- pyCSEP version: `0.8.0`
- pyCSEP source: `/home/kennyg/projects/ETASModels/opensha-oaf/vendor/pycsep/csep/__init__.py`
- Event: `2016p858000`
- Analysis date: `Mon Mar 30 19:30:26 NZDT 2026`
- Mainshock origin time: `2016-11-13T11:02:56.346094+00:00`
- Mainshock metadata source: `GeoNet FDSN event service`
- Mainshock magnitude: `7.82`
- Forecast window: `7.0` to `14.0` days
- Forecast absolute window: `2016-11-20T11:02:56.346094+00:00` to `2016-11-27T11:02:56.346094+00:00`
- Catalogs loaded into pyCSEP: `1000`
- Raw ETAS rows read: `3551889`
- Events kept after `M>=Mc` filtering: `360343`
- Events kept after NZ pyCSEP region filtering: `348320`
- Representative catalog: `sim_0102` with `334` events
- Ensemble event-count median: `334`
- Median indirect (`Gen>=2`) share of `M>=Mc` events: `32.6%`

## Observed Catalog

- Observed catalog: `GeoNet observed 2016p858000 days 7.0-14.0`
- Observed event count in testing region: `323`
- Observed catalog cache: `build/pycsep/cache/2016p858000_d7_14_mc3_observed.csv`

## Catalog-Test Diagnostics

- Observed events in zero ETAS spatial-rate cells: `16` across `14` spatial cells
- Observed events in zero ETAS space-magnitude bins: `51`
- Zero-rate ETAS spatial cells in testing region: `3002` of `6343`

## Evaluation Results

- `catalog_number_test`: observed statistic `323`, quantile `(0.594, 0.411)`, status `normal`
- `catalog_magnitude_test`: observed statistic `0.550051`, quantile `(0.736, 0.264)`, status `normal`
- `catalog_spatial_test`: observed statistic `-5.73941`, quantile `(0.963, 0.037)`, status `undersampled`
- `catalog_pseudolikelihood_test`: observed statistic `-313.41`, quantile `(0.969, 0.031)`, status `undersampled`
- `catalog_resampled_magnitude_test`: observed statistic `0.550051`, quantile `(0.821, 0.179)`, status `normal`
- `catalog_mll_magnitude_test`: observed statistic `163.598`, quantile `(0.356, 0.644)`, status `normal`

## Rolling Diagnostics

- Rolling number-test sub-windows: `7`
- Rolling calibration KS statistic: `0.16000000000000003` with p-value `0.9800289364735593`

## Generated Files

- `build/pycsep/cache/2016p858000_d7_14_mc3_observed.csv`
- `build/pycsep/cache/2016p858000_mainshock.json`
- `build/pycsep/evaluation_json/catalog_magnitude_test.json`
- `build/pycsep/evaluation_json/catalog_mll_magnitude_test.json`
- `build/pycsep/evaluation_json/catalog_number_test.json`
- `build/pycsep/evaluation_json/catalog_pseudolikelihood_test.json`
- `build/pycsep/evaluation_json/catalog_resampled_magnitude_test.json`
- `build/pycsep/evaluation_json/catalog_spatial_test.json`
- `build/pycsep/evaluation_json/rolling_number_calibration.json`
- `build/pycsep/nz_etas_pycsep_catalog_magnitude_test.png`
- `build/pycsep/nz_etas_pycsep_catalog_mll_magnitude_test.png`
- `build/pycsep/nz_etas_pycsep_catalog_number_test.png`
- `build/pycsep/nz_etas_pycsep_catalog_pseudolikelihood_test.png`
- `build/pycsep/nz_etas_pycsep_catalog_resampled_magnitude_test.png`
- `build/pycsep/nz_etas_pycsep_catalog_spatial_test.png`
- `build/pycsep/nz_etas_pycsep_cumulative.png`
- `build/pycsep/nz_etas_pycsep_evaluation_distributions.png`
- `build/pycsep/nz_etas_pycsep_expected_rates.png`
- `build/pycsep/nz_etas_pycsep_generation_cumulative.png`
- `build/pycsep/nz_etas_pycsep_histogram.png`
- `build/pycsep/nz_etas_pycsep_magnitude_time.png`
- `build/pycsep/nz_etas_pycsep_max_magnitude_exceedance.png`
- `build/pycsep/nz_etas_pycsep_observed_catalog.png`
- `build/pycsep/nz_etas_pycsep_rolling_calibration.png`
- `build/pycsep/nz_etas_pycsep_rolling_number_consistency.png`
- `build/pycsep/nz_etas_pycsep_skill_diagrams.png`
- `build/pycsep/nz_etas_pycsep_spatial_residuals.png`
- `build/pycsep/nz_etas_pycsep_summary.md`

## Notes

- The cumulative and histogram plots use GeoNet observations when available; otherwise they fall back to a representative simulation.
- The rolling-window calibration test is a within-forecast diagnostic built from daily sub-window number tests inside the current ETAS horizon.
- pyCSEP emitted undersampling notices for the spatial/pseudolikelihood tests; these were captured and summarized here instead of relying on raw stdout.
- In pyCSEP, `status=undersampled` for the spatial and pseudolikelihood tests means observed events occurred in cells where the forecast had zero spatial support, so those events were removed before recomputing the score.
- The Poisson paired T/W comparison tests were skipped because pyCSEP comparison scores require positive target rates for all observed events, which is not true here.
- The catalog number test uses the empirical distribution of synthetic catalog sizes; the catalog magnitude tests compare the observed magnitude histogram against the union of all synthetic catalogs scaled to the observed event count.
