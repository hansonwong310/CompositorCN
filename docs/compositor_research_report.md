# Robbie Tilton 开源图像编辑器 Compositor 深度调研与试用指南

## 一、项目概述与定位
* **官方网站**：[robbietilton.com/compositor](https://robbietilton.com/compositor)
* **GitHub 仓库**：[github.com/robbietilton/Compositor](https://github.com/robbietilton/Compositor)
* **开源协议**：MIT License
* **平台架构**：macOS 原生（Swift + Metal，Apple Silicon 优化）
* **体积对比**：仅约 **12 MB**（对比 Adobe Photoshop 动辄 6.4 GB+，缩减达 99.8%）

---

## 二、核心技术架构与特色
1. **纯原生 macOS 极速图形管线**：
   - 界面与系统交互基于 **Swift (SwiftUI / AppKit)**，深度契合 macOS 操作习惯。
   - 图形合成渲染由 **Apple Metal** 硬件加速强力驱动，低延迟高帧率。
2. **AI Agent / 自动化友好**：
   - 摒弃私有封闭的单体二进制工程格式，采用透明开放的项目目录与 JSON manifest。便于 AI 助手与自动化脚本直接生成、组合并修改工程文件。
3. **专业级核心修图合成能力**：
   - **完整图层系统**：图层编组、图层蒙版（Layer Mask）、剪切蒙版（Clipping Mask）。
   - **工业级混合模式与调色**：完整 Blend Modes，内置 Curves、Levels、Hue/Saturation 等 GPU 实时调色图层。
   - **非破坏性编辑与工具流**：支持仿制图章（Clone Stamp）、污点修复、自由变换等常用工具。
   - **PSD 兼容性**：原生支持打开与保存 8-bit RGB PSD/PSB 格式文件。

---

## 三、试用方案与安装方式

### 方式 1：Homebrew 快速安装（推荐）
在终端中执行：
```bash
brew install --cask robbietilton-compositor
```

### 方式 2：直接下载 Releases 运行
1. 前往 Releases 页面：`https://github.com/robbietilton/Compositor/releases`
2. 下载预编译的最新 `.dmg` 或 `.zip` 压缩包。
3. 解压拖入 `/Applications` 文件夹即可直接启动使用。

### 方式 3：Xcode 本地源码编译
```bash
git clone https://github.com/robbietilton/Compositor.git
cd Compositor
open Compositor.xcodeproj
```
