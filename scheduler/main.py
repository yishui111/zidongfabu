"""多平台视频自动发布调度服务入口。

用法（项目根目录下执行）:
  runtime\\python.exe scheduler\\main.py [--config config.yaml] [--once] [--dry-run] [--mock]
"""

import argparse
import logging
import os
import queue
import sys
import threading
import time
from logging.handlers import TimedRotatingFileHandler


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.config import load_config          # noqa: E402
from scheduler.db import DB                      # noqa: E402
from scheduler.matrix_client import DryRunClient, MatrixClient  # noqa: E402
from scheduler.mock_matrix_api import start_mock  # noqa: E402
from scheduler.processor import TaskProcessor     # noqa: E402


log = logging.getLogger("main")


def setup_logging(cfg):
    logs_dir = cfg["dirs"]["logs"]
    os.makedirs(logs_dir, exist_ok=True)
    level = getattr(logging, str(cfg["logging"]["level"]).upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = TimedRotatingFileHandler(
        os.path.join(logs_dir, "scheduler.log"),
        when="midnight",
        backupCount=int(cfg["logging"]["keep_days"]),
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def write_pid(cfg):
    pid_file = os.path.join(cfg["dirs"]["data"], "scheduler.pid")
    with open(pid_file, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def remove_pid(cfg):
    pid_file = os.path.join(cfg["dirs"]["data"], "scheduler.pid")
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description="多平台视频自动发布调度服务")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--once", action="store_true",
                        help="处理当前已有的任务后退出（测试/重启恢复用）")
    parser.add_argument("--dry-run", action="store_true", help="模拟发布，不调用真实接口")
    parser.add_argument("--mock", action="store_true",
                        help="启动内置模拟 MatrixMedia API 并指向它（自动化测试用）")
    parser.add_argument("--mock-port", type=int, default=31088)
    args = parser.parse_args()

    cfg = load_config(os.path.abspath(args.config))
    if args.dry_run:
        cfg["publish"]["dry_run"] = True
    setup_logging(cfg)
    for key in cfg["dirs"]:
        os.makedirs(cfg["dirs"][key], exist_ok=True)

    log.info("=" * 60)
    log.info("调度服务启动 config=%s root=%s", os.path.abspath(args.config), cfg["root"])

    db = DB(os.path.join(cfg["dirs"]["data"], "tasks.db"))

    mock_server = None
    if args.mock:
        mock_server, base = start_mock(args.mock_port)
        cfg["matrix_api"]["base_url"] = base
        log.info("模拟 MatrixMedia API 已启动: %s", base)

    if cfg["publish"]["dry_run"]:
        client = DryRunClient(
            cfg["matrix_api"]["base_url"],
            timeout=cfg["matrix_api"]["timeout"],
            poll_interval=cfg["matrix_api"]["poll_interval"],
            ready_timeout=cfg["matrix_api"]["ready_timeout"],
        )
        log.info("dry-run 模式：不会真正发布视频")
    else:
        client = MatrixClient(
            cfg["matrix_api"]["base_url"],
            timeout=cfg["matrix_api"]["timeout"],
            poll_interval=cfg["matrix_api"]["poll_interval"],
            ready_timeout=cfg["matrix_api"]["ready_timeout"],
        )
        if not args.mock:
            if not client.wait_ready():
                log.error("MatrixMedia API 不可用，请先运行 start.bat 或手动启动 MatrixMedia")
                sys.exit(1)

    processor = TaskProcessor(cfg, db, client)
    task_queue = queue.Queue()

    def worker():
        while True:
            try:
                folder = task_queue.get(timeout=1)
            except queue.Empty:
                if processor.stopped():
                    log.info("收到停止信号，工作线程退出")
                    return
                continue
            try:
                if processor.stopped():
                    log.info("收到停止信号，工作线程退出")
                    return
                processor.process_task(folder)
            except Exception:
                log.exception("处理任务异常: %s", folder)
            finally:
                processor.mark_done(folder)
                task_queue.task_done()

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    write_pid(cfg)
    log.info("监听目录: %s", cfg["dirs"]["watch"])

    try:
        if args.once:
            processor.scan_and_enqueue(task_queue)
            processor.process_pending_once(task_queue)
            task_queue.join()
            log.info("一次性处理完成")
        else:
            scan_interval = float(cfg["publish"]["scan_interval"])
            while not processor.stopped():
                processor.scan_and_enqueue(task_queue)
                processor.process_pending_once(task_queue)
                step = max(0.2, scan_interval / 10.0)
                for _ in range(10):
                    if processor.stopped():
                        break
                    time.sleep(step)
            log.info("收到停止信号，等待当前任务结束（最多 120 秒）...")
            worker_thread.join(timeout=120)
            log.info("调度服务已退出")
    finally:
        stop_flag = os.path.join(cfg["dirs"]["data"], "stop.flag")
        try:
            if os.path.exists(stop_flag):
                os.remove(stop_flag)
        except OSError:
            pass
        remove_pid(cfg)
        if mock_server:
            mock_server.shutdown()


if __name__ == "__main__":
    main()
