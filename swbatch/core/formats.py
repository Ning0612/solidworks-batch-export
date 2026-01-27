"""輸出格式定義"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ExportFormat(Enum):
    """支援的輸出格式"""

    STL = "stl"
    THREEMF = "3mf"

    @property
    def extension(self) -> str:
        """取得副檔名（含點號）"""
        return f".{self.value}"

    @property
    def display_name(self) -> str:
        """顯示名稱"""
        names = {
            ExportFormat.STL: "STL (Stereolithography)",
            ExportFormat.THREEMF: "3MF (3D Manufacturing Format)",
        }
        return names.get(self, self.value.upper())

    @classmethod
    def from_string(cls, value: str) -> "ExportFormat":
        """從字串轉換為 ExportFormat"""
        value = value.lower().strip()
        if value in ("3mf", "threemf"):
            return cls.THREEMF
        if value == "stl":
            return cls.STL
        raise ValueError(f"不支援的格式: {value}，支援的格式: stl, 3mf")


@dataclass
class ExportOptions:
    """輸出選項"""

    format: ExportFormat
    # STL 選項
    stl_binary: bool = True  # True=二進位，False=ASCII
    stl_quality: str = "fine"  # coarse, fine, custom
    # 3MF 選項
    threemf_include_materials: bool = True

    def to_solidworks_options(self) -> dict[str, Any]:
        """轉換為 SolidWorks API 選項"""
        # 這些選項會在 SaveAs3 時使用
        options: dict[str, Any] = {}

        if self.format == ExportFormat.STL:
            # swExportSTLBinary = 0, swExportSTLAscii = 1
            options["stl_format"] = 0 if self.stl_binary else 1

        return options


# SolidWorks 文件類型常數
SW_DOC_PART = 1
SW_DOC_ASSEMBLY = 2
SW_DOC_DRAWING = 3

# 支援轉檔的來源副檔名
SUPPORTED_EXTENSIONS = {".sldprt", ".sldasm"}


def parse_formats(formats_str: str, allow_all: bool = False) -> list[ExportFormat]:
    """解析格式字串

    統一 CLI 和 GUI 的格式解析邏輯。

    Args:
        formats_str: 格式字串，如 "stl", "3mf", "stl,3mf", "all"
        allow_all: 是否允許 "all" 關鍵字（展開為所有格式）

    Returns:
        ExportFormat 列表

    Raises:
        ValueError: 不支援的格式

    Examples:
        >>> parse_formats("stl")
        [ExportFormat.STL]
        >>> parse_formats("stl,3mf")
        [ExportFormat.STL, ExportFormat.THREEMF]
        >>> parse_formats("all", allow_all=True)
        [ExportFormat.STL, ExportFormat.THREEMF]
    """
    formats_str = formats_str.strip().lower()

    # 處理 "all" 關鍵字
    if allow_all and formats_str == "all":
        return [ExportFormat.STL, ExportFormat.THREEMF]

    # 處理空字串
    if not formats_str:
        return [ExportFormat.STL]

    # 解析逗號分隔的格式
    formats = []
    for fmt in formats_str.split(","):
        fmt = fmt.strip()
        if fmt:
            formats.append(ExportFormat.from_string(fmt))

    return formats if formats else [ExportFormat.STL]
