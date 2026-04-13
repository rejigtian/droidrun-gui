#!/usr/bin/env python3
"""
从 PNG 图标生成其他格式

用法：
    cd desktop-app
    python scripts/generate_icons.py
"""

from PIL import Image
import os
import sys
from pathlib import Path

def generate_icons():
    """从 app_icon.png 生成其他格式"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    icon_dir = project_dir / "resources" / "icons"
    png_path = icon_dir / "app_icon.png"
    
    print("🖼️  DroidRun 图标生成工具")
    print("=" * 50)
    print()
    
    if not png_path.exists():
        print(f"❌ 找不到图标文件: {png_path}")
        print()
        print("📝 请先完成以下步骤：")
        print("1. 将 Android 机器人图标保存为 PNG 格式")
        print(f"2. 放到这里: {png_path}")
        print("3. 再次运行此脚本")
        print()
        print("💡 提示：")
        print("   - 推荐尺寸：1024x1024 像素")
        print("   - 背景：透明")
        print("   - 格式：PNG")
        return 1
    
    print(f"📁 找到图标: {png_path}")
    
    # 检查文件大小
    file_size = png_path.stat().st_size
    print(f"📦 文件大小: {file_size / 1024:.1f} KB")
    
    # 加载图标
    try:
        img = Image.open(png_path)
        print(f"✅ 图标尺寸: {img.size[0]}x{img.size[1]} 像素")
        print(f"✅ 图标格式: {img.format}")
        print()
    except Exception as e:
        print(f"❌ 加载图标失败: {e}")
        return 1
    
    # 生成 .ico (Windows)
    print("🪟 生成 Windows 图标...")
    ico_path = icon_dir / "app_icon.ico"
    
    try:
        # Windows ICO 需要多个尺寸
        sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        
        # 创建多尺寸图标
        icon_images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # 保存为 ICO
        icon_images[0].save(
            ico_path,
            format='ICO',
            sizes=sizes
        )
        
        ico_size = ico_path.stat().st_size
        print(f"   ✅ 已生成: {ico_path.name} ({ico_size / 1024:.1f} KB)")
        print(f"   📐 包含尺寸: {', '.join([f'{s[0]}x{s[1]}' for s in sizes])}")
    except Exception as e:
        print(f"   ❌ 生成失败: {e}")
        print(f"   💡 可能需要安装 Pillow: pip install Pillow")
    
    print()
    
    # macOS 的 .icns 格式
    print("🍎 macOS 图标说明:")
    print("   ℹ️  PyInstaller 会自动从 PNG 转换为 .icns")
    print("   ℹ️  不需要手动生成 .icns 文件")
    print()
    
    # 总结
    print("=" * 50)
    print("✅ 图标生成完成！")
    print()
    print("📝 下一步：")
    print()
    print("1️⃣  测试开发模式：")
    print("   cd desktop-app")
    print("   ./run_dev.sh")
    print("   👀 查看窗口左上角是否显示图标")
    print()
    print("2️⃣  打包应用：")
    print("   ./quick_release.sh 1.2.3")
    print("   👀 检查打包的应用图标")
    print()
    print("3️⃣  分发应用：")
    print("   macOS: dist/*.dmg")
    print("   Windows: dist/*.exe")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(generate_icons())

