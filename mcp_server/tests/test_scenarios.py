"""
端到端场景驱动集成测试 (Scenario-driven Integration Tests)
严格对齐用户指令需求：
- 【场景 1：空白海报排版】：创建画布 -> 生成主体图层 -> 触发扣图 -> 调色变换 -> 获取预览验证
- 【场景 2：多图层批量事务】：批处理 run_pipeline 执行失败时的回滚与错误隔离
- 【场景 3：draw-things-cli 调用与约束】：参数合法性校验 (64整数倍拦截、模型步数CFG锁定)
"""

import json
import os
import tempfile
import time
import unittest
import uuid

from mcp_server.client import CompositorRPCError
from mcp_server.draw_things import DrawThingsService
from mcp_server.mock_bridge import MockCompositorBridgeServer
from mcp_server.server import CompositorMCPServer


class TestCompositorScenarios(unittest.TestCase):
    def setUp(self):
        self.sock_path = os.path.join(
            "/tmp", f"test_scenario_{uuid.uuid4().hex[:8]}.sock"
        )
        self.mock_server = MockCompositorBridgeServer(socket_path=self.sock_path)
        self.mock_server.start()
        time.sleep(0.05)

        self.dt_service = DrawThingsService(mock=True)
        client = self.mock_server.create_connected_client()
        self.server = CompositorMCPServer(
            draw_things_service=self.dt_service, client=client
        )

    def tearDown(self):
        self.server.client.disconnect()
        self.mock_server.stop()
        if os.path.exists(self.sock_path):
            try:
                os.unlink(self.sock_path)
            except OSError:
                pass

    def test_scenario_1_blank_poster_composition(self):
        """
        【场景 1：空白海报排版】
        端到端全链路业务流程：
        1. 创建 1080x1920 海报画布
        2. 生成 AI 主体图层 (auto_matting=True 自动触发 Apple Vision 抠图)
        3. 对主体图层进行位置缩放变换
        4. 对图层调整调色参数 (提升对比度与饱和度)
        5. 抓取 Metal 即时渲染画面预览并校验图层树状态
        """
        # Step 1: 创建画布
        canvas_res = self.server.compositor_create_canvas(
            width=1080, height=1920, name="Cyberpunk_Movie_Poster"
        )
        self.assertEqual(canvas_res["status"], "success")
        self.assertEqual(canvas_res["canvas"]["width"], 1080)
        self.assertEqual(canvas_res["canvas"]["height"], 1920)

        # Step 2: 自动生成素材并插入图层 + 自动抠图
        gen_res = self.server.compositor_generate_and_add_layer(
            prompt="futuristic neon cyber samurai girl standing in pouring rain, cinematic lighting",
            style="realistic",
            width=768,
            height=1024,
            auto_matting=True,
        )
        self.assertEqual(gen_res["status"], "success")
        layer_id = gen_res["layer_id"]
        self.assertTrue(gen_res["matted"])
        self.assertTrue(gen_res["matting_result"]["matted"])

        # Step 3: 图层位置居中微调与缩放
        transform_res = self.server.compositor_transform_layer(
            layer_id=layer_id,
            x=156.0,
            y=400.0,
            scale_x=1.2,
            scale_y=1.2,
            rotation=0.0,
        )
        self.assertEqual(transform_res["status"], "success")
        self.assertEqual(transform_res["layer"]["x"], 156.0)
        self.assertEqual(transform_res["layer"]["scale_x"], 1.2)

        # Step 4: 调色参数调节 (对比度 +15, 饱和度 +10)
        color_res = self.server.compositor_adjust_color(
            layer_id=layer_id,
            brightness=5.0,
            contrast=15.0,
            saturation=10.0,
        )
        self.assertEqual(color_res["status"], "success")
        self.assertEqual(color_res["layer"]["contrast"], 15.0)

        # Step 5: 抓取即时画面 Base64 预览供多模态视觉分析
        preview_res = self.server.compositor_capture_preview()
        self.assertEqual(preview_res["status"], "success")
        self.assertIn("preview_base64", preview_res)
        self.assertEqual(preview_res["width"], 1080)
        self.assertEqual(preview_res["height"], 1920)

        # Step 6: 校验图层树状态闭环
        state = self.server.compositor_get_state()
        self.assertEqual(state["layer_count"], 1)
        layer = state["layers"][0]
        self.assertEqual(layer["id"], layer_id)
        self.assertTrue(layer["matted"])
        self.assertEqual(layer["contrast"], 15.0)

    def test_scenario_2_pipeline_atomic_rollback(self):
        """
        【场景 2：多图层批量事务与错误回滚隔离】
        批处理 run_pipeline 执行过程中若遭遇非预期错误或指令非法，
        必须具备原子事务保护，完整回滚至流水线执行前的状态，防止残留半脏数据。
        """
        # 先建立一个初始画布，并添加图层 0 作为初始基线
        self.server.compositor_create_canvas(width=1920, height=1080, name="BaseCanvas")
        initial_layer = self.server.compositor_add_layer(
            image_path="/tmp/background.png", name="Background", x=0, y=0
        )
        initial_state = self.server.compositor_get_state()
        self.assertEqual(initial_state["layer_count"], 1)

        # 构造批量 pipeline: 包含 2 个合法动作 + 1 个故意非法的动作
        pipeline_actions = [
            {
                "action": "add_layer",
                "args": {"image_path": "/tmp/decor_1.png", "name": "Decor1", "x": 100, "y": 100},
            },
            {
                "action": "add_layer",
                "args": {"image_path": "/tmp/decor_2.png", "name": "Decor2", "x": 200, "y": 200},
            },
            {
                "action": "transform_layer",
                "args": {"layer_id": "non_existent_layer_xyz", "x": 999},  # 必定失败
            },
        ]

        # 执行流水线，应抛出异常
        with self.assertRaises(CompositorRPCError) as ctx:
            self.server.compositor_run_pipeline(actions=pipeline_actions)
        self.assertIn("Pipeline transaction failed", str(ctx.exception))

        # 核心断言：事务回滚后，图层树必须与 Pipeline 执行前完全一致，不能残留 Decor1 或 Decor2
        after_state = self.server.compositor_get_state()
        self.assertEqual(after_state["layer_count"], 1)
        self.assertEqual(after_state["layers"][0]["id"], initial_layer["layer_id"])

        # 再执行一个全部合法的流水线以验证流水线正常能力
        valid_actions = [
            {
                "action": "add_layer",
                "args": {"image_path": "/tmp/valid_1.png", "name": "Valid1", "x": 10, "y": 10},
            },
            {
                "action": "add_layer",
                "args": {"image_path": "/tmp/valid_2.png", "name": "Valid2", "x": 20, "y": 20},
            },
        ]
        valid_res = self.server.compositor_run_pipeline(actions=valid_actions)
        self.assertEqual(valid_res["status"], "success")
        self.assertEqual(valid_res["executed_count"], 2)

        final_state = self.server.compositor_get_state()
        self.assertEqual(final_state["layer_count"], 3)

    def test_scenario_3_draw_things_constraints_and_validation(self):
        """
        【场景 3：draw-things-cli 约束规范与容错】
        严格断言：
        1. 64 整数倍尺寸拦截 (如 500x700 或 1000x1000 均被拒绝)
        2. Prompt 不能为空
        3. 风格路由严密锁定大模型和步数参数
        """
        # 非 64 整数倍分辨率拦截
        with self.assertRaises(ValueError) as ctx:
            self.server.compositor_generate_and_add_layer(
                prompt="test prompt", width=500, height=700
            )
        self.assertIn("必须为 64 的整数倍", str(ctx.exception))

        # 空 prompt 拦截
        with self.assertRaises(ValueError) as ctx:
            self.server.compositor_generate_and_add_layer(prompt="")
        self.assertIn("Prompt 提示词不能为空", str(ctx.exception))

        # 验证各风格路由在生图返回中的元数据一致性
        res_oil = self.dt_service.generate(
            prompt="oil painting masterpiece", style="oil_painting", width=512, height=768
        )
        self.assertEqual(res_oil["model"], "majicmixrealistic_v7_f16.ckpt")
        self.assertEqual(res_oil["steps"], 25)
        self.assertEqual(res_oil["cfg"], 6.5)

        res_flux = self.dt_service.generate(
            prompt="hyperrealistic portrait", style="realistic", width=768, height=1024
        )
        self.assertEqual(res_flux["model"], "flux_2_klein_4b_q6p.ckpt")
        self.assertEqual(res_flux["steps"], 4)
        self.assertEqual(res_flux["cfg"], 1.0)


if __name__ == "__main__":
    unittest.main()
