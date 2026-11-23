#!/usr/bin/env python3
"""
PradoOS Desktop Standalone App Builder.

Packages PradoOS into a native standalone GUI bundle using PyInstaller:
- macOS: dist/PradoOS.app and dist/PradoOS-macos.zip
- Windows: dist/PradoOS.exe and dist/PradoOS-windows.zip
- Linux: dist/PradoOS and dist/PradoOS-linux.tar.gz

Zero terminal required for students!
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
from typing import Callable, List, Optional
import zipfile


BUNDLE_IDENTIFIER = "es.ugr.pradoos"


def _default_has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def collect_pyinstaller_args(
    repo_root: Path,
    target_platform: Optional[str] = None,
    has_module: Optional[Callable[[str], bool]] = None,
) -> List[str]:
    """Collects platform-specific PyInstaller hidden imports and package data flags."""
    plat = target_platform or sys.platform
    check_mod = has_module or _default_has_module
    is_windows = plat in ("win32", "cygwin", "nt")

    hidden_imports = [
        "prado",
        "prado.ui",
        "prado.ui.tray",
        "prado.ui.server",
        "prado.ui.frontend",
        "prado.ui.dialogs",
        "prado.ui.icon",
        "prado.ui.autostart",
        "prado.ui.instance",
        "prado.ui.updater",
        "prado.i18n",
        "prado.config",
        "prado.cli",
        "pystray",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "cryptography",
        "keyring",
        "keyring.backends",
    ]
    collect_all: List[str] = []

    if check_mod("webview"):
        hidden_imports.append("webview")
        if is_windows:
            collect_all.append("webview")
            hidden_imports.extend([
                "webview.platforms.edgechromium",
                "webview.platforms.winforms",
                "webview.platforms.mshtml",
                "webview.guilib",
                "webview.window",
                "webview.event",
                "bottle",
                "proxy_tools",
                "typing_extensions",
                "tkinter",
                "tkinter.filedialog",
            ])

    if plat == "darwin":
        hidden_imports.extend([
            "pystray._darwin",
            "keyring.backends.macOS",
        ])
    elif is_windows:
        hidden_imports.extend([
            "pystray._win32",
            "keyring.backends.Windows",
            "_cffi_backend",
            "tkinter",
            "tkinter.filedialog",
        ])
        if check_mod("cffi"):
            collect_all.append("cffi")
        if check_mod("clr_loader"):
            collect_all.append("clr_loader")
        if check_mod("pythonnet"):
            collect_all.append("pythonnet")
            hidden_imports.extend(["pythonnet", "clr"])
    else:
        hidden_imports.extend([
            "pystray._appindicator",
            "pystray._xorg",
        ])

    args: List[str] = [f"--paths={repo_root / 'src'}"]
    if plat == "darwin":
        args.append(f"--osx-bundle-identifier={BUNDLE_IDENTIFIER}")
    for pkg in collect_all:
        args.append(f"--collect-all={pkg}")
    for hi in hidden_imports:
        args.append(f"--hidden-import={hi}")
    return args


def _resolve_app_version(repo_root: Path) -> str:
    src_dir = str(repo_root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    try:
        from prado import __version__
        return str(__version__).strip() or "0.2.0"
    except Exception:
        return "0.2.0"


def _resolve_release_tag(repo_root: Path) -> str:
    env_tag = os.environ.get("PRADO_RELEASE_TAG", "").strip()
    if env_tag:
        return env_tag
    gh_ref = os.environ.get("GITHUB_REF_NAME", "").strip()
    if gh_ref.lower().startswith("v"):
        return gh_ref
    return f"v{_resolve_app_version(repo_root)}"


def build() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    repo_root = Path(__file__).resolve().parent.parent
    assets_dir = repo_root / "assets"
    packaging_dir = repo_root / "packaging"
    dist_dir = repo_root / "dist"
    build_dir = repo_root / "build"

    print("🎓 Building PradoOS Standalone Desktop Application...")
    print(f"  • Repository Root: {repo_root}")
    print(f"  • Target Platform: {sys.platform} ({platform.machine()})")

    # 1. Ensure icon assets exist
    try:
        from prado.ui.icon import generate_desktop_assets

        generated = generate_desktop_assets(assets_dir)
        print(f"  ✓ Icon assets verified: {list(generated.keys())}")
    except Exception as exc:
        print(f"  ⚠ Warning generating icons: {exc}")

    # 2. Select appropriate platform icon
    icon_arg = []
    if sys.platform == "darwin":
        icns_file = assets_dir / "icon.icns"
        if icns_file.exists():
            icon_arg = [f"--icon={icns_file}"]
    elif sys.platform in ("win32", "cygwin") or os.name == "nt":
        ico_file = assets_dir / "icon.ico"
        if ico_file.exists():
            icon_arg = [f"--icon={ico_file}"]
    else:
        png_file = assets_dir / "icon.png"
        if png_file.exists():
            icon_arg = [f"--icon={png_file}"]

    # 3. Determine platform-specific PyInstaller imports and runtime data
    app_version = _resolve_app_version(repo_root)
    release_tag = _resolve_release_tag(repo_root)
    build_dir.mkdir(parents=True, exist_ok=True)
    build_info_file = build_dir / "prado_build.json"
    build_info_file.write_text(
        json.dumps({"release_tag": release_tag, "version": release_tag.lstrip("vV")}),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=PradoOS",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--add-data={build_info_file}{os.pathsep}.",
        *collect_pyinstaller_args(repo_root=repo_root),
    ]

    if icon_arg:
        cmd.extend(icon_arg)

    launcher_script = packaging_dir / "launch_app.py"
    cmd.append(str(launcher_script))

    print(f"\n🚀 Running PyInstaller...")
    ret = subprocess.run(cmd, cwd=str(repo_root))
    if ret.returncode != 0:
        print("\n❌ PyInstaller build failed!")
        return ret.returncode

    print("\n✓ Standalone binary built successfully in dist/")

    # 4. Create release archives
    if sys.platform == "darwin":
        app_path = dist_dir / "PradoOS.app"
        if app_path.exists():
            plist_file = app_path / "Contents" / "Info.plist"
            if plist_file.exists():
                with open(plist_file, "rb") as pf:
                    plist_data = plistlib.load(pf)
                plist_data["CFBundleIdentifier"] = BUNDLE_IDENTIFIER
                plist_data["CFBundleShortVersionString"] = app_version
                plist_data["CFBundleVersion"] = app_version
                with open(plist_file, "wb") as pf:
                    plistlib.dump(plist_data, pf)
                if shutil.which("codesign"):
                    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app_path)], check=False)
                print(f"  ✓ Updated Info.plist ({BUNDLE_IDENTIFIER}, v{app_version})")

            zip_dest = dist_dir / "PradoOS-macos.zip"
            print(f"📦 Packaging macOS release archive: {zip_dest.name}...")
            # Use ditto for preserving macOS app bundle metadata and symlinks
            subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app_path), str(zip_dest)], check=True)
            print(f"  ✓ Created: {zip_dest} ({zip_dest.stat().st_size / (1024 * 1024):.1f} MB)")
    elif sys.platform in ("win32", "cygwin") or os.name == "nt":
        win_dir = dist_dir / "PradoOS"
        exe_path = dist_dir / "PradoOS.exe"
        zip_dest = dist_dir / "PradoOS-windows.zip"
        if win_dir.is_dir():
            if not (win_dir / "PradoOS.exe").exists():
                print("❌ Missing dist/PradoOS/PradoOS.exe after PyInstaller build!")
                return 1
            wv_loaders = list(win_dir.rglob("WebView2Loader.dll"))
            if wv_loaders:
                print(f"  ✓ Bundled WebView2Loader.dll ({wv_loaders[0]})")
            else:
                print("  ⚠ Warning: WebView2Loader.dll not found under dist/PradoOS/")
            print(f"📦 Packaging Windows release archive: {zip_dest.name}...")
            with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in win_dir.rglob("*"):
                    if p.is_file():
                        zf.write(p, arcname=str(Path("PradoOS") / p.relative_to(win_dir)))
            print(f"  ✓ Created: {zip_dest} ({zip_dest.stat().st_size / (1024 * 1024):.1f} MB)")
        elif exe_path.exists():
            print(f"📦 Packaging Windows release archive: {zip_dest.name}...")
            with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(exe_path, arcname="PradoOS.exe")
            print(f"  ✓ Created: {zip_dest} ({zip_dest.stat().st_size / (1024 * 1024):.1f} MB)")

    print("\n🎉 Desktop build completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(build())
