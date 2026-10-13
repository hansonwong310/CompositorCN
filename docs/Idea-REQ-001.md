# Idea: 自然语言 Agent 驱动 Compositor 图像创作与精准编辑

**Status: Approved**  
**Resolves: REQ-001**

---

## 1. 为什么做这个项目 (Why)
当前主流的 AI 生图体验多为“一步到位、黑盒生成”，缺乏如 Adobe Photoshop 等专业图像软件细粒度、非破坏性的图层排版、精准遮罩蒙版与调色控制。一旦画面细节有瑕疵，用户往往需要反复抽卡或手动导入笨重的桌面软件逐层修图。
本项目旨在结合 **Robbie Tilton 开源原生轻量图像合成器 Compositor (macOS Swift + Metal)** 与 **大语言模型 Agent**：
用户只需使用自然语言进行对话，Agent 即可跨进程精准操纵 Compositor 画布，实现图层创建、本地/生成素材插入、macOS 原生硬件级抠图蒙版、GPU 调色滤镜调节与自由排版变换，同时在 macOS 桌面实时展示渲染结果并保留系统级 Cmd+Z 撤销体验。

---

## 2. 调研与灵感 (Research & Inspiration)
1. **Photoshop 官方 Generative Workspace & UXP/Firefly 插件**：
   - 优势：成熟的生态与图层体系。
   - 痛点：Photoshop 安装包高达 6.4GB+，内存吞吐重，UXP/ExtendScript 脚本延迟高、异步桥接复杂且封闭。
2. **Robbie Tilton Compositor**：
   - 优势：仅约 12MB 的原生 macOS 编辑器，SwiftUI + Metal 硬件级超低延迟渲染管线，极适合作为本地轻量级图形驱动底座。
3. **Apple Vision 框架 (Vision Framework)**：
   - 原生 `VNGenerateForegroundInstanceMaskRequest` 能够在 macOS 神经引擎 (NPU) 上实现毫秒级的主体分离提取，无需额外加载数百兆的 Python 模型即可生成非破坏性图层蒙版。

---

## 3. 核心人机体验与交互愿景 (User Experience)
- **对话驱动排版**：用户输入：“新建一个 1920x1080 画布，导入这张人像并自动抠图，背景铺设一张赛博朋克城市图，给背景图层加一点高斯模糊并把色温调冷”。
- **桌面视窗实时可见 (Live Session)**：Compositor 窗口在桌面上保持开启，Agent 的每一次调用都在画布上以 Metal 硬件级帧率即时呈现，用户随时可以接管鼠标进行像素级手工微调。
- **多模态视觉闭环**：Agent 可主动抓取画布预览图，“眼见为实”评估视觉效果并迭代优化。
- **系统级 Undo/Redo 保障**：所有 Agent 操作均注册到原生 `UndoManager` 中，用户随时可以通过 `Cmd+Z` 一键回退。
