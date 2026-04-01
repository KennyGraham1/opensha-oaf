# Probabilistic Skill Summary

- Figure: `build/comparison/publication_probabilistic_scores.png`.
- CSV table: `build/comparison/publication_probabilistic_scores.csv`.

## Highlights

- Best weekly CRPS: **7 d** (14.48).
- Best daily mean CRPS: **7 d** (5.74).
- Worst daily mean CRPS: **2 h** (31.17).
- Early runs (generic to 1d) show extreme daily PIT concentration near 1.0, confirming one-sided underprediction.
- Intermediate runs (2d, 3d) reduce score penalties but remain one-sided overpredictive in daily bins.
- The 7d run uniquely minimizes both score penalties and distributional divergence to the calibrated reference.
