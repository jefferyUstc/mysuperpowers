#!/usr/bin/env python3
"""Preview rendered HTML at iPhone-width (375 px) in a local browser.

Step [10] of the pipeline. Starts a small local HTTP server in the
HTML file's directory and opens a wrapper page that iframes the output
at mobile width. Ctrl-C shuts down and cleans up the wrapper.

Works best when render.py was run without --wrap (body-only fragment);
the wrapper provides the <html>/<body> shell. Also works with full
standalone HTML.
"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path


WRAPPER_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>WeChat mobile preview — {html_name}</title>
<style>
  body {{
    margin: 0;
    background: #1e1e1e;
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    color: #eeeeee;
  }}
  .header {{
    padding: 10px 18px;
    background: #2a2a2a;
    border-bottom: 1px solid #3a3a3a;
    font-size: 13px;
    line-height: 1.5;
  }}
  .header code {{
    background: #101010;
    padding: 2px 6px;
    border-radius: 3px;
    color: #7fd;
  }}
  .ruler {{
    width: 375px;
    margin: 14px auto 4px;
    color: #888;
    text-align: center;
    font-size: 11px;
    letter-spacing: 1px;
  }}
  .frame-outer {{
    width: 375px;
    margin: 0 auto 24px;
    background: white;
    box-shadow: 0 6px 20px rgba(0,0,0,0.45);
    border-radius: 10px;
    overflow: hidden;
  }}
  iframe {{
    display: block;
    width: 375px;
    height: calc(100vh - 130px);
    border: 0;
    background: white;
  }}
</style>
</head>
<body>
  <div class="header">
    Previewing <code>{html_name}</code> at 375 px (iPhone SE logical width).
    WeChat renders at up to 750 px but reading happens on phones.
    <strong>Ctrl-C in terminal</strong> to stop.
  </div>
  <div class="ruler">── 375 px ──</div>
  <div class="frame-outer">
    <iframe src="{html_name}"></iframe>
  </div>
</body>
</html>
"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        # silence per-request logs
        pass


def start_server(serve_dir: Path, port: int) -> tuple[socketserver.TCPServer, int]:
    os.chdir(serve_dir)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), QuietHandler)
    actual_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, actual_port


def main() -> int:
    ap = argparse.ArgumentParser(description="Preview output.html at iPhone width")
    ap.add_argument("html", help="path to output.html")
    ap.add_argument("--port", type=int, default=0, help="port (0 = random free port)")
    ap.add_argument("--no-open", action="store_true", help="print URL, do not launch browser")
    args = ap.parse_args()

    html_path = Path(args.html).resolve()
    if not html_path.is_file():
        print(f"[error] not found: {html_path}", file=sys.stderr)
        return 2

    # Contract: html_path is `<work_dir>/output*.html` and `<work_dir>/figures/`
    # exists alongside it. `render.py` enforces this on its end. The HTTP
    # server serves from html_path's parent directly — no walk-up.
    serve_dir = html_path.parent
    wrapper_name = "_preview_wrapper.html"
    wrapper_path = serve_dir / wrapper_name
    wrapper_path.write_text(WRAPPER_TEMPLATE.format(html_name=html_path.name))

    try:
        httpd, port = start_server(serve_dir, args.port)
    except OSError as e:
        print(f"[error] could not bind port: {e}", file=sys.stderr)
        try:
            wrapper_path.unlink()
        except OSError:
            pass
        return 2

    url = f"http://127.0.0.1:{port}/{wrapper_name}"
    print(f"Preview at {url}")
    print(f"Serving  {serve_dir}")
    print("Ctrl-C to stop.")

    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.shutdown()
        httpd.server_close()
        try:
            wrapper_path.unlink()
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
