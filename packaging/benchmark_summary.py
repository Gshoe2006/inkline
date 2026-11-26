#!/usr/bin/env python3
"""One markdown table from several `inkline.py --benchmark OUT.json` files (benchmark.yml's summary job).

    python3 packaging/benchmark_summary.py benchmark-*.json >> "$GITHUB_STEP_SUMMARY"
    python3 packaging/benchmark_summary.py results/        (every .json in a folder, and its subfolders)

Each file is a column, named after the file (benchmark-windows-latest.json is "windows-latest"). Rows are the
items, slowest first (by the slowest machine). Times are medians in seconds.
"""

import json
import os
import sys


def label(path):
    name = os.path.splitext(os.path.basename(path))[0]
    return name[len("benchmark-"):] if name.startswith("benchmark-") else name


def find(args):
    files = []
    for a in args:
        if os.path.isdir(a):
            for root, _dirs, names in os.walk(a):
                files += [os.path.join(root, n) for n in names if n.endswith(".json")]
        else:
            files.append(a)
    return sorted(files, key=label)


def markdown(reports):
    """reports: [(label, report dict)] -> the summary as markdown."""
    if not reports:
        return "## Benchmark\n\nNo results.\n"
    out = ["## Benchmark", "", "Median seconds per item; lower is faster. Pages are US Letter at "
           f"{reports[0][1].get('settings', {}).get('dpi', 300)} dpi.", "",
           "| machine | platform | CPUs | Python | Qt | inkline_fast |", "|---|---|---|---|---|---|"]
    for name, r in reports:
        m = r.get("machine", {})
        out.append(f"| {name} | {m.get('platform', '?')} ({m.get('machine', '?')}) | {m.get('cpu_count', '?')} | "
                   f"{m.get('python', '?')} | {m.get('qt', '?')} | {'yes' if m.get('inkline_fast') else 'no'} |")
    times = [{x["name"]: x["seconds"] for x in r.get("results", [])} for _n, r in reports]
    items = {k for t in times for k in t}
    rows = sorted(items, key=lambda k: (-max(t.get(k, 0) for t in times), k))
    out += ["", "| item | " + " | ".join(n for n, _r in reports) + " |", "|---|" + "---:|" * len(reports)]
    for k in rows:
        out.append(f"| {k} | " + " | ".join(f"{t[k]:.3f}" if k in t else "-" for t in times) + " |")
    totals = [sum(t.values()) for t in times]
    out.append("| **total** | " + " | ".join(f"**{v:.2f}**" for v in totals) + " |")
    return "\n".join(out) + "\n"


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    reports = []
    for f in find(args):
        with open(f, encoding="utf-8") as fh:
            reports.append((label(f), json.load(fh)))
    sys.stdout.write(markdown(reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
