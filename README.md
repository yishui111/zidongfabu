<div align="center">

# 📤 多平台视频自动发布调度系统（zidongfabu）

> ⭐ **喜欢这个项目？请先点个 Star 支持一下，让更多人看到！** ⭐

![GitHub stars](https://img.shields.io/github/stars/yishui111/zidongfabu.svg?style=flat-square&color=orange)
![GitHub forks](https://img.shields.io/github/forks/yishui111/zidongfabu.svg?style=flat-square)
![GitHub repo size](https://img.shields.io/github/repo-size/yishui111/zidongfabu.svg?style=flat-square)

**把 AI 流水线生成的视频任务文件夹，自动分发到抖音、快手、B站、头条、百家号、视频号、小红书、番茄视频等平台。**

</div>

---

## ✨ 项目简介

AI 流水线每天产出大量视频，逐个平台手动上传费时费力。本项目是一个**任务文件夹驱动的自动发布调度服务**：

把「视频 + 封面 + info.json」按固定格式丢进 `watch/` 文件夹，调度服务自动完成：
扫描 → 去重（MD5）→ 定时等待 → 逐平台调用 MatrixMedia 发布 → 失败自动重试 → 结果归档（success/fail）→ SQLite 记录与按天日志。

- **自研调度服务**（本仓库，MIT）：监听、去重、重试、定时、日志、结果记录，全部逻辑自研；
- **MatrixMedia 矩媒**（上游开源项目，GPL-2.0）：负责各平台网页端自动化上传，通过其内置 HTTP API 驱动，独立进程、不修改其代码、互不传染。

## 🎯 主要功能

- 📁 **任务文件夹驱动**：`watch/任务名/`（video + 可选 cover + info.json）放入即自动发布
- 📱 **多平台分发**：抖音 `dy`、快手 `ks`、B站 `blbl`、头条 `tt`、百家号 `bjh`、视频号 `sph`、小红书 `xhs`、番茄视频 `fqsp`
- 🕐 **定时发布**：`publish_at` 指定时间（`2026-08-11 12:00:00`），未到点任务留在 pending 等待
- 🔁 **失败自动重试**：每平台最多 3 次、间隔递增（10/30/60s），最终失败进入 `fail/` 并附 `result.json`
- 🧮 **MD5 去重**：同一视频只发一次，重复任务自动进 `success/duplicate/`
- 🔐 **账号别名机制**：任务里只写别名（如 `dy-01`），手机号只存在本机 `config.yaml`，不随任务/仓库流转
- 🗂️ **结果归档 + 数据库**：success/fail 目录保存任务与 result.json，发布记录入库（SQLite）
- 🛡️ **优雅启停**：stop 后当前平台发完才退出；崩溃重启自动从中断处继续
- 🧪 **免账号自测**：内置模拟 API，不联网即可跑通 成功/重试/失败/去重/定时 全流程
- 💻 **多环境可跑**：系统 Python 或 内嵌便携运行时 均可（详见 DEPLOY.md）

## 🗂️ 目录结构

```
zidongfabu/
├── scheduler/          # 调度服务源码（自研：config/db/main/matrix_client/mock_api/processor）
├── scripts/            # 自测脚本（run_tests）、GitHub 推送辅助脚本
├── examples/任务模板/    # 任务文件夹模板（info.json 示例）
├── docs/使用说明.md      # 详细使用说明（配置账号/发布/排障）
├── matrixmedia/        # MatrixMedia 安装包放置处（上游下载，不随仓库分发）
├── config.yaml         # 全部配置（账号别名占位，填写真实手机号前请看注意事项）
├── requirements.txt    # Python 依赖（锁定版本）
├── start.bat           # 一键启动（检测/拉起 MatrixMedia + 后台调度服务）
├── stop.bat            # 一键停止（优雅停调度 + 关闭 MatrixMedia）
├── install.bat         # 还原内嵌运行时/离线依赖（可选离线部署）
├── README.md / DEPLOY.md / LICENSE / .gitignore
├── 部署方案.md          # 原项目部署笔记
├── 项目速览.md          # 原项目速览备忘
└── （首次运行自动生成）watch/ pending/ success/ fail/ data/ logs/
```

> 💡 本仓库只包含**源代码 / 脚本 / 配置 / 文档**。
> 内嵌 Python 运行时、离线 wheels、MatrixMedia 安装包等**大件不随仓库分发**，获取方式见下方「大件资源下载」与 DEPLOY.md。

## 🚀 快速开始（拉到新电脑即可部署）

### 环境要求

- 操作系统：Windows 10/11 64 位
- 运行时：Python 3.12+（`pip install -r requirements.txt`），或按 DEPLOY.md 还原内嵌运行时（免装 Python）
- 上游：MatrixMedia（GPL-2.0，首次需下载安装包并登录各平台账号一次）

### 1. 克隆

```bash
git clone https://github.com/yishui111/zidongfabu.git
cd zidongfabu
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 准备 MatrixMedia 与账号

1. 从 [MatrixMedia 官方 Release](https://github.com/hanliang97/MatrixMedia/releases) 下载 Windows 安装包，放入 `matrixmedia/` 目录（`start.bat` 会识别并自动静默安装），或手动安装一次；
2. 打开 MatrixMedia，登录你要用的各平台账号（每平台登录一次，登录态保存在本机）；
3. 编辑 `config.yaml` 的 `accounts` 段，把账号别名映射到手机号（与 MatrixMedia「账号管理」一致）。

### 4. 启动

```bash
# Windows：双击 start.bat，或命令行运行：
start.bat
```

`start.bat` 会：检测 Python → 检查依赖 → 拉起 MatrixMedia 并等待其 API（端口 30088）就绪 → 后台启动调度服务（pythonw，无黑窗口）。

### 5. 发布与验证

把任务文件夹放进 `watch/`（格式见 `examples/任务模板/`），3 秒内自动开始处理：
全部成功 → `success/`；有失败 → `fail/`（附 `result.json`）；重复视频 → `success/duplicate/`。日志在 `logs/scheduler.log`。

停止：双击 `stop.bat`。

## 📥 大件资源下载（按需获取，不随仓库分发）

| 资源 | 用途 | 下载地址 / 获取方式 |
| ---- | ---- | ---- |
| MatrixMedia 安装包（约 70MB，win-x64） | 各平台网页端自动上传引擎（上游 GPL-2.0） | [hanliang97/MatrixMedia Releases](https://github.com/hanliang97/MatrixMedia/releases)，放入 `matrixmedia/` |
| Python 3.12 嵌入式运行时（可选，离线免装 Python） | 自包含运行（配合 cache/wheels） | [python.org 官方下载](https://www.python.org/downloads/windows/) 嵌入式包，详见 DEPLOY.md |
| 离线 wheels（可选，无网环境） | 离线安装依赖 | 用 `pip download -r requirements.txt -d wheels` 生成，详见 DEPLOY.md |

## 🧪 自动化自测（不需要真实账号/网络）

```bash
scripts\run_tests.bat
```

启动内置模拟 API（端口 31088），覆盖：正常多平台发布、失败重试后成功、固定失败平台进 fail、一成一败部分成功、重复视频去重、定时到点发布。

## 🛠️ 本地开发 & 提交

```bash
git add .
git commit -m "feat: xxx"
git push origin main
```

推送辅助：`scripts\push-github.bat`（交互式填入仓库地址）。

## ❓ 常见问题（FAQ）

- **Q：发布失败提示未登录 / Cookie 过期？** A：打开 MatrixMedia 重新扫码/登录对应平台即可，登录态会自动复用。
- **Q：任务一直停在 pending/？** A：查看 `info.json` 的 `publish_at` 是否在未来时间，或看 `logs/scheduler.log`。
- **Q：提示「账号别名未配置」？** A：在 `config.yaml` 的 `accounts` 段补上对应别名→手机号映射。
- **Q：MatrixMedia 窗口打不开？** A：删除 `%LOCALAPPDATA%\matrixmedia` 后，重跑 `matrixmedia/` 下的安装包。
- **Q：平台页面改版导致发布失败？** A：MatrixMedia 是上游维护项目，去其 Release 页下载新版本替换 `matrixmedia/` 安装包。
- **Q：没有 Python 也不想装？** A：按 DEPLOY.md「方式二：自包含离线部署」还原内嵌运行时 + wheels。
- **Q：需要改端口？** A：编辑 `config.yaml` 的 `matrix_api.base_url`（默认 `http://127.0.0.1:30088`）。

## ⚠️ 注意事项

- **账号安全**：本仓库 `config.yaml` 只含占位符，**请勿把真实手机号/账号/Cookie 提交到公开仓库**；登录态由 MatrixMedia 保存在本机；
- **平台合规**：自动化批量发布可能违反部分平台服务条款，请仅用于自己账号的低频、真实发布，避免批量刷量，账号风险自负；
- 本仓库仅供学习交流使用，使用后果自负；
- 调度服务与 MatrixMedia 相互独立开源（本仓库 MIT / 上游 GPL-2.0），通过 HTTP API 集成，不构成代码传染。

## 📄 许可证

- 本仓库（调度服务）：MIT License（见 [LICENSE](LICENSE)）
- MatrixMedia（矩媒）：上游开源项目，GPL-2.0，以独立进程方式被调用

## 🙏 支持与致谢

如果这个项目帮到了你，**请点亮右上角的 ⭐ Star**，你的支持是我持续更新的最大动力！
