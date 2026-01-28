"""CLI 入口模組"""

import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.tree import Tree

from swbatch.core import SolidWorksConverter, FileScanner, ExportFormat, ConversionTask, parse_formats
from swbatch.core.converter import ConversionStatus, ConversionStats
from swbatch.core.logging_config import setup_logging, get_logger
from swbatch.core.paths import get_log_dir

app = typer.Typer(
    name="swbatch",
    help="SolidWorks 批次轉檔工具 - 支援 CLI 命令行與 GUI 圖形介面切換",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,  # 禁用自動補齊功能
)


console = Console(
    force_terminal=True,
    legacy_windows=False,  # 使用現代 Windows 終端機功能
)
logger = get_logger(__name__)


@app.command()
def convert(
    input_dir: Annotated[
        Path,
        typer.Argument(
            help="輸入目錄：包含 SolidWorks (.sldprt, .sldasm) 的資料夾",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            show_default=False,
        ),
    ],


    output_dir: Annotated[
        Path,
        typer.Argument(
            help="輸出目錄：轉檔後的檔案存放路徑",
            resolve_path=True,
            show_default=False,
        ),
    ],


    formats: Annotated[
        str,
        typer.Option(
            "--format", "-f",
            help="輸出格式：支援 stl, 3mf，可用逗號分隔多個方式",
            metavar="FORMATS",
        ),
    ] = "stl",


    flat: Annotated[
        bool,
        typer.Option(
            "--flat",
            help="不保留目錄結構，所有檔案輸出到同一目錄",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force", "-F",
            help="強制重新轉檔，忽略已存在的檔案",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n",
            help="預覽模式，只顯示將要轉檔的檔案",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="顯示詳細日誌",
        ),
    ] = False,
) -> None:
    """
    批次轉換 SolidWorks 檔案

    掃描輸入目錄下的所有 SolidWorks 零件與組合檔，並調用 SolidWorks 背景執行轉檔。

    範例：
    - 標準轉檔： swbatch convert F:\Parts F:\Output
    - 多格式轉檔： swbatch convert F:\Parts F:\Output -f stl,3mf
    - 忽略目錄結構： swbatch convert F:\Parts F:\Output --flat
    - 強制覆蓋現有檔： swbatch convert F:\Parts F:\Output --force
    """


    log_dir = get_log_dir()
    setup_logging(verbose=verbose, log_dir=log_dir, console=console)
    logger.info(f"開始批次轉檔：{input_dir} -> {output_dir}")

    # 解析格式
    try:
        export_formats = parse_formats(formats)
    except ValueError as e:
        console.print(f"[red]錯誤：{e}[/red]")
        logger.error(f"格式解析失敗：{e}")
        raise typer.Exit(1)

    console.print(f"[bold blue]輸入目錄：[/bold blue]{input_dir}")
    console.print(f"[bold blue]輸出目錄：[/bold blue]{output_dir}")
    console.print(f"[bold blue]輸出格式：[/bold blue]{', '.join(f.value.upper() for f in export_formats)}")

    # 掃描檔案
    scanner = FileScanner(
        input_dir=input_dir,
        output_dir=output_dir,
        formats=export_formats,
        preserve_structure=not flat,
    )

    with console.status("[bold green]掃描檔案中..."):
        pending, skipped = scanner.scan_pending()

    # 顯示統計
    console.print()
    console.print(f"[green]需要轉檔：[/green]{len(pending)} 個檔案")
    console.print(f"[yellow]可略過：[/yellow]{len(skipped)} 個檔案")

    if not pending and not force:
        console.print("[bold green]沒有需要轉檔的檔案！[/bold green]")
        return

    # 若強制模式，將略過的也加入
    tasks = pending if not force else pending + skipped

    # 預覽模式
    if dry_run:
        tree = _build_tasks_tree(tasks, input_dir, "將要轉檔的檔案")
        console.print(tree)
        return

    # 確認繼續
    if not typer.confirm(f"是否開始轉檔 {len(tasks)} 個檔案？"):
        console.print("[yellow]已取消[/yellow]")
        return

    # 建立輸出目錄
    output_dir.mkdir(parents=True, exist_ok=True)

    # 開始轉檔
    _run_conversion(tasks, skip_existing=not force)


def _build_tasks_tree(tasks: list[ConversionTask], root_path: Path, title: str) -> Tree:
    """建立任務樹狀結構"""
    tree = Tree(f"[bold blue]{title}[/bold blue] (於 {root_path.name})")

    # 建立目錄節點的映射
    nodes: dict[Path, Tree] = {Path("."): tree}

    # 依檔案名稱排序任務
    sorted_tasks = sorted(tasks, key=lambda t: t.source_path)

    for task in sorted_tasks:
        try:
            rel_path = task.source_path.parent.relative_to(root_path)
        except ValueError:
            rel_path = Path(".")

        # 確保所有父目錄節點都已建立
        current = Path(".")
        for part in rel_path.parts:
            parent = current
            current = current / part
            if current not in nodes:
                nodes[current] = nodes[parent].add(f"📁 [bold]{part}[/bold]")

        # 建立檔案節點
        needs_convert = task.needs_conversion()
        status_tag = "[red]需轉檔[/red]" if needs_convert else "[green]已是最新[/green]"
        
        # 取得該檔案的所有格式（如果有重複掃描到多格式）
        # 注意：雖然 tasks 列表可能包含同一檔案的多個格式任務，但我們在樹中合併顯示
        filename = task.source_path.name
        label = f"{filename} [cyan]({task.format.value.upper()})[/cyan] {status_tag}"
        nodes[rel_path].add(label)

    return tree


