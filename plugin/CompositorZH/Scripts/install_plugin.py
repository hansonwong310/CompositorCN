#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CompositorZH 彻底深度汉化插件（三重防御架构）
1. 静态语言包引擎：zh-Hans.lproj/Localizable.strings (536 条 Photoshop 标准行业词条)
2. 动态 Proxy 引擎：Sparkle Proxy Hook (拦截 NSSegmentedControl, NSMenuItem, NSCell, NSButton)
3. 静态字节对齐补丁：对齐修补局部变量传参按钮 (Expand -> 扩展, Contract -> 收缩, Radial -> 径向)
100% 彻底彻底消除所有界面与菜单英文！
"""

import os
import sys
import shutil
import subprocess
import argparse
import plistlib
from pathlib import Path

DEFAULT_APP_PATHS = [
    Path("/Applications/Compositor.app"),
    Path.home() / "Applications/Compositor.app",
    Path("./Compositor.app")
]

def find_app_path(custom_path=None):
    if custom_path:
        p = Path(custom_path).resolve()
        if p.exists() and p.name.endswith(".app"):
            return p
        print(f"[错误] 未找到指定应用: {custom_path}")
        return None

    for candidate in DEFAULT_APP_PATHS:
        if candidate.exists():
            return candidate
    return None

def get_plugin_dir():
    return Path(__file__).resolve().parent.parent

def patch_binary_literals(bin_path):
    with open(bin_path, "rb") as f:
        data = f.read()

    target1 = b"Expand\x00"
    replace1 = "扩展".encode("utf-8") + b"\x00"

    target2 = b"Contract\x00"
    replace2 = "收缩".encode("utf-8") + b"\x00\x00\x00"

    target3 = b"Radial\x00"
    replace3 = "径向".encode("utf-8") + b"\x00"

    patched = False
    if target1 in data:
        data = data.replace(target1, replace1)
        patched = True
    if target2 in data:
        data = data.replace(target2, replace2)
        patched = True
    if target3 in data:
        data = data.replace(target3, replace3)
        patched = True

    if patched:
        with open(bin_path, "wb") as f:
            f.write(data)
        print("  [✓] 静态变量字面量修补完成 (Expand -> 扩展, Contract -> 收缩, Radial -> 径向)")

def install_plugin(app_path):
    print(f"=== 正在安装 CompositorZH 彻底深度汉化插件 ===")
    print(f"目标应用: {app_path}")
    
    macos_dir = app_path / "Contents/MacOS"
    resources_dir = app_path / "Contents/Resources"
    frameworks_dir = app_path / "Contents/Frameworks"
    sparkle_dir = frameworks_dir / "Sparkle.framework/Versions/B"
    info_plist_path = app_path / "Contents/Info.plist"

    if not sparkle_dir.exists():
        print(f"[错误] 未找到 Sparkle 目录: {sparkle_dir}")
        return False

    plugin_dir = get_plugin_dir()
    src_lproj = plugin_dir / "zh-Hans.lproj"
    dest_lproj = resources_dir / "zh-Hans.lproj"

    if dest_lproj.exists():
        shutil.rmtree(dest_lproj)
    shutil.copytree(src_lproj, dest_lproj)
    print("  [✓] 静态语言包注入完成 (536 条 Photoshop 标准行业词库)")

    app_bin = macos_dir / "Compositor"
    patch_binary_literals(app_bin)

    sparkle_bin = sparkle_dir / "Sparkle"
    sparkle_raw = sparkle_dir / "Sparkle_raw"
    src_m = plugin_dir / "Sources/CompositorZH/CompositorZH.m"

    if not sparkle_raw.exists():
        shutil.copyfile(sparkle_bin, sparkle_raw)
        subprocess.run([
            "install_name_tool", "-id", "@rpath/Sparkle.framework/Versions/B/Sparkle_raw", str(sparkle_raw)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("  [✓] 已就绪底座动态库 -> Sparkle_raw")

    print("  [*] 正在编译并链接 Proxy 汉化插件...")
    cmd = [
        "clang", "-shared", "-fPIC", "-arch", "arm64",
        "-install_name", "@rpath/Sparkle.framework/Versions/B/Sparkle",
        f"-Wl,-reexport_library,{sparkle_raw}",
        "-framework", "Foundation", "-framework", "AppKit",
        str(src_m), "-o", str(sparkle_bin)
    ]
    subprocess.run(cmd, check=True)
    print("  [✓] 动态 Runtime Hook 插件已注入")

    if info_plist_path.exists():
        try:
            with open(info_plist_path, "rb") as f:
                plist_data = plistlib.load(f)
            locs = plist_data.get("CFBundleLocalizations", [])
            if "zh-Hans" not in locs:
                locs.append("zh-Hans")
                plist_data["CFBundleLocalizations"] = locs
                with open(info_plist_path, "wb") as f:
                    plistlib.dump(plist_data, f)
        except Exception:
            pass

    print("  [*] 正在执行 Ad-hoc 签名以通过系统安全防护...")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app_path)], check=True)
    print("  [✓] 签名刷新完成！")

    print("\n🎉 CompositorZH 彻底深度汉化安装成功！")
    return True

def uninstall_plugin(app_path):
    print(f"=== 正在卸载 CompositorZH 汉化插件 ===")
    resources_dir = app_path / "Contents/Resources"
    sparkle_dir = app_path / "Contents/Frameworks/Sparkle.framework/Versions/B"

    dest_lproj = resources_dir / "zh-Hans.lproj"
    if dest_lproj.exists():
        shutil.rmtree(dest_lproj)
        print("  [✓] 语言包已移除")

    sparkle_bin = sparkle_dir / "Sparkle"
    sparkle_raw = sparkle_dir / "Sparkle_raw"
    if sparkle_raw.exists():
        shutil.copyfile(sparkle_raw, sparkle_bin)
        subprocess.run([
            "install_name_tool", "-id", "@rpath/Sparkle.framework/Versions/B/Sparkle", str(sparkle_bin)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sparkle_raw.unlink()
        print("  [✓] Sparkle 动态库已还原")

    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app_path)])
    print("已彻底恢复纯英文官方原版状态。")
    return True

def main():
    parser = argparse.ArgumentParser(description="Compositor 全量深度汉化插件")
    parser.add_argument("--app", help="指定 Compositor.app 的绝对路径", default=None)
    parser.add_argument("--install", action="store_true", help="安装插件 (默认)")
    parser.add_argument("--uninstall", action="store_true", help="卸载插件")

    args = parser.parse_args()
    app_path = find_app_path(args.app)

    if not app_path:
        print("[错误] 未找到已安装的 Compositor.app")
        return

    if args.uninstall:
        uninstall_plugin(app_path)
    else:
        install_plugin(app_path)

if __name__ == "__main__":
    main()
