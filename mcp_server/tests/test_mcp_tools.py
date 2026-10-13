"""
单元测试：CompositorMCPServer 工具集成与 MCP 协议标准交互
"""

import json
import os
import tempfile
import time
import unittest
import uuid

from mcp_server.draw_things import DrawThingsService
from mcp_server.mock_bridge import MockCompositorBridgeServer
from mcp_server.server import CompositorMCPServer


class TestCompositorMCPTools(unittest.TestCase):
    def setUp(self):
        self.sock_path = os.path.join(
            "/tmp", f"test_mcp_tool_{uuid.uuid4().hex[:8]}.sock"
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

    def test_mcp_initialize_and_ping(self):
        """测试 MCP initialize 握手与 ping 心跳"""
        init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.server._process_mcp_message(init_req)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "compositor-mcp-server")
        self.assertIn("tools", resp["result"]["capabilities"])

        ping_req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        ping_resp = self.server._process_mcp_message(ping_req)
        self.assertEqual(ping_resp["result"], {})

    def test_tools_list_schema(self):
        """测试 tools/list 协议返回全部 10 项核心工具及其 Schema"""
        req = {"jsonrpc": "2.0", "id": 10, "method": "tools/list"}
        resp = self.server._process_mcp_message(req)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        expected_tools = [
            "compositor_create_canvas",
            "compositor_add_layer",
            "compositor_transform_layer",
            "compositor_adjust_color",
            "compositor_apply_matting",
            "compositor_get_state",
            "compositor_capture_preview",
            "compositor_undo",
            "compositor_run_pipeline",
            "compositor_generate_and_add_layer",
        ]
        for exp in expected_tools:
            self.assertIn(exp, tool_names)

    def test_tools_call_create_canvas_and_add_layer(self):
        """测试 tools/call 执行原子工具"""
        call_req = {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "compositor_create_canvas",
                "arguments": {"width": 1280, "height": 720, "name": "Banner"},
            },
        }
        resp = self.server._process_mcp_message(call_req)
        self.assertFalse(resp["result"]["isError"])
        content_text = resp["result"]["content"][0]["text"]
        data = json.loads(content_text)
        self.assertEqual(data["canvas"]["name"], "Banner")

    def test_capture_preview_multimodal_content(self):
        """测试 tools/call 执行 capture_preview 返回多模态图像 Content"""
        # 先创建画布
        self.server.compositor_create_canvas(width=800, height=600)

        call_req = {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "compositor_capture_preview",
                "arguments": {},
            },
        }
        resp = self.server._process_mcp_message(call_req)
        self.assertFalse(resp["result"]["isError"])
        contents = resp["result"]["content"]
        # 应包含一个 image 类型 content 和一个 text 类型 content
        image_content = next((c for c in contents if c["type"] == "image"), None)
        self.assertIsNotNone(image_content)
        self.assertEqual(image_content["mimeType"], "image/png")
        self.assertTrue(len(image_content["data"]) > 0)


if __name__ == "__main__":
    unittest.main()
