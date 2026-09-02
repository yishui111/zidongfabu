"""模拟 MatrixMedia HTTP API，用于自动化测试（不联网、不真发视频）。"""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


_attempts = {}
_lock = threading.Lock()


def _bump(file_path, platform):
    with _lock:
        key = (file_path, platform)
        n = _attempts.get(key, 0) + 1
        _attempts[key] = n
        return n


class MockMatrixHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # 任意 HTTP 响应都表示服务在线，客户端据此判断 API 就绪
        self._send(200, {"ok": True})

    def do_POST(self):
        if self.path != "/publish":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send(400, {"success": False, "exitCode": 2, "message": "bad json"})
            return
        platform = body.get("platform")
        file_path = body.get("file")
        title = body.get("title", "")
        fail = False
        msg = "模拟：发布成功"
        if not file_path or not os.path.exists(file_path):
            fail = True
            msg = "模拟：文件不存在"
        elif "FAIL" in title.upper():
            fail = True
            msg = "模拟：标题包含 FAIL"
        elif platform == "xhs":
            fail = True
            msg = "模拟：小红书固定失败"
        elif platform == "ks" and _bump(file_path, platform) <= 2:
            fail = True
            msg = "模拟：快手前两次失败"
        time.sleep(0.3)
        if fail:
            self._send(200, {
                "success": False,
                "exitCode": 3,
                "status": "failed",
                "message": msg,
                "platform": platform,
            })
        else:
            self._send(200, {
                "success": True,
                "exitCode": 0,
                "status": "success",
                "message": msg,
                "platform": platform,
                "id": "mock-123",
            })


def start_mock(port=31088):
    server = ThreadingHTTPServer(("127.0.0.1", port), MockMatrixHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, "http://127.0.0.1:%d" % port
