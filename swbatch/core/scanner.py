"""檔案掃描模組"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from swbatch.core.formats import ExportFormat, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


@dataclass
class ConversionTask:
    """轉檔任務"""

    source_path: Path
    output_dir: Path
    format: ExportFormat
    input_dir: Path | None = None
    base_output_dir: Path | None = None
    _output_path: Path | None = field(default=None, init=False, repr=False)

    @property
    def output_path(self) -> Path:
        """計算輸出檔案路徑"""
        if self._output_path is None:
            self._output_path = self.output_dir / (self.source_path.stem + self.format.extension)
        return self._output_path

    @property
    def source_mtime(self) -> float:
        """來源檔案修改時間"""
        return self.source_path.stat().st_mtime

    @property
    def output_exists(self) -> bool:
        """輸出檔案是否存在"""
        return self.output_path.exists()

    @property
    def output_mtime(self) -> float | None:
        """輸出檔案修改時間（若不存在則為 None）"""
        if self.output_exists:
            return self.output_path.stat().st_mtime
        return None

    def needs_conversion(self) -> bool:
        """判斷是否需要轉檔"""
        if not self.output_exists:
            return True
        output_mtime = self.output_mtime
        if output_mtime is None:
            return True
        return output_mtime < self.source_mtime

    @property
    def relative_source(self) -> str:
        """相對來源路徑（用於顯示）"""
        if self.input_dir:
            try:
                # 嘗試取得相對於輸入目錄的顯示路徑
                return str(self.source_path.relative_to(self.input_dir))
            except ValueError:
                pass
        return self.source_path.name

    @property
    def relative_output(self) -> str:
        """相對輸出路徑（用於顯示）"""
        if self.base_output_dir:
            try:
                # 嘗試取得相對於基礎輸出目錄的顯示路徑
                return str(self.output_path.relative_to(self.base_output_dir))
            except ValueError:
                pass
        return self.output_path.name

    def __str__(self) -> str:
        status = "需轉檔" if self.needs_conversion() else "可略過"
        return f"[{status}] {self.source_path.name} -> {self.format.value.upper()}"


class FileScanner:
    """檔案掃描器"""

    def __init__(
        self,
        input_dir: Path | str,
        output_dir: Path | str,
        formats: list[ExportFormat] | None = None,
        preserve_structure: bool = True,
        input_extensions: set[str] | None = None,
    ):
        """
        初始化掃描器

        Args:
            input_dir: 輸入目錄
            output_dir: 輸出目錄
            formats: 要輸出的格式列表，預設為 [STL]
            preserve_structure: 是否保留原目錄結構
            input_extensions: 要掃描的副檔名集合，預設為 {".sldprt"}
        """
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.formats = formats or [ExportFormat.STL]
        self.preserve_structure = preserve_structure
        self.input_extensions = input_extensions or {".sldprt"}

    def scan(self) -> list[ConversionTask]:
        """
        掃描輸入目錄，產生轉檔任務清單

        Returns:
            所有找到的轉檔任務（不論是否需要轉檔）
        """
        tasks: list[ConversionTask] = []

        if not self.input_dir.exists():
            raise FileNotFoundError(f"輸入目錄不存在: {self.input_dir}")

        for root, _, files in os.walk(self.input_dir):
            root_path = Path(root)
            for filename in files:
                # 跳過暫存檔
                if filename.startswith("~$"):
                    continue

                filepath = root_path / filename
                ext = filepath.suffix.lower()

                if ext not in self.input_extensions:
                    continue

                # 計算輸出目錄（保留結構或扁平化）
                if self.preserve_structure:
                    rel_path = root_path.relative_to(self.input_dir)
                    task_output_dir = self.output_dir / rel_path
                else:
                    task_output_dir = self.output_dir

                # 為每種輸出格式建立任務
                for fmt in self.formats:
                    tasks.append(
                        ConversionTask(
                            source_path=filepath,
                            output_dir=task_output_dir,
                            format=fmt,
                            input_dir=self.input_dir,
                            base_output_dir=self.output_dir,
                        )
                    )

        return tasks

    def scan_pending(self) -> tuple[list[ConversionTask], list[ConversionTask]]:
        """
        掃描並分類任務

        Returns:
            (需要轉檔的任務, 可略過的任務)
        """
        all_tasks = self.scan()
        pending = [t for t in all_tasks if t.needs_conversion()]
        skipped = [t for t in all_tasks if not t.needs_conversion()]
        return pending, skipped
