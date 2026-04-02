#!/usr/bin/env python3
"""Cache a full observed GeoNet catalog in pyCSEP ASCII format for a chosen post-mainshock window."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import csep
from csep.core import regions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mainshock-json", default="build/pycsep/cache/2016p858000_mainshock.json")
    parser.add_argument("--start-days", type=float, default=0.0)
    parser.add_argument("--end-days", type=float, default=14.5)
    parser.add_argument("--mc", type=float, default=3.0)
    parser.add_argument("--output", default="build/pycsep/cache/2016p858000_d0_14p5_mc3_observed.csv")
    return parser.parse_args()


def parse_mainshock_time(path: Path) -> datetime:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = str(payload["origin_time"])
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> None:
    args = parse_args()
    mainshock_time = parse_mainshock_time(Path(args.mainshock_json))
    start = mainshock_time + timedelta(days=args.start_days)
    end = mainshock_time + timedelta(days=args.end_days)
    region = regions.nz_csep_collection_region()

    catalog = csep.query_gns(
        start_time=start,
        end_time=end,
        max_longitude=180.0,
        min_longitude=164.0,
        min_latitude=-49.0,
        max_latitude=-33.0,
    )
    catalog = catalog.filter([f"magnitude >= {args.mc}"], in_place=False)
    catalog.region = region
    catalog = catalog.filter_spatial(region=region, in_place=False)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_ascii(str(output))
    print(f"Wrote {output}")
    print(f"Event count: {catalog.event_count}")


if __name__ == "__main__":
    main()
