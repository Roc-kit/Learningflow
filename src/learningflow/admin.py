from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .bridge import parse_record_packet, render_context_packet
from .runtime import service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Learningflow local maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure = subparsers.add_parser("ensure-student", help="Create a local student if missing")
    ensure.add_argument("--id", required=True, dest="student_id")
    ensure.add_argument("--name", required=True, dest="display_name")
    ensure.add_argument("--mode", choices=["test", "real"], required=True, dest="data_mode")
    ensure.add_argument("--timezone", default="Asia/Shanghai", dest="timezone_name")

    context = subparsers.add_parser("context", help="Print current bounded learning context")
    context.add_argument("--id", required=True, dest="student_id")
    context.add_argument("--mode", choices=["test", "real"], required=True, dest="data_mode")
    context.add_argument("--focus")
    context.add_argument("--limit", type=int, default=8)

    packet = subparsers.add_parser(
        "context-packet", help="Render a compact packet for pasting into ChatGPT"
    )
    packet.add_argument("--id", required=True, dest="student_id")
    packet.add_argument("--mode", choices=["test", "real"], required=True, dest="data_mode")
    packet.add_argument("--focus")
    packet.add_argument("--limit", type=int, default=8)

    record = subparsers.add_parser(
        "record-packet", help="Persist a JSON evidence packet copied from ChatGPT"
    )
    record.add_argument(
        "--file",
        default="-",
        help="JSON file to read; '-' reads stdin",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "ensure-student":
        result = service().ensure_student(
            student_id=args.student_id,
            display_name=args.display_name,
            data_mode=args.data_mode,
            timezone_name=args.timezone_name,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command in {"context", "context-packet"}:
        result = service().get_learning_context(
            student_id=args.student_id,
            data_mode=args.data_mode,
            focus=args.focus,
            limit=args.limit,
        )
        if args.command == "context-packet":
            print(render_context_packet(result), end="")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    payload = parse_record_packet(text)
    result = service().record_assessment_run(**payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
