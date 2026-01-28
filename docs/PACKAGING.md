# 打包部署指南

本文件說明如何將 SolidWorks Batch Export 打包成獨立執行檔。

## 目錄

- [打包方式](#打包方式)
- [使用 PyInstaller + spec 檔案](#使用-pyinstaller--spec-檔案)
- [打包後檔案結構](#打包後檔案結構)
- [測試驗證](#測試驗證)
- [常見問題](#常見問題)

## 打包方式

本專案使用 **PyInstaller** 搭配 `swbatch.spec` 配置檔進行打包，產生單一執行檔（`swbatch.exe`）同時支援 CLI 和 GUI 模式。

## 使用 PyInstaller + spec 檔案

### 1. 安裝 PyInstaller

```bash
pip install pyinstaller
```

### 2. 執行打包

```bash
# 使用專案提供的 spec 檔案
pyinstaller swbatch.spec
```

打包完成後，執行檔位於 `dist/swbatch.exe`。

### 3. spec 檔案說明

`swbatch.spec` 是 PyInstaller 的詳細配置檔，包含以下關鍵設定：

#### 入口點

```python
a = Analysis(
    ['runner.py'],  # 使用 runner.py 作為入口點
    ...
)
```

**為什麼使用 `runner.py`？**

- `runner.py` 是一個簡單的啟動器，指向 `swbatch/__main__.py`
- 讓 PyInstaller 正確打包整個 `swbatch` 套件
- 保持與 `python -m swbatch` 一致的行為

#### Hidden Imports

```python
hiddenimports=[
    # pywin32 COM 支援（關鍵！）
    'pythoncom',
    'pywintypes',
    'win32com.client',
    # CLI 相關
    'typer',
    'rich',
    *rich_hiddenimports,  # rich 的隱藏依賴
    # tkinter GUI 相關
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
],
```

這些模組無法自動偵測，必須手動指定：
- **pywin32**: SolidWorks COM 互動的核心
- **rich**: CLI 進度條與格式化輸出需要額外的 Unicode 資料
- **tkinter**: GUI 介面

#### Rich 資料收集

```python
from PyInstaller.utils.hooks import collect_all

rich_datas, rich_binaries, rich_hiddenimports = collect_all('rich')
```

這行很重要！`rich` 需要 Unicode 資料檔案，沒有這行會出現 `ModuleNotFoundError`。

#### Console 模式

```python
exe = EXE(
    ...
    console=True,  # Console 模式，支援 CLI 輸出
    ...
)
```

**為什麼使用 `console=True`？**

- 支援 CLI 模式的輸出（進度條、錯誤訊息等）
- GUI 模式會暫時顯示控制台視窗（這是已接受的限制）
- 若改為 `console=False`（windowed 模式），CLI 輸出會消失

## 打包後檔案結構

```
dist/
└── swbatch.exe       # 單一執行檔（約 30-50 MB）
```

## 使用打包後的執行檔

### CLI 模式

```bash
# 在命令提示字元或 PowerShell 中執行
.\swbatch.exe convert F:\Parts F:\Output
.\swbatch.exe convert F:\Parts F:\Output -f stl,3mf
.\swbatch.exe scan F:\Parts
.\swbatch.exe --help
```

### GUI 模式

```bash
# 方法一：雙擊 swbatch.exe（無參數時自動啟動 GUI）
# 方法二：使用 gui 子指令
.\swbatch.exe gui
```

### 入口點行為說明

| 執行方式 | 行為 |
|---------|------|
| 雙擊 `swbatch.exe` | 啟動 GUI |
| `swbatch.exe` （命令列無參數） | 啟動 GUI |
| `swbatch.exe --help` | 顯示 CLI 說明 |
| `swbatch.exe convert ...` | 執行 CLI 轉檔 |
| `swbatch.exe scan ...` | 執行 CLI 掃描 |
| `swbatch.exe gui` | 啟動 GUI |

## 測試驗證

打包完成後，請執行以下測試：

### 1. CLI 測試

```bash
# 測試幫助資訊
.\dist\swbatch.exe --help

# 測試掃描功能
.\dist\swbatch.exe scan F:\TestParts

# 測試轉檔（預覽模式）
.\dist\swbatch.exe convert F:\TestParts F:\TestOutput --dry-run

# 測試實際轉檔
.\dist\swbatch.exe convert F:\TestParts F:\TestOutput -f stl --verbose
```

### 2. GUI 測試

```bash
# 測試 GUI 啟動
.\dist\swbatch.exe gui

# 測試無參數啟動（應該開啟 GUI）
.\dist\swbatch.exe
```

在 GUI 中測試：
1. 瀏覽並選擇目錄
2. 掃描檔案
3. 選擇檔案並開始轉檔
4. 檢查進度顯示

### 3. 日誌檢查

打包後的日誌位置：`%LOCALAPPDATA%\swbatch\logs\swbatch.log`

```bash
# 查看日誌
type %LOCALAPPDATA%\swbatch\logs\swbatch.log
```

## 常見問題

### Q: 打包後出現 `ModuleNotFoundError: No module named 'rich._unicode_data...`

**A**: 這是因為沒有正確收集 rich 的資料檔案。確保 `swbatch.spec` 中有：

```python
from PyInstaller.utils.hooks import collect_all
rich_datas, rich_binaries, rich_hiddenimports = collect_all('rich')

a = Analysis(
    ...,
    binaries=rich_binaries,
    datas=rich_datas,
    hiddenimports=[..., *rich_hiddenimports],
)
```

### Q: 打包後無法連接 SolidWorks

**A**: 確保 `hiddenimports` 包含：
```python
'pythoncom',
'pywintypes',
'win32com.client',
```

這三個是 pywin32 COM 支援的關鍵模組。

### Q: GUI 模式有控制台視窗閃現

**A**: 這是 `console=True` 的預期行為。要完全隱藏控制台視窗，需要：
1. 改為 `console=False`
2. 接受 CLI 模式無法輸出的限制
3. 或者建立兩個版本（CLI 版 + GUI 版）

目前專案選擇 `console=True` 以支援 CLI 功能。

### Q: 執行檔很大（40+ MB）

**A**: 這是正常的，因為包含了：
- Python 直譯器
- pywin32 完整 COM 支援
- rich 與 typer CLI 框架
- tkinter GUI 框架

可以考慮：
- 使用 UPX 壓縮（已在 spec 中啟用 `upx=True`）
- 移除不需要的模組（謹慎操作）

### Q: 如何更新打包配置？

**A**: 

1. 編輯 `swbatch.spec`
2. 重新打包：`pyinstaller swbatch.spec`
3. 測試驗證

**不要**使用 `pyinstaller --onefile ...` 等指令重新生成 spec，會覆蓋現有配置。

## 進階配置

### 建立兩個版本（CLI + GUI）

若需要分別建立 CLI 和 GUI 版本：

1. **CLI 版本** (`swbatch-cli.spec`):
```python
exe = EXE(
    ...,
    name='swbatch-cli',
    console=True,
    ...
)
```

2. **GUI 版本** (`swbatch-gui.spec`):
```python
exe = EXE(
    ...,
    name='swbatch-gui',
    console=False,  # 隱藏控制台
    ...
)
```

分別打包：
```bash
pyinstaller swbatch-cli.spec
pyinstaller swbatch-gui.spec
```

### 加入圖示

在 spec 檔案中加入圖示：

```python
exe = EXE(
    ...,
    icon='path/to/icon.ico',
    ...
)
```

## 相關文件

- [使用者指南](USER_GUIDE.md) - 執行檔使用說明
- [開發者指南](DEVELOPMENT.md) - 開發環境與專案結構
- [架構設計文件](ARCHITECTURE.md) - 技術架構
