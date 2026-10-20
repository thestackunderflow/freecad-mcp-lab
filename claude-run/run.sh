#!/usr/bin/env bash
# One logged, headless Claude Code run: the same prompt, model and budget for both arms.
#   bash claude-run/run.sh freecad|solidcraft RUN_ID
# Claude Code --stdio--> docker run -i ... [mcp_log_proxy.py --stdio--> the arm's MCP server]
# Only that server's MCP tools are allowed: no built-in tools, no other servers. Clean: no user CLAUDE.md, no user
# settings, no auto-memory. (12 earlier runs loaded the owner's global CLAUDE.md: out/runs-pilot-primed*/, not evidence.)
set -euo pipefail
ARM=$1; RUN=$2
cd "$(dirname "$0")/.."
LAB="$(pwd -W 2>/dev/null || pwd)"
OUT=out/runs/$ARM-$RUN
mkdir -p "$OUT"; rm -f "$OUT"/*
MODEL="${MODEL:-claude-sonnet-5-5}"
BUDGET="${BUDGET:-1.50}"

if [ "$ARM" = freecad ]; then
  SERVER='"freecad-mcp-lab:1.1.4", "/opt/mcp/bin/python3", "/proxy/mcp_log_proxy.py", "--log", "/lab/out/transcript.jsonl", "--png-dir", "/lab/out", "--", "freecad-mcp", "--only-text-feedback"'
else
  SERVER='"freecad-mcp-lab-solidcraft:0.16.2", "python3", "/proxy/mcp_log_proxy.py", "--log", "/lab/out/transcript.jsonl", "--png-dir", "/lab/out", "--", "solidcraft-cli", "mcp", "--allow-path", "/lab/out"'
fi
cat > "$OUT/mcp-config.json" <<JSON
{"mcpServers": {"$ARM": {"command": "docker", "args": ["run", "-i", "--rm", "-v", "$LAB/proxy:/proxy:ro", "-v", "$LAB/$OUT:/lab/out", $SERVER]}}}
JSON

PROMPT="Use the $ARM MCP tools to model a wall bracket in millimetres. It is an L shape: a base plate and a back plate, both 4 mm thick. Put the corner at the origin: width along X, depth along Y, height along Z. The base plate is 60 mm deep and lies on the XY plane (Z from 0 to 4). The back plate stands at Y from 0 to 4 and is 50 mm tall overall. Drill two 5 mm holes through the back plate, 40 mm apart, centred across the width, with their centres 35 mm above the bottom. The width is 80 mm. Make the width a parameter, so that changing it keeps the holes centred. Export the part as STEP and STL to /lab/out/bracket-80.step and /lab/out/bracket-80.stl. Then change the width to 100 mm by changing that parameter, and export /lab/out/bracket-100.step and /lab/out/bracket-100.stl. Report the bounding box after each export and any step that failed."
printf '%s\n' "$PROMPT" > "$OUT/prompt.txt"

T0=$(date +%s)
set +e
MSYS_NO_PATHCONV=1 timeout 900 "${CLAUDE:-claude}" -p "$PROMPT" --model "$MODEL" \
  --mcp-config "$OUT/mcp-config.json" --strict-mcp-config \
  --tools "" --allowedTools "mcp__${ARM}__*" --permission-mode dontAsk \
  --max-budget-usd "$BUDGET" --no-session-persistence \
  --setting-sources project,local --settings '{"claudeMdExcludes":["**/.claude/CLAUDE.md"],"autoMemoryEnabled":false}' \
  --output-format json < /dev/null > "$OUT/claude-output.json"
RC=$?
set -e
# keep no host path in the saved config (the lab may be published): write $LAB instead
sed -i "s#$LAB#\$LAB#g" "$OUT/mcp-config.json"
echo "{\"arm\": \"$ARM\", \"run\": \"$RUN\", \"model\": \"$MODEL\", \"budget_usd\": $BUDGET, \"exit\": $RC, \"wall_s\": $(( $(date +%s) - T0 )), \"claude_version\": \"$(${CLAUDE:-claude} --version | head -1)\"}" > "$OUT/run-meta.json"
cat "$OUT/run-meta.json"
