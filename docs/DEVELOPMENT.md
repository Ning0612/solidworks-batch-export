# 開發者指南

本文件提供 SolidWorks Batch Export 的開發環境設定、專案結構、程式碼規範等資訊。

## 目錄

- [開發環境設定](#開發環境設定)
- [專案結構](#專案結構)
- [核心模組說明](#核心模組說明)
- [開發常用指令](#開發常用指令)
- [程式碼規範](#程式碼規範)
- [貢獻指南](#貢獻指南)

## 開發環境設定

### 系統需求

- Windows 10/11
- Python 3.10+
- SolidWorks 已安裝
- Git

### 安裝步驟

```bash
# 1. Clone 專案
git clone https://github.com/your-repo/solidworks-batch-export.git
cd solidworks-batch-export

# 2. 建立虛擬環境
python -m venv .venv

# 3. 啟用虛擬環境
.\.venv\Scripts\activate

# 4. 安裝開發依賴
pip install -e ".[dev]"
```

### 驗證安裝

```bash
# 測試 CLI
swbatch --help

# 測試 GUI
swbatch-gui

# 測試模組
python -m swbatch --help

# 執行 lint
ruff check swbatch/

# 執行測試（若有）
pytest
```

## 專案結構

```
solidworks-batch-export/
├── swbatch/                    # 主要套件目錄
│   ├── __init__.py            # 套件初始化，定義版本號
│   ├── __main__.py            # 模組入口（python -m swbatch）
│   ├── core/                  # 核心共用模組
│   │   ├── __init__.py        # 統一匯出介面
│   │   ├── converter.py       # SolidWorks COM 轉檔邏輯
│   │   ├── scanner.py         # 檔案掃描與任務建立
│   │   ├── formats.py         # 格式定義與解析
│   │   ├── validation.py      # 路徑驗證（GUI 專用）
│   │   ├── paths.py           # 路徑處理（開發/打包模式）
│   │   └── logging_config.py  # 日誌配置
│   ├── cli/                   # CLI 命令列介面
│   │   ├── __init__.py
│   │   └── main.py            # Typer CLI 入口
│   └── gui/                   # GUI 圖形介面
│       ├── __init__.py
│       └── main.py            # Tkinter GUI 實作
├── docs/                      # 文件目錄
│   ├── USER_GUIDE.md          # 使用者指南
│   ├── DEVELOPMENT.md         # 開發者指南（本文件）
│   ├── PACKAGING.md           # 打包部署指南
│   ├── ARCHITECTURE.md        # 架構設計文件
│   └── LOGGING.md             # 日誌配置說明
├── runner.py                  # PyInstaller 入口點
├── swbatch.spec               # PyInstaller 配置檔
├── pyproject.toml             # 專案配置與依賴
├── .gitignore                 # Git 忽略清單
├── README.md                  # 專案簡介
└── CLAUDE.md                  # Claude AI 協作指南
```

### 重要檔案說明

#### 專案配置

- **`pyproject.toml`**: 專案元資料、依賴、建構設定、腳本入口點
- **`.gitignore`**: Git 版本控制忽略清單

#### 入口點檔案

- **`swbatch/__main__.py`**: `python -m swbatch` 的入口，支援 CLI/GUI 自動切換
- **`runner.py`**: PyInstaller 打包時的入口點，指向 `__main__.py`
- **`swbatch.spec`**: PyInstaller 詳細配置（hidden imports, data files 等）

#### 協作文件

- **`CLAUDE.md`**: Claude AI 協作時的專案指引（架構、設計原則、API 參考）

## 核心模組說明

### core/formats.py

定義支援的轉檔格式與解析邏輯。

```python
class ExportFormat(Enum):
    STL = "stl"
    THREEMF = "3mf"

def parse_formats(formats_str: str, allow_all: bool = False) -> list[ExportFormat]:
    """解析格式字串，支援 "stl", "3mf", "stl,3mf", "all" """
```

### core/scanner.py

檔案掃描與任務建立。

```python
@dataclass
class ConversionTask:
    source_path: Path
    output_dir: Path
    format: ExportFormat
    input_dir: Path | None = None
    
    def needs_conversion(self) -> bool:
        """判斷是否需要轉檔（比較 mtime）"""

class FileScanner:
    def scan(self) -> list[ConversionTask]:
        """掃描所有任務"""
    
    def scan_pending(self) -> tuple[list[ConversionTask], list[ConversionTask]]:
        """分別返回待轉檔與可略過的任務"""
```

### core/converter.py

SolidWorks COM API 轉檔核心邏輯。

```python
class ConversionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    OPEN_FAILED = "open_failed"

@dataclass
class ConversionStats:
    success: int
    skipped: int
    failed: int  # 包含 FAILED 和 OPEN_FAILED
    
    @classmethod
    def from_results(cls, results: list[ConversionResult]) -> ConversionStats:
        """從結果列表建立統計"""

class SolidWorksConverter:
    def convert_batch(
        self,
        tasks: list[ConversionTask],
        on_progress: ProgressCallback | None = None,
        skip_existing: bool = True,
    ) -> list[ConversionResult]:
        """批次轉檔"""
```

### core/validation.py

路徑驗證（供 GUI 使用，CLI 使用 Typer 內建驗證）。

```python
def validate_input_dir(path: Path | str) -> tuple[bool, str]:
    """驗證輸入目錄"""

def validate_output_dir(path: Path | str) -> tuple[bool, str]:
    """驗證輸出目錄"""

def validate_paths(input_dir, output_dir) -> tuple[bool, str]:
    """同時驗證輸入與輸出目錄"""
```

### core/paths.py

路徑處理（開發/打包模式差異）。

```python
def get_log_dir() -> Path:
    """取得日誌目錄，處理開發/打包模式差異
    
    - 開發模式：使用 `./logs/`
    - 打包後：使用 `%LOCALAPPDATA%\\swbatch\\logs`
    """
```

### core/logging_config.py

統一日誌配置。

```python
def setup_logging(verbose: bool = False, log_dir: Path | None = None, console: Console | None = None) -> None:
    """配置日誌系統（Console + File）"""

def get_logger(name: str) -> logging.Logger:
    """取得模組專屬 logger"""
```

## 開發常用指令

### 語法檢查

```bash
# 檢查單一檔案
.\.venv\Scripts\python.exe -m py_compile swbatch/core/converter.py

# 檢查整個模組
.\.venv\Scripts\python.exe -m compileall swbatch/
```

### Lint（程式碼風格檢查）

```bash
# 檢查所有程式碼
ruff check swbatch/

# 自動修正可修正的問題
ruff check swbatch/ --fix

# 格式化程式碼
ruff format swbatch/
```

### 測試

```bash
# 執行所有測試
pytest

# 執行測試並顯示覆蓋率
pytest --cov=swbatch --cov-report=html

# 執行特定測試檔案
pytest tests/test_converter.py

# 執行特定測試函式
pytest tests/test_converter.py::test_convert_batch
```

### 執行與除錯

```bash
# 以模組方式執行（自動啟動 GUI）
python -m swbatch

# CLI 模式
python -m swbatch convert F:\Parts F:\Output

# 直接執行腳本（安裝後）
swbatch convert F:\Parts F:\Output --verbose
swbatch-gui
```

## 程式碼規範

### Python 版本

- **最低支援**：Python 3.10
- **開發使用**：Python 3.12（建議）

### 程式碼風格

本專案使用 **Ruff** 進行 lint 與格式化：

- 行長度：100 字元
- 啟用規則：E, F, W, I, UP, B, C4
- 目標版本：Python 3.10

配置詳見 `pyproject.toml` 中的 `[tool.ruff]` 區段。

### 型別提示

- **必須使用**型別提示（type hints）
- 使用 `from __future__ import annotations` 啟用新式型別語法
- 函式參數與返回值都需要標註型別

範例：
```python
from __future__ import annotations
from pathlib import Path

def process_file(input_path: Path, output_format: str) -> bool:
    """處理單一檔案
    
    Args:
        input_path: 輸入檔案路徑
        output_format: 輸出格式（如 "stl"）
    
    Returns:
        是否處理成功
    """
    ...
```

### Docstring 規範

使用 **Google Style** docstring：

```python
def example_function(param1: str, param2: int = 0) -> list[str]:
    """簡短描述（一行）
    
    詳細說明（可選，多行）。
    
    Args:
        param1: 參數1的說明
        param2: 參數2的說明（預設值：0）
    
    Returns:
        返回值說明
    
    Raises:
        ValueError: 何時會拋出此例外
    
    Examples:
        >>> example_function("test", 42)
        ['result1', 'result2']
    """
    ...
```

### 共用模組設計原則

**重要：CLI 和 GUI 相同的功能必須統一提取至 `core/` 模組，避免重複實作。**

#### 共用函式對照表

| 共用功能 | 模組位置 | 說明 |
|---------|---------|------|
| 格式解析 | `formats.parse_formats()` | 支援 `allow_all=True` 處理 GUI 的 "all" 選項 |
| 轉檔統計 | `converter.ConversionStats` | 統一 SUCCESS/FAILED/SKIPPED/OPEN_FAILED 計數 |
| 跳過判斷 | `converter.convert_batch()` | `skip_existing` 邏輯只在此處實作 |
| 路徑驗證 | `validation.validate_paths()` | GUI 專用，CLI 保留 Typer 原生驗證 |
| 日誌目錄 | `paths.get_log_dir()` | 統一處理開發/打包模式的日誌路徑 |

#### 新增功能時的流程

1. 若 CLI 和 GUI 都需要，**先在 `core/` 實作共用函式**
2. 避免在 `cli/` 或 `gui/` 中重複實作相同邏輯
3. 使用 `__init__.py` 統一匯出，方便使用
4. 新增共用函式後，更新 `CLAUDE.md` 的對照表

## 關鍵設計決策

### 1. COM 執行緒安全

SolidWorks COM 要求 STA 模式，所有 COM 操作必須在同一執行緒。

- **CLI**：主執行緒直接執行
- **GUI**：透過 `threading.Thread` 背景執行緒處理轉檔
  - 在執行緒內呼叫 `pythoncom.CoInitialize()`
  - 使用 `queue.Queue` 與主執行緒通訊

### 2. 進度回呼機制

`SolidWorksConverter.convert_batch()` 接受 `on_progress` callback，解耦核心邏輯與 UI 層。

```python
def on_progress(
    current: int,
    total: int,
    task: ConversionTask,
    status: ConversionStatus | None
) -> None:
    # status=None 表示開始處理
    # status 有值表示處理完成
    pass
```

GUI 的 `ConversionWorker` 直接使用 `convert_batch` 而非自行實作循環。

### 3. 跳過邏輯

統一在 `convert_batch(skip_existing=...)` 中處理：

- `ConversionTask.needs_conversion()` 比較來源與目標 mtime
- 每種輸出格式獨立判斷
- CLI 和 GUI 都透過此參數控制

### 4. SaveAs3 vs SaveAs

優先使用 `SaveAs3` 取得詳細錯誤碼，舊版 SolidWorks 自動 fallback 到 `SaveAs`。

### 5. UI 狀態更新

GUI 使用 **task index** 而非檔名比對更新 TreeView，避免不同目錄中同名檔案誤更新。

### 6. Shell Completion 已移除

本專案已移除 shell completion 支援：

- `__main__.py` 會偵測 completion 環境變數並直接退出
- `cli/main.py` 不再設定 `add_completion` 參數
- 若使用者仍有舊版 completion 腳本，請手動移除

## 貢獻指南

### 提交程式碼前

1. **執行 lint**：
```bash
ruff check swbatch/ --fix
ruff format swbatch/
```

2. **語法檢查**：
```bash
.\.venv\Scripts\python.exe -m compileall swbatch/
```

3. **測試**（若有）：
```bash
pytest
```

4. **更新文件**：
- 若新增 CLI 選項，更新 `docs/USER_GUIDE.md`
- 若修改架構，更新 `docs/ARCHITECTURE.md` 和 `CLAUDE.md`
- 若新增共用模組，更新本文件的「核心模組說明」

### Commit Message 規範

使用語義化 commit message：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新功能
- `fix`: 錯誤修正
- `docs`: 文件更新
- `style`: 格式調整（不影響程式碼邏輯）
- `refactor`: 重構
- `perf`: 效能優化
- `test`: 測試相關
- `chore`: 建構/工具相關

**範例**:
```
feat(cli): 新增 --force 選項強制重新轉檔

允許使用者透過 --force 選項忽略已存在的檔案，強制重新轉檔所有任務。

Closes #123
```

## 相關文件

- [使用者指南](USER_GUIDE.md) - 安裝與使用說明
- [打包部署指南](PACKAGING.md) - 如何打包成執行檔
- [架構設計文件](ARCHITECTURE.md) - 技術架構與設計決策
- [日誌配置](LOGGING.md) - 日誌系統詳細說明
- [CLAUDE.md](../CLAUDE.md) - Claude AI 協作指引
