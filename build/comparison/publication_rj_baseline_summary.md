# RJ Baseline Comparison Summary

- RJ specification: fixed `p=1.00`, fixed `c=0.10` day, productivity estimated from observed count in [0, issue-time).
- Canonical observed catalog: stitched from `build/pycsep/cache/2016p858000_d0_14p5_mc3_observed.csv` (0–2h) and
  `build/pycsep_2h/cache/2016p858000_d0p08333_14p5_mc3_observed.csv` (2h–14.5d) to remain consistent with the fixed-horizon 7–14d target (`N_obs=323`).
- RJ has lower weekly CRPS than ETAS at: `Generic, 2 h, 6 h, 12 h, 1 d, 2 d, 3 d`.
