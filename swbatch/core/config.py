"""GUI 設定管理模組

提供 GUI 設定的儲存與載入功能。
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from swbatch.core.paths import get_config_dir

logger = logging.getLogger(__name__)

# 允許的格式值
VALID_INPUT_FORMATS = {"sldprt", "sldasm", "all"}
VALID_OUTPUT_FORMATS = {"stl", "3mf", "all"}


@dataclass
class GuiConfig:
    """GUI 設定資料類別"""

    input_dir: str = ""
    output_dir: str = ""
    input_format: str = "sldprt"
    output_format: str = "stl"
    preserve_structure: bool = True
    skip_existing: bool = True


def get_default_config() -> GuiConfig:
    """取得預設設定

    Returns:
        GuiConfig: 預設設定值
    """
    return GuiConfig()


def load_gui_config() -> GuiConfig:
    """載入 GUI 設定

    從設定檔載入設定，如果檔案不存在或損壞則返回預設值。

    Returns:
        GuiConfig: 載入的設定或預設設定
    """
    config_file = get_config_dir() / "gui_config.json"

    # 檔案不存在，返回預設值
    if not config_file.exists():
        logger.debug("設定檔不存在，使用預設值")
        return get_default_config()

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 驗證並建立設定
        config = get_default_config()

        # 載入各欄位，並進行驗證
        if "input_dir" in data and isinstance(data["input_dir"], str):
            config.input_dir = data["input_dir"]

        if "output_dir" in data and isinstance(data["output_dir"], str):
            config.output_dir = data["output_dir"]

        if "input_format" in data and isinstance(data["input_format"], str):
            if data["input_format"] in VALID_INPUT_FORMATS:
                config.input_format = data["input_format"]
            else:
                logger.warning(f"無效的 input_format: {data['input_format']}，使用預設值")

        if "output_format" in data and isinstance(data["output_format"], str):
            if data["output_format"] in VALID_OUTPUT_FORMATS:
                config.output_format = data["output_format"]
            else:
                logger.warning(f"無效的 output_format: {data['output_format']}，使用預設值")

        if "preserve_structure" in data and isinstance(data["preserve_structure"], bool):
            config.preserve_structure = data["preserve_structure"]

        if "skip_existing" in data and isinstance(data["skip_existing"], bool):
            config.skip_existing = data["skip_existing"]

        logger.debug(f"成功載入設定: {config}")
        return config

    except json.JSONDecodeError as e:
        logger.warning(f"設定檔 JSON 解析失敗: {e}，使用預設值")
        return get_default_config()
    except Exception as e:
        logger.error(f"載入設定檔時發生錯誤: {e}，使用預設值")
        return get_default_config()


def save_gui_config(config: GuiConfig) -> None:
    """儲存 GUI 設定

    將設定儲存為 JSON 檔案。

    Args:
        config: 要儲存的設定
    """
    config_dir = get_config_dir()
    config_file = config_dir / "gui_config.json"

    try:
        # 轉換為字典
        data = asdict(config)

        # 寫入檔案
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"成功儲存設定: {config_file}")

    except Exception as e:
        logger.error(f"儲存設定檔時發生錯誤: {e}")
