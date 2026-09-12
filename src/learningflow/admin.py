from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .bridge import parse_record_packet, render_context_packet
from .config import data_dir
from .evidence_compiler import run_codex_selector, selection_to_record_packet
from .runtime import service
from .transcripts import CodexTranscriptAdapter


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

    sessions = subparsers.add_parser("codex-sessions", help="List locally available Codex chats")
    sessions.add_argument("--limit", type=int, default=20)

    transcript = subparsers.add_parser(
        "codex-transcript", help="Export visible user/assistant messages from one Codex chat"
    )
    transcript_group = transcript.add_mutually_exclusive_group(required=True)
    transcript_group.add_argument("--session-id")
    transcript_group.add_argument("--latest", action="store_true")
    transcript.add_argument("--output", help="Optional JSON output path; defaults to stdout")

    sync = subparsers.add_parser(
        "sync-codex", help="Normalize Codex chats into local Learningflow transcript files"
    )
    sync.add_argument("--limit", type=int)

    compile_codex = subparsers.add_parser(
        "compile-codex", help="Use Codex to extract a reviewable Evidence Packet from one chat"
    )
    compile_group = compile_codex.add_mutually_exclusive_group(required=True)
    compile_group.add_argument("--session-id")
    compile_group.add_argument("--latest", action="store_true")
    compile_codex.add_argument("--student-id", required=True)
    compile_codex.add_argument("--mode", choices=["test", "real"], required=True, dest="data_mode")
    compile_codex.add_argument("--write", action="store_true", help="Persist after compilation")
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

    if args.command == "codex-sessions":
        rows = CodexTranscriptAdapter().list_sessions(limit=args.limit)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if args.command == "codex-transcript":
        adapter = CodexTranscriptAdapter()
        session_id = adapter.latest_session_id() if args.latest else args.session_id
        result = adapter.read_session(session_id)
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return

    if args.command == "sync-codex":
        destination = data_dir() / "transcripts" / "codex"
        result = CodexTranscriptAdapter().sync(destination, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "compile-codex":
        adapter = CodexTranscriptAdapter()
        session_id = adapter.latest_session_id() if args.latest else args.session_id
        transcript = adapter.read_session(session_id)
        selection = run_codex_selector(transcript)
        packet = selection_to_record_packet(
            transcript,
            selection,
            student_id=args.student_id,
            data_mode=args.data_mode,
        )
        if packet is None:
            print(json.dumps({"status": "no_learning_evidence", "selection": selection}, ensure_ascii=False, indent=2))
            return
        if not args.write:
            print(json.dumps({"status": "review", "record_packet": packet}, ensure_ascii=False, indent=2))
            return
        saved = service().record_assessment_run(**packet)
        print(json.dumps({"status": "saved", "record_packet": packet, "result": saved}, ensure_ascii=False, indent=2))
        return

    text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    payload = parse_record_packet(text)
    result = service().record_assessment_run(**payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
