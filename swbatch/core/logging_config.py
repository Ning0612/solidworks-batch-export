"""日誌配置模組

提供統一的日誌配置功能，支援：
- Console 輸出（使用 RichHandler）
- 檔案輸出（使用 TimedRotatingFileHandler）
- 自動 fallback 策略（處理權限問題）
- Verbosity 層級控制
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# 全域 Console 實例
console = Console()


def _get_writable_log_dir(preferred_dir: Optional[Path]) -> Optional[Path]:
    """嘗試找到可寫入的日誌目錄
    
    依序嘗試以下路徑：
    1. preferred_dir（如果提供）
    2. 當前工作目錄的 logs/
    3. %LOCALAPPDATA%\\swbatch\\logs（Windows）
    4. ~/.swbatch/logs（跨平台 fallback）
    
    Args:
        preferred_dir: 優先使用的日誌目錄
        
    Returns:
        可寫入的路徑，若所有路徑都失敗則返回 None
    """
    candidates = []
    
    if preferred_dir:
        candidates.append(Path(preferred_dir))
    
    # Fallback 選項
    candidates.append(Path.cwd() / "logs")
    
    # Windows AppData
    if os.name == 'nt':
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(Path(local_app_data) / "swbatch" / "logs")
    
    # 跨平台 home 目錄
    candidates.append(Path.home() / ".swbatch" / "logs")
    
    for path in candidates:
        try:
            # 確保目錄存在
            path.mkdir(parents=True, exist_ok=True)
            
            # 測試寫入權限
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            return path
        except (OSError, PermissionError):
            continue
    
    return None


def setup_logging(
    verbose: bool = False, 
    log_dir: Optional[Path | str] = None,
    console: Optional[Console] = None
) -> None:
    """設定日誌系統
    
    配置 Console Handler 和 File Handler（若可用）。
    
    Args:
        verbose: 是否啟用詳細模式（DEBUG 層級）
        log_dir: 日誌目錄路徑，None 表示僅使用 Console Handler
        console: 共用的 Console 實例，None 表示建立新實例（確保與 Progress 共用以避免輸出競爭）
    """
    # 清除現有的 handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 設定根日誌層級為 DEBUG（讓 handler 決定實際輸出層級）
    root_logger.setLevel(logging.DEBUG)
    
    # 使用提供的 console 或建立新的（向後相容）
    _console = console if console is not None else Console()
    
    # Console Handler（RichHandler）
    console_level = logging.DEBUG if verbose else logging.INFO
    console_handler = RichHandler(
        console=_console,
        rich_tracebacks=True,
        show_path=False,
        markup=True,
        level=console_level,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)
    
    # File Handler（若 log_dir 提供）
    if log_dir is not None:
        log_dir_path = Path(log_dir) if isinstance(log_dir, str) else log_dir
        writable_dir = _get_writable_log_dir(log_dir_path)
        
        if writable_dir:
            log_file = writable_dir / "swbatch.log"
            
            try:
                file_handler = TimedRotatingFileHandler(
                    filename=str(log_file),
                    when="midnight",        # 每日午夜 rotation
                    interval=1,             # 每 1 天
                    backupCount=30,         # 保留 30 天
                    encoding="utf-8",       # UTF-8 編碼
                    delay=True,             # 延遲檔案建立直到首次寫入
                    utc=False,              # 使用本地時區
                )
                file_handler.suffix = "%Y-%m-%d"  # 備份檔名後綴格式
                file_handler.setLevel(logging.DEBUG)  # 檔案永遠記錄 DEBUG
                
                # 檔案日誌格式
                file_formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
                file_handler.setFormatter(file_formatter)
                
                root_logger.addHandler(file_handler)
                
                # 記錄日誌檔案位置（僅在 verbose 模式）
                if verbose:
                    logging.info(f"日誌檔案：{log_file}")
                    
            except (OSError, PermissionError) as e:
                logging.warning(f"無法建立檔案日誌：{e}，僅使用 Console 輸出")
        else:
            logging.warning("找不到可寫入的日誌目錄，僅使用 Console 輸出")


def get_logger(name: str) -> logging.Logger:
    """取得具名 logger
    
    Args:
        name: Logger 名稱（通常使用 __name__）
        
    Returns:
        Logger 實例
    """
    return logging.getLogger(name)