def _show_preview(tasks: list[ConversionTask]) -> None:
    """顯示預覽（已棄用，改用 _build_tasks_tree）"""
    table = Table(title="將要轉檔的檔案")
    table.add_column("來源檔案", style="cyan")
    table.add_column("輸出格式", style="green")
    table.add_column("狀態", style="yellow")

    for task in tasks:
        status = "需轉檔" if task.needs_conversion() else "將重新轉檔"
        table.add_row(task.source_path.name, task.format.value.upper(), status)

    console.print(table)


def _run_conversion(tasks: list[ConversionTask], skip_existing: bool) -> None:
    """執行轉檔"""
    results = []

    start_time = time.perf_counter()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TextColumn("{task.fields[filename]}", style="cyan"),
        console=console,
        expand=True,
        transient=True,
    ) as progress:
        task_id = progress.add_task(
            "[bold green]轉檔中...",
            total=len(tasks),
            filename=""
        )

        def on_progress(
            current: int,
            total: int,
            task: ConversionTask,
            status: ConversionStatus | None,
        ) -> None:
            if status is not None:
                # 檔案處理完成，更新進度條
                progress.update(task_id, advance=1, filename="", refresh=True)
            else:
                # 正在處理中，顯示檔名
                progress.update(task_id, filename=task.relative_source)

        try:
            with SolidWorksConverter(visible=False) as converter:
                results = converter.convert_batch(
                    tasks=tasks,
                    on_progress=on_progress,
                    skip_existing=skip_existing,
                )
        except RuntimeError as e:
            console.print(f"[red]錯誤：{e}[/red]")
            console.print("[yellow]請確認 SolidWorks 已安裝並可正常啟動[/yellow]")
            raise typer.Exit(1)

    elapsed_time = time.perf_counter() - start_time

    # 使用 ConversionStats 統計結果
    stats = ConversionStats.from_results(results)

    # 顯示結果
    console.print()
    console.print("[bold]轉檔完成！[/bold]")
    console.print(f"[green]成功：{stats.success}[/green]")
    console.print(f"[yellow]略過：{stats.skipped}[/yellow]")
    if stats.failed > 0:
        console.print(f"[red]失敗：{stats.failed}[/red]")
    console.print(f"[blue]總耗時：{elapsed_time:.1f} 秒[/blue]")


@app.command()
def scan(
    input_dir: Annotated[
        Path,
        typer.Argument(
            help="輸入目錄路徑",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    output_dir: Annotated[
        Optional[Path],
        typer.Argument(
            help="輸出目錄：若提供此路徑，將比對並標示哪些檔案尚未轉檔",
            resolve_path=True,
            show_default=False,
        ),
    ] = None,

    formats: Annotated[
        str,
        typer.Option(
            "--format", "-f",
            help="掃描格式：指定要尋找的目標轉檔格式 (stl, 3mf)",
            metavar="FORMATS",
        ),
    ] = "stl",


) -> None:
    """
    掃描並列出 SolidWorks 檔案

    僅執行掃描動作，以樹狀結構列出目錄下的所有零件圖與組合圖。

    範例：
    - 簡易掃描： swbatch scan F:\Parts
    - 比對輸出目錄： swbatch scan F:\Parts F:\Output
    """


    try:
        export_formats = parse_formats(formats)
    except ValueError as e:
        console.print(f"[red]錯誤：{e}[/red]")
        raise typer.Exit(1)

    scanner = FileScanner(
        input_dir=input_dir,
        output_dir=output_dir or input_dir,
        formats=export_formats,
    )

    with console.status("[bold green]掃描檔案中..."):
        if output_dir:
            pending, skipped = scanner.scan_pending()
            tasks = pending + skipped
        else:
            tasks = scanner.scan()

    # 建立樹狀顯示
    title = f"找到 {len(tasks)} 個檔案"
    tree = _build_tasks_tree(tasks, input_dir, title)
    console.print(tree)


@app.command()
def gui() -> None:
    """
    啟動圖形介面 (GUI)

    開啟視窗版視窗，提供更直覺的檔案選擇與轉檔進度顯示。
    """


    try:
        from swbatch.gui.main import main as gui_main
        gui_main()
    except ImportError as e:
        console.print(f"[red]無法啟動 GUI：{e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

