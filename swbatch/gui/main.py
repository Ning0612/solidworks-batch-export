"""GUI 主模組 (tkinter)"""

import sys
import logging
import threading
import queue
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from swbatch.core import SolidWorksConverter, FileScanner, ExportFormat, ConversionTask
from swbatch.core.converter import ConversionStatus, ConversionResult

logger = logging.getLogger(__name__)


class ConversionWorker(threading.Thread):
    """背景轉檔執行緒

    注意：所有 SolidWorks COM 操作都在此執行緒中進行，
    以符合 COM STA 模式的要求。
    """

    def __init__(
        self,
        tasks: list[ConversionTask],
        result_queue: queue.Queue,
        skip_existing: bool = True,
    ):
        super().__init__(daemon=True)
        self.tasks = tasks
        self.result_queue = result_queue
        self.skip_existing = skip_existing
        self._cancelled = False

    def cancel(self) -> None:
        """取消轉檔"""
        self._cancelled = True

    def run(self) -> None:
        """執行轉檔（在背景執行緒中）"""
        results: list[ConversionResult] = []

        try:
            with SolidWorksConverter(visible=False) as converter:
                total = len(self.tasks)

                for idx, task in enumerate(self.tasks, start=1):
                    if self._cancelled:
                        break

                    # 發送進度訊號
                    self.result_queue.put(("progress", idx, total, task.source_path.name, "轉檔中..."))

                    # 檢查是否需要跳過
                    if self.skip_existing and not task.needs_conversion():
                        result = ConversionResult(
                            task=task,
                            status=ConversionStatus.SKIPPED,
                            message="已是最新",
                        )
                    else:
                        result = converter.convert_single(task)

                    results.append(result)

                    # 發送完成狀態
                    status_text = {
                        ConversionStatus.SUCCESS: "成功",
                        ConversionStatus.FAILED: "失敗",
                        ConversionStatus.SKIPPED: "略過",
                        ConversionStatus.OPEN_FAILED: "開啟失敗",
                    }.get(result.status, "未知")
                    self.result_queue.put(("progress", idx, total, task.source_path.name, status_text))

        except Exception as e:
            logger.exception("轉檔時發生錯誤")
            self.result_queue.put(("error", str(e)))
            return

        self.result_queue.put(("finished", results))


