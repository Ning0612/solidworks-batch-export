"""SolidWorks 批次轉檔工具 - 套件入口點

支援以 `python -m swbatch` 方式啟動。
"""

import sys


def main() -> None:
    """主入口點"""
    import os
    # 強制使用 UTF-8 編碼 (Windows 環境修復)
    # 解決 PyInstaller 打包後在 cp950 環境下的 UnicodeEncodeError
    if sys.platform == 'win32':
        # 設定 stdout/stderr 為 UTF-8，使用 replace 錯誤處理避免崩潰
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        # 設定環境變數供子程序使用
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    

    if len(sys.argv) == 1:
        # 無參數時，啟動 GUI
        from swbatch.gui.main import main as gui_main
        gui_main()
    else:
        # 有參數時，啟動 CLI (Typer)
        from swbatch.cli.main import app
        app(prog_name="swbatch")




if __name__ == "__main__":
    main()
