"""MatrixMedia HTTP API 客户端。"""

import logging
import time

import requests


log = logging.getLogger("matrix")


class MatrixClient:
    def __init__(self, base_url, timeout=1800, poll_interval=3, ready_timeout=120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.ready_timeout = ready_timeout
        self.session = requests.Session()

    def wait_ready(self):
        """轮询等待 MatrixMedia 内置 API 可访问（任意 HTTP 响应即视为就绪）。"""
        deadline = time.time() + self.ready_timeout
        while time.time() < deadline:
            try:
                self.session.get(self.base_url + "/", timeout=3)
                log.info("MatrixMedia API 已就绪: %s", self.base_url)
                return True
            except requests.RequestException:
                time.sleep(self.poll_interval)
        log.error("MatrixMedia API 不可用: %s", self.base_url)
        return False

    def publish(self, platform, phone, file_path, title, tags=None, bt2=None,
                publish_at=None):
        """单平台发布；成功返回 (True, 响应)。"""
        payload = {
            "platform": platform,
            "file": file_path,
            "title": title,
        }
        if phone:
            payload["phone"] = phone
        if tags:
            payload["tags"] = tags
        if bt2:
            payload["bt2"] = bt2
        if publish_at:
            payload["publishAt"] = publish_at
        log.info("POST /publish platform=%s title=%s", platform, title)
        resp = self.session.post(
            self.base_url + "/publish", json=payload, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        ok = bool(data.get("success")) and data.get("exitCode") == 0
        return ok, data


class DryRunClient(MatrixClient):
    """不发起真实请求，直接模拟成功，用于测试流程。"""

    def publish(self, platform, phone, file_path, title, tags=None, bt2=None,
                publish_at=None):
        log.info("[dry-run] 模拟发布 platform=%s title=%s", platform, title)
        time.sleep(0.2)
        return True, {
            "success": True,
            "exitCode": 0,
            "status": "success",
            "message": "dry-run 模拟成功",
            "platform": platform,
        }
