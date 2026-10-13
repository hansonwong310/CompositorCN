"""
Compositor MCP Server (FastMCP & Standard MCP 2024-11-05 兼容)
提供双轨制 MCP 工具接口：
1. 原子工具集：画布创建、图层管理、变换、调色、Apple Vision 硬件抠图、状态查询、即时预览导出、Undo
2. 批量流水线工具：compositor_run_pipeline (事务化批量排版)
3. AI 素材联动工具：compositor_generate_and_add_layer (深度整合 draw-things-cli 自动生图与一键主体抠图)
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Callable, Dict, List, Optional

from mcp_server.client import (
    CompositorConnectionError,
    CompositorRPCError,
    CompositorSocketClient,
    CompositorTimeoutError,
)
from mcp_server.draw_things import DrawThingsService

logger = logging.getLogger("CompositorMCPServer")


class CompositorMCPServer:
    """
    Compositor MCP Server 核心实现。
    封装底层 Socket Client 与 Draw Things CLI，提供标准的工具调用集合。
    """

    def __init__(
        self,
        socket_path: Optional[str] = None,
        draw_things_service: Optional[DrawThingsService] = None,
        client: Optional[CompositorSocketClient] = None,
    ):
        if client is not None:
            self.client = client
        else:
            sock_path = socket_path or os.environ.get(
                "COMPOSITOR_SOCKET_PATH", "/tmp/compositor_agent.sock"
            )
            self.client = CompositorSocketClient(socket_path=sock_path)
        self.dt_service = draw_things_service or DrawThingsService()
        self._register_tools()

    def _register_tools(self) -> None:
        self.tools: Dict[str, Dict[str, Any]] = {
            "compositor_create_canvas": {
                "name": "compositor_create_canvas",
                "description": "创建指定尺寸的空白画布并重置图层树（Top-Left 坐标系，原点在左上角）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "width": {
                            "type": "integer",
                            "description": "画布物理宽度（像素，如 1920、1080）",
                        },
                        "height": {
                            "type": "integer",
                            "description": "画布物理高度（像素，如 1080、1920）",
                        },
                        "name": {
                            "type": "string",
                            "description": "画布工程名称",
                            "default": "Untitled",
                        },
                    },
                    "required": ["width", "height"],
                },
                "handler": self.compositor_create_canvas,
            },
            "compositor_add_layer": {
                "name": "compositor_add_layer",
                "description": "向当前画布导入图片素材并创建新图层",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "本地图片文件的绝对路径",
                        },
                        "name": {
                            "type": "string",
                            "description": "图层名称（可选）",
                        },
                        "x": {
                            "type": "number",
                            "description": "图层左上角在画布中的 X 坐标 (像素)",
                            "default": 0.0,
                        },
                        "y": {
                            "type": "number",
                            "description": "图层左上角在画布中的 Y 坐标 (像素)",
                            "default": 0.0,
                        },
                    },
                    "required": ["image_path"],
                },
                "handler": self.compositor_add_layer,
            },
            "compositor_transform_layer": {
                "name": "compositor_transform_layer",
                "description": "对指定图层进行平移位置、缩放比例或旋转角度变换",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "layer_id": {
                            "type": "string",
                            "description": "目标图层的唯一标识符 (例如 'layer_1')",
                        },
                        "x": {
                            "type": "number",
                            "description": "新的 X 坐标 (像素)",
                        },
                        "y": {
                            "type": "number",
                            "description": "新的 Y 坐标 (像素)",
                        },
                        "scale_x": {
                            "type": "number",
                            "description": "水平缩放倍数 (例如 1.0 为原始大小，1.5 为放大 50%)",
                        },
                        "scale_y": {
                            "type": "number",
                            "description": "垂直缩放倍数",
                        },
                        "rotation": {
                            "type": "number",
                            "description": "旋转角度 (度数，顺时针方向)",
                        },
                    },
                    "required": ["layer_id"],
                },
                "handler": self.compositor_transform_layer,
            },
            "compositor_adjust_color": {
                "name": "compositor_adjust_color",
                "description": "调节图层调色参数（明度、对比度、饱和度或语义预设）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "layer_id": {
                            "type": "string",
                            "description": "目标图层的唯一标识符",
                        },
                        "brightness": {
                            "type": "number",
                            "description": "亮度调节 [-100, 100]，默认为 0",
                            "default": 0.0,
                        },
                        "contrast": {
                            "type": "number",
                            "description": "对比度调节 [-100, 100]，默认为 0",
                            "default": 0.0,
                        },
                        "saturation": {
                            "type": "number",
                            "description": "饱和度调节 [-100, 100]，默认为 0",
                            "default": 0.0,
                        },
                        "preset": {
                            "type": "string",
                            "description": "快捷预设 ('slight', 'medium', 'strong', 'vintage', 'dramatic')",
                        },
                    },
                    "required": ["layer_id"],
                },
                "handler": self.compositor_adjust_color,
            },
            "compositor_apply_matting": {
                "name": "compositor_apply_matting",
                "description": "调用 Apple Vision 硬件神经引擎 (VNGenerateForegroundInstanceMaskRequest) 提取主体并生成图层蒙版",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "layer_id": {
                            "type": "string",
                            "description": "需要抠出前景主体的目标图层 ID",
                        },
                    },
                    "required": ["layer_id"],
                },
                "handler": self.compositor_apply_matting,
            },
            "compositor_get_state": {
                "name": "compositor_get_state",
                "description": "查询当前画布尺寸、所有图层的层级树、可见性、坐标及调色属性",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.compositor_get_state,
            },
            "compositor_capture_preview": {
                "name": "compositor_capture_preview",
                "description": "抓取当前桌面画布的即时 Metal 渲染画面，导出为 Base64 供多模态视觉分析",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.compositor_capture_preview,
            },
            "compositor_undo": {
                "name": "compositor_undo",
                "description": "触发原生 NSUndoManager 回退最近一次操作（等效于键盘 Cmd+Z）",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.compositor_undo,
            },
            "compositor_run_pipeline": {
                "name": "compositor_run_pipeline",
                "description": "批量执行排版动作流水线。具备原子事务保护，任何步骤出错自动回退全部更改",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "actions": {
                            "type": "array",
                            "description": "动作列表，每项形如 {'action': 'add_layer', 'args': {...}}",
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["actions"],
                },
                "handler": self.compositor_run_pipeline,
            },
            "compositor_generate_and_add_layer": {
                "name": "compositor_generate_and_add_layer",
                "description": "调用本地 Draw Things CLI 渲染 AI 素材图片，自动插入为新图层，并可选触发 Apple Vision 主体抠图",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "AI 图像生成英文提示词",
                        },
                        "style": {
                            "type": "string",
                            "description": "风格路由：'speed'/'realistic' (FLUX.2 极速4步), 'oil_painting'/'vintage' (majicMix), 'portrait_oriental' (SDXL写真), 'flagship' (FLUX.1 Dev)",
                            "default": "realistic",
                        },
                        "width": {
                            "type": "integer",
                            "description": "生成图像宽度（必须为 64 的整数倍，如 768, 1024）",
                            "default": 1024,
                        },
                        "height": {
                            "type": "integer",
                            "description": "生成图像高度（必须为 64 的整数倍，如 768, 1024）",
                            "default": 1024,
                        },
                        "auto_matting": {
                            "type": "boolean",
                            "description": "生成后是否立即调用 Apple Vision 抠出前景主体",
                            "default": False,
                        },
                    },
                    "required": ["prompt"],
                },
                "handler": self.compositor_generate_and_add_layer,
            },
        }

    # ==========================
    # 工具业务逻辑实现
    # ==========================

    def compositor_create_canvas(
        self, width: int, height: int, name: str = "Untitled"
    ) -> Dict[str, Any]:
        return self.client.create_canvas(width=width, height=height, name=name)

    def compositor_add_layer(
        self,
        image_path: str,
        name: Optional[str] = None,
        x: float = 0.0,
        y: float = 0.0,
    ) -> Dict[str, Any]:
        return self.client.add_layer(image_path=image_path, name=name, x=x, y=y)

    def compositor_transform_layer(
        self,
        layer_id: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        scale_x: Optional[float] = None,
        scale_y: Optional[float] = None,
        rotation: Optional[float] = None,
    ) -> Dict[str, Any]:
        return self.client.transform_layer(
            layer_id=layer_id,
            x=x,
            y=y,
            scale_x=scale_x,
            scale_y=scale_y,
            rotation=rotation,
        )

    def compositor_adjust_color(
        self,
        layer_id: str,
        brightness: float = 0.0,
        contrast: float = 0.0,
        saturation: float = 0.0,
        preset: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.client.adjust_color(
            layer_id=layer_id,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            preset=preset,
        )

    def compositor_apply_matting(self, layer_id: str) -> Dict[str, Any]:
        return self.client.apply_matting(layer_id=layer_id)

    def compositor_get_state(self) -> Dict[str, Any]:
        return self.client.get_state()

    def compositor_capture_preview(self) -> Dict[str, Any]:
        return self.client.capture_preview()

    def compositor_undo(self) -> Dict[str, Any]:
        return self.client.undo()

    def compositor_run_pipeline(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.client.run_pipeline(actions=actions)

    def compositor_generate_and_add_layer(
        self,
        prompt: str,
        style: str = "realistic",
        width: int = 1024,
        height: int = 1024,
        auto_matting: bool = False,
    ) -> Dict[str, Any]:
        # 1. 调用 Draw Things 生成图片
        dt_res = self.dt_service.generate(
            prompt=prompt,
            style=style,
            width=width,
            height=height,
        )
        image_path = dt_res["image_path"]

        # 2. 插入到画布中作为新图层
        layer_name = f"AI_{style}_{os.path.basename(image_path)}"
        add_res = self.client.add_layer(
            image_path=image_path,
            name=layer_name,
            x=0.0,
            y=0.0,
        )
        layer_id = add_res.get("layer_id")

        # 3. 若 auto_matting 为 True，执行主体抠图
        matting_res = None
        if auto_matting and layer_id:
            matting_res = self.client.apply_matting(layer_id=layer_id)

        return {
            "status": "success",
            "generation": dt_res,
            "layer": add_res.get("layer"),
            "layer_id": layer_id,
            "matted": auto_matting,
            "matting_result": matting_res,
        }

    # ==========================
    # 标准 MCP JSON-RPC 协议层
    # ==========================

    def dispatch_mcp_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行 MCP 工具调用并返回标准格式"""
        if tool_name not in self.tools:
            raise KeyError(f"Tool '{tool_name}' not found.")
        handler = self.tools[tool_name]["handler"]
        return handler(**arguments)

    def run_stdio(self) -> None:
        """基于标准输入输出运行 MCP Server 循环"""
        logger.info("Compositor MCP Server (stdio) 已就绪，正在监听...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
                continue

            resp = self._process_mcp_message(msg)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

    def _process_mcp_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "compositor-mcp-server",
                        "version": "1.0.0",
                    },
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            tools_list = []
            for t in self.tools.values():
                tools_list.append(
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t["inputSchema"],
                    }
                )
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                result = self.dispatch_mcp_call(tool_name, arguments)

                content = []
                # 检查是否包含预览图像
                if isinstance(result, dict) and "preview_base64" in result:
                    content.append(
                        {
                            "type": "image",
                            "data": result["preview_base64"],
                            "mimeType": result.get("format", "image/png"),
                        }
                    )
                content.append(
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2),
                    }
                )

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": content, "isError": False},
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                        "isError": True,
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not supported: {method}",
                },
            }


def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    server = CompositorMCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()
