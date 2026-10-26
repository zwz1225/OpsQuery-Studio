"""Standalone HTML reports for recorded benchmark traces."""

from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
from typing import Any

from evaluation.trace import EvaluationTrace
from evaluation.trace_visualizer import TraceVisualizer


DEFAULT_TRACE_DIR = Path(__file__).resolve().parent / "results" / "traces"


def _display(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class TraceReportBuilder:
    """Render the visualization nodes as a readable, self-contained timeline."""

    @staticmethod
    def render_html(
        trace: EvaluationTrace | dict[str, Any] | None,
        *,
        case_id: str = "",
        question: str = "",
    ) -> str:
        visual = TraceVisualizer.visualize(trace)
        trace_data = trace.to_dict() if isinstance(trace, EvaluationTrace) else trace
        has_trace = isinstance(trace_data, dict) and any(bool(value) for value in trace_data.values())
        cards: list[str] = []
        for node in visual["nodes"]:
            status = node["status"]
            metrics = node["metrics"]
            latency = (
                escape(_display(node["latency_ms"])) + " ms"
                if node["latency_ms"] is not None else "N/A"
            )
            details: list[str] = [
                '<div class="detail"><dt>Latency</dt><dd>' + latency + "</dd></div>"
            ]
            for key, value in metrics.items():
                label = key.replace("_", " ").title()
                if key == "generated_sql":
                    content = "<pre class=\"sql\"><code>" + escape(_display(value)) + "</code></pre>"
                elif isinstance(value, (dict, list)):
                    content = "<pre>" + escape(_display(value)) + "</pre>"
                else:
                    content = escape(_display(value))
                details.append(
                    "<div class=\"detail\"><dt>" + escape(label)
                    + "</dt><dd>" + content + "</dd></div>"
                )
            cards.append(
                f'<li class="node status-{status}">'
                '<div class="node-head"><h2>' + escape(node["name"]) + "</h2>"
                f'<span class="badge">{escape(status.upper())}</span></div>'
                '<p class="summary">' + escape(node["summary"]) + "</p>"
                + ("<dl>" + "".join(details) + "</dl>" if details else "")
                + "</li>"
            )
        notice = (
            '<p class="notice">No recorded EvaluationTrace is available for this case. '
            'Skipped stages are shown below.</p>' if not has_trace else ""
        )
        return "\n".join([
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>AskData Studio Trace Report</title>",
            "<style>",
            ":root{font-family:system-ui,Segoe UI,sans-serif;color:#17212b;background:#f5f7fa}",
            "body{max-width:900px;margin:0 auto;padding:32px 20px}",
            "h1{font-size:1.8rem;margin:0 0 20px}h2{font-size:1.15rem;margin:0}",
            ".query,.notice{background:white;border-radius:10px;padding:16px;margin:0 0 22px}",
            ".notice{border-left:5px solid #64748b}",
            ".timeline{list-style:none;margin:0;padding:0}",
            ".node{position:relative;background:white;border:1px solid #dce4ed;"
            "border-left:6px solid #94a3b8;border-radius:10px;padding:18px;margin:0 0 34px}",
            ".node:not(:last-child)::after{content:'↓';position:absolute;left:50%;bottom:-31px;"
            "font-size:22px;color:#64748b}",
            ".status-success{border-left-color:#15803d}.status-failed{border-left-color:#b91c1c;"
            "background:#fff5f5}.status-pending{border-left-color:#b45309}",
            ".node-head{display:flex;justify-content:space-between;gap:12px;align-items:center}",
            ".badge{font-size:.76rem;font-weight:700;letter-spacing:.06em;padding:5px 9px;"
            "border-radius:20px;background:#e2e8f0}",
            ".status-success .badge{background:#dcfce7;color:#166534}",
            ".status-failed .badge{background:#fee2e2;color:#991b1b}",
            ".status-pending .badge{background:#fef3c7;color:#92400e}",
            ".summary{margin:12px 0;overflow-wrap:anywhere}",
            "dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}",
            ".detail{background:#f8fafc;padding:10px;border-radius:7px;min-width:0}",
            "dt{font-size:.78rem;color:#475569;text-transform:capitalize}",
            "dd{margin:5px 0 0;overflow-wrap:anywhere}pre{white-space:pre-wrap;"
            "overflow-wrap:anywhere;margin:4px 0 0;font-size:.85rem}",
            "</style>",
            "</head>",
            "<body>",
            "<h1>AskData Studio Trace Report</h1>",
            '<section class="query"><strong>Case:</strong> ' + escape(case_id)
            + '<br><strong>User Query:</strong> ' + escape(question or "Not recorded") + "</section>",
            notice,
            '<ol class="timeline">',
            *cards,
            "</ol>",
            "</body></html>",
            "",
        ])

    @staticmethod
    def _filename(case_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", case_id).strip("_") or "case"
        if safe != case_id:
            safe += "_" + hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:8]
        return f"trace_{safe}.html"

    @classmethod
    def write_case(cls, case: dict[str, Any], output_dir: Path | str = DEFAULT_TRACE_DIR) -> Path:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        case_id = str(case.get("case_id") or "unknown")
        trace = case.get("trace")
        trace = trace if isinstance(trace, (EvaluationTrace, dict)) else {}
        question = str(case.get("query") or case.get("question") or "")
        path = output / cls._filename(case_id)
        path.write_text(cls.render_html(trace, case_id=case_id, question=question), encoding="utf-8")
        return path

    @classmethod
    def write_reports(
        cls, benchmark_json: Path | str, output_dir: Path | str = DEFAULT_TRACE_DIR,
    ) -> list[Path]:
        payload = json.loads(Path(benchmark_json).read_text(encoding="utf-8"))
        cases = payload.get("cases") if isinstance(payload, dict) else None
        if not isinstance(cases, list):
            raise ValueError("Benchmark JSON must contain a cases list")
        seen: set[str] = set()
        paths: list[Path] = []
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError("Each benchmark case must be an object")
            case_id = str(case.get("case_id") or "unknown")
            filename = cls._filename(case_id)
            if filename in seen:
                raise ValueError(f"Duplicate trace report filename: {filename}")
            seen.add(filename)
            paths.append(cls.write_case(case, output_dir))
        return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Render EvaluationTrace timelines from benchmark JSON")
    parser.add_argument("--input", type=Path, required=True, help="Existing benchmark JSON file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TRACE_DIR)
    args = parser.parse_args()
    paths = TraceReportBuilder.write_reports(args.input, args.output_dir)
    print(f"trace reports: {len(paths)} written to {args.output_dir}")


if __name__ == "__main__":
    main()
