# Compositor MCP Server

基于 Python 与标准 MCP (Model Context Protocol, 2024-11-05 规范) 开发的 Compositor 视觉合成服务，通过 Unix Domain Socket (`/tmp/compositor_agent.sock`) 驱动 Compositor macOS 原生图形工作台。

---

## 🌟 核心特性

1. **高可靠 IPC 通信**：
   - 专属 Unix Domain Socket 连接器 (`CompositorSocketClient`)。
   - JSON-RPC 2.0 协议帧封装，支持自动断线重连、超时检测与异常分级处理。
2. **双轨制工具架构**：
   - **原子工具**：画布创建、图层导入、变换、调色、Apple Vision 硬件抠图、状态查询、即时渲染预览抓取、原生 Undo 回滚。
   - **流水线工具**：`compositor_run_pipeline` 事务化批处理，单步出错全量安全回退。
3. **AI 工业级生图无缝联动**：
   - 深度集成 `draw-things-cli`，严格遵守分辨率 64 整数倍铁律。
   - 依据风格自动路由主力基底模型（FLUX.2 Klein 4B 极速 4 步 / majicMix 等）并注入物理防崩负向词。
   - 支持生成、插入图层与 Apple Vision 抠图一键闭环。
4. **测试驱动与离线自测**：
   - 内置 `MockCompositorBridgeServer`，在 Compositor.app 未启动时支持协议端到端无损自测。

---

## 🛠️ MCP 工具清单

| 工具名 | 类型 | 说明 | 核心参数 |
| :--- | :--- | :--- | :--- |
| `compositor_create_canvas` | 原子 | 创建指定尺寸空白画布并重置图层树 | `width`, `height`, `name` |
| `compositor_add_layer` | 原子 | 导入外部图片素材并创建新图层 | `image_path`, `name`, `x`, `y` |
| `compositor_transform_layer` | 原子 | 调整图层位置、缩放比例或旋转角度 | `layer_id`, `x`, `y`, `scale_x`, `scale_y`, `rotation` |
| `compositor_adjust_color` | 原子 | 调节图层明度、对比度、饱和度或预设 | `layer_id`, `brightness`, `contrast`, `saturation`, `preset` |
| `compositor_apply_matting` | 原子 | 触发 Apple Vision 抠图提取主体并绑定蒙版 | `layer_id` |
| `compositor_get_state` | 原子 | 查询画布尺寸及完整图层树属性 | 无 |
| `compositor_capture_preview` | 原子 | 抓取 Metal 实时画面供多模态视觉审查 | 无 |
| `compositor_undo` | 原子 | 触发原生 NSUndoManager 回退最近操作 | 无 |
| `compositor_run_pipeline` | 流水线 | 事务化批量执行多项排版动作 | `actions: list[dict]` |
| `compositor_generate_and_add_layer` | AI 联动 | 调度 Draw Things CLI 渲染并插入新图层 | `prompt`, `style`, `width`, `height`, `auto_matting` |

---

## 🚀 启动与配置接入

### 1. 命令行直接启动 (stdio 模式)
```bash
python3 -m mcp_server.server
```

### 2. 外部 Agent 配置 (Claude Desktop / Cursor / Antigravity)
在 `mcp_config.json` 中配置：
```json
{
  "mcpServers": {
    "compositor": {
      "command": "python3",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/Users/hansonwang/Documents/PS-Compositor",
      "env": {
        "COMPOSITOR_SOCKET_PATH": "/tmp/compositor_agent.sock",
        "DRAW_THINGS_MOCK": "0"
      }
    }
  }
}
```

---

## 🧪 自动化测试套件

运行包含 17 项单元测试与三大场景驱动集成测试的自测套件：
```bash
python3 mcp_server/test_mcp_mock.py
```
- **场景 1**：空白海报排版（创建画布 -> 生成主体 -> 自动抠图 -> 变换调色 -> 多模态预览审查）
- **场景 2**：多图层批量事务（流水线原子执行与出错回滚）
- **场景 3**：Draw Things 约束（64倍数校验、大模型步数锁定与 Prompt 防护）
