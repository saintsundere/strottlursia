#!/usr/bin/env python3
"""Convert Claude Code session JSONL files to readable text transcripts."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

CLAUDE_PROJECTS_DIR = Path("/root/.claude/projects")


def find_sessions():
    """Find all session JSONL files across all projects."""
    sessions = []
    if not CLAUDE_PROJECTS_DIR.exists():
        return sessions

    for project_dir in sorted(CLAUDE_PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        for jsonl_file in sorted(project_dir.glob("*.jsonl")):
            first_line = None
            last_line = None
            line_count = 0
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        line_count += 1
                        parsed = json.loads(line)
                        if first_line is None:
                            first_line = parsed
                        last_line = parsed
            except (json.JSONDecodeError, IOError):
                continue

            if first_line is None:
                continue

            timestamp = first_line.get("timestamp", "unknown")
            end_timestamp = last_line.get("timestamp", "unknown") if last_line else timestamp
            project_name = project_dir.name
            session_id = first_line.get("sessionId", jsonl_file.stem)
            first_msg = ""
            if first_line.get("type") == "user":
                msg = first_line.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, str):
                    first_msg = content[:80]
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            first_msg = block["text"][:80]
                            break

            sessions.append({
                "path": jsonl_file,
                "project": project_name,
                "session_id": session_id,
                "timestamp": timestamp,
                "end_timestamp": end_timestamp,
                "first_msg": first_msg,
                "line_count": line_count,
            })

    return sessions


def extract_text_content(content):
    """Pull readable text from a message content field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block["text"])
                elif block.get("type") == "thinking":
                    pass  # skip thinking blocks
                elif block.get("type") == "tool_use":
                    name = block.get("name", "unknown_tool")
                    inp = block.get("input", {})
                    if name == "Bash":
                        parts.append(f"[Tool: {name}] {inp.get('command', '')}")
                    elif name == "Read":
                        parts.append(f"[Tool: {name}] {inp.get('file_path', '')}")
                    elif name in ("Edit", "Write"):
                        parts.append(f"[Tool: {name}] {inp.get('file_path', '')}")
                    elif name == "WebFetch":
                        parts.append(f"[Tool: {name}] {inp.get('url', '')}")
                    else:
                        parts.append(f"[Tool: {name}]")
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str) and result_content.strip():
                        parts.append(f"[Result]: {result_content[:500]}")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content) if content else ""


def convert_session(jsonl_path, output_path=None):
    """Convert a session JSONL file to a readable text transcript."""
    lines = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not lines:
        print("No data found in session file.")
        return None

    meta = lines[0]
    session_id = meta.get("sessionId", "unknown")
    timestamp = meta.get("timestamp", "unknown")

    out = []
    out.append("=" * 70)
    out.append(f"CLAUDE CODE SESSION TRANSCRIPT")
    out.append(f"Session ID: {session_id}")
    out.append(f"Started:    {timestamp}")
    out.append(f"Project:    {meta.get('cwd', 'unknown')}")
    out.append(f"Branch:     {meta.get('gitBranch', 'unknown')}")
    out.append("=" * 70)
    out.append("")

    for entry in lines:
        entry_type = entry.get("type")
        ts = entry.get("timestamp", "")
        try:
            ts_short = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M:%S")
        except (ValueError, AttributeError):
            ts_short = ""

        if entry_type == "user":
            msg = entry.get("message", {})
            content = extract_text_content(msg.get("content", ""))
            if content.strip():
                out.append(f"[{ts_short}] USER:")
                out.append(content.strip())
                out.append("")

        elif entry_type == "assistant":
            msg = entry.get("message", {})
            content = extract_text_content(msg.get("content", ""))
            if content.strip():
                out.append(f"[{ts_short}] ASSISTANT:")
                out.append(content.strip())
                out.append("")

        elif entry_type == "tool_result":
            msg = entry.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                preview = content.strip()[:1000]
                out.append(f"[{ts_short}] TOOL OUTPUT:")
                out.append(preview)
                if len(content.strip()) > 1000:
                    out.append(f"  ... ({len(content.strip())} chars total)")
                out.append("")

    transcript = "\n".join(out)

    if output_path is None:
        output_path = jsonl_path.with_suffix(".txt")
    else:
        output_path = Path(output_path)

    with open(output_path, "w") as f:
        f.write(transcript)

    return output_path


def main():
    sessions = find_sessions()

    if not sessions:
        print("No Claude Code sessions found.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  CLAUDE CODE SESSION SELECTOR")
    print("=" * 60 + "\n")

    for i, s in enumerate(sessions, 1):
        try:
            dt = datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00"))
            ts_display = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            ts_display = s["timestamp"]

        preview = s["first_msg"] if s["first_msg"] else "(no preview)"
        print(f"  [{i}] {ts_display}")
        print(f"      Project:  {s['project']}")
        print(f"      Messages: ~{s['line_count']} entries")
        print(f"      Preview:  {preview}")
        print()

    while True:
        try:
            choice = input("Select a session number (or 'q' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)

        if choice.lower() == "q":
            sys.exit(0)

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                break
            print(f"Please enter a number between 1 and {len(sessions)}.")
        except ValueError:
            print("Invalid input. Enter a number or 'q'.")

    selected = sessions[idx]
    print(f"\nConverting session: {selected['session_id'][:12]}...")

    output_file = convert_session(selected["path"])
    if output_file:
        print(f"\nTranscript saved to: {output_file}")
        print(f"File size: {output_file.stat().st_size:,} bytes")

        copy_dest = Path("/home/user/strottlursia/Projects") / output_file.name
        try:
            import shutil
            shutil.copy2(output_file, copy_dest)
            print(f"Also copied to:     {copy_dest}")
        except IOError:
            pass
    else:
        print("Conversion failed.")


if __name__ == "__main__":
    main()
