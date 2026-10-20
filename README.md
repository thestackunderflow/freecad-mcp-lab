# FreeCAD MCP vs SolidCraft MCP: the same bracket, the same prompt (a test-first lab)

**Lab snapshot: 19 Oct 2026.** FreeCAD 1.1.4 (AppImage, SHA-256 checked) + the FreeCAD MCP addon and server
`neka-nat/freecad-mcp` v0.1.27 (MIT). SolidCraft 0.16.2 (release tarball, SHA256SUMS checked). Everything runs in
Docker; nothing is installed on the host.

## The question

Viewers search "solidcraft vs freecad". Both programs now have an MCP server, so an AI agent can drive either. This lab
asks one fair question: **given the same English request, which one does Claude Code build correctly, and which one
keeps the design parametric when one number changes?**

## The two servers are built differently (the video's explainer)

- **FreeCAD MCP** is two parts: an addon inside the FreeCAD desktop app runs an XML-RPC server on `127.0.0.1:9875`, and
  the `freecad-mcp` package is the MCP server that forwards each tool call to it. Its main modelling tool is
  `execute_code`: the agent writes FreeCAD Python and FreeCAD runs it on its GUI thread. The app must be running, so the
  lab runs FreeCAD's GUI on a virtual display (Xvfb).
- **SolidCraft MCP** is one binary (`solidcraft-cli mcp`) that speaks MCP itself. The agent calls typed commands
  (`batch`, `set_parameter`, `export`...) with no code; the server can only write to `--allow-path` folders.

## The part (the spec both agents get)

A wall bracket, an L shape, origin at the corner, width along X, depth along Y, height along Z:

| Dimension | Value |
|---|---|
| Width (parameter) | 80 mm, then changed to 100 mm |
| Base plate | depth 60 mm, thickness 4 mm, on the XY plane (Z 0..4) |
| Back plate | height 50 mm overall, thickness 4 mm, at Y 0..4 |
| Two holes through the back plate | diameter 5 mm, 40 mm apart, centred across the width, centres 35 mm above the bottom |

Design intent tested by the change: after width 80 → 100, the holes must still be centred (at X = 30/70 for 100 mm).
Analytic volume: W·60·4 + W·4·46 − 2·π·2.5²·4 = 33,762.9 mm³ at 80 mm, 42,242.9 mm³ at 100 mm.

## How a result is measured (the same for both)

- `tests/measure.py` reads the exported **STL** with NumPy only (no CAD kernel): bounding box, volume (signed
  tetrahedra), base and back thickness, both hole diameters (circle fit to the hole-edge vertices), hole spacing, hole
  height and how far the pair sits from the width centre. Tolerance ±0.1 mm, volume ±0.5 %.
- The exported **STEP** is re-read by FreeCAD's `freecadcmd` (OpenCASCADE) for an independent bounding box and volume.

## Tests (no AI)

Written first and run red, then green (`out/red-phase.log`, `out/green-phase.log`).

- `tests/test_measure.py`: the measurer itself, on synthetic STL meshes with known answers (runs anywhere with NumPy).
- `tests/test_freecad.py` (FreeCAD image): versions; MCP `initialize`; the documented tools are listed;
  `get_rpc_status`; a reference bracket built by a fixed script through `execute_code`, exported, and measured.
- `tests/test_solidcraft.py` (SolidCraft image): version; MCP `initialize`; the documented tools; a reference bracket
  built by one `batch` with parameters, exported, measured; `set_parameter width "100 mm"` and re-measured.

The reference builds prove each server can make the part and that the measurer agrees with the spec, before any agent
run is scored.

## Agent runs (paid; held until approved)

`claude-run/run.sh freecad|solidcraft`: one headless Claude Code run, the same prompt for both, only that server's MCP
tools allowed, every JSON-RPC line logged by `proxy/mcp_log_proxy.py`. Scored by `claude-run/score.py`: the 6
dimensions and volume at 80 and 100 mm, holes still centred, how the change was made (one parameter vs a rebuild),
tool calls, failed calls, wall time and cost.

## Run it

```bash
docker compose build
docker compose run --rm measure-tests
docker compose run --rm freecad-tests
docker compose run --rm solidcraft-tests
```

## Run plan (decided before the first paid run, 19 Oct 2026)

- 3 runs per arm, alternating (freecad-1, solidcraft-1, freecad-2, ...), so a bad hour hits both arms alike.
- Same for both arms: model `claude-sonnet-5-5`, the prompt in `claude-run/run.sh` (only the server name differs), the
  parametric instruction, `--max-budget-usd 1.50` per run, a 900 s wall-clock limit, only that server's MCP tools.
- Budget: 6 x $1.50 = $9.00 maximum; $1.00 reserve. Actual spend is in `out/runs/SCORES.json`.
- Disclosed difference: FreeCAD MCP runs with `--only-text-feedback` (its documented flag) so neither arm gets images
  unless the agent asks for one (`get_view` / `screenshot`).
- The verdict covers this one part and these 6 runs; it can't crown a winner for CAD in general.
- Correction, same day: the first 12 runs loaded the owner's global CLAUDE.md (final answers mention "your global
  workflow rules"): 6 before the problem was seen (`out/runs-pilot-primed/`, $0.69), and 6 more by a script mistake
  (the clean-flag edit failed and the loop ran anyway: `out/runs-pilot-primed-2/`, $0.84). Neither set is evidence.
  The 6 runs in `out/runs/` are clean (`--setting-sources project,local`, `claudeMdExcludes`, no auto-memory), with
  nothing else changed. Spend counts all 18 runs against the $10 cap. The pilot folders are kept locally and are not
  in this repo (.gitignore): they quote the owner's personal settings.
- Redactions in the clean runs: each `mcp-config.json` shows the host lab folder as `$LAB`, and in
  `out/runs/freecad-2/transcript.jsonl` (seq 20) a Windows temp path that Claude guessed is replaced by
  `[host temp path removed]`. Nothing else in the logs was changed. Publish from a fresh one-commit copy: the
  first commit of this repo still holds the unredacted files.
- Replay fixtures (`tests/fixtures/*.json`) are built from the clean runs only by `tests/fixtures/make_fixtures.py`.
