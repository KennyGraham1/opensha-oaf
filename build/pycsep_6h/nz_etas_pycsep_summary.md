# pyCSEP NZ ETAS Summary

- pyCSEP version: `0.8.0`
- pyCSEP source: `/home/kennyg/projects/ETASModels/opensha-oaf/vendor/pycsep/csep/__init__.py`
- Event: `2016p858000`
- Analysis date: `Wed Apr 01 19:50:06 NZDT 2026`
- Mainshock origin time: `2016-11-13T11:02:56.346094+00:00`
- Mainshock metadata source: `GeoNet FDSN event service`
- Mainshock magnitude: `7.82`
- Forecast window: `0.2` to `14.5` days
- Forecast absolute window: `2016-11-13T17:02:56.346094+00:00` to `2016-11-27T23:02:56.346094+00:00`
- Catalogs loaded into pyCSEP: `1000`
- Raw ETAS rows read: `4315093`
- Events kept after `M>=Mc` filtering: `436343`
- Events kept after NZ pyCSEP region filtering: `417174`
- Representative catalog: `sim_0041` with `380` events
- Ensemble event-count median: `380`
- Median indirect (`Gen>=2`) share of `M>=Mc` events: `17.2%`

## Observed Catalog

- Observed catalog: `GeoNet observed 2016p858000 days 0.2-14.5`
- Observed event count in testing region: `1924`
- Observed catalog cache: `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/cache/2016p858000_d0p25_14p5_mc3_observed.csv`

## Catalog-Test Diagnostics

- Observed events in zero ETAS spatial-rate cells: `30` across `18` spatial cells
- Observed events in zero ETAS space-magnitude bins: `67`
- Zero-rate ETAS spatial cells in testing region: `2597` of `6343`

## Evaluation Results

- `catalog_number_test`: observed statistic `1924`, quantile `(0, 1)`, status `normal`
- `catalog_magnitude_test`: observed statistic `1.27533`, quantile `(0.971, 0.029)`, status `normal`
- `catalog_spatial_test`: observed statistic `-4.75459`, quantile `(0, 1)`, status `undersampled`
- `catalog_pseudolikelihood_test`: observed statistic `2005.08`, quantile `(0, 1)`, status `undersampled`
- `catalog_resampled_magnitude_test`: observed statistic `1.27533`, quantile `(0.031, 0.969)`, status `normal`
- `catalog_mll_magnitude_test`: observed statistic `208.493`, quantile `(0, 1)`, status `normal`

## Rolling Diagnostics

- Rolling number-test sub-windows: `15`
- Rolling calibration KS statistic: `0.966` with p-value `1.875917571037498e-22`

## Generated Files

- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/cache/2016p858000_d0p25_14p5_mc3_observed.csv`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/cache/2016p858000_mainshock.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/evaluation_json/catalog_magnitude_test.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/evaluation_json/catalog_mll_magnitude_test.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/evaluation_json/catalog_number_test.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/evaluation_json/catalog_pseudolikelihood_test.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/evaluation_json/catalog_resampled_magnitude_test.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/evaluation_json/catalog_spatial_test.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/evaluation_json/rolling_number_calibration.json`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_catalog_magnitude_test.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_catalog_mll_magnitude_test.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_catalog_number_test.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_catalog_pseudolikelihood_test.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_catalog_resampled_magnitude_test.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_catalog_spatial_test.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_cumulative.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_evaluation_distributions.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_expected_rates.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_generation_cumulative.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_histogram.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_magnitude_time.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_max_magnitude_exceedance.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_observed_catalog.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_rolling_calibration.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_rolling_number_consistency.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_skill_diagrams.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_spatial_residuals.png`
- `/home/kennyg/projects/ETASModels/opensha-oaf/build/pycsep_6h/nz_etas_pycsep_summary.md`

## Notes

- The cumulative and histogram plots use GeoNet observations when available; otherwise they fall back to a representative simulation.
- The rolling-window calibration test is a within-forecast diagnostic built from daily sub-window number tests inside the current ETAS horizon.
- pyCSEP emitted undersampling notices for the spatial/pseudolikelihood tests; these were captured and summarized here instead of relying on raw stdout.
- In pyCSEP, `status=undersampled` for the spatial and pseudolikelihood tests means observed events occurred in cells where the forecast had zero spatial support, so those events were removed before recomputing the score.
- The Poisson paired T/W comparison tests were skipped because pyCSEP comparison scores require positive target rates for all observed events, which is not true here.
- The catalog number test uses the empirical distribution of synthetic catalog sizes; the catalog magnitude tests compare the observed magnitude histogram against the union of all synthetic catalogs scaled to the observed event count.
