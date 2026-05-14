"""
Converts Claude Code session JSONL files into readable text transcripts.

USAGE — paste this into any Claude Code chat:

    Run the transcript converter: python3 convert-session.py

It will find all sessions and let you pick one, or convert the most recent.
You can also point it at a specific file:

    python3 convert-session.py path/to/session.jsonl
"""

import json
import datetime
import glob
import os
import sys


def find_sessions():
    home = os.path.expanduser("~")
    patterns = [
        os.path.join(home, ".claude", "projects", "*", "*.jsonl"),
        os.path.join(home, ".claude", "sessions", "*", "*.jsonl"),
        os.path.join(home, ".claude", "sessions", "*.jsonl"),
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    files.sort(key=os.path.getmtime, reverse=True)
    return files


def convert(jsonl_path):
    with open(jsonl_path, encoding="utf-8") as f:
        lines = f.readlines()

    output = []
    output.append("CLAUDE CODE SESSION TRANSCRIPT")
    output.append("=" * 50)

    first_ts = ""
    for line in lines:
        try:
            entry = json.loads(line.strip())
            ts = entry.get("timestamp", "")
            if ts and not first_ts:
                first_ts = ts
        except:
            pass

    if first_ts:
        try:
            dt = datetime.datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            output.append(f"Date: {dt.strftime('%Y-%m-%d %H:%M')}")
        except:
            pass

    output.append(f"Source: {os.path.basename(jsonl_path)}")
    output.append("")

    for line in lines:
        try:
            entry = json.loads(line.strip())
            msg = entry.get("message", {})
            role = msg.get("role", "")
            timestamp = entry.get("timestamp", "")

            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif part.get("type") == "tool_use":
                            name = part.get("name", "unknown")
                            text_parts.append(f"  [Used tool: {name}]")
                    elif isinstance(part, str):
                        text_parts.append(part)
                text = "\n".join(t for t in text_parts if t.strip())
            elif isinstance(content, str):
                text = content
            else:
                text = ""

            if not text.strip():
                continue

            time_str = ""
            if timestamp:
                try:
                    dt = datetime.datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    )
                    time_str = f" ({dt.strftime('%H:%M')})"
                except:
                    pass

            if role == "user":
                label = "YOU"
            elif role == "assistant":
                label = "CLAUDE"
            else:
                label = role.upper() if role else "SYSTEM"

            output.append(f"--- {label}{time_str} ---")

            if len(text) > 5000:
                text = text[:5000] + "\n... [trimmed for length]"
            output.append(text)
            output.append("")
        except:
            pass

    return "\n".join(output)


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.exists(path):
            print(f"File not found: {path}")
            sys.exit(1)
        sessions = [path]
    else:
        sessions = find_sessions()
        if not sessions:
            print("No session files found in ~/.claude/")
            print("This script looks for .jsonl files in:")
            print("  ~/.claude/projects/*/")
            print("  ~/.claude/sessions/")
            sys.exit(1)

    print(f"Found {len(sessions)} session(s).\n")

    if len(sessions) == 1:
        pick = sessions[0]
    else:
        print("Most recent sessions:")
        for i, s in enumerate(sessions[:10]):
            mod = datetime.datetime.fromtimestamp(os.path.getmtime(s))
            size = os.path.getsize(s)
            print(f"  [{i + 1}] {mod.strftime('%Y-%m-%d %H:%M')}  ({size:,} bytes)  {os.path.basename(s)}")
        print(f"\nPress Enter for most recent, or type a number (1-{min(10, len(sessions))}):")

        try:
            choice = input("> ").strip()
        except EOFError:
            choice = ""

        if choice == "":
            pick = sessions[0]
        else:
            try:
                idx = int(choice) - 1
                pick = sessions[idx]
            except:
                print("Invalid choice")
                sys.exit(1)

    print(f"Converting: {pick}")
    result = convert(pick)

    out_name = os.path.splitext(os.path.basename(pick))[0] + "-transcript.txt"
    out_path = os.path.join(os.getcwd(), out_name)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"Saved to: {out_path}")
    print(f"({len(result):,} characters)")


if __name__ == "__main__":
    main()
