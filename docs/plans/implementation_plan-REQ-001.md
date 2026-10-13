# 落地实施执行计划：Agent 驱动 Compositor (implementation_plan-REQ-001)

**Status: Approved**  
**Resolves: REQ-001**

---

## 1. 里程碑与阶段划分 (Milestones)

### 阶段一：Compositor 官方源码引入与基础编译
- **目标**：在项目空间拉取/链接 Robbie Tilton 的 Compositor 官方 Swift 源码，确保在本地 Xcode / `swift build` 下能够成功构建出原生可执行文件。
- **产出**：本地可直接运行并渲染出桌面视窗的 Compositor 编译 target。

### 阶段二：Swift 原生 CompositorAgentBridge 模块开发
- **目标**：在 Compositor 中实现原生桥接模块，包含：
  1. **Unix Domain Socket 监听器**：监听 `/tmp/compositor_agent.sock`，实现异步 JSON-RPC 协议解析。
  2. **画布操作原子加锁 (CanvasLock)**：线程安全的原子锁控制，规避 GUI 交互竞争。
  3. **图层操作与 Undo 注册**：图层增删、移动缩放、调色滤镜调节，并挂接到 `NSUndoManager`。
  4. **Apple Vision 原生抠图**：封装 `VNGenerateForegroundInstanceMaskRequest`，支持一键主体提取并绑定图层蒙版。
  5. **画布预览导出**：支持抓取当前渲染帧生成 PNG/JPEG 数据流供多模态回传。

### 阶段三：Python Compositor MCP Server 开发
- **目标**：基于 FastMCP 编写专属 MCP Server，封装双轨制工具集：
  1. **原子工具**：
     - `compositor_create_canvas`
     - `compositor_add_layer`
     - `compositor_transform_layer`
     - `compositor_adjust_color`
     - `compositor_apply_matting`
     - `compositor_get_state`
     - `compositor_capture_preview`
     - `compositor_undo`
  2. **批量流水线工具**：
     - `compositor_run_pipeline`（一次性批处理排版）
  3. **素材联动与兼容**：支持本地文件路径输入与 AI 生成图无缝插入。

### 阶段四：端到端联调与多模态闭环验证
- **目标**：配置 Agent MCP 路由，进行全流程实测：
  - 自然语言创建画布并排版多张素材。
  - 触发 Apple Vision 原生抠图。
  - 验证桌面 GUI 窗口实时渲染、Cmd+Z 物理回退与多模态画布审查。
