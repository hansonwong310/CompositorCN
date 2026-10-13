"""
Draw Things CLI 深度联动服务 (DrawThingsService)
遵循 draw-things-cli 技能工业级生图规范：
- 分辨率严格校验 64 整数倍 (Multiple of 64)
- 依据画风自动路由四大主力基底模型 (FLUX.2 Klein 4B 极速 4步 / majicMix 等)
- 自动注入物理防崩负向词 (Universal Negative Prompt)
- 支持真实 CLI 调用与离线/测试环境 Mock 优雅降级
"""

import json
import logging
import os
import subprocess
import struct
import tempfile
import uuid
import zlib
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("DrawThingsService")

# 规范默认路径
DEFAULT_CLI_PATH = "/opt/homebrew/bin/draw-things-cli"
DEFAULT_MODELS_DIR = "/Volumes/MacMini 1T/DrawThings/Models.ext"

# 通用物理防崩负向词
UNIVERSAL_NEGATIVE_PROMPT = (
    "deformed, bad anatomy, bad hands, missing fingers, extra fingers, mutated, blurry, "
    "bad eyes, disfigured, poorly drawn face, mutation, duplicate, floating limbs, "
    "disconnected limbs, malformed limbs, out of focus, low quality, worst quality"
)

# 风格到模型参数的黄金映射表
STYLE_ROUTING_MAP = {
    "speed": {
        "model": "flux_2_klein_4b_q6p.ckpt",
        "steps": 4,
        "cfg": 1.0,
        "config_json": '{"shift": 3.0, "sampler": 16}',
    },
    "realistic": {
        "model": "flux_2_klein_4b_q6p.ckpt",
        "steps": 4,
        "cfg": 1.0,
        "config_json": '{"shift": 3.0, "sampler": 16}',
    },
    "oil_painting": {
        "model": "majicmixrealistic_v7_f16.ckpt",
        "steps": 25,
        "cfg": 6.5,
        "config_json": None,
    },
    "vintage": {
        "model": "majicmixrealistic_v7_f16.ckpt",
        "steps": 25,
        "cfg": 6.5,
        "config_json": None,
    },
    "portrait_oriental": {
        "model": "biglove_photo6_f16.ckpt",
        "steps": 28,
        "cfg": 7.0,
        "config_json": None,
    },
    "flagship": {
        "model": "flux_1_dev_q8p.ckpt",
        "steps": 24,
        "cfg": 1.0,
        "config_json": '{"shift": 3.0}',
    },
}


def create_minimal_png(width: int = 64, height: int = 64, color: Tuple[int, int, int] = (100, 150, 240)) -> bytes:
    """使用 Python 标准库生成合法极简 PNG 二进制流（用于 Mock 与离线自测）"""
    # PNG Signature
    png = b"\x89PNG\r\n\x1a\n"
    # IHDR Chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    png += struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    # IDAT Chunk (RGB uncompressed scanlines)
    raw_scanlines = bytearray()
    for _ in range(height):
        raw_scanlines.append(0)  # Filter type 0 (None)
        for _ in range(width):
            raw_scanlines.extend(color)
    compressed = zlib.compress(bytes(raw_scanlines))
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed))
    png += struct.pack(">I", len(compressed)) + b"IDAT" + compressed + idat_crc

    # IEND Chunk
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND"))
    png += struct.pack(">I", 0) + b"IEND" + iend_crc
    return png


class DrawThingsService:
    def __init__(
        self,
        cli_path: str = DEFAULT_CLI_PATH,
        models_dir: str = DEFAULT_MODELS_DIR,
        mock: bool = False,
    ):
        self.cli_path = cli_path
        self.models_dir = models_dir
        self.mock = mock or (os.environ.get("DRAW_THINGS_MOCK", "0") == "1")

    def validate_resolution(self, width: int, height: int) -> None:
        """严格校验尺寸是否为 64 的整数倍"""
        if width <= 0 or height <= 0:
            raise ValueError(f"尺寸必须为正整数: width={width}, height={height}")
        if width % 64 != 0 or height % 64 != 0:
            raise ValueError(
                f"分辨率必须为 64 的整数倍 (当前: {width}x{height})。"
                f"建议分辨率: 768x1024 (竖版3:4), 1024x1024 (1:1), 512x768"
            )

    def route_model(self, style: str) -> Dict[str, Any]:
        """依据风格获取模型参数"""
        style_key = style.lower().strip()
        if style_key in STYLE_ROUTING_MAP:
            return STYLE_ROUTING_MAP[style_key]
        # 默认回退至极速真实感 FLUX.2 Klein 4B
        return STYLE_ROUTING_MAP["realistic"]

    def generate(
        self,
        prompt: str,
        style: str = "realistic",
        width: int = 1024,
        height: int = 1024,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        根据提示词和风格生成 AI 素材图片
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt 提示词不能为空。")

        self.validate_resolution(width, height)
        config = self.route_model(style)

        if not output_path:
            filename = f"compositor_ai_{uuid.uuid4().hex[:8]}.png"
            output_path = os.path.join("/tmp", filename)

        neg = negative_prompt or UNIVERSAL_NEGATIVE_PROMPT

        # 判断是否进入 Mock 模式
        is_mock = self.mock or not os.path.exists(self.cli_path)

        if is_mock:
            logger.info(f"[Mock Mode] 模拟生成图像: {output_path} ({width}x{height}, style={style})")
            png_bytes = create_minimal_png(min(width, 128), min(height, 128))
            with open(output_path, "wb") as f:
                f.write(png_bytes)

            return {
                "status": "success",
                "image_path": output_path,
                "model": config["model"],
                "steps": config["steps"],
                "cfg": config["cfg"],
                "width": width,
                "height": height,
                "prompt": prompt,
                "style": style,
                "mock": True,
            }

        # 真实 CLI 命令行构建
        cmd = [
            self.cli_path,
            "generate",
            "--models-dir",
            self.models_dir,
            "-m",
            config["model"],
            "-p",
            prompt,
            "--negative-prompt",
            neg,
            "--steps",
            str(config["steps"]),
            "--cfg",
            str(config["cfg"]),
            "--width",
            str(width),
            "--height",
            str(height),
            "-o",
            output_path,
        ]

        if seed is not None:
            cmd.extend(["-s", str(seed)])
        if config.get("config_json"):
            cmd.extend(["--config-json", config["config_json"]])

        logger.info(f"执行 Draw Things CLI 生图: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180.0,
                check=True,
            )
            if not os.path.exists(output_path):
                raise RuntimeError(f"CLI 执行成功但未生成目标文件: {output_path}")

            return {
                "status": "success",
                "image_path": output_path,
                "model": config["model"],
                "steps": config["steps"],
                "cfg": config["cfg"],
                "width": width,
                "height": height,
                "prompt": prompt,
                "style": style,
                "mock": False,
            }
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr or e.stdout or str(e)
            raise RuntimeError(f"Draw Things CLI 渲染失败: {err_msg}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Draw Things CLI 渲染超时 (超过 180s)。")
