"""路徑處理輔助模組

提供統一的路徑處理函數，支援開發模式與打包後執行。
"""

import sys
from pathlib import Path


def get_log_dir() -> Path:
    """取得日誌目錄（支援打包後執行與權限問題）
    
    打包後使用 Windows 用戶目錄，避免權限問題。
    開發模式使用當前目錄。
    
    Returns:
        Path: 日誌目錄路徑
    """
    if getattr(sys, 'frozen', False):
        # 打包後：使用 Windows 用戶目錄
        import os
        log_dir = Path(os.environ.get('LOCALAPPDATA', '.')) / 'swbatch' / 'logs'
    else:
        # 開發模式：使用當前目錄
        log_dir = Path.cwd() / 'logs'
    
    # 確保目錄存在
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_config_dir() -> Path:
    """取得設定目錄（支援打包後執行與權限問題）
    
    打包後使用 Windows 用戶目錄，避免權限問題。
    開發模式使用當前目錄。
    
    Returns:
        Path: 設定目錄路徑
    """
    if getattr(sys, 'frozen', False):
        # 打包後：使用 Windows 用戶目錄
        import os
        config_dir = Path(os.environ.get('LOCALAPPDATA', '.')) / 'swbatch' / 'config'
    else:
        # 開發模式：使用當前目錄
        config_dir = Path.cwd() / 'config'
    
    # 確保目錄存在
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
