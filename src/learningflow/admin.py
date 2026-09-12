from __future__ import annotations

import argparse
import json

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
    else:
        result = service().get_learning_context(
            student_id=args.student_id,
            data_mode=args.data_mode,
            focus=args.focus,
            limit=args.limit,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
