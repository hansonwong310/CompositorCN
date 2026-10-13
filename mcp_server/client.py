"""
Unix Domain Socket 客户端连接器 (CompositorSocketClient)
用于与 Compositor 原生 Swift Bridge 进程 (/tmp/compositor_agent.sock) 进行高可靠双向通信。
特性：
- JSON-RPC 2.0 帧编码与多行流式解码
- 自动断线重连与指数退避
- 严密请求超时控制与并发线程安全
"""

import json
import logging
import os
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("CompositorSocketClient")


class CompositorError(Exception):
    """Compositor 客户端基础异常"""
    pass


class CompositorConnectionError(CompositorError):
    """Socket 连接异常（未启动、拒绝连接或意外断开）"""
    pass


class CompositorTimeoutError(CompositorError):
    """请求超时异常"""
    pass


class CompositorRPCError(CompositorError):
    """服务端返回的 JSON-RPC 错误"""
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"RPC Error [{code}]: {message}")
        self.code = code
        self.message = message
        self.data = data


class CompositorSocketClient:
    def __init__(
        self,
        socket_path: str = "/tmp/compositor_agent.sock",
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 0.2,
        sock_factory: Optional[Callable[[], socket.socket]] = None,
    ):
        self.socket_path = socket_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.sock_factory = sock_factory

        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._next_id = 1
        self._buffer = ""

    def is_connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> None:
        """连接到 Unix Domain Socket"""
        with self._lock:
            self._connect_locked()

    def _connect_locked(self) -> None:
        if self._sock is not None:
            return

        if self.sock_factory:
            try:
                sock = self.sock_factory()
                sock.settimeout(self.timeout)
                self._sock = sock
                self._buffer = ""
                logger.info("已通过自定义工厂成功建立 Socket 连接")
                return
            except Exception as e:
                raise CompositorConnectionError(f"通过工厂建立 Socket 失败: {e}")

        if not os.path.exists(self.socket_path):
            raise CompositorConnectionError(
                f"Socket 文件不存在: {self.socket_path}。请确认 Compositor.app 是否已启动。"
            )

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self.socket_path)
            self._sock = sock
            self._buffer = ""
            logger.info(f"已成功连接至 Compositor Socket: {self.socket_path}")
        except Exception as e:
            sock.close()
            raise CompositorConnectionError(f"无法连接至 Socket {self.socket_path}: {e}")

    def disconnect(self) -> None:
        """安全关闭连接"""
        with self._lock:
            self._disconnect_locked()

    def _disconnect_locked(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
            self._buffer = ""
            logger.info("已断开 Socket 连接")

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """发送 JSON-RPC 2.0 请求并等待响应，支持失败重试"""
        if params is None:
            params = {}

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            with self._lock:
                try:
                    if self._sock is None:
                        self._connect_locked()

                    req_id = self._next_id
                    self._next_id += 1

                    request_data = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": method,
                        "params": params,
                    }
                    payload = (json.dumps(request_data) + "\n").encode("utf-8")
                    self._sock.sendall(payload)

                    # 读取并解析响应
                    response = self._read_response_locked(expected_id=req_id)
                    if "error" in response:
                        err = response["error"]
                        raise CompositorRPCError(
                            code=err.get("code", -32000),
                            message=err.get("message", "Unknown error"),
                            data=err.get("data"),
                        )
                    return response.get("result")

                except socket.timeout as e:
                    self._disconnect_locked()
                    last_exception = CompositorTimeoutError(
                        f"指令 '{method}' 在 {self.timeout}s 内响应超时。"
                    )
                    break  # 超时通常不盲目立即重发以防副作用
                except (socket.error, BrokenPipeError, ConnectionResetError, CompositorConnectionError) as e:
                    self._disconnect_locked()
                    last_exception = CompositorConnectionError(
                        f"通信中断 ({type(e).__name__}): {e}"
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay * attempt)
                        continue
                    break
                except CompositorRPCError:
                    # 业务层 RPC 错误直接向外抛出，不进行重试
                    raise

        if last_exception:
            raise last_exception
        raise CompositorConnectionError(f"请求 '{method}' 失败，重试耗尽。")

    def _read_response_locked(self, expected_id: int) -> Dict[str, Any]:
        """按行缓冲读取直到获得匹配 expected_id 的响应帧"""
        deadline = time.time() + self.timeout
        while True:
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("id") == expected_id:
                        return data
                except json.JSONDecodeError:
                    logger.warning(f"丢弃异常非 JSON 数据: {line[:100]}")

            remaining = deadline - time.time()
            if remaining <= 0:
                raise socket.timeout("Timed out waiting for response frame")

            self._sock.settimeout(remaining)
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionResetError("Socket closed by remote bridge")
            self._buffer += chunk.decode("utf-8")

    # ==========================
    # 高层业务便捷包装
    # ==========================

    def create_canvas(self, width: int, height: int, name: str = "Untitled") -> Dict[str, Any]:
        return self.call("create_canvas", {"width": width, "height": height, "name": name})

    def add_layer(
        self, image_path: str, name: Optional[str] = None, x: float = 0.0, y: float = 0.0
    ) -> Dict[str, Any]:
        return self.call(
            "add_layer",
            {"image_path": image_path, "name": name, "x": x, "y": y},
        )

    def transform_layer(
        self,
        layer_id: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        scale_x: Optional[float] = None,
        scale_y: Optional[float] = None,
        rotation: Optional[float] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"layer_id": layer_id}
        if x is not None:
            params["x"] = x
        if y is not None:
            params["y"] = y
        if scale_x is not None:
            params["scale_x"] = scale_x
        if scale_y is not None:
            params["scale_y"] = scale_y
        if rotation is not None:
            params["rotation"] = rotation
        return self.call("transform_layer", params)

    def adjust_color(
        self,
        layer_id: str,
        brightness: float = 0.0,
        contrast: float = 0.0,
        saturation: float = 0.0,
        preset: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.call(
            "adjust_color",
            {
                "layer_id": layer_id,
                "brightness": brightness,
                "contrast": contrast,
                "saturation": saturation,
                "preset": preset,
            },
        )

    def apply_matting(self, layer_id: str) -> Dict[str, Any]:
        return self.call("apply_matting", {"layer_id": layer_id})

    def get_state(self) -> Dict[str, Any]:
        return self.call("get_state", {})

    def capture_preview(self) -> Dict[str, Any]:
        return self.call("capture_preview", {})

    def undo(self) -> Dict[str, Any]:
        return self.call("undo", {})

    def run_pipeline(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.call("run_pipeline", {"actions": actions})
