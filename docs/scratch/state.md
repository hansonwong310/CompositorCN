# Agent Active State (战术草稿本)

## 🎯 Current Target (当前聚焦的目标)
- [ ] 并行推进 MVP 核心工程：
  1. 子智能体 1 (Swift/Native Bridge): Compositor 官方源码适配与原生 Socket Bridge 模块构建
  2. 子智能体 2 (Python/MCP Server): Compositor MCP Server 工具体系搭建与 draw-things-cli 生图联动

## 🤖 Active Subagents (活跃子智能体)
- `23f1b0d7-2a1e-4438-b823-f6fc9569f277` (Role: Compositor Native Bridge Dev)
  - 任务: Compositor 官方源码拉取、Swift 构建验证与 Unix Domain Socket Bridge 实现 (Running, 正在运行 Swift 测试用例)
- `cc8b601f-3908-4d3a-a721-f9522b42db84` (Role: Compositor MCP Server Dev)
  - 状态: 已完成交付！
  - 成果: 完成 `mcp_server/` 搭建，包含客户端、draw-things-cli 联动与 10 项核心 MCP 工具，17 个 TDD/场景用例 100% 绿灯。

## 💡 Proven Facts (已验证的结论)
- 已完成需求深入访谈（Grill-me）并与用户就所有关键架构分支达成共识。
- 架构定型：外部 Agent -> FastMCP Server -> Unix Domain Socket (/tmp/compositor_agent.sock) -> Compositor 原生 Bridge (Swift)。
- 关键能力定型：桌面 GUI 窗口实时渲染联动、原生 Apple Vision 硬件抠图、标准 Top-Left 坐标系、调色参数双轨映射、严格原子加锁与原生 UndoManager 绑定、汉化插件解耦。
- 已建立标准四级规范文档：`requirements_board.md`、`Idea-REQ-001.md`、`system_design-REQ-001.md`、`implementation_plan-REQ-001.md`。
- 核心开发准则强化：已向所有子智能体注入【测试驱动 (TDD)】与【场景驱动 (Scenario-driven)】强约束（Swift 协议断言 + Pytest 场景集成测试，先红后绿）。

## ❌ Dead Ends (已证伪的死胡同)
- 禁止反编译二进制或做脆弱的外部输入模拟；必须基于官方开源源码进行原生 Bridge 扩展。
- 不使用可能被 SIP 拦截的外部注入方案来承载核心 IPC，采用源码级原生 Socket 监听。

## 🏃 Next Action (下一步明确行动)
- 启动子智能体进行 Compositor 官方源码仓库的拉取与本地构建验证。
