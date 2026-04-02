# Operational GO/NO-GO Decision Table

- Decision logic:
  - `GO`: N-test pass, rolling KS p>=0.05, weekly 90% coverage=1, and 0.8<=median_ratio<=1.2.
  - `CAUTION`: partial pass (N-test pass, rolling p>=0.01, coverage>=0.5).
  - `NO-GO`: otherwise.

- Generic: **NO-GO** (N-test=underpredict, rolling p=4.99e-12, coverage=0.00, median/obs=0.27, RJ better CRPS=True).
- 2 h: **NO-GO** (N-test=underpredict, rolling p=4.37e-18, coverage=0.00, median/obs=0.17, RJ better CRPS=True).
- 6 h: **NO-GO** (N-test=underpredict, rolling p=1.56e-16, coverage=0.00, median/obs=0.15, RJ better CRPS=True).
- 12 h: **NO-GO** (N-test=underpredict, rolling p=2e-21, coverage=0.00, median/obs=0.14, RJ better CRPS=True).
- 1 d: **NO-GO** (N-test=underpredict, rolling p=2.56e-19, coverage=0.00, median/obs=0.16, RJ better CRPS=True).
- 2 d: **NO-GO** (N-test=overpredict, rolling p=2.6e-05, coverage=0.00, median/obs=1.54, RJ better CRPS=True).
- 3 d: **NO-GO** (N-test=overpredict, rolling p=3.11e-05, coverage=0.00, median/obs=1.52, RJ better CRPS=True).
- 7 d: **GO** (N-test=pass, rolling p=0.98, coverage=1.00, median/obs=1.03, RJ better CRPS=False).
