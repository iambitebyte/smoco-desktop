#!/usr/bin/env python3
"""
图标转换工具 - 将 PNG 转换为 ICO 格式
"""

import sys

try:
    from PIL import Image

    def convert_png_to_ico(png_path, ico_path):
        """将 PNG 转换为 ICO（多尺寸）"""
        print(f"正在转换 {png_path} -> {ico_path}")

        # 打开 PNG 图像
        img = Image.open(png_path)

        # 定义所需的尺寸
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        # 创建不同尺寸的图标
        ico_images = []
        for size in sizes:
            try:
                # 调整大小（使用高质量重采样）
                resized = img.resize(size, Image.Resampling.LANCZOS)
                ico_images.append(resized)
            except Exception as e:
                print(f"  警告: 无法生成 {size} 尺寸: {e}")

        # 保存为 ICO 文件
        ico_images[0].save(
            ico_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in ico_images]
        )

        print(f"转换完成！生成了 {len(ico_images)} 个尺寸")

    if __name__ == "__main__":
        png_file = "smoco_logo_circle.png"
        ico_file = "smoco_logo_circle.ico"

        convert_png_to_ico(png_file, ico_file)
        print("\n图标文件已生成: smoco_logo_circle.ico")
        print("可以在 build.spec 中配置: icon='smoco_logo_circle.ico'")

except ImportError:
    print("错误: 需要安装 Pillow 库")
    print("安装命令: uv add --dev pillow")
    sys.exit(1)
