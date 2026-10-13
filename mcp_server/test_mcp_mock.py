#!/usr/bin/env python3
"""
Compositor MCP Server 本地 Mock 端到端自动化自测试驱动入口
支持在 Compositor App 未启动时使用 Mock Socket Server 进行全套协议端到端自测。
涵盖：
1. Socket 客户端断线重连、超时、编解码单元测试 (test_client)
2. Draw Things CLI 64倍数约束、大模型路由单元测试 (test_draw_things)
3. MCP Server 双轨制工具与标准 MCP 协议交互单元测试 (test_mcp_tools)
4. 端到端场景驱动集成测试：
   - 场景 1：空白海报排版 (创建画布 -> 生图 -> 抠图 -> 变换调色 -> 预览多模态)
   - 场景 2：多图层批量事务原子性与回滚
   - 场景 3：draw-things-cli 参数合法性与黄金路由
"""

import os
import sys
import time
import unittest

# 确保项目根目录在 sys.path 中
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


def main():
    print("=" * 70)
    print("🚀 启动 Compositor MCP Server 端到端自测试驱动 (TDD & Scenario-driven)")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.join(WORKSPACE_ROOT, "mcp_server", "tests"),
        pattern="test_*.py",
        top_level_dir=WORKSPACE_ROOT,
    )

    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"📊 测试结果统计:")
    print(f"   总执行用例: {result.testsRun}")
    print(f"   成功用例:   {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败 (Failures): {len(result.failures)}")
    print(f"   异常 (Errors):   {len(result.errors)}")
    print(f"   总耗时:     {duration:.2f} 秒")
    print("=" * 70)

    if result.wasSuccessful():
        print("✅ 恭喜！所有单元测试与端到端场景驱动测试 100% 验证通过！")
        sys.exit(0)
    else:
        print("❌ 警告：部分测试未通过，请检查错误详情。")
        sys.exit(1)


if __name__ == "__main__":
    main()
