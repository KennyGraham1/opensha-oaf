# Reproducibility Metadata

- Git commit: `28968a57744d735779973fe1dbc9b8ec6cff8ec3`
- UTC generation time: `2026-04-01T21:46:49.551177+00:00`
- Python: `3.12.9`
- NumPy: `1.26.4`
- Matplotlib: `3.8.4`
- pyCSEP: `unknown`
- Bootstrap RNG seed (publication diagnostics): `20260402`
- Change-point permutation RNG seed: `20260402`
- Change-point permutations: `10000`
- Breakpoint bootstrap replicates: `5000`

## Run Order (fixed-horizon issue-time set)

1. `./run_etas_pipeline.sh etas_config_premainshock.json`
2. `./run_etas_pipeline.sh etas_config_2h.json`
3. `./run_etas_pipeline.sh etas_config_6h.json`
4. `./run_etas_pipeline.sh etas_config_12h.json`
5. `./run_etas_pipeline.sh etas_config_1d.json`
6. `./run_etas_pipeline.sh etas_config_2d.json`
7. `./run_etas_pipeline.sh etas_config_3d.json`
8. `./run_etas_pipeline.sh etas_config.json`
9. `python3 scripts/python/compare_etas_experiments.py`
10. `python3 scripts/python/build_publication_figures.py`
