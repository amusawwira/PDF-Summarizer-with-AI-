"""Export helpers for transcripts and summaries."""
from __future__ import annotations

from datetime import datetime


def transcript_markdown(messages, doc_name: str = "document") -> str:
    lines = [f"# Chat transcript — {doc_name}", "",
             f"_Exported {datetime.now().strftime('%Y-%m-%d %H:%M')}_", ""]
    for m in messages:
        role = "You" if m["role"] == "user" else "Assistant"
        lines.append(f"## {role}")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines)
