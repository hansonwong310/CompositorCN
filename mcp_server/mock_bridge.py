"""
Mock Compositor Bridge Server
用于本地测试与离线自测的 Unix Domain Socket 模拟服务器。
协议契约与原生 Swift CompositorAgentBridge 100% 对齐。
"""

import base64
import copy
import json
import logging
import os
import select
import socket
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MockBridge")


class MockCompositorBridgeServer:
    def __init__(self, socket_path: str = "/tmp/compositor_agent.sock"):
        self.socket_path = socket_path
        self._server_sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 模拟画布内部状态
        self.canvas: Optional[Dict[str, Any]] = None
        self.layers: Dict[str, Dict[str, Any]] = {}
        self.history_stack: List[Dict[str, Any]] = []
        self._layer_counter = 0

        # 测试钩子
        self.inject_disconnect_on_method: Optional[str] = None
        self.inject_delay_on_method: Optional[str] = None
        self.inject_delay_seconds: float = 0.0

    def create_connected_client(
        self, timeout: float = 1.0, max_retries: int = 3, retry_delay: float = 0.05
    ) -> Any:
        """创建直接连接到此 Mock Server 的 CompositorSocketClient (通过 socketpair 穿透沙箱)"""
        from mcp_server.client import CompositorSocketClient

        def factory() -> socket.socket:
            client_sock, server_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            threading.Thread(
                target=self._handle_client, args=(server_sock,), daemon=True
            ).start()
            return client_sock

        return CompositorSocketClient(
            socket_path=self.socket_path,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            sock_factory=factory,
        )

    def start(self) -> None:
        """启动 Mock Socket Server 监听"""
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_sock.bind(self.socket_path)
        self._server_sock.listen(5)
        self._server_sock.settimeout(0.5)

        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        logger.info(f"Mock Compositor Bridge Server 已在 {self.socket_path} 启动监听")

    def stop(self) -> None:
        """停止 Mock Server"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass
        logger.info("Mock Compositor Bridge Server 已停止")

    def _accept_loop(self) -> None:
        while self._running:
            try:
                client_sock, _ = self._server_sock.accept()
                threading.Thread(
                    target=self._handle_client, args=(client_sock,), daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _push_undo_snapshot(self) -> None:
        """保存当前画布快照供 Undo 回滚"""
        snapshot = {
            "canvas": copy.deepcopy(self.canvas),
            "layers": copy.deepcopy(self.layers),
        }
        self.history_stack.append(snapshot)
        if len(self.history_stack) > 50:
            self.history_stack.pop(0)

    def _handle_client(self, client_sock: socket.socket) -> None:
        buffer = ""
        client_sock.settimeout(1.0)
        try:
            while self._running:
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    buffer += data.decode("utf-8")
                except socket.timeout:
                    continue
                except Exception:
                    break

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        req = json.loads(line)
                        req_id = req.get("id")
                        method = req.get("method")
                        params = req.get("params", {})

                        # 故障注入：断线
                        if self.inject_disconnect_on_method == method:
                            client_sock.close()
                            return

                        # 故障注入：超时延迟
                        if self.inject_delay_on_method == method:
                            time.sleep(self.inject_delay_seconds)

                        resp = self._dispatch(req_id, method, params)
                        try:
                            client_sock.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                        except (BrokenPipeError, ConnectionResetError):
                            break
                    except json.JSONDecodeError:
                        err_resp = {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
                        }
                        try:
                            client_sock.sendall((json.dumps(err_resp) + "\n").encode("utf-8"))
                        except (BrokenPipeError, ConnectionResetError):
                            break
        finally:
            try:
                client_sock.close()
            except Exception:
                pass

    def _dispatch(self, req_id: Any, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            try:
                handler = getattr(self, f"_rpc_{method}", None)
                if not handler:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }
                result = handler(params)
                return {"jsonrpc": "2.0", "id": req_id, "result": result}
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(e)},
                }

    def _rpc_create_canvas(self, params: Dict[str, Any]) -> Dict[str, Any]:
        width = int(params.get("width", 1920))
        height = int(params.get("height", 1080))
        name = str(params.get("name", "Untitled"))
        if width <= 0 or height <= 0:
            raise ValueError("Canvas dimensions must be positive integers.")

        self._push_undo_snapshot()
        self.canvas = {"width": width, "height": height, "name": name}
        self.layers.clear()
        self._layer_counter = 0
        return {
            "status": "success",
            "canvas": copy.deepcopy(self.canvas),
            "message": f"Canvas '{name}' ({width}x{height}) created.",
        }

    def _rpc_add_layer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.canvas:
            raise RuntimeError("No active canvas. Please create a canvas first.")

        image_path = params.get("image_path")
        if not image_path:
            raise ValueError("Missing 'image_path' parameter.")

        self._push_undo_snapshot()
        self._layer_counter += 1
        layer_id = f"layer_{self._layer_counter}"
        name = params.get("name") or f"Layer {self._layer_counter}"
        x = float(params.get("x", 0.0))
        y = float(params.get("y", 0.0))

        layer_data = {
            "id": layer_id,
            "name": name,
            "image_path": image_path,
            "x": x,
            "y": y,
            "scale_x": 1.0,
            "scale_y": 1.0,
            "rotation": 0.0,
            "brightness": 0.0,
            "contrast": 0.0,
            "saturation": 0.0,
            "preset": None,
            "matted": False,
            "visible": True,
            "opacity": 1.0,
        }
        self.layers[layer_id] = layer_data
        return {
            "status": "success",
            "layer_id": layer_id,
            "layer": copy.deepcopy(layer_data),
        }

    def _rpc_transform_layer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        layer_id = params.get("layer_id")
        if not layer_id or layer_id not in self.layers:
            raise KeyError(f"Layer '{layer_id}' not found.")

        self._push_undo_snapshot()
        layer = self.layers[layer_id]
        if "x" in params and params["x"] is not None:
            layer["x"] = float(params["x"])
        if "y" in params and params["y"] is not None:
            layer["y"] = float(params["y"])
        if "scale_x" in params and params["scale_x"] is not None:
            layer["scale_x"] = float(params["scale_x"])
        if "scale_y" in params and params["scale_y"] is not None:
            layer["scale_y"] = float(params["scale_y"])
        if "rotation" in params and params["rotation"] is not None:
            layer["rotation"] = float(params["rotation"])

        return {
            "status": "success",
            "layer_id": layer_id,
            "layer": copy.deepcopy(layer),
        }

    def _rpc_adjust_color(self, params: Dict[str, Any]) -> Dict[str, Any]:
        layer_id = params.get("layer_id")
        if not layer_id or layer_id not in self.layers:
            raise KeyError(f"Layer '{layer_id}' not found.")

        self._push_undo_snapshot()
        layer = self.layers[layer_id]
        if "brightness" in params and params["brightness"] is not None:
            layer["brightness"] = float(params["brightness"])
        if "contrast" in params and params["contrast"] is not None:
            layer["contrast"] = float(params["contrast"])
        if "saturation" in params and params["saturation"] is not None:
            layer["saturation"] = float(params["saturation"])
        if "preset" in params and params["preset"] is not None:
            layer["preset"] = str(params["preset"])

        return {
            "status": "success",
            "layer_id": layer_id,
            "layer": copy.deepcopy(layer),
        }

    def _rpc_apply_matting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        layer_id = params.get("layer_id")
        if not layer_id or layer_id not in self.layers:
            raise KeyError(f"Layer '{layer_id}' not found.")

        self._push_undo_snapshot()
        layer = self.layers[layer_id]
        layer["matted"] = True
        return {
            "status": "success",
            "layer_id": layer_id,
            "matted": True,
            "message": "Apple Vision foreground mask applied successfully.",
        }

    def _rpc_get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "canvas": copy.deepcopy(self.canvas),
            "layers": [copy.deepcopy(l) for l in self.layers.values()],
            "layer_count": len(self.layers),
            "undo_available": len(self.history_stack) > 0,
        }

    def _rpc_capture_preview(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.canvas:
            raise RuntimeError("No canvas available for preview.")

        # 构造极简测试 1x1 PNG base64 数据
        tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return {
            "status": "success",
            "width": self.canvas.get("width", 1920),
            "height": self.canvas.get("height", 1080),
            "format": "image/png",
            "preview_base64": tiny_png_b64,
            "timestamp": time.time(),
        }

    def _rpc_undo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.history_stack:
            return {"status": "noop", "message": "Nothing to undo."}

        snapshot = self.history_stack.pop()
        self.canvas = snapshot["canvas"]
        self.layers = snapshot["layers"]
        return {
            "status": "success",
            "message": "Undo operation completed.",
            "remaining_undo_levels": len(self.history_stack),
        }

    def _rpc_run_pipeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        actions = params.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("'actions' must be a list of action dictionaries.")

        # 保存 Pipeline 执行前快照
        pre_pipeline_snapshot = {
            "canvas": copy.deepcopy(self.canvas),
            "layers": copy.deepcopy(self.layers),
        }

        results = []
        try:
            for idx, action in enumerate(actions):
                action_type = action.get("action")
                action_args = action.get("args", {})
                handler = getattr(self, f"_rpc_{action_type}", None)
                if not handler:
                    raise ValueError(f"Action '{action_type}' at index {idx} not recognized.")
                res = handler(action_args)
                results.append({"index": idx, "action": action_type, "result": res})
        except Exception as e:
            # 事务失败：物理回滚至 Pipeline 执行前状态
            self.canvas = pre_pipeline_snapshot["canvas"]
            self.layers = pre_pipeline_snapshot["layers"]
            raise RuntimeError(f"Pipeline transaction failed at index {idx}: {str(e)}. Changes rolled back.")

        return {
            "status": "success",
            "executed_count": len(results),
            "results": results,
        }
