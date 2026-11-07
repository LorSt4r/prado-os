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

import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile


def build() -> int:
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

    # 3. Determine hidden imports
    hidden_imports = [
        "prado",
        "prado.ui",
        "prado.ui.tray",
        "prado.ui.server",
        "prado.ui.frontend",
        "prado.ui.dialogs",
        "prado.ui.icon",
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
    try:
        import webview  # noqa: F401
        hidden_imports.append("webview")
    except ImportError:
        pass

    if sys.platform == "darwin":
        hidden_imports.extend([
            "pystray._darwin",
            "keyring.backends.macOS",
        ])
    elif sys.platform in ("win32", "cygwin") or os.name == "nt":
        hidden_imports.extend([
            "pystray._win32",
            "keyring.backends.Windows",
        ])
    else:
        hidden_imports.extend([
            "pystray._appindicator",
            "pystray._xorg",
        ])

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=PradoOS",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--paths={repo_root / 'src'}",
    ]

    for hi in hidden_imports:
        cmd.append(f"--hidden-import={hi}")

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
