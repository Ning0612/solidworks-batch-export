# 使用者指南

本文件提供 SolidWorks Batch Export 工具的完整使用說明。

## 目錄

- [系統需求](#系統需求)
- [安裝方式](#安裝方式)
- [CLI 命令列模式](#cli-命令列模式)
- [GUI 圖形介面模式](#gui-圖形介面模式)
- [常見問題](#常見問題)

## 系統需求

- **作業系統**：Windows 10/11
- **SolidWorks**：已安裝並可正常啟動
- **Python**：3.10+ （開發式安裝需要）

## 安裝方式

### 方式一：開發模式安裝（推薦）

```bash
# 1. 複製專案
git clone https://github.com/your-repo/solidworks-batch-export.git
cd solidworks-batch-export

# 2. 建立虛擬環境
python -m venv .venv
.\.venv\Scripts\activate

# 3. 安裝套件（可編輯模式）
pip install -e .

# 4. （可選）安裝開發工具
pip install -e ".[dev]"
```

### 方式二：使用預編譯執行檔

下載 `swbatch.exe` 後可直接執行，無需安裝 Python。詳見 [打包部署指南](PACKAGING.md)。

## CLI 命令列模式

### 基本用法

#### 批次轉檔

```bash
# 基本轉檔（預設輸出 STL，只轉換零件檔）
swbatch convert F:\Parts F:\Output

# 轉換組合檔
swbatch convert F:\Parts F:\Output -i sldasm

# 轉換所有檔案（零件+組合）
swbatch convert F:\Parts F:\Output -i all

# 指定輸出格式
swbatch convert F:\Parts F:\Output -o stl
swbatch convert F:\Parts F:\Output -o 3mf
swbatch convert F:\Parts F:\Output -o stl,3mf  # 同時輸出兩種格式

# 組合使用：轉換所有檔案並輸出多種格式
swbatch convert F:\Parts F:\Output -i all -o stl,3mf

# 不保留目錄結構（扁平化）
swbatch convert F:\Parts F:\Output --flat

# 強制重新轉檔（忽略已存在的檔案）
swbatch convert F:\Parts F:\Output --force

# 預覽模式（只顯示將要轉檔的檔案，不實際執行）
swbatch convert F:\Parts F:\Output --dry-run

# 顯示詳細日誌
swbatch convert F:\Parts F:\Output --verbose
```

#### 掃描檔案

```bash
# 列出目錄下的所有 SolidWorks 零件檔（預設）
swbatch scan F:\Parts

# 掃描組合檔
swbatch scan F:\Parts -i sldasm

# 掃描所有檔案（零件+組合）
swbatch scan F:\Parts -i all

# 比對輸出目錄，顯示哪些檔案需要轉檔
swbatch scan F:\Parts F:\Output

# 指定多種輸出格式進行比對
swbatch scan F:\Parts F:\Output -o stl,3mf
```

#### 啟動 GUI

```bash
swbatch gui
```

### 完整選項說明

#### `convert` 指令

| 選項 | 縮寫 | 說明 | 預設值 |
|------|------|------|--------|
| `--input-format` | `-i` | 輸入格式：`sldprt`、`sldasm`、`all` | `sldprt` |
| `--output-format` | `-o` | 輸出格式：`stl`、`3mf`、`all`，可用逗號分隔 | `stl` |
| `--flat` | | 不保留目錄結構，所有檔案輸出到同一目錄 | `False` |
| `--force` | `-F` | 強制重新轉檔，忽略已存在的檔案 | `False` |
| `--dry-run` | `-n` | 預覽模式，只顯示將要轉檔的檔案 | `False` |
| `--verbose` | `-v` | 顯示詳細日誌 | `False` |

> **注意**：
> - 預設只掃描 `.sldprt` 零件檔，若需要轉換組合檔請使用 `-i sldasm` 或 `-i all`
> - `convert` 指令會在開始轉檔前要求確認，不適合完全自動化腳本。若需要跳過互動確認，可使用 `--dry-run` 先預覽，或直接使用 Python API。

#### `scan` 指令

| 選項 | 縮寫 | 說明 | 預設值 |
|------|------|------|--------|
| `--input-format` | `-i` | 輸入格式：`sldprt`、`sldasm`、`all` | `sldprt` |
| `--output-format` | `-o` | 輸出格式：`stl`、`3mf`、`all` | `stl` |

### 支援的檔案格式

#### 輸入格式

| 副檔名 | 說明 |
|--------|------|
| `.sldprt` | SolidWorks 零件檔 |
| `.sldasm` | SolidWorks 組合檔 |

> **注意**：暫存檔（以 `~$` 開頭的檔案）會自動略過。

#### 輸出格式

| 格式 | 副檔名 | 說明 |
|------|--------|------|
| STL | `.stl` | Stereolithography，廣泛用於 3D 列印 |
| 3MF | `.3mf` | 3D Manufacturing Format，支援材質與顏色資訊 |

## GUI 圖形介面模式

### 啟動方式

```bash
# 方法一：透過 CLI 啟動
swbatch gui

# 方法二：直接使用捷徑指令
swbatch-gui

# 方法三：使用 Python 模組（無參數時自動啟動 GUI）
python -m swbatch
```

### 操作步驟

1. **選擇輸入目錄**：點擊「瀏覽」選擇包含 SolidWorks 檔案的資料夾
2. **選擇輸出目錄**：點擊「瀏覽」選擇轉檔後檔案的存放位置
3. **選擇輸入格式**：選擇要掃描的檔案類型（sldprt / sldasm / all）
4. **選擇輸出格式**：選擇轉檔格式（stl / 3mf / all）
5. **掃描檔案**：點擊「掃描檔案」查看檔案清單
6. **選擇檔案**：在清單中勾選要轉檔的檔案
   - 雙擊項目可切換勾選狀態
   - 按空白鍵也可切換勾選狀態
7. **開始轉檔**：點擊「開始轉檔」執行批次轉檔
8. **查看進度**：進度條會顯示當前處理進度

### GUI 功能特色

- ✅ 視覺化檔案選擇
- ✅ 即時進度顯示
- ✅ 支援重新掃描
- ✅ 自動跳過已存在且較新的檔案（增量轉檔）

## 日誌檔案

日誌檔案會自動儲存，可用於故障排除。

### 日誌位置

- **開發模式**：`./logs/swbatch.log`
- **打包後執行**：`%LOCALAPPDATA%\swbatch\logs\swbatch.log`
- **備援位置**：`~/.swbatch/logs/swbatch.log`（當主要位置無法寫入時）

### 日誌輪替

- 每日自動輪替
- 保留 30 天
- 詳細資訊請參考 [日誌配置文件](LOGGING.md)

## 常見問題

### Q: 轉檔時出現「無法連接 SolidWorks」錯誤

**A**: 請確認：
1. SolidWorks 已正確安裝
2. 可以手動啟動 SolidWorks
3. 沒有其他程式正在使用 SolidWorks
4. 以系統管理員身分執行命令提示字元或 PowerShell

### Q: 轉檔速度很慢

**A**: 這是正常現象，因為每個檔案都需要：
1. 啟動 SolidWorks COM 連線
2. 開啟檔案
3. 儲存為目標格式
4. 關閉檔案

**優化建議**：
- 使用增量轉檔功能（預設開啟），只處理有變更的檔案
- 避免使用 `--force` 強制重新轉檔所有檔案
- 關閉其他占用資源的應用程式

### Q: 某些檔案轉檔失敗

**A**: 可能原因：
- 檔案損壞或版本不相容
- 檔案被其他程式鎖定
- SolidWorks 無法正確開啟該檔案
- 檔案路徑過長（Windows 路徑長度限制）

**解決方式**：
1. 查看日誌檔案取得詳細錯誤訊息
2. 嘗試手動在 SolidWorks 中開啟失敗的檔案
3. 使用 `--verbose` 選項查看詳細轉檔過程

### Q: 如何在自動化腳本中使用？

**A**: CLI 的 `convert` 指令會要求互動式確認。建議使用以下方式：

1. **先預覽再決定**：
```bash
swbatch convert F:\Parts F:\Output --dry-run
```

2. **使用 Python API**（進階）：
```python
from swbatch.core import SolidWorksConverter, FileScanner

scanner = FileScanner(input_dir, output_dir, formats)
tasks = scanner.scan_pending()[0]  # 取得待轉檔清單

with SolidWorksConverter(visible=False) as converter:
    results = converter.convert_batch(tasks, skip_existing=True)
```

### Q: 支援批次處理多個專案嗎？

**A**: 目前每次只能處理一個輸入目錄。若要處理多個專案，可以：
1. 使用腳本多次呼叫 `swbatch convert`
2. 將所有專案整合到同一個父目錄下（會保留各專案的子目錄結構）

### Q: 輸出檔案會覆蓋原始檔案嗎？

**A**: 不會。輸出目錄和輸入目錄必須分開指定，工具不會修改原始 SolidWorks 檔案。

## 相關文件

- [開發者指南](DEVELOPMENT.md) - 開發環境設定、程式碼結構
- [打包部署指南](PACKAGING.md) - 如何打包成執行檔
- [架構設計文件](ARCHITECTURE.md) - 技術架構與設計決策
- [日誌配置](LOGGING.md) - 日誌系統詳細說明
