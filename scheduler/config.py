"""配置加载与路径解析。"""

import os

import yaml


DEFAULTS = {
    "matrix_api": {
        "base_url": "http://127.0.0.1:30088",
        "timeout": 1800,          # 单平台发布最长等待（秒），大文件上传可能很慢
        "poll_interval": 3,       # 等待 API 就绪时的轮询间隔
        "ready_timeout": 120,     # 等待 API 就绪的最长时间
    },
    "dirs": {
        "watch": "watch",
        "pending": "pending",
        "success": "success",
        "fail": "fail",
        "logs": "logs",
        "data": "data",
    },
    "publish": {
        "dry_run": False,          # True: 不真正调接口，模拟发布成功（测试用）
        "retry_times": 3,          # 每个平台最多尝试次数
        "retry_delays": [10, 30, 60],  # 各次重试前的等待秒数
        "per_platform_delay": 5,   # 平台之间的间隔秒数（降低风控风险）
        "scan_interval": 3,        # 扫描 watch/ 目录的间隔秒数
        "pending_check_interval": 30,  # 定时任务的检查间隔秒数
        "default_platforms": [],   # info.json 未指定平台时的默认平台
        "default_title": "未命名视频",
    },
    "accounts": {},                # 账号别名 -> 手机号（与 MatrixMedia 账号树一致）
    "logging": {"level": "INFO", "keep_days": 30},
    "dedup": True,                 # 同一视频只允许发布一次
}


def load_config(path):
    """读取 YAML 配置并与默认值合并，返回绝对路径解析后的配置字典。"""
    cfg = _deep_copy(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        _merge(cfg, user)
    root = os.path.dirname(os.path.abspath(path))
    cfg["root"] = root
    for key in cfg["dirs"]:
        cfg["dirs"][key] = os.path.abspath(os.path.join(root, cfg["dirs"][key]))
    return cfg


def _deep_copy(obj):
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj


def _merge(base, override):
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
