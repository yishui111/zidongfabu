"""任务处理核心：扫描、去重、定时、发布、重试、归档。"""

import hashlib
import json
import logging
import os
import time


log = logging.getLogger("processor")

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".ts", ".mts"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _parse_publish_at(value):
    if not value:
        return None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
            try:
                return time.mktime(time.strptime(value, fmt))
            except ValueError:
                continue
    return None


def _find_media(folder):
    videos, images = [], []
    try:
        for name in sorted(os.listdir(folder)):
            ext = os.path.splitext(name)[1].lower()
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            if ext in VIDEO_EXTS:
                videos.append(path)
            elif ext in IMAGE_EXTS:
                images.append(path)
    except OSError as exc:
        log.warning("读取目录失败 %s: %s", folder, exc)
    return videos, images


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class TaskProcessor:
    def __init__(self, cfg, db, client):
        self.cfg = cfg
        self.db = db
        self.client = client
        self.dirs = cfg["dirs"]
        self.stop_file = os.path.join(self.dirs["data"], "stop.flag")
        self.in_progress = set()

    # ---------- 扫描与入队 ----------

    def stopped(self):
        return os.path.exists(self.stop_file)

    def _enqueue(self, queue, folder):
        key = os.path.basename(folder)
        if key in self.in_progress:
            return
        self.in_progress.add(key)
        queue.put(folder)

    def mark_done(self, folder):
        self.in_progress.discard(os.path.basename(folder))

    def scan_and_enqueue(self, queue):
        """扫描 watch/，把完整任务目录（含 info.json 和视频）移入 pending/ 并入队。"""
        watch = self.dirs["watch"]
        if not os.path.isdir(watch):
            return
        for name in sorted(os.listdir(watch)):
            if self.stopped():
                return
            src = os.path.join(watch, name)
            if not os.path.isdir(src):
                continue
            videos, _ = _find_media(src)
            if not videos or not os.path.isfile(os.path.join(src, "info.json")):
                continue
            dst = os.path.join(self.dirs["pending"], name)
            if os.path.exists(dst):
                dst = os.path.join(
                    self.dirs["pending"], "%s_%d" % (name, int(time.time()))
                )
            try:
                os.replace(src, dst)
                log.info("任务入队: %s", name)
                self._enqueue(queue, dst)
            except OSError as exc:
                log.error("移动任务失败 %s: %s", name, exc)

    def process_pending_once(self, queue):
        """把 pending/ 中到点（或无定时）的任务重新入队，用于重启恢复与定时到点。"""
        pending = self.dirs["pending"]
        if not os.path.isdir(pending):
            return
        for name in sorted(os.listdir(pending)):
            if self.stopped():
                return
            folder = os.path.join(pending, name)
            if not os.path.isdir(folder):
                continue
            info = self._load_info(folder)
            publish_at = _parse_publish_at(
                info.get("publish_at") or info.get("publishAt")
            )
            if publish_at and publish_at > time.time():
                continue  # 未到定时时间
            self._enqueue(queue, folder)

    # ---------- 任务处理 ----------

    def process_task(self, folder):
        name = os.path.basename(folder)
        info = self._load_info(folder)
        videos, _ = _find_media(folder)
        if not videos:
            log.error("任务缺少视频文件: %s", name)
            self._write_result(folder, {"status": "failed", "error": "缺少视频文件"})
            self._archive(folder, "fail")
            return

        video = videos[0]
        md5 = _md5(video)
        log.info("处理任务 %s md5=%s", name, md5[:12])

        if self.cfg.get("dedup", True):
            existing = self.db.find_folder_by_md5(md5)
            if existing and existing["status"] in ("success", "partial", "duplicate"):
                log.warning("检测到重复视频，跳过发布: %s (md5=%s)", name, md5[:12])
                self.db.record_task(
                    name, md5, info, "duplicate", error="重复视频，已发布过"
                )
                self._write_result(folder, {
                    "status": "duplicate",
                    "md5": md5,
                    "message": "重复视频，跳过发布",
                })
                self._archive(folder, "success", subdir="duplicate")
                return

        publish_at = _parse_publish_at(
            info.get("publish_at") or info.get("publishAt")
        )
        if publish_at and publish_at > time.time():
            remain = int(publish_at - time.time())
            log.info("任务 %s 定时 %s，剩余 %d 秒", name, info.get("publish_at"), remain)
            self.db.record_task(
                name, md5, info, "scheduled",
                error="定时发布等待中 (%ds)" % remain,
            )
            return  # 继续留在 pending/

        platforms = self._resolve_platforms(info)
        if not platforms:
            log.error("任务 %s 未指定平台，且未配置默认平台", name)
            self._write_result(folder, {"status": "failed", "error": "未指定发布平台"})
            self._archive(folder, "fail")
            return

        results = []
        any_fail = False
        for idx, platform in enumerate(platforms):
            if self.stopped():
                log.warning("收到停止信号，任务 %s 未完成，保留在 pending", name)
                return
            if idx > 0:
                time.sleep(float(self.cfg["publish"]["per_platform_delay"]))
            ok, detail, attempts, error = self._publish_with_retry(info, video, platform)
            results.append({
                "platform": platform,
                "success": ok,
                "attempts": attempts,
                "error": error,
                "detail": detail,
                "account": self._resolve_alias(info, platform),
            })
            if not ok:
                any_fail = True

        status = "success" if not any_fail else "partial"
        self.db.record_task(name, md5, info, status, results=results)
        self._write_result(folder, {"status": status, "md5": md5, "results": results})
        self._archive(folder, "fail" if any_fail else "success")

    def _publish_with_retry(self, info, video, platform):
        alias = self._resolve_alias(info, platform)
        phone = self.cfg["accounts"].get(alias) if alias else None
        if not alias or not phone:
            msg = "账号别名未配置: %s" % (alias or "（未指定 account）")
            log.error("平台 %s: %s", platform, msg)
            return False, {"message": msg}, 0, msg

        retry_times = int(self.cfg["publish"]["retry_times"])
        delays = list(self.cfg["publish"]["retry_delays"] or [10] * retry_times)
        title = info.get("title") or self.cfg["publish"]["default_title"]
        tags = info.get("tags")
        bt2 = info.get("bt2")
        publish_at = info.get("publish_at") or info.get("publishAt")
        last_detail, last_error, attempts = None, "", 0
        for attempt in range(1, retry_times + 1):
            if self.stopped():
                return False, last_detail, attempts, "收到停止信号"
            try:
                ok, detail = self.client.publish(
                    platform, phone, video, title,
                    tags=tags, bt2=bt2, publish_at=publish_at,
                )
            except Exception as exc:  # 网络/超时等异常
                ok, detail = False, {"error": str(exc)}
            attempts = attempt
            last_detail = detail
            if ok:
                log.info("平台 %s 发布成功（第 %d 次尝试）", platform, attempt)
                return True, detail, attempts, ""
            msg = (detail or {}).get("message") or (detail or {}).get("error") or str(detail)
            last_error = msg
            log.warning("平台 %s 发布失败（第 %d/%d 次）: %s",
                        platform, attempt, retry_times, msg)
            if attempt < retry_times:
                delay = delays[min(attempt - 1, len(delays) - 1)]
                log.info("平台 %s 将在 %d 秒后重试", platform, delay)
                time.sleep(delay)
        return False, last_detail, attempts, last_error

    # ---------- 辅助 ----------

    def _load_info(self, folder):
        path = os.path.join(folder, "info.json")
        try:
            # utf-8-sig 兼容记事本/PowerShell 生成的带 BOM 文件
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f) or {}
        except Exception as exc:
            log.warning("读取 %s 失败: %s", path, exc)
            return {}

    def _resolve_alias(self, info, platform):
        accounts_map = info.get("accounts") or {}
        return accounts_map.get(platform) or info.get("account")

    def _resolve_platforms(self, info):
        platforms = info.get("platforms") or info.get("platform")
        if isinstance(platforms, str):
            platforms = [p.strip() for p in platforms.split(",") if p.strip()]
        if not platforms:
            platforms = list(self.cfg["publish"]["default_platforms"])
        return platforms

    def _write_result(self, folder, data):
        try:
            with open(os.path.join(folder, "result.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            log.error("写入 result.json 失败: %s", exc)

    def _archive(self, folder, bucket, subdir=None):
        target = self.dirs[bucket]
        if subdir:
            target = os.path.join(target, subdir)
        os.makedirs(target, exist_ok=True)
        dst = os.path.join(target, os.path.basename(folder))
        if os.path.exists(dst):
            dst = os.path.join(
                target, "%s_%d" % (os.path.basename(folder), int(time.time()))
            )
        os.replace(folder, dst)
        log.info("任务已归档: %s/%s", bucket, os.path.basename(dst))
