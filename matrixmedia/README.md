# MatrixMedia（矩媒）安装包放置目录

本仓库**不随附** MatrixMedia 安装包（上游开源项目，GPL-2.0，约 70MB 的 Windows 安装包，属大件不随仓库分发）。

**获取方式**：前往上游项目 Release 页面下载 Windows 安装包：

- 上游仓库：https://github.com/hanliang97/MatrixMedia/releases
- 原项目使用版本：`MatrixMedia-0.11.0-win-x64.exe`（新版本可直接替换）

**使用方式**（二选一）：

1. 把下载的安装包放入本目录（保持 `matrixmedia\MatrixMedia-*.exe` 命名），`start.bat` 检测到未安装时会自动静默安装；或
2. 直接双击安装包手动安装一次。

> MatrixMedia 独立开源（GPL-2.0），负责各平台网页端自动化上传，通过其内置 HTTP API 被本仓库调度服务驱动；本仓库（MIT）不修改其代码，两者互不传染。安装包在 .gitignore 中（`matrixmedia/*.exe`），不会被提交。
