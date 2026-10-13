"""
单元测试：CompositorSocketClient 与 Mock Socket Server 协议与容错验证
"""

import os
import tempfile
import time
import unittest
import uuid

from mcp_server.client import (
    CompositorConnectionError,
    CompositorRPCError,
    CompositorSocketClient,
    CompositorTimeoutError,
)
from mcp_server.mock_bridge import MockCompositorBridgeServer


class TestCompositorSocketClient(unittest.TestCase):
    def setUp(self):
        self.sock_path = os.path.join(
            "/tmp", f"test_comp_{uuid.uuid4().hex[:8]}.sock"
        )
        self.mock_server = MockCompositorBridgeServer(socket_path=self.sock_path)
        self.mock_server.start()
        self.client = self.mock_server.create_connected_client(
            timeout=1.0, max_retries=3, retry_delay=0.05
        )

    def tearDown(self):
        self.client.disconnect()
        self.mock_server.stop()
        if os.path.exists(self.sock_path):
            try:
                os.unlink(self.sock_path)
            except OSError:
                pass

    def test_basic_create_canvas_and_get_state(self):
        """测试正常创建画布与状态获取"""
        res = self.client.create_canvas(width=1920, height=1080, name="Poster")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["canvas"]["width"], 1920)

        state = self.client.get_state()
        self.assertEqual(state["status"], "success")
        self.assertEqual(state["canvas"]["name"], "Poster")
        self.assertEqual(len(state["layers"]), 0)

    def test_layer_operations_and_undo(self):
        """测试图层增删改、调色、抠图及 Undo 回滚"""
        self.client.create_canvas(width=1000, height=1000, name="TestCanvas")

        # 添加图层
        add_res = self.client.add_layer(image_path="/tmp/test.png", name="Hero", x=50, y=80)
        layer_id = add_res["layer_id"]
        self.assertTrue(layer_id.startswith("layer_"))

        # 图层变换
        trans_res = self.client.transform_layer(layer_id=layer_id, scale_x=1.5, rotation=45.0)
        self.assertEqual(trans_res["layer"]["scale_x"], 1.5)
        self.assertEqual(trans_res["layer"]["rotation"], 45.0)

        # 调色
        color_res = self.client.adjust_color(layer_id=layer_id, brightness=15.0, saturation=-20.0)
        self.assertEqual(color_res["layer"]["brightness"], 15.0)

        # 抠图
        matting_res = self.client.apply_matting(layer_id=layer_id)
        self.assertTrue(matting_res["matted"])

        # Undo 回滚
        undo_res = self.client.undo()
        self.assertEqual(undo_res["status"], "success")
        # 抠图状态被回滚为 False
        state = self.client.get_state()
        layer = next(l for l in state["layers"] if l["id"] == layer_id)
        self.assertFalse(layer["matted"])

    def test_timeout_handling(self):
        """测试请求超时检测与 CompositorTimeoutError 抛出"""
        self.mock_server.inject_delay_on_method = "create_canvas"
        self.mock_server.inject_delay_seconds = 1.5  # 超过 client 的 timeout=1.0s

        with self.assertRaises(CompositorTimeoutError):
            self.client.create_canvas(width=500, height=500)

    def test_reconnection_on_severed_connection(self):
        """测试连接意外断开后自动重连"""
        # 第一次请求成功
        self.client.create_canvas(width=800, height=600)
        self.assertTrue(self.client.is_connected())

        # 注入断线
        self.mock_server.inject_disconnect_on_method = "get_state"
        # 客户端遭遇断开后重试，下一次调用应当能够自愈
        try:
            self.client.get_state()
        except CompositorConnectionError:
            pass

        # 清除故障注入
        self.mock_server.inject_disconnect_on_method = None
        # 重试应当成功重连
        state = self.client.get_state()
        self.assertEqual(state["status"], "success")

    def test_missing_socket_error(self):
        """测试 Socket 文件不存在时抛出清晰的 CompositorConnectionError"""
        bad_client = CompositorSocketClient(socket_path="/tmp/non_existent_compositor.sock")
        with self.assertRaises(CompositorConnectionError) as ctx:
            bad_client.create_canvas(width=100, height=100)
        self.assertIn("Socket 文件不存在", str(ctx.exception))

    def test_rpc_error_propagation(self):
        """测试服务端业务报错 (如图层不存在) 正确抛出 CompositorRPCError"""
        self.client.create_canvas(width=800, height=600)
        with self.assertRaises(CompositorRPCError) as ctx:
            self.client.transform_layer(layer_id="non_existent_layer", x=10)
        self.assertIn("Layer 'non_existent_layer' not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
