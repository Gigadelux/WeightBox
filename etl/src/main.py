"""Entry point for the WeightBox ETL container.

    python -m src.main                 run all four phases
    python -m src.main --only etl      run one phase
    python -m src.main --from indexing start at a phase, run to the end
"""

from __future__ import annotations

import argparse
import logging
import sys

from services.config import get_settings
from src.pipeline import PHASE_NAMES, Pipeline


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="weightbox-etl")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--only", choices=PHASE_NAMES, help="run a single phase")
    group.add_argument("--from", dest="start_from", choices=PHASE_NAMES,
                       help="start at this phase and run to the end")
    p.add_argument("--log-level", default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = get_settings()
    level = (args.log_level or settings.etl_log_level).upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("weightbox.etl")

    pipeline = Pipeline(settings)
    try:
        report = pipeline.run(only=args.only, start_from=args.start_from)
    finally:
        pipeline.close()

    for r in report.phases:
        log.info("summary: %-15s %-7s %6.1fs  %s",
                 r.phase, "ok" if r.ok else "FAIL", r.duration_s,
                 "; ".join(r.errors) if r.errors else "")
    log.info("pipeline: %s", "OK" if report.ok else "FAILED")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
