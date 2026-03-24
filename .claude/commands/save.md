---
description: Print current chat session as copyable text block
allowed-tools: Bash, Read
---

1. Run the save script, redirecting output to a temp file:

```bash
python3 /home/l4nd0/tenn/scripts/save-chat.py > /tmp/claude-session-export.txt 2>&1 && echo "OK"
```

The script now prefers the live Claude session transcript when available and falls back to Cockpit's latest `reports/cockpit/exports/claude_context.json` export if the transcript is unavailable.

2. Use the Read tool to read `/tmp/claude-session-export.txt`.

3. In your response, paste the **full file contents** verbatim inside a fenced code block like this:

```text
<full contents here>
```

Do not summarise. Do not truncate. Paste everything verbatim between the triple backticks so the user gets a single selectable/copyable block.
