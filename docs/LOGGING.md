# 日誌配置說明

本文件說明 SolidWorks Batch Export 的日誌系統配置與使用方式。

## 日誌檔案位置

日誌系統會自動選擇可寫入的目錄，按以下順序嘗試：

### 1. 開發模式

```
./logs/swbatch.log
```

當偵測到專案處於開發模式時（非 PyInstaller 打包），使用專案根目錄下的 `logs/` 資料夾。

### 2. 打包後模式（首選）

```
%LOCALAPPDATA%\swbatch\logs\swbatch.log
```

Windows 路徑範例：
```
C:\Users\<username>\AppData\Local\swbatch\logs\swbatch.log
```

### 3. 備援位置

```
~/.swbatch/logs/swbatch.log
```

當 `%LOCALAPPDATA%` 無法寫入時使用。

## 日誌輪替策略

- **輪替頻率**：每日午夜自動輪替
- **命名格式**：`swbatch.log.YYYY-MM-DD`
- **保留期限**：30 天
- **自動清理**：超過 30 天的舊日誌會自動刪除

範例：
```
swbatch.log                # 當前日誌
swbatch.log.2026-01-28    # 昨天的日誌
swbatch.log.2026-01-27    # 前天的日誌
...
```

## 日誌級別

### Console 輸出

- **一般模式**：只顯示 WARNING 以上級別
- **Verbose 模式** (`--verbose`)：顯示 DEBUG 級別

### 檔案輸出

- 總是記錄 DEBUG 級別以上的所有訊息
- 適合故障排除與詳細追蹤

## 日誌格式

### Console 格式（使用 rich.logging.RichHandler）

```
[時間] 訊息內容
```

範例：
```
[23:20:15] 開始批次轉檔：F:\Parts -> F:\Output
[23:20:16] 掃描到 15 個檔案
[23:20:30] 轉檔完成！
```

### 檔案格式

```
YYYY-MM-DD HH:MM:SS - 模組名稱 - 級別 - 訊息
```

範例：
```
2026-01-28 23:20:15 - swbatch.cli.main - INFO - 開始批次轉檔：F:\Parts -> F:\Output
2026-01-28 23:20:16 - swbatch.core.scanner - DEBUG - 找到檔案：part001.sldprt
2026-01-28 23:20:30 - swbatch.cli.main - INFO - 轉檔完成！
```

## 使用方式

### CLI 模式

```bash
# 一般模式（WARNING 以上）
swbatch convert F:\Parts F:\Output

# Verbose 模式（DEBUG 級別）
swbatch convert F:\Parts F:\Output --verbose
```

### GUI 模式

GUI 模式總是以 DEBUG 級別記錄到檔案，Console 輸出為 INFO 級別。

### 程式碼中使用

```python
from swbatch.core.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("詳細的除錯訊息")
logger.info("一般資訊")
logger.warning("警告訊息")
logger.error("錯誤訊息")
logger.critical("嚴重錯誤")
```

## 故障排除

### 找不到日誌檔案

1. 檢查開發模式位置：`./logs/swbatch.log`
2. 檢查打包後位置：`%LOCALAPPDATA%\swbatch\logs\swbatch.log`
3. 檢查備援位置：`~/.swbatch/logs/swbatch.log`

PowerShell 指令：
```powershell
# 查看打包後日誌
type $env:LOCALAPPDATA\swbatch\logs\swbatch.log

# 查看備援日誌
type ~\.swbatch\logs\swbatch.log
```

### 日誌權限問題

若所有位置都無法寫入，系統會 fallback 到只輸出 Console，並顯示警告訊息：

```
警告：無法建立日誌檔案，僅使用 Console 輸出
```

**解決方式**：
- 以系統管理員身分執行
- 檢查資料夾權限
- 確保防毒軟體未封鎖

### 日誌檔案過大

雖然有 30 天自動清理機制，但若每日日誌量很大，可手動刪除舊日誌：

```powershell
# 刪除 7 天前的日誌
Get-ChildItem "$env:LOCALAPPDATA\swbatch\logs\" -Filter "swbatch.log.*" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
    Remove-Item
```

## 日誌配置原始碼

詳見 `swbatch/core/logging_config.py`：

- `setup_logging()`: 設定日誌系統
- `get_logger()`: 取得模組專用 logger
- `_get_writable_log_dir()`: 智慧選擇可寫入的日誌目錄

## 相關文件

- [使用者指南](USER_GUIDE.md) - 基本使用說明
- [開發者指南](DEVELOPMENT.md) - 開發環境設定
