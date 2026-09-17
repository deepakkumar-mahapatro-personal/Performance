import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.table import Table


EXECUTION_ID = "item-CIG_DTS-20260819T141311Z"
ENTITY = "item-CIG_DTS"


def build_summary_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    components = {}
    for row in rows:
        component = row["component_name"]
        if component not in components:
            components[component] = {
                "replicas": int(row["replica_count"]),
                "cpu_avg": None,
                "cpu_peak": None,
                "mem_avg": None,
                "mem_peak": None,
            }

        metric_name = row["metric_name"]
        if metric_name == "CPU Usage (%)":
            components[component]["cpu_avg"] = float(row["average"])
            components[component]["cpu_peak"] = float(row["peak_value"])
        elif metric_name == "Memory Usage (%)":
            components[component]["mem_avg"] = float(row["average"])
            components[component]["mem_peak"] = float(row["peak_value"])

    summary = [
        {
            "component": name,
            "replicas": values["replicas"],
            "cpu_avg": values["cpu_avg"],
            "cpu_peak": values["cpu_peak"],
            "mem_avg": values["mem_avg"],
            "mem_peak": values["mem_peak"],
        }
        for name, values in components.items()
    ]

    summary.sort(key=lambda item: (item["cpu_avg"] is None, -(item["cpu_avg"] or 0)))
    return summary


