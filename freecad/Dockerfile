# FreeCAD 1.1.4 (official AppImage, SHA-256 checked, extracted: no FUSE needed) on a virtual display, plus the
# FreeCAD MCP addon and the freecad-mcp MCP server, both pinned to neka-nat/freecad-mcp v0.1.27 (MIT). Lab snapshot 19 Oct 2026.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xvfb xauth \
      libgl1 libegl1 libglu1-mesa libxkbcommon0 libxkbcommon-x11-0 libfontconfig1 libfreetype6 libdbus-1-3 \
      libx11-xcb1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 \
      libxcb-cursor0 libxcb-shape0 libxcb-randr0 libxcb-xfixes0 libxrender1 libxi6 libsm6 libice6 libnss3 libasound2t64 \
      python3 python3-venv python3-numpy python3-pytest \
 && rm -rf /var/lib/apt/lists/*
ARG FC=FreeCAD_1.1.4-Linux-x86_64-py311.AppImage
ARG FC_BASE=https://github.com/FreeCAD/FreeCAD/releases/download/1.1.4
WORKDIR /opt
RUN curl -fsSLO "$FC_BASE/$FC" && curl -fsSLO "$FC_BASE/$FC-SHA256.txt" && sha256sum -c "$FC-SHA256.txt" \
 && chmod +x "$FC" && ./"$FC" --appimage-extract > /dev/null && mv squashfs-root /opt/freecad \
 && cp "$FC-SHA256.txt" /opt/freecad/ && rm "$FC"
# The MCP server (needs Python >= 3.12; FreeCAD's bundled Python is separate, as the project's docs require)
RUN python3 -m venv /opt/mcp && /opt/mcp/bin/pip install --no-cache-dir freecad-mcp==0.1.27
# The addon, from the same tag, installed into FreeCAD's user Mod folder, with its RPC server set to auto-start
ARG ADDON_TAG=v0.1.27
RUN curl -fsSL "https://github.com/neka-nat/freecad-mcp/archive/refs/tags/$ADDON_TAG.tar.gz" | tar -xz -C /tmp \
 && UD=$(/opt/freecad/usr/bin/freecadcmd -c "import FreeCAD;print('UD='+FreeCAD.getUserAppDataDir())" 2>/dev/null | sed -n 's/^UD=//p' | tail -1) \
 && echo "user app data dir: $UD" && test -n "$UD" && mkdir -p "$UD/Mod" \
 && cp -r /tmp/freecad-mcp-*/addon/FreeCADMCP "$UD/Mod/" \
 && printf '{"remote_enabled": false, "allowed_ips": "127.0.0.1", "auto_start_rpc": true, "auth_token": ""}\n' > "$UD/freecad_mcp_settings.json" \
 && echo "$UD" > /opt/freecad-userdir.txt && rm -rf /tmp/freecad-mcp-*
ENV PATH=/opt/freecad/usr/bin:/opt/mcp/bin:$PATH QT_QPA_PLATFORM=xcb DISPLAY=:99
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh && mkdir -p /lab/out /lab/forbidden
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/start.sh"]