class MainWindow:
    """主視窗"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SolidWorks 批次轉檔工具")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)

        self.tasks: list[ConversionTask] = []
        self.worker: Optional[ConversionWorker] = None
        self.result_queue: queue.Queue = queue.Queue()
        self.check_vars: dict[str, tk.BooleanVar] = {}  # iid -> BooleanVar
        self.task_to_iid: dict[int, str] = {}  # task index -> tree iid
        self.iid_to_task: dict[str, int] = {}  # tree iid -> task index
        self.input_path: Optional[Path] = None

        self._setup_ui()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """設定樣式"""
        style = ttk.Style()
        style.configure("Title.TLabel", font=("", 11, "bold"))
        style.configure("Big.TButton", font=("", 11))

    def _setup_ui(self) -> None:
        """建立 UI"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 路徑設定區
        path_frame = ttk.LabelFrame(main_frame, text="路徑設定", padding="10")
        path_frame.pack(fill=tk.X, pady=(0, 10))

        # 輸入目錄
        ttk.Label(path_frame, text="輸入目錄：").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(path_frame, textvariable=self.input_var, width=60)
        self.input_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(path_frame, text="瀏覽...", command=self._browse_input).grid(row=0, column=2, pady=2)

        # 輸出目錄
        ttk.Label(path_frame, text="輸出目錄：").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.output_var = tk.StringVar()
        self.output_entry = ttk.Entry(path_frame, textvariable=self.output_var, width=60)
        self.output_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(path_frame, text="瀏覽...", command=self._browse_output).grid(row=1, column=2, pady=2)

        path_frame.columnconfigure(1, weight=1)

        # 選項區
        options_frame = ttk.LabelFrame(main_frame, text="轉檔選項", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(options_frame, text="輸出格式：").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value="stl")
        format_combo = ttk.Combobox(
            options_frame,
            textvariable=self.format_var,
            values=["stl", "3mf", "all"],
            state="readonly",
            width=15,
        )
        format_combo.pack(side=tk.LEFT, padx=5)

        self.preserve_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="保留目錄結構", variable=self.preserve_var).pack(side=tk.LEFT, padx=20)

        self.skip_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="略過已存在的檔案", variable=self.skip_var).pack(side=tk.LEFT)

        # 掃描按鈕區
        scan_frame = ttk.Frame(main_frame)
        scan_frame.pack(fill=tk.X, pady=(0, 10))

        self.scan_btn = ttk.Button(scan_frame, text="掃描檔案", command=self._scan_files, style="Big.TButton")
        self.scan_btn.pack(side=tk.LEFT)

        self.select_all_btn = ttk.Button(scan_frame, text="全選", command=self._select_all, state=tk.DISABLED)
        self.select_all_btn.pack(side=tk.LEFT, padx=5)

        self.deselect_all_btn = ttk.Button(scan_frame, text="全不選", command=self._deselect_all, state=tk.DISABLED)
        self.deselect_all_btn.pack(side=tk.LEFT)

        # 檔案列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview with scrollbar - 樹狀結構顯示
        columns = ("format", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="檔案/目錄")
        self.tree.heading("format", text="格式")
        self.tree.heading("status", text="狀態")

        self.tree.column("#0", width=500, stretch=True)
        self.tree.column("format", width=80, anchor=tk.CENTER)
        self.tree.column("status", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 綁定雙擊事件切換勾選
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<space>", self._on_tree_space)

        # 進度條
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(side=tk.LEFT, padx=10)

        # 轉檔按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        self.convert_btn = ttk.Button(
            button_frame,
            text="開始轉檔",
            command=self._start_conversion,
            state=tk.DISABLED,
            style="Big.TButton",
        )
        self.convert_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(
            button_frame,
            text="取消",
            command=self._cancel_conversion,
            state=tk.DISABLED,
        )
        self.cancel_btn.pack(side=tk.LEFT)

        # 狀態列
        self.status_var = tk.StringVar(value="就緒")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

    def _browse_input(self) -> None:
        """選擇輸入目錄"""
        dir_path = filedialog.askdirectory(initialdir=self.input_var.get())
        if dir_path:
            self.input_var.set(dir_path)

    def _browse_output(self) -> None:
        """選擇輸出目錄"""
        dir_path = filedialog.askdirectory(initialdir=self.output_var.get())
        if dir_path:
            self.output_var.set(dir_path)

    def _get_selected_formats(self) -> list[ExportFormat]:
        """取得選擇的輸出格式"""
        fmt = self.format_var.get()
        if fmt == "all":
            return [ExportFormat.STL, ExportFormat.THREEMF]
        if fmt == "3mf":
            return [ExportFormat.THREEMF]
        return [ExportFormat.STL]

    def _scan_files(self) -> None:
        """掃描檔案"""
        input_dir = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()

        if not input_dir:
            messagebox.showwarning("警告", "請選擇輸入目錄")
            return

        if not output_dir:
            messagebox.showwarning("警告", "請選擇輸出目錄")
            return

        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.exists():
            messagebox.showwarning("警告", f"輸入目錄不存在：{input_dir}")
            return

        formats = self._get_selected_formats()
        preserve_structure = self.preserve_var.get()

        scanner = FileScanner(
            input_dir=input_path,
            output_dir=output_path,
            formats=formats,
            preserve_structure=preserve_structure,
        )

        self.status_var.set("掃描中...")
        self.root.update()

        try:
            self.tasks = scanner.scan()
            self.input_path = input_path
        except Exception as e:
            messagebox.showerror("錯誤", f"掃描失敗：{e}")
            return

        self._populate_tree()
        self.status_var.set(f"找到 {len(self.tasks)} 個檔案")
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        self.convert_btn.config(state=tk.NORMAL if self.tasks else tk.DISABLED)

    def _populate_tree(self) -> None:
        """填充檔案列表（樹狀結構）"""
        # 清空現有項目
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.check_vars.clear()
        self.task_to_iid.clear()
        self.iid_to_task.clear()

        if not self.input_path:
            return

        # 建立目錄節點的映射
        dir_nodes: dict[Path, str] = {}  # 相對路徑 -> tree iid

        for idx, task in enumerate(self.tasks):
            # 計算相對路徑
            try:
                rel_path = task.source_path.parent.relative_to(self.input_path)
            except ValueError:
                rel_path = Path(".")

            # 建立目錄節點（如果不存在）
            parent_iid = ""
            if rel_path != Path("."):
                parts = rel_path.parts
                current_path = Path()
                for part in parts:
                    current_path = current_path / part
                    if current_path not in dir_nodes:
                        # 建立目錄節點
                        dir_iid = f"dir_{current_path}"
                        self.tree.insert(
                            parent_iid,
                            tk.END,
                            iid=dir_iid,
                            text=f"📁 {part}",
                            values=("", ""),
                            open=True,
                        )
                        dir_nodes[current_path] = dir_iid
                    parent_iid = dir_nodes[current_path]

            # 建立檔案節點
            needs_convert = task.needs_conversion()
            check_var = tk.BooleanVar(value=needs_convert)

            status = "需轉檔" if needs_convert else "已是最新"
            check_text = "☑" if needs_convert else "☐"

            file_iid = f"file_{idx}"
            self.tree.insert(
                parent_iid,
                tk.END,
                iid=file_iid,
                text=f"{check_text} {task.source_path.name}",
                values=(task.format.value.upper(), status),
            )

            self.check_vars[file_iid] = check_var
            self.task_to_iid[idx] = file_iid
            self.iid_to_task[file_iid] = idx

    def _toggle_item(self, iid: str) -> None:
        """切換項目的勾選狀態"""
        if iid not in self.check_vars:
            return  # 目錄節點不可勾選

        var = self.check_vars[iid]
        new_state = not var.get()
        var.set(new_state)

        # 更新顯示文字
        task_idx = self.iid_to_task[iid]
        task = self.tasks[task_idx]
        check_text = "☑" if new_state else "☐"
        self.tree.item(iid, text=f"{check_text} {task.source_path.name}")

    def _on_tree_double_click(self, event) -> None:
        """處理 Treeview 雙擊事件（切換勾選）"""
        item = self.tree.identify_row(event.y)
        if item and item.startswith("file_"):
            self._toggle_item(item)

    def _on_tree_space(self, event) -> None:
        """處理空白鍵（切換選中項目的勾選）"""
        selected = self.tree.selection()
        for item in selected:
            if item.startswith("file_"):
                self._toggle_item(item)

    def _select_all(self) -> None:
        """全選"""
        for iid, var in self.check_vars.items():
            var.set(True)
            task_idx = self.iid_to_task[iid]
            task = self.tasks[task_idx]
            self.tree.item(iid, text=f"☑ {task.source_path.name}")

    def _deselect_all(self) -> None:
        """全不選"""
        for iid, var in self.check_vars.items():
            var.set(False)
            task_idx = self.iid_to_task[iid]
            task = self.tasks[task_idx]
            self.tree.item(iid, text=f"☐ {task.source_path.name}")

    def _get_selected_tasks(self) -> list[ConversionTask]:
        """取得勾選的任務"""
        selected = []
        for iid, var in self.check_vars.items():
            if var.get():
                task_idx = self.iid_to_task[iid]
                selected.append(self.tasks[task_idx])
        return selected

    def _start_conversion(self) -> None:
        """開始轉檔"""
        selected_tasks = self._get_selected_tasks()
        if not selected_tasks:
            messagebox.showwarning("警告", "請選擇要轉檔的檔案")
            return

        # 確認
        if not messagebox.askyesno("確認", f"是否開始轉檔 {len(selected_tasks)} 個檔案？"):
            return

        # 建立輸出目錄
        output_dir = Path(self.output_var.get())
        output_dir.mkdir(parents=True, exist_ok=True)

        # 禁用 UI
        self._set_ui_enabled(False)
        self.progress_var.set(0)
        self.cancel_btn.config(state=tk.NORMAL)

        # 啟動背景執行緒
        skip_existing = self.skip_var.get()
        self.result_queue = queue.Queue()
        self.worker = ConversionWorker(selected_tasks, self.result_queue, skip_existing)
        self.worker.start()

        # 開始檢查佇列
        self._check_queue()

    def _cancel_conversion(self) -> None:
        """取消轉檔"""
        if self.worker:
            self.worker.cancel()
            self.status_var.set("正在取消...")

    def _set_ui_enabled(self, enabled: bool) -> None:
        """設定 UI 啟用狀態"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.input_entry.config(state=state)
        self.output_entry.config(state=state)
        self.scan_btn.config(state=state)
        self.select_all_btn.config(state=state)
        self.deselect_all_btn.config(state=state)
        self.convert_btn.config(state=state)

    def _check_queue(self) -> None:
        """檢查結果佇列"""
        try:
            while True:
                msg = self.result_queue.get_nowait()
                msg_type = msg[0]

                if msg_type == "progress":
                    _, current, total, filename, status = msg
                    self.progress_var.set((current / total) * 100)
                    self.progress_label.config(text=f"{current}/{total}")
                    self.status_var.set(f"[{status}] {filename}")

                    # 更新樹狀列表狀態
                    for idx, task in enumerate(self.tasks):
                        if task.source_path.name == filename:
                            iid = self.task_to_iid.get(idx)
                            if iid:
                                self.tree.set(iid, "status", status)
                            break

                elif msg_type == "finished":
                    results = msg[1]
                    self._on_finished(results)
                    return

                elif msg_type == "error":
                    error_msg = msg[1]
                    self._on_error(error_msg)
                    return

        except queue.Empty:
            pass

        # 繼續檢查
        self.root.after(100, self._check_queue)

    def _on_finished(self, results: list[ConversionResult]) -> None:
        """處理轉檔完成"""
        self._set_ui_enabled(True)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="")

        # 統計結果
        success = sum(1 for r in results if r.status == ConversionStatus.SUCCESS)
        failed = sum(1 for r in results if r.status in (ConversionStatus.FAILED, ConversionStatus.OPEN_FAILED))
        skipped = sum(1 for r in results if r.status == ConversionStatus.SKIPPED)

        self.status_var.set(f"完成！成功: {success}, 略過: {skipped}, 失敗: {failed}")

        messagebox.showinfo(
            "轉檔完成",
            f"轉檔完成！\n\n成功：{success}\n略過：{skipped}\n失敗：{failed}",
        )

        self.worker = None

    def _on_error(self, error_msg: str) -> None:
        """處理錯誤"""
        self._set_ui_enabled(True)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="")
        self.status_var.set("發生錯誤")

        messagebox.showerror(
            "錯誤",
            f"轉檔時發生錯誤：\n\n{error_msg}\n\n請確認 SolidWorks 已安裝並可正常啟動。",
        )

        self.worker = None


def main() -> None:
    """GUI 入口點"""
    from swbatch.core.logging_config import setup_logging

    # GUI 不需要 Rich Console，日誌只記錄到檔案
    # 使用項目目錄的 logs/ 與 CLI 統一
    log_dir = Path.cwd() / "logs"
    setup_logging(verbose=False, log_dir=log_dir, console=None)

    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
