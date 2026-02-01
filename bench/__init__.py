"""SV-Bench metrics and report generation."""

__version__ = "0.1.0"

from .report import (
    compute_e1_metrics,
    compute_e2_metrics,
    generate_report_md,
    generate_summary,
    load_results,
)

__all__ = [
    "compute_e1_metrics",
    "compute_e2_metrics",
    "generate_summary",
    "generate_report_md",
    "load_results",
]
