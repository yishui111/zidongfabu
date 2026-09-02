"""自动化自测：启动模拟 API，构造各种任务，验证全流程正确性。

运行方式（项目根目录）:
  runtime\\python.exe scripts\\run_tests.py
"""

import json
import os
import queue
import sys
import threading
import time

import yaml


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scheduler.config import load_config  # noqa: E402
from scheduler.db import DB              # noqa: E402
from scheduler.matrix_client import MatrixClient  # noqa: E402
from scheduler.mock_matrix_api import start_mock  # noqa: E402
from scheduler.processor import TaskProcessor     # noqa: E402


MOCK_PORT = 31088
FAILURES = []


def check(cond, msg):
    if cond:
        print("  [PASS]", msg)
    else:
        print("  [FAIL]", msg)
        FAILURES.append(msg)


def make_video(path, size=8192):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42" + os.urandom(size))


def make_task(base, name, title, platforms, publish_at=None, account="test-01",
              extra=None):
    folder = os.path.join(base, "watch", name)
    os.makedirs(folder, exist_ok=True)
    make_video(os.path.join(folder, "video.mp4"))
    info = {"title": title, "platforms": platforms, "account": account}
    if publish_at:
        info["publish_at"] = publish_at
    if extra:
        info.update(extra)
    with open(os.path.join(folder, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return folder


def drain(processor, task_queue, rounds=1):
    for _ in range(rounds):
        processor.scan_and_enqueue(task_queue)
        processor.process_pending_once(task_queue)
        while True:
            try:
                folder = task_queue.get_nowait()
            except queue.Empty:
                break
            processor.process_task(folder)
            processor.mark_done(folder)
            task_queue.task_done()
        time.sleep(0.3)


def setup(base):
    cfg = {
        "matrix_api": {
            "base_url": "http://127.0.0.1:%d" % MOCK_PORT,
            "timeout": 60,
            "poll_interval": 1,
            "ready_timeout": 10,
        },
        "dirs": {
            "watch": "watch", "pending": "pending", "success": "success",
            "fail": "fail", "logs": "logs", "data": "data",
        },
        "publish": {
            "dry_run": False, "retry_times": 3, "retry_delays": [1, 1, 1],
            "per_platform_delay": 1, "scan_interval": 2,
            "pending_check_interval": 2, "default_platforms": [],
            "default_title": "默认标题",
        },
        "accounts": {"test-01": "13800138000"},
        "logging": {"level": "INFO", "keep_days": 30},
        "dedup": True,
    }
    cfg_path = os.path.join(base, "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True)
    loaded = load_config(cfg_path)
    for key in loaded["dirs"]:
        os.makedirs(loaded["dirs"][key], exist_ok=True)
    return loaded


def main():
    base = os.path.join(ROOT, "data", "test_%d" % int(time.time()))
    os.makedirs(base, exist_ok=True)
    cfg = setup(base)
    db = DB(os.path.join(cfg["dirs"]["data"], "tasks.db"))
    server, mock_url = start_mock(MOCK_PORT)
    client = MatrixClient(mock_url, timeout=60, poll_interval=1, ready_timeout=10)
    processor = TaskProcessor(cfg, db, client)
    tq = queue.Queue()

    print("== 测试 1：正常多平台发布 ==")
    make_task(base, "ok_task", "正常任务", ["dy", "blbl"])
    drain(processor, tq)
    check(os.path.isdir(os.path.join(cfg["dirs"]["success"], "ok_task")),
          "ok_task 进入 success")
    row = db.find_folder_by_md5(
        __import__("scheduler.processor", fromlist=["_md5"])._md5(
            os.path.join(cfg["dirs"]["success"], "ok_task", "video.mp4")
        )
    )
    check(row is not None and row["status"] == "success", "DB 记录 status=success")

    print("== 测试 2：失败自动重试后成功（快手前两次失败） ==")
    make_task(base, "retry_task", "重试任务", ["ks"])
    drain(processor, tq)
    check(os.path.isdir(os.path.join(cfg["dirs"]["success"], "retry_task")),
          "retry_task 最终进入 success")
    cur = db.conn.execute(
        "SELECT attempts FROM tasks WHERE folder_name='retry_task' AND platform='ks'"
    )
    attempts = cur.fetchone()
    check(attempts is not None and attempts[0] >= 3,
          "快手平台实际尝试 3 次后成功 (attempts=%s)" % (attempts[0] if attempts else None))

    print("== 测试 3：固定失败平台进入 fail ==")
    make_task(base, "fail_task", "失败任务", ["xhs"])
    drain(processor, tq)
    fail_dir = os.path.join(cfg["dirs"]["fail"], "fail_task")
    check(os.path.isdir(fail_dir), "fail_task 进入 fail")
    check(os.path.isfile(os.path.join(fail_dir, "result.json")),
          "fail 目录保留 result.json")
    with open(os.path.join(fail_dir, "result.json"), encoding="utf-8") as f:
        result = json.load(f)
    check(result["status"] == "partial" and result["results"][0]["success"] is False,
          "result.json 标记失败与错误信息")

    print("== 测试 4：部分平台失败（一成一败） ==")
    make_task(base, "partial_task", "部分失败任务", ["dy", "xhs"])
    drain(processor, tq)
    partial_dir = os.path.join(cfg["dirs"]["fail"], "partial_task")
    check(os.path.isdir(partial_dir), "partial_task 进入 fail")
    with open(os.path.join(partial_dir, "result.json"), encoding="utf-8") as f:
        result = json.load(f)
    statuses = {r["platform"]: r["success"] for r in result["results"]}
    check(statuses.get("dy") is True and statuses.get("xhs") is False,
          "dy 成功 / xhs 失败，结果正确")

    print("== 测试 5：重复视频去重 ==")
    src_video = os.path.join(cfg["dirs"]["success"], "ok_task", "video.mp4")
    dup = make_task(base, "dup_task", "重复视频", ["dy"])
    shutil_copy = __import__("shutil").copy2(src_video,
                                             os.path.join(dup, "video.mp4"))
    drain(processor, tq)
    dup_dir = os.path.join(cfg["dirs"]["success"], "duplicate", "dup_task")
    check(os.path.isdir(dup_dir), "dup_task 进入 success/duplicate 而非重新发布")

    print("== 测试 6：定时发布 ==")
    when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 3))
    make_task(base, "sched_task", "定时任务", ["dy"], publish_at=when)
    drain(processor, tq)
    check(os.path.isdir(os.path.join(cfg["dirs"]["pending"], "sched_task")),
          "定时任务未到点，停留在 pending")
    time.sleep(4)
    drain(processor, tq)
    check(os.path.isdir(os.path.join(cfg["dirs"]["success"], "sched_task")),
          "定时到点后自动发布并进入 success")

    server.shutdown()
    print()
    if FAILURES:
        print("共 %d 项失败：" % len(FAILURES))
        for msg in FAILURES:
            print("  -", msg)
        print("测试结果：FAILED")
        return 1
    print("全部测试通过。")
    print("测试数据目录：%s（可手动检查 success/fail/pending 分布）" % base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
