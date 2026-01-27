"""SolidWorks COM 轉檔核心"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

from swbatch.core.formats import SW_DOC_PART, SW_DOC_ASSEMBLY, ExportFormat
from swbatch.core.scanner import ConversionTask

logger = logging.getLogger(__name__)


class ConversionStatus(Enum):
    """轉檔狀態"""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    OPEN_FAILED = "open_failed"


@dataclass
class ConversionResult:
    """轉檔結果"""

    task: ConversionTask
    status: ConversionStatus
    message: str = ""
    error_code: int = 0
    warning_code: int = 0


@dataclass
class ConversionStats:
    """轉檔統計結果

    統一 CLI 和 GUI 的統計邏輯，確保 OPEN_FAILED 被正確計入失敗數。
    """

    success: int = 0
    skipped: int = 0
    failed: int = 0  # 包含 FAILED 和 OPEN_FAILED

    @classmethod
    def from_results(cls, results: list["ConversionResult"]) -> "ConversionStats":
        """從轉檔結果建立統計

        Args:
            results: ConversionResult 列表

        Returns:
            ConversionStats 實例
        """
        stats = cls()
        for result in results:
            if result.status == ConversionStatus.SUCCESS:
                stats.success += 1
            elif result.status == ConversionStatus.SKIPPED:
                stats.skipped += 1
            else:
                # FAILED 和 OPEN_FAILED 都計入失敗
                stats.failed += 1
        return stats

    @property
    def total(self) -> int:
        """總數"""
        return self.success + self.skipped + self.failed

    def format_summary(self) -> str:
        """格式化摘要字串"""
        return f"成功: {self.success}, 略過: {self.skipped}, 失敗: {self.failed}"


class ProgressCallback(Protocol):
    """進度回呼介面"""

    def __call__(
        self,
        current: int,
        total: int,
        task: ConversionTask,
        status: ConversionStatus | None,
    ) -> None:
        """
        進度回呼

        Args:
            current: 目前處理到第幾個（1-based）
            total: 總任務數
            task: 目前處理的任務
            status: 處理結果（None 表示尚未處理完）
        """
        ...


def _get_doc_type(filepath: Path) -> int:
    """根據副檔名取得 SolidWorks 文件類型"""
    ext = filepath.suffix.lower()
    if ext == ".sldprt":
        return SW_DOC_PART
    if ext == ".sldasm":
        return SW_DOC_ASSEMBLY
    raise ValueError(f"不支援的檔案類型: {ext}")


class SolidWorksConverter:
    """SolidWorks 轉檔器

    注意：所有 COM 操作必須在同一個執行緒中執行（STA 模式）。
    GUI 應用應在背景執行緒中呼叫此類的方法，並在該執行緒內完成所有操作。
    """

    def __init__(self, visible: bool = False):
        """
        初始化轉檔器

        Args:
            visible: 是否顯示 SolidWorks 視窗
        """
        self.visible = visible
        self._sw_app = None

    def __enter__(self) -> "SolidWorksConverter":
        """Context manager 進入"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 退出"""
        self.disconnect()

    def connect(self) -> None:
        """連接 SolidWorks COM"""
        if self._sw_app is not None:
            return

        try:
            import win32com.client
            import pythoncom

            # 確保 COM 已初始化（對於背景執行緒很重要）
            pythoncom.CoInitialize()

            self._sw_app = win32com.client.Dispatch("SldWorks.Application")
            self._sw_app.Visible = self.visible
            logger.info(f"已連接 SolidWorks COM (Visible={self.visible})")
            logger.debug(f"SolidWorks 版本：{self._sw_app.RevisionNumber}")
        except Exception as e:
            logger.error(f"連接 SolidWorks 失敗: {e}")
            raise RuntimeError(f"無法連接 SolidWorks: {e}") from e

    def disconnect(self) -> None:
        """斷開 SolidWorks COM 連線"""
        if self._sw_app is not None:
            try:
                import pythoncom

                self._sw_app = None
                pythoncom.CoUninitialize()
                logger.info("已斷開 SolidWorks COM")
            except Exception as e:
                logger.warning(f"斷開 SolidWorks 時發生錯誤: {e}")

    def convert_single(self, task: ConversionTask) -> ConversionResult:
        """
        轉換單一檔案

        Args:
            task: 轉檔任務

        Returns:
            轉檔結果
        """
        if self._sw_app is None:
            raise RuntimeError("尚未連接 SolidWorks，請先呼叫 connect()")

        logger.debug(f"開始轉檔：{task.relative_source} -> {task.format.value.upper()}")

        # 確保輸出目錄存在
        task.output_dir.mkdir(parents=True, exist_ok=True)

        # 開啟文件
        doc_type = _get_doc_type(task.source_path)
        model = self._sw_app.OpenDoc(str(task.source_path), doc_type)

        if model is None:
            logger.error(f"開啟失敗: {task.source_path}")
            return ConversionResult(
                task=task,
                status=ConversionStatus.OPEN_FAILED,
                message=f"無法開啟檔案: {task.source_path}",
            )

        try:
            # 使用 SaveAs3 取得詳細錯誤資訊
            # SaveAs3 參數: (FileName, Version, Options, ExportData, Errors, Warnings)
            errors = 0
            warnings = 0
            output_path = str(task.output_path)

            # 嘗試使用 SaveAs3（如果可用）
            try:
                result = model.Extension.SaveAs3(
                    output_path,
                    0,  # Version
                    0,  # Options (swSaveAsOptions_Silent = 0)
                    None,  # ExportData
                    None,  # ExportPdfData
                    errors,
                    warnings,
                )
                # SaveAs3 回傳 True/False
                success = result
            except AttributeError:
                # 舊版 SolidWorks 可能沒有 SaveAs3，fallback 到 SaveAs
                success = model.SaveAs(output_path)

            if success:
                logger.info(f"已轉檔: {task.relative_source} -> {task.relative_output}")
                return ConversionResult(
                    task=task,
                    status=ConversionStatus.SUCCESS,
                    message="轉檔成功",
                    error_code=errors,
                    warning_code=warnings,
                )
            else:
                logger.error(f"轉檔失敗: {task.relative_source}")
                return ConversionResult(
                    task=task,
                    status=ConversionStatus.FAILED,
                    message=f"轉檔失敗 (error: {errors}, warning: {warnings})",
                    error_code=errors,
                    warning_code=warnings,
                )
        finally:
            # 確保關閉文件
            try:
                # GetTitle 在 COM 中是屬性而非方法
                title = model.GetTitle
                self._sw_app.CloseDoc(title)
            except Exception as e:
                logger.warning(f"關閉文件時發生錯誤: {e}")

    def convert_batch(
        self,
        tasks: list[ConversionTask],
        on_progress: ProgressCallback | None = None,
        skip_existing: bool = True,
    ) -> list[ConversionResult]:
        """
        批次轉檔

        Args:
            tasks: 轉檔任務清單
            on_progress: 進度回呼函數
            skip_existing: 是否略過已存在且較新的檔案

        Returns:
            所有轉檔結果
        """
        results: list[ConversionResult] = []
        total = len(tasks)

        for idx, task in enumerate(tasks, start=1):
            # 回報進度（開始處理）
            if on_progress:
                on_progress(idx, total, task, None)

            # 檢查是否需要跳過
            if skip_existing and not task.needs_conversion():
                result = ConversionResult(
                    task=task,
                    status=ConversionStatus.SKIPPED,
                    message="輸出檔案已是最新",
                )
            else:
                result = self.convert_single(task)

            results.append(result)

            # 回報進度（處理完成）
            if on_progress:
                on_progress(idx, total, task, result.status)

        return results
