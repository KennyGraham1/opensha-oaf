# Change-Point / Segmented Analysis Summary

- Model family: piecewise-constant mean with 0, 1, or 2 breakpoints.
- Minimum segment size: 2 issue-time points.
- Significance: permutation test (10,000 permutations) for two-break model vs null.
- Breakpoint support: bootstrap resampling from run-specific metric distributions (5,000 replicates).

- **count_ratio**: one-break at 1 d (1.00 d; p=0.0363); two-breaks after 2 h (0.08 d) and 1 d (1.00 d), p(two vs null)=0.0127, p(two vs one)=0.9696, support=(100.0%, 100.0%).
- **log10_weekly_crps**: one-break at 2 d (2.00 d; p=0.0717); two-breaks after 12 h (0.50 d) and 2 d (2.00 d), p(two vs null)=0.0844, p(two vs one)=0.8452, support=(100.0%, 100.0%).
