# Reproducibility Metadata

- Git commit: `65cc224202b45442395303f8cc0de6299736a04c`
- UTC generation time: `2026-04-02T00:05:08.193841+00:00`
- Python: `3.9.21`
- NumPy: `2.0.2`
- Matplotlib: `3.9.4`
- pyCSEP: `0.8.0`
- Bootstrap RNG seed (publication diagnostics): `20260402`
- Change-point permutation RNG seed: `20260402`
- Change-point permutations: `10000`
- Breakpoint bootstrap replicates: `5000`

## Run Order (fixed-horizon issue-time set)

1. `python3 scripts/python/cache_full_observed_catalog.py`
2. `./run_etas_pipeline.sh etas_config_premainshock.json`
3. `./run_etas_pipeline.sh etas_config_2h.json`
4. `./run_etas_pipeline.sh etas_config_6h.json`
5. `./run_etas_pipeline.sh etas_config_12h.json`
6. `./run_etas_pipeline.sh etas_config_1d.json`
7. `./run_etas_pipeline.sh etas_config_2d.json`
8. `./run_etas_pipeline.sh etas_config_3d.json`
9. `./run_etas_pipeline.sh etas_config.json`
10. `python3 scripts/python/compare_etas_experiments.py`
11. `python3 scripts/python/build_publication_figures.py`
