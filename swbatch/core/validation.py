"""路徑驗證模組

提供 GUI 使用的路徑驗證函式。
CLI 繼續使用 typer 的參數驗證以保持其 UX。
"""

from pathlib import Path


def validate_input_dir(path: Path | str) -> tuple[bool, str]:
    """驗證輸入目錄

    Args:
        path: 輸入目錄路徑

    Returns:
        (是否有效, 錯誤訊息)。有效時錯誤訊息為空字串。

    Examples:
        >>> valid, error = validate_input_dir("/existing/path")
        >>> if not valid:
        ...     show_error(error)
    """
    if not path:
        return False, "請選擇輸入目錄"

    path = Path(path)

    if not path.exists():
        return False, f"輸入目錄不存在：{path}"

    if not path.is_dir():
        return False, f"路徑不是目錄：{path}"

    return True, ""


def validate_output_dir(path: Path | str) -> tuple[bool, str]:
    """驗證輸出目錄

    不要求輸出目錄必須存在（會自動建立），但會檢查路徑的有效性。

    Args:
        path: 輸出目錄路徑

    Returns:
        (是否有效, 錯誤訊息)。有效時錯誤訊息為空字串。

    Examples:
        >>> valid, error = validate_output_dir("/some/output/path")
        >>> if not valid:
        ...     show_error(error)
    """
    if not path:
        return False, "請選擇輸出目錄"

    path = Path(path)

    # 如果已存在，檢查是否為目錄
    if path.exists() and not path.is_dir():
        return False, f"路徑已存在但不是目錄：{path}"

    return True, ""


def validate_paths(
    input_dir: Path | str,
    output_dir: Path | str,
) -> tuple[bool, str]:
    """驗證輸入和輸出目錄

    Args:
        input_dir: 輸入目錄路徑
        output_dir: 輸出目錄路徑

    Returns:
        (是否有效, 錯誤訊息)。有效時錯誤訊息為空字串。
    """
    valid, error = validate_input_dir(input_dir)
    if not valid:
        return False, error

    valid, error = validate_output_dir(output_dir)
    if not valid:
        return False, error

    return True, ""
