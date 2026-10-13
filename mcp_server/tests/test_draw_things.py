"""
单元测试：Draw Things CLI 联动层参数校验、模型路由与 Mock 生成
"""

import os
import tempfile
import unittest

from mcp_server.draw_things import (
    STYLE_ROUTING_MAP,
    UNIVERSAL_NEGATIVE_PROMPT,
    DrawThingsService,
)


class TestDrawThingsService(unittest.TestCase):
    def setUp(self):
        # 强制开启 mock 模式进行离线自测
        self.service = DrawThingsService(mock=True)

    def test_resolution_multiple_of_64_validation(self):
        """测试 64 整数倍强制校验：非 64 倍数严密拦截"""
        # 合法尺寸测试通过
        self.service.validate_resolution(1024, 1024)
        self.service.validate_resolution(768, 1024)
        self.service.validate_resolution(512, 768)

        # 非 64 整数倍抛出 ValueError
        with self.assertRaises(ValueError) as ctx1:
            self.service.validate_resolution(500, 700)
        self.assertIn("必须为 64 的整数倍", str(ctx1.exception))

        with self.assertRaises(ValueError) as ctx2:
            self.service.validate_resolution(1000, 1000)
        self.assertIn("必须为 64 的整数倍", str(ctx2.exception))

        # 0 或负数拦截
        with self.assertRaises(ValueError):
            self.service.validate_resolution(0, 512)

    def test_model_routing_and_parameters(self):
        """测试各大画风的基底大模型路由与参数黄金法则"""
        # 1. 极速 / 默认现实风格路由 -> FLUX.2 Klein 4B (4步, cfg 1.0)
        cfg_realistic = self.service.route_model("realistic")
        self.assertEqual(cfg_realistic["model"], "flux_2_klein_4b_q6p.ckpt")
        self.assertEqual(cfg_realistic["steps"], 4)
        self.assertEqual(cfg_realistic["cfg"], 1.0)
        self.assertIn("shift", cfg_realistic["config_json"])

        cfg_speed = self.service.route_model("speed")
        self.assertEqual(cfg_speed["model"], "flux_2_klein_4b_q6p.ckpt")
        self.assertEqual(cfg_speed["steps"], 4)

        # 2. 油画 / 复古风格路由 -> majicmixrealistic_v7_f16.ckpt (25步, cfg 6.5)
        cfg_oil = self.service.route_model("oil_painting")
        self.assertEqual(cfg_oil["model"], "majicmixrealistic_v7_f16.ckpt")
        self.assertEqual(cfg_oil["steps"], 25)
        self.assertEqual(cfg_oil["cfg"], 6.5)

        # 3. 东方女性写真 -> biglove_photo6_f16.ckpt (28步, cfg 7.0)
        cfg_oriental = self.service.route_model("portrait_oriental")
        self.assertEqual(cfg_oriental["model"], "biglove_photo6_f16.ckpt")
        self.assertEqual(cfg_oriental["steps"], 28)

        # 4. 旗舰写实大片 -> flux_1_dev_q8p.ckpt (24步, cfg 1.0)
        cfg_flagship = self.service.route_model("flagship")
        self.assertEqual(cfg_flagship["model"], "flux_1_dev_q8p.ckpt")
        self.assertEqual(cfg_flagship["steps"], 24)

    def test_mock_image_generation(self):
        """测试 Mock 模式下生成合法本地 PNG 图片文件"""
        res = self.service.generate(
            prompt="cyberpunk ninja in the rain",
            style="realistic",
            width=768,
            height=1024,
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["mock"])
        output_path = res["image_path"]
        self.assertTrue(os.path.exists(output_path))
        # 验证文件大小 > 0 且头部为 PNG 魔数
        with open(output_path, "rb") as f:
            header = f.read(8)
            self.assertEqual(header, b"\x89PNG\r\n\x1a\n")

        # 清理临时文件
        try:
            os.unlink(output_path)
        except OSError:
            pass

    def test_empty_prompt_validation(self):
        """测试空 Prompt 输入拦截"""
        with self.assertRaises(ValueError):
            self.service.generate(prompt="   ", style="realistic")


if __name__ == "__main__":
    unittest.main()
