# CompositorZH：Compositor 独立汉化插件 (Photoshop 专业级术语标准)

## 📌 设计理念与特色
1. **零源码侵入 (Zero-invasive)**：
   - 不修改原项目任何一行业务代码，原项目可保持纯净与上游最新分支同步。
   - 基于 macOS 原生 Bundle 本地化机制（`zh-Hans.lproj` 独立资源包注入）。
2. **升级无影响 (Upgrade-Resilient)**：
   - 当原作者发布新版 Compositor（通过 Homebrew 或 GitHub Releases 升级）后，无需等待任何代码合并，只需重新运行一行脚本即可秒级恢复汉化。
3. **行业标准专业翻译 (Photoshop Terminology)**：
   - 严格对照 Adobe Photoshop 官方简体中文版的经典术语习惯（如：正片叠底、滤色、色阶、曲线、内容识别填充、羽化、自由变换等），零翻译腔，修图师无缝切换。

---

## 🚀 使用指南

### 1. 一键安装 / 刷新汉化
当您安装了 Compositor（如通过 `brew install --cask robbietilton-compositor` 或从 GitHub 下载到 `/Applications`）：
```bash
python3 plugin/CompositorZH/Scripts/install_plugin.py
```
> 如果应用安装在非标准目录，可通过 `--app` 参数指定：
> ```bash
> python3 plugin/CompositorZH/Scripts/install_plugin.py --app /path/to/Compositor.app
> ```

### 2. 检查汉化状态
```bash
python3 plugin/CompositorZH/Scripts/install_plugin.py --status
```

### 3. 一键还原纯英文原生状态 (卸载)
```bash
python3 plugin/CompositorZH/Scripts/install_plugin.py --uninstall
```

---

## 📂 插件目录结构
```text
plugin/CompositorZH/
├── zh-Hans.lproj/
│   └── Localizable.strings   # 核心本地化词条包（对照中文版 Photoshop 术语库）
└── Scripts/
    └── install_plugin.py     # 独立挂载/卸载管理工具
```
