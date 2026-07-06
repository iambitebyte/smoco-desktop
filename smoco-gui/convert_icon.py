#!/usr/bin/env python3
"""
图标转换工具 - 将 PNG 转换为 ICO 格式
"""

import sys

try:
    from PIL import Image

    def convert_png_to_ico(png_path, ico_path):
        """将 PNG 转换为 ICO（多尺寸，PIL 从原图对每个尺寸做 LANCZOS 缩放）"""
        print(f"正在转换 {png_path} -> {ico_path}")

        img = Image.open(png_path)
        print(f"源图尺寸: {img.size}")

        # 多分辨率：直接对原图 save，PIL 自动缩放每个尺寸
        # （旧实现误用 ico_images[0]=16x16 作为 save 源，导致整个 ico 从 16x16 放大、全模糊）
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, format='ICO', sizes=sizes)

        print(f"转换完成！生成 {len(sizes)} 个尺寸: {sizes}")

    if __name__ == "__main__":
        png_file = "resources/icons/smoco_logo.png"
        ico_file = "smoco_logo_circle.ico"

        convert_png_to_ico(png_file, ico_file)
        print("\n图标文件已生成: smoco_logo_circle.ico")
        print("可以在 build.spec 中配置: icon='smoco_logo_circle.ico'")

except ImportError:
    print("错误: 需要安装 Pillow 库")
    print("安装命令: uv add --dev pillow")
    sys.exit(1)
