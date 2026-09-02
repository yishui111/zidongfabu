# AGENTS.md — 多平台视频自动发布调度系统 项目档案

> ⚠️ 修改本仓库前先读本文件（AI 助手/开发者项目记忆）。用户向文档见 README.md / DEPLOY.md。

## 1. 定位
任务文件夹驱动，把 AI 流水线产出的视频自动分发到抖音/快手/B站/头条/百家号/视频号/小红书/番茄视频（dy/ks/blbl/tt/bjh/sph/xhs/fqsp）的本地调度系统：watch 目录即放即发 → pending → 调 MatrixMedia HTTP API(127.0.0.1:30088) → success/fail 归档，含 MD5 去重/重试3次/定时发布/SQLite 记录。

## 2. 组件
| 组件 | 说明 |
| ---- | ---- |
| scheduler/ | 自研调度 7 个 .py |
| scripts/ | run_tests 自测 + push-github |
| examples/ | 任务模板（仅别名占位，无真实账号） |
| config.yaml | 账号「别名→手机号」仅本机配置（真实手机号勿 commit） |
| docs/使用说明.md | 使用文档 |
| LICENSE | MIT |

## 3. 公开版边界（不入库）
matrixmedia/*.exe(71MB 上游 GPL 安装包→README 指引去 hanliang97/MatrixMedia Releases 下载)、runtime/、wheels/、cache/、data/(tasks.db)、logs/、__pycache__、watch/pending/success/fail（运行时生成）、部署方案.txt(早期对话稿)。
> 平台账号登录态与 MatrixMedia 会话仅本机保存，绝不入库；平台合规风险见 README 免责声明。

## 4. 维护约定
- Windows: start.bat（内嵌 runtime 优先→cache 自动 install→系统 Python 三级回退）/ stop.bat / install.bat / scripts\run_tests.bat
- 改动后同步 README/DEPLOY/本文件；提交 `git push origin main`；中文 UTF-8、bat 纯 ASCII+CRLF+无 BOM（去 chcp）
---
### 关键点（2026-09-02 上传整理补充）
- 调度：watch 任务文件夹 → pending → 调 MatrixMedia HTTP API(127.0.0.1:30088) → success/fail 归档；平台 dy/ks/blbl/tt/bjh/sph/xhs/fqsp；MD5 去重/重试3次/定时/SQLite
- config.yaml 只放"别名→手机号"，真实手机号与平台登录态仅本机，勿 commit
- MatrixMedia 71MB 上游 GPL 安装包不入库 → matrixmedia/README 指引去 hanliang97/MatrixMedia Releases 下载
- 自测用模拟 API 31088（免账号）；start.bat：内嵌 runtime → cache 自动 install → 系统 python 三级回退
- 合规风险见 README 免责声明
