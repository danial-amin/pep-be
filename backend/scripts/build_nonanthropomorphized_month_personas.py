"""Write one non-anthropomorphized persona set per month.

Reads conduct-group JSON from moltbook-ddps and writes
backend/default_personas/personas_moltbook_conduct_<month>.json.
Demographic fields stay empty. Titles, goals, and frustrations restate measured conduct.

    python backend/scripts/build_nonanthropomorphized_month_personas.py
    python backend/scripts/build_nonanthropomorphized_month_personas.py \\
        --source /path/to/revision/final/personas \\
        --out backend/default_personas
"""
import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.nonanthropomorphized_personas import (  # noqa: E402
    default_source_dir,
    write_month_persona_sets,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source_dir(),
        help="Directory of month folders (YYYY-MM/<month>_cN.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=BACKEND_ROOT / "default_personas",
        help="Directory for personas_moltbook_conduct_<month>.json",
    )
    args = parser.parse_args()
    if args.source is None:
        raise SystemExit("Pass --source. The default moltbook-ddps personas directory was not found.")

    written = write_month_persona_sets(args.source, args.out)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
