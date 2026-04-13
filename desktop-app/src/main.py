"""
DroidRun Desktop - 主程序入口
一个带图形界面的 DroidRun 桌面应用
"""

import customtkinter as ctk
from ui.main_window import MainWindow


def main():
    """主函数"""
    # 设置外观模式和主题
    ctk.set_appearance_mode("dark")  # "dark" 或 "light"
    ctk.set_default_color_theme("green")  # DroidRun 品牌色
    
    # 创建主窗口
    app = MainWindow()
    
    # 运行应用
    app.mainloop()


if __name__ == "__main__":
    main()

