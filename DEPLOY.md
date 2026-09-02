# zidongfabu · 部署方案（DEPLOY.md）

> 目标：在一台**新的 Windows 电脑**上，把本仓库部署成可用的自动发布系统。
> 本仓库不含大件（内嵌 Python 运行时、离线 wheels、MatrixMedia 安装包），下文两种方式二选一即可。

## 1. 环境要求

- Windows 10/11 64 位
- 网络：首次部署需要联网（下载依赖 / MatrixMedia 安装包）；后续运行可断网（纯本机服务）
- 发布能力依赖 MatrixMedia（GPL-2.0 上游项目）：自动化操作平台网页端，需 Chrome/Edge 内核环境，各平台**登录一次**，登录态保存在本机
- 数据目录：`watch/`（待发布）、`pending/`、`success/`、`fail/`、`data/`（SQLite/pid/停止标记）、`logs/`（按天日志）——均由程序首次运行自动创建

## 2. 获取代码

```bash
git clone https://github.com/yishui111/zidongfabu.git
cd zidongfabu
```

> 不会 git？到 GitHub 仓库页 `Code` → `Download ZIP`，解压即可，效果一样。

## 3. 两种部署方式（任选其一）

### 方式一：系统 Python（推荐，最简单）

1. 安装 Python 3.12+：从 [python.org](https://www.python.org/downloads/) 下载安装，勾选 **Add python.exe to PATH**；
2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

3. 安装 MatrixMedia：从 [hanliang97/MatrixMedia Releases](https://github.com/hanliang97/MatrixMedia/releases) 下载 Windows 安装包，放入仓库 `matrixmedia/` 目录（`start.bat` 会自动静默安装），或直接双击手动安装；
4. 继续看下方「4. 配置」与「5. 启动」。

### 方式二：自包含离线部署（目标机器免装 Python）

适用：目标电脑不能/不想装 Python，或需要完全离线运行。

1. 在**有网且装了 Python** 的机器上准备好离线件：

   ```bash
   # 1) Python 3.12 嵌入式运行时（选 Windows embeddable package）
   #    下载: https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
   #    放入 cache/ 目录
   # 2) get-pip.py
   #    下载: https://bootstrap.pypa.io/get-pip.py  -> 放入 cache/
   # 3) 离线 wheels
   pip download -r requirements.txt -d wheels
   ```

2. 把上面准备的 `cache/`、`wheels/` 与整个仓库目录一起复制到目标机器；
3. 目标机器双击 `install.bat`：自动解压内嵌运行时、离线装依赖、安装 MatrixMedia；
4. 之后正常使用 `start.bat` / `stop.bat`（走 `runtime\python.exe`，不依赖系统 Python）。

> 说明：`runtime/`（解压产物）、`cache/`、`wheels/`、`matrixmedia/*.exe` 都在 .gitignore 中，不会被提交进仓库；需要时按本方式自行准备即可。

## 4. 配置

编辑 `config.yaml`（路径均相对项目根目录）：

```yaml
accounts:
  dy-01: "13800138000"   # 换成你的真实手机号（与 MatrixMedia「账号管理」一致）
  sph-01: "13900139000"
```

- `matrix_api.base_url`：MatrixMedia 内置 HTTP API 地址，默认 `http://127.0.0.1:30088`，一般不用改；
- `publish.retry_times` / `retry_delays`：每平台重试次数与间隔；`per_platform_delay`：平台间间隔（降风控）；
- `publish.dry_run`：`true` 时不调用真实接口，模拟发布（测试用）；
- `dirs.*`：可自定义各目录名，默认相对项目根。

> ⚠️ **敏感信息不入库**：`config.yaml` 填了真实手机号后，请勿 `git add` 提交到公开仓库（参考 README 注意事项与 .gitignore）。

## 5. 启动 / 停止

- **启动**：双击 `start.bat`，或命令行 `start.bat`
  流程：检测 Python（内嵌运行时优先，其次系统 python）→ 检查依赖 → 检测/安装 MatrixMedia → 拉起 MatrixMedia 并等待其 API（`http://127.0.0.1:30088`）就绪 → 后台启动调度服务（pythonw）→ 等待 pid 文件出现即成功。
- **停止**：双击 `stop.bat`（向调度服务写停止标记 → 优雅退出 → 关闭 MatrixMedia）。
- **环境修复 / 重装**：双击 `install.bat`（方式二离线还原用）。

调度服务也可手动前台运行（便于看日志）：

```bash
# 一次性处理已有任务后退出
python scheduler\main.py --once
# 模拟发布（不调真实接口）
python scheduler\main.py --dry-run
# 带内置模拟 API 自测
python scheduler\main.py --mock
```

## 6. 使用流程（调度说明）

```
watch\任务文件夹\（video.mp4 + 可选 cover.jpg + info.json）
  → pending\（处理中/定时等待）
  → 逐平台调用 MatrixMedia 发布（每平台失败自动重试）
  → success\（全部成功）/ success\duplicate\（重复视频）/ fail\（部分或全部失败，附 result.json）
```

- `info.json` 字段：`title`、`platforms`（平台代码数组）、`account`（默认账号别名）/ `accounts`（按平台覆盖）、`tags`、`bt2`（视频号短标题，可选）、`publish_at`（定时，`null` 为立即）；
- 平台代码：`dy` 抖音、`ks` 快手、`blbl` B站、`tt` 头条、`bjh` 百家号、`sph` 视频号、`xhs` 小红书、`fqsp` 番茄视频；
- 完整模板见 `examples\任务模板\`；
- 单线程串行发布、平台间默认间隔 5 秒；同视频按 MD5 去重；日志 `logs\scheduler.log` 按天切割保留 30 天；
- 任务只写账号**别名**，手机号仅存于本机 `config.yaml`，避免分享/发布时泄露。

## 7. 验证是否部署成功

1. `start.bat` 结束后，`logs\scheduler.log` 出现「调度服务启动」且 `data\scheduler.pid` 存在；
2. 打开 MatrixMedia 已登录至少一个平台账号；
3. 把一个示例任务文件夹放入 `watch\`（可先用 `examples\任务模板\` 改名复制），3 秒内被移入 `pending\`，随后发布并归档到 `success\` 或 `fail\`（附 `result.json` 排查）；
4. 自测（不依赖账号/网络）：`scripts\run_tests.bat` 应全部 PASS。

## 8. 常见问题排查

| 现象 | 处理 |
| --- | --- |
| `start.bat` 提示 Python 不存在 | 方式一先装 Python 并加 PATH；或按方式二准备内嵌运行时 |
| 提示 Python 依赖缺失 | 执行 `pip install -r requirements.txt` |
| MatrixMedia API 30088 起不来 | 手动打开 MatrixMedia；删除 `%LOCALAPPDATA%\matrixmedia` 后重装 `matrixmedia\` 下安装包 |
| 发布失败：未登录/Cookie 过期 | MatrixMedia 中重新登录对应平台 |
| 任务停在 pending | 检查 `publish_at` 是否在未来时间 |
| 平台改版发布失败 | 到 MatrixMedia 上游 Release 换新安装包 |
| 30088 端口被占用 | 改 MatrixMedia 内设置 + `config.yaml` 的 `matrix_api.base_url` 保持一致 |

## 9. 本机与目标机器可能不同的项

| 项 | 默认 | 说明 |
| --- | --- | --- |
| Python 路径 | 内嵌 `runtime\` 优先，否则 PATH 上的 `python` | 两台机器可不同，脚本自动探测 |
| MatrixMedia 安装位置 | `%LOCALAPPDATA%\Programs\matrixmedia\` 等 | `start.bat` 多点探测 |
| API 端口 | 30088 | 两台机器可不同，需 MatrixMedia 与 config.yaml 一致 |
| 数据/日志目录 | 项目根下 watch/pending/success/fail/data/logs | 可在 config.yaml 改 |

## 10. 更新约定

每次修改代码后，同步更新本文件与 README.md。