def make_report_pdf(summary, output_path: Path):
    dts = next((row for row in summary if row["component"] == "dts"), None)

    with PdfPages(str(output_path)) as pdf:
        # Page 1: Executive summary
        fig = plt.figure(figsize=(11.7, 16.5))
        fig.patch.set_facecolor("#f7f9fc")

        fig.text(0.06, 0.96, "Executive Technical Performance Report", fontsize=26, fontweight="bold")
        fig.text(0.06, 0.92, f"Entity: {ENTITY} | Execution: {EXECUTION_ID}", fontsize=12, color="#4d4d4d")

        status_ax = fig.add_axes([0.06, 0.80, 0.24, 0.08])
        status_ax.axis("off")
        status_ax.set_facecolor("#d9f2e3")
        status_ax.text(0.5, 0.5, "STATUS: STABLE", ha="center", va="center", fontsize=18, fontweight="bold", color="#14532d")

        fig.text(0.32, 0.84, "Executive Summary", fontsize=16, fontweight="bold")
        exec_points = [
            "• Overall workload performance remains stable across the execution window.",
            "• CPU demand is concentrated in the dts component, which is the primary capacity hotspot.",
            "• Memory usage is contained and does not indicate current memory saturation risk.",
            "• No broad systemic bottleneck was identified; the main operational focus is CPU headroom in dts.",
        ]
        for idx, line in enumerate(exec_points):
            fig.text(0.32, 0.80 - idx * 0.05, line, fontsize=11, va="center")

        table_data = [["Component", "Replicas", "Avg CPU %", "Peak CPU %", "Avg Mem %", "Peak Mem %"]]
        for row in summary:
            table_data.append([
                row["component"],
                str(row["replicas"]),
                f"{row['cpu_avg']:.2f}" if row["cpu_avg"] is not None else "N/A",
                f"{row['cpu_peak']:.2f}" if row["cpu_peak"] is not None else "N/A",
                f"{row['mem_avg']:.2f}" if row["mem_avg"] is not None else "N/A",
                f"{row['mem_peak']:.2f}" if row["mem_peak"] is not None else "N/A",
            ])

        table_ax = fig.add_axes([0.06, 0.35, 0.88, 0.40])
        table_ax.axis("off")
        table = Table(table_ax, cellText=table_data[1:], colLabels=table_data[0], cellLoc="center", loc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.15, 2.4)
        for (row_idx, _), cell in table.get_celld().items():
            cell.set_linewidth(0.8)
            cell.set_edgecolor("#b0bec9")
            if row_idx == 0:
                cell.set_facecolor("#dfeaf7")
                cell.set_text_props(fontweight="bold")
            elif row_idx % 2 == 1:
                cell.set_facecolor("#f5f7fa")
        table_ax.add_table(table)

        risk_ax = fig.add_axes([0.06, 0.18, 0.88, 0.12])
        risk_ax.axis("off")
        risk_ax.set_facecolor("#fff5e0")
        risk_ax.text(0.02, 0.68, "Primary Risk Area", fontsize=14, fontweight="bold", color="#8a4b00")
        if dts:
            risk_ax.text(
                0.02,
                0.28,
                (
                    f"dts is the dominant compute component with an average CPU utilization of {dts['cpu_avg']:.2f}% and a peak of {dts['cpu_peak']:.2f}%. "
                    "This is the main potential constraint for throughput during higher-demand periods."
                ),
                fontsize=11,
                color="#4d2d00",
                va="center",
                wrap=True,
            )

        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: technical detail and recommendation
        fig2 = plt.figure(figsize=(11.7, 16.5))
        fig2.patch.set_facecolor("#ffffff")
        fig2.text(0.06, 0.96, "Technical Detail and Recommendation", fontsize=24, fontweight="bold")

        labels = [row["component"] for row in summary]
        cpu_values = [row["cpu_avg"] for row in summary]
        mem_values = [row["mem_avg"] for row in summary]

        ax1 = fig2.add_axes([0.08, 0.52, 0.82, 0.34])
        ax1.bar(labels, cpu_values, color=["#4c78a8" if label != "dts" else "#d62728" for label in labels])
        ax1.set_title("Average CPU Usage by Component (%)", fontsize=13, fontweight="bold")
        ax1.set_ylabel("CPU %")
        ax1.set_ylim(0, max(max(cpu_values) * 1.25 if cpu_values else 10, 10))
        for idx, value in enumerate(cpu_values):
            if value is not None:
                ax1.text(idx, value + 0.8, f"{value:.2f}", ha="center", va="bottom", fontsize=9)

        ax2 = fig2.add_axes([0.08, 0.12, 0.82, 0.34])
        ax2.bar(labels, mem_values, color=["#66a61e" if label != "dts" else "#f0ad4e" for label in labels])
        ax2.set_title("Average Memory Usage by Component (%)", fontsize=13, fontweight="bold")
        ax2.set_ylabel("Memory %")
        ax2.set_ylim(0, max(max(mem_values) * 1.25 if mem_values else 60, 60))
        for idx, value in enumerate(mem_values):
            if value is not None:
                ax2.text(idx, value + 0.7, f"{value:.2f}", ha="center", va="bottom", fontsize=9)

        rec_ax = fig2.add_axes([0.08, 0.02, 0.82, 0.08])
        rec_ax.axis("off")
        rec_ax.text(0.0, 0.55, "Recommendation", fontsize=14, fontweight="bold", color="#1f2d3d")
        rec_ax.text(
            0.0,
            0.10,
            "1) Prioritize dts CPU optimization and validate scaling headroom. 2) Maintain monitoring for sustained CPU above 45%. 3) Continue to track memory and replica counts, but treat memory as a secondary concern for this execution.",
            fontsize=10,
            va="center",
            color="#2d3b4f",
            wrap=True,
        )

        pdf.savefig(fig2)
        plt.close(fig2)


def main():
    root = Path(__file__).resolve().parent
    csv_path = root / "output" / EXECUTION_ID / "aggregated" / ENTITY / "entity-summary.csv"
    output_dir = root / "output" / EXECUTION_ID / "reports" / ENTITY
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{EXECUTION_ID}_Executive_Report.pdf"

    if not csv_path.exists():
        raise FileNotFoundError(f"Summary CSV not found: {csv_path}")

    summary = build_summary_rows(csv_path)
    make_report_pdf(summary, output_path)
    print(f"Created PDF report: {output_path}")


if __name__ == "__main__":
    main()
