from __future__ import annotations

import json
from pathlib import Path

from pipeline.graph import get_pipeline


def run_pipeline(file_path: str, file_type: str) -> None:
    print(f"\n🚀 Starting Fire Safety Pipeline")
    print(f"   File: {file_path}")
    print(f"   Type: {file_type}\n")

    pipeline = get_pipeline()

    initial_state = {
        "input_file_path": file_path,
        "input_file_type": file_type,
        "rooms": [],
        "building_summary": {},
        "occupancy_classification": {},
        "hazard_map": [],
        "code_analysis": [],
        "system_design": [],
        "hydraulic_design": {},
        "compliance_report": {},
        "report_path": "",
        "current_agent": "start",
        "errors": [],
        "warnings": [],
    }

    result = pipeline.invoke(initial_state)

    print(f"✅ Pipeline complete!")
    print(f"   Current agent: {result.get('current_agent')}")
    print(f"   Rooms processed: {len(result.get('rooms', []))}")
    print(f"   Compliance score: {result.get('compliance_report', {}).get('compliance_score', 'N/A')}")
    print(f"   Report saved to: {result.get('report_path', 'N/A')}")

    errors = result.get("errors", [])
    if errors:
        print(f"\n⚠️  Errors encountered ({len(errors)}):")
        for error in errors:
            print(f"   - {error}")

    # Save full output JSON for debugging
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "pipeline_output.json", "w", encoding="utf-8") as f:
        # Exclude non-serializable fields if any
        serializable = {k: v for k, v in result.items()}
        json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)
    print(f"   Debug JSON: output/pipeline_output.json")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python main.py <file_path> <file_type>")
        print("Example: python main.py sample.dxf dxf")
        print("Example: python main.py floorplan.pdf pdf")
        sys.exit(1)

    run_pipeline(sys.argv[1], sys.argv[2])