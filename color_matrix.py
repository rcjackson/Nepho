"""Render a color matrix (model x day) of DQ severities from report JSON files.

Each DQ report (see :mod:`dq_pipeline`) contains a list of days, and each day
holds one verdict per model with a ``severity`` of ``Good``, ``Indeterminate``,
or ``Bad`` (or no verdict when the day was skipped / had no quicklook image).

This script reads one or more such reports and draws a grid with one row per
model and one column per day, where each cell is colored by that day's
severity. It writes a PNG (via matplotlib) and also prints an ANSI-colored
version to the terminal.

Usage:
    python color_matrix.py [report*.json ...] [-o matrix.png]

With no file arguments it defaults to every ``report*.json`` in the cwd.
"""

import argparse
import glob
import json
import sys
from collections import OrderedDict

# Severity -> (hex color for PNG, ANSI background code for terminal, short label)
_SEVERITY_STYLE = OrderedDict(
    [
        ("Good", ("#2ca02c", 42, "G")),          # green
        ("Indeterminate", ("#f0c000", 43, "I")),  # yellow
        ("Bad", ("#d62728", 41, "B")),            # red
        ("No data", ("#cccccc", 100, ".")),       # gray (skipped / missing)
    ]
)
_NO_DATA = "No data"


def _verdict_severity(day):
    """Return the canonical severity string for one day entry.

    Falls back to ``"No data"`` when the day was skipped, had no verdicts, or
    the verdict's severity is missing/unrecognized.
    """
    if day.get("skipped") or not day.get("verdicts"):
        return _NO_DATA
    # A day may carry one verdict per model; this is resolved per-model by the
    # caller, so here we just take the first as a sensible default.
    severity = day["verdicts"][0].get("severity")
    return severity if severity in _SEVERITY_STYLE else _NO_DATA


def load_reports(paths):
    """Parse report files into ``(days, matrix)``.

    ``days`` is the sorted union of all day strings across reports. ``matrix``
    maps ``model_name -> {day -> severity}``.
    """
    days = set()
    matrix = OrderedDict()  # model -> {day -> severity}

    for path in paths:
        try:
            report = json.load(open(path))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warning: skipping {path}: {exc}", file=sys.stderr)
            continue

        # Models declared in the report; fall back to the filename.
        report_models = report.get("models") or [path]
        for model in report_models:
            matrix.setdefault(model, {})

        for day in report.get("days", []):
            day_name = day.get("day")
            if not day_name:
                continue
            days.add(day_name)

            verdicts = day.get("verdicts") or []
            if verdicts:
                # Assign each verdict to its own model row.
                for verdict in verdicts:
                    model = verdict.get("model_name") or report_models[0]
                    sev = verdict.get("severity")
                    matrix.setdefault(model, {})[day_name] = (
                        sev if sev in _SEVERITY_STYLE else _NO_DATA
                    )
            else:
                # Skipped / no image: mark every model in this report.
                for model in report_models:
                    matrix[model].setdefault(day_name, _NO_DATA)

    return sorted(days), matrix


def print_terminal_matrix(days, matrix):
    """Print an ANSI-colored matrix to stdout."""
    if not matrix:
        print("No data to display.")
        return

    label_w = max(len(m) for m in matrix)
    # Legend
    legend = "  ".join(
        f"\033[{ansi}m {lbl} \033[0m={name}"
        for name, (_hex, ansi, lbl) in _SEVERITY_STYLE.items()
    )
    print("Legend:", legend)
    print()

    # Column header: day-of-month (last two chars) to keep it narrow.
    header = " " * label_w + " " + " ".join(d[-2:] for d in days)
    print(header)

    for model, row in matrix.items():
        cells = []
        for d in days:
            sev = row.get(d, _NO_DATA)
            _hex, ansi, lbl = _SEVERITY_STYLE[sev]
            cells.append(f"\033[{ansi}m{lbl} \033[0m")
        print(f"{model.ljust(label_w)} " + " ".join(cells))


def render_png(days, matrix, out_path):
    """Render the matrix to a PNG using matplotlib. Returns the path or None."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
    except ImportError:
        print("matplotlib not available; skipping PNG output.", file=sys.stderr)
        return None

    severities = list(_SEVERITY_STYLE)
    sev_index = {s: i for i, s in enumerate(severities)}
    colors = [_SEVERITY_STYLE[s][0] for s in severities]
    cmap = ListedColormap(colors)

    models = list(matrix)
    grid = [
        [sev_index[matrix[m].get(d, _NO_DATA)] for d in days] for m in models
    ]

    fig_w = max(6, 0.5 * len(days) + 3)
    fig_h = max(2, 0.5 * len(models) + 2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=len(severities) - 1, aspect="auto")

    ax.set_xticks(range(len(days)))
    ax.set_xticklabels(days, rotation=90, fontsize=8)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models, fontsize=9)

    # Gridlines between cells.
    ax.set_xticks([x - 0.5 for x in range(len(days) + 1)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(len(models) + 1)], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", length=0)

    legend_handles = [
        mpatches.Patch(color=_SEVERITY_STYLE[s][0], label=s) for s in severities
    ]
    ax.legend(
        handles=legend_handles,
        bbox_to_anchor=(1.01, 1),
        loc="upper left",
        fontsize=8,
        title="Severity",
    )

    ax.set_title("DQ severity by model and day")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="*",
        help="Report JSON files (default: report*.json in cwd).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="dq_color_matrix.png",
        help="Output PNG path (default: dq_color_matrix.png).",
    )
    parser.add_argument(
        "--no-png",
        action="store_true",
        help="Skip PNG rendering; terminal output only.",
    )
    args = parser.parse_args(argv)

    paths = args.files or sorted(glob.glob("report*.json"))
    if not paths:
        parser.error("no report files found (pass paths or add report*.json)")

    days, matrix = load_reports(paths)
    if not days:
        print("No day entries found in the given reports.", file=sys.stderr)
        return 1

    print_terminal_matrix(days, matrix)

    if not args.no_png:
        out = render_png(days, matrix, args.output)
        if out:
            print(f"\nWrote {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
