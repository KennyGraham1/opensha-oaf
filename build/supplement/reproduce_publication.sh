#!/usr/bin/env bash
set -euo pipefail
python3 scripts/python/cache_full_observed_catalog.py
./run_etas_pipeline.sh etas_config_premainshock.json
./run_etas_pipeline.sh etas_config_2h.json
./run_etas_pipeline.sh etas_config_6h.json
./run_etas_pipeline.sh etas_config_12h.json
./run_etas_pipeline.sh etas_config_1d.json
./run_etas_pipeline.sh etas_config_2d.json
./run_etas_pipeline.sh etas_config_3d.json
./run_etas_pipeline.sh etas_config.json
python3 scripts/python/compare_etas_experiments.py
python3 scripts/python/build_publication_figures.py
