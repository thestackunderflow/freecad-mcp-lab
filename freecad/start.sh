#!/usr/bin/env bash
# Start a virtual display and the FreeCAD GUI (its MCP addon auto-starts the RPC server on 127.0.0.1:9875),
# wait until the port answers, then run the command (the MCP server, or the tests). FreeCAD's log: /tmp/freecad.log.
set -e
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp > /tmp/xvfb.log 2>&1 &
for i in $(seq 1 50); do [ -e /tmp/.X11-unix/X99 ] && break; sleep 0.1; done
/opt/freecad/AppRun > /tmp/freecad.log 2>&1 &
python3 - <<'PY' >&2
import socket, sys, time
t0 = time.time()
while time.time() - t0 < 180:
    try:
        socket.create_connection(("127.0.0.1", 9875), 1).close()
        print(f"[start.sh] FreeCAD RPC up after {time.time() - t0:.1f} s", file=sys.stderr); sys.exit(0)
    except OSError:
        time.sleep(0.5)
print("[start.sh] FreeCAD RPC did not start in 180 s; see /tmp/freecad.log", file=sys.stderr); sys.exit(1)
PY
exec "$@"
