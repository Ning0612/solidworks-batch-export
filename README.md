# SolidWorks Batch Export

批次轉換 SolidWorks 零件檔（`.sldprt`）與組合檔（`.sldasm`）為 STL、3MF 格式的工具。

支援 **CLI 命令列** 和 **GUI 圖形介面** 雙模式。

## 功能特色

- ✅ **批次轉檔**：一次處理整個目錄下的所有 SolidWorks 檔案
- ✅ **多格式輸出**：支援 STL、3MF 格式，可同時輸出多種格式
- ✅ **增量轉檔**：自動跳過已存在且較新的輸出檔案，節省時間
- ✅ **保留目錄結構**：輸出時可選擇保留原始目錄結構或扁平化
- ✅ **雙模式操作**：CLI 適合自動化腳本、GUI 適合互動式操作
- ✅ **設定快取**：GUI 模式會記住上次的路徑和選項設定

## 快速開始

### 安裝

```bash
# 1. Clone專案
git clone https://github.com/your-repo/solidworks-batch-export.git
cd solidworks-batch-export

# 2. 建立虛擬環境
python -m venv .venv
.\.venv\Scripts\activate

# 3. 安裝套件
pip install -e .
```

### CLI 基本用法

```bash
# 基本轉檔（預設只轉換零件檔）
swbatch convert F:\Parts F:\Output

# 轉換組合檔
swbatch convert F:\Parts F:\Output -i sldasm

# 轉換所有檔案（零件+組合）
swbatch convert F:\Parts F:\Output -i all

# 多格式輸出
swbatch convert F:\Parts F:\Output -o stl,3mf

# 掃描零件檔
swbatch scan F:\Parts

# 掃描所有檔案
swbatch scan F:\Parts -i all

# 查看說明
swbatch --help
```

### GUI 圖形介面

```bash
# 啟動 GUI
swbatch gui

# 或使用捷徑指令
swbatch-gui

# 或無參數啟動（自動開啟 GUI）
python -m swbatch
```

## 文件

完整文件請參考 `docs/` 目錄：

- **[使用者指南](docs/USER_GUIDE.md)** - 完整安裝與使用說明、常見問題
- **[開發者指南](docs/DEVELOPMENT.md)** - 開發環境設定、專案結構、程式碼規範
- **[打包部署指南](docs/PACKAGING.md)** - PyInstaller 打包說明
- **[架構設計文件](docs/ARCHITECTURE.md)** - 技術架構與設計決策
- **[日誌配置](docs/LOGGING.md)** - 日誌系統詳細說明

## 系統需求

- Windows 10/11
- SolidWorks 已安裝並可正常啟動
- Python 3.10+ （開發模式需要）

## 技術堆疊

| 技術 | 用途 |
|------|------|
| **SolidWorks COM API** | 透過 `win32com.client` 操作 SolidWorks |
| **typer + rich** | CLI 框架與進度條 |
| **tkinter** | GUI 框架（Python 標準庫） |
| **hatchling** | 打包建構系統 |

## License

MIT License

## 相關連結

- [GitHub Repository](https://github.com/your-repo/solidworks-batch-export)
- [Issue Tracker](https://github.com/your-repo/solidworks-batch-export/issues)
