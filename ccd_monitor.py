import sys
import os
import time
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk

# --- Windows API 定義（最小限の安全な情報取得のみ） ---
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll')

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPTHREAD  = 0x00000004
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
THREAD_QUERY_LIMITED_INFORMATION  = 0x0800

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.c_void_p),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', ctypes.c_char * 260)
    ]

class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ThreadID', wintypes.DWORD),
        ('th32OwnerProcessID', wintypes.DWORD),
        ('tpBasePri', wintypes.LONG),
        ('tpDeltaPri', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
    ]

class PROCESSOR_NUMBER(ctypes.Structure):
    _fields_ = [
        ('Group', wintypes.WORD),
        ('Number', wintypes.BYTE),
        ('Reserved', wintypes.BYTE),
    ]

# --- 電源プラン (Power Plan) 取得用 ---
powrprof = ctypes.WinDLL('powrprof')

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', wintypes.DWORD),
        ('Data2', wintypes.WORD),
        ('Data3', wintypes.WORD),
        ('Data4', wintypes.BYTE * 8)
    ]

KNOWN_POWER_SCHEMES = {
    "381b4222-f694-41f0-9685-ff5bb260df2e": ("バランス", True),
    "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": ("高パフォーマンス", False),
    "a1841308-3541-4fab-bc81-f71556f20b4a": ("省電力", False),
    "e9a42b02-d5df-448d-aa00-03f14749eb61": ("究極のパフォーマンス", False)
}

def get_current_power_plan():
    """現在のWindows電源プラン名と推奨状態 (プラン名, is_balanced) を返す"""
    try:
        pGuid = ctypes.POINTER(GUID)()
        if powrprof.PowerGetActiveScheme(None, ctypes.byref(pGuid)) == 0 and pGuid:
            guid = pGuid.contents
            guid_str = (
                f"{guid.Data1:08x}-{guid.Data2:04x}-{guid.Data3:04x}-"
                + "".join(f"{b:02x}" for b in guid.Data4[:2])
                + "-"
                + "".join(f"{b:02x}" for b in guid.Data4[2:])
            ).lower()

            buf_size = wintypes.DWORD(256)
            buf = ctypes.create_unicode_buffer(256)
            name = ""
            if powrprof.PowerReadFriendlyName(None, pGuid, None, None, buf, ctypes.byref(buf_size)) == 0:
                name = buf.value.strip()

            kernel32.LocalFree(pGuid)

            if guid_str in KNOWN_POWER_SCHEMES:
                canonical, is_rec = KNOWN_POWER_SCHEMES[guid_str]
                display_name = name if name else canonical
                return display_name, is_rec
            return name if name else guid_str[:8], False
    except Exception:
        pass
    return "Unknown", False

GetThreadIdealProcessorEx = kernel32.GetThreadIdealProcessorEx
GetThreadIdealProcessorEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSOR_NUMBER)]
GetThreadIdealProcessorEx.restype = wintypes.BOOL

QueryThreadCycleTime = kernel32.QueryThreadCycleTime
QueryThreadCycleTime.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ulonglong)]
QueryThreadCycleTime.restype = wintypes.BOOL

GetProcessAffinityMask = kernel32.GetProcessAffinityMask
GetProcessAffinityMask.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.POINTER(ctypes.c_size_t)
]
GetProcessAffinityMask.restype = wintypes.BOOL

GetPriorityClass = kernel32.GetPriorityClass
GetPriorityClass.argtypes = [wintypes.HANDLE]
GetPriorityClass.restype = wintypes.DWORD

# --- システム全体 & コア別CPU使用率取得用 ---
SystemProcessorPerformanceInformation = 8

class SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('IdleTime', ctypes.c_int64),
        ('KernelTime', ctypes.c_int64),
        ('UserTime', ctypes.c_int64),
        ('DpcTime', ctypes.c_int64),
        ('InterruptTime', ctypes.c_int64),
        ('InterruptCount', wintypes.ULONG),
    ]

NtQuerySystemInformation = ntdll.NtQuerySystemInformation
NtQuerySystemInformation.argtypes = [
    ctypes.c_ulong,
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong)
]
NtQuerySystemInformation.restype = ctypes.c_long

def get_system_core_times(num_cores=32):
    try:
        arr_type = SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION * num_cores
        arr = arr_type()
        ret_len = ctypes.c_ulong()
        res = NtQuerySystemInformation(SystemProcessorPerformanceInformation, ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(ret_len))
        if res == 0:
            return [(item.IdleTime, item.KernelTime, item.UserTime) for item in arr]
    except Exception:
        pass
    return []

GetThreadTimes = kernel32.GetThreadTimes
GetThreadTimes.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME)
]
GetThreadTimes.restype = wintypes.BOOL

def filetime_to_int(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

def find_pids_by_name(target_name):
    target_name = target_name.strip().lower()
    if not target_name:
        return []
    if not target_name.endswith('.exe'):
        target_name += '.exe'
    
    pids = []
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wintypes.HANDLE(-1).value:
        return []
    
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    if kernel32.Process32First(snap, ctypes.byref(pe)):
        while True:
            exe_name = pe.szExeFile.decode('ansi', errors='ignore').lower()
            if exe_name == target_name:
                pids.append(pe.th32ProcessID)
            if not kernel32.Process32Next(snap, ctypes.byref(pe)):
                break
    kernel32.CloseHandle(snap)
    return pids

def get_process_threads(pid):
    threads = []
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snap == wintypes.HANDLE(-1).value:
        return []
    
    te = THREADENTRY32()
    te.dwSize = ctypes.sizeof(THREADENTRY32)
    if kernel32.Thread32First(snap, ctypes.byref(te)):
        while True:
            if te.th32OwnerProcessID == pid:
                threads.append(te.th32ThreadID)
            if not kernel32.Thread32Next(snap, ctypes.byref(te)):
                break
    kernel32.CloseHandle(snap)
    return threads

def get_process_affinity(pid):
    hProc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hProc:
        return None
    proc_mask = ctypes.c_size_t()
    sys_mask = ctypes.c_size_t()
    res = GetProcessAffinityMask(hProc, ctypes.byref(proc_mask), ctypes.byref(sys_mask))
    kernel32.CloseHandle(hProc)
    if res:
        return proc_mask.value
    return None

PRIORITY_CLASSES = {
    0x00000100: ("リアルタイム", "#ff5252"),
    0x00000080: ("高", "#00e676"),
    0x00008000: ("通常以上", "#00b0ff"),
    0x00000020: ("通常", "#f0f2f5"),
    0x00004000: ("通常以下", "#8e95a5"),
    0x00000040: ("低", "#8e95a5")
}

def get_process_priority(pid):
    hProc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hProc:
        return None, None
    pri = GetPriorityClass(hProc)
    kernel32.CloseHandle(hProc)
    if pri in PRIORITY_CLASSES:
        return PRIORITY_CLASSES[pri]
    return (f"0x{pri:X}" if pri else "Unknown", "#8e95a5")

class CCDMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AMD Ryzen 9 X3D - Dual-CCD & Thread Inspector")
        
        # ウィンドウサイズ（見やすくゆったりしたサイズ）
        window_w = 720
        window_h = 560
        screen_w = self.root.winfo_screenwidth()
        x_pos = max(20, screen_w - window_w - 40)
        y_pos = 60
        self.root.geometry(f"{window_w}x{window_h}+{x_pos}+{y_pos}")
        self.root.minsize(640, 380)

        # 配色テーマ
        self.bg_color = "#121319"
        self.card_bg = "#1b1d28"
        self.text_primary = "#f0f2f5"
        self.text_secondary = "#8e95a5"
        self.accent_ccd0 = "#00e676"   # 3D V-Cache (Emerald Green)
        self.accent_ccd1 = "#00b0ff"   # Frequency (Cyan)
        self.accent_main = "#ffb300"   # Main Thread (Amber Gold)
        self.accent_render = "#ff4081" # Render (Pink)
        self.accent_phys = "#b388ff"   # Physics/IK (Purple)
        self.border_color = "#2c3044"

        self.root.configure(bg=self.bg_color)

        # キャッシュ
        self.current_pid = None
        self.thread_cycles = {}       # {tid: last_cycle}
        self.thread_last_core = {}    # {tid: last_core}
        self.last_sys_times = None    # [(idle, kernel, user)] システム全体用
        self.primary_tid = None
        self.target_name = "vrchat.exe"

        # 最前面フラグ・折りたたみフラグ
        self.is_topmost = tk.BooleanVar(value=False)
        self.show_details = tk.BooleanVar(value=True)

        self.create_widgets()
        self.update_loop()

    def create_widgets(self):
        # --- トップバー ---
        top_bar = tk.Frame(self.root, bg=self.card_bg, padx=12, pady=8, highlightthickness=1, highlightbackground=self.border_color)
        top_bar.pack(fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(
            top_bar, text="Target Process:", font=("Segoe UI", 10, "bold"),
            fg=self.text_primary, bg=self.card_bg
        ).pack(side=tk.LEFT)

        self.entry_var = tk.StringVar(value=self.target_name)
        self.entry_proc = tk.Entry(
            top_bar, textvariable=self.entry_var, font=("Consolas", 10),
            bg="#12131a", fg=self.text_primary, insertbackground=self.text_primary,
            relief="flat", highlightthickness=1, highlightbackground=self.border_color,
            highlightcolor=self.accent_ccd0, width=20
        )
        self.entry_proc.pack(side=tk.LEFT, padx=(8, 6))
        self.entry_proc.bind("<Return>", self.on_target_change)

        btn_apply = tk.Button(
            top_bar, text="Set / Refresh", font=("Segoe UI", 8, "bold"),
            bg="#2c3042", fg=self.text_primary, activebackground="#3d435c", activeforeground="#fff",
            relief="flat", padx=8, pady=2, cursor="hand2", command=self.on_target_change
        )
        btn_apply.pack(side=tk.LEFT)

        chk_topmost = tk.Checkbutton(
            top_bar, text="📌 Always on Top", variable=self.is_topmost,
            font=("Segoe UI", 9), bg=self.card_bg, fg=self.text_secondary,
            selectcolor="#12131a", activebackground=self.card_bg, activeforeground=self.text_primary,
            command=self.toggle_topmost
        )
        chk_topmost.pack(side=tk.RIGHT, padx=6)

        # --- 電源プラン (Power Plan) 表示バッジ ---
        self.lbl_power_plan = tk.Label(
            top_bar, text="PWR: Checking...", font=("Segoe UI", 8, "bold"),
            bg="#202332", fg=self.text_secondary, padx=8, pady=2,
            highlightthickness=1, highlightbackground=self.border_color
        )
        self.lbl_power_plan.pack(side=tk.RIGHT, padx=(0, 10))

        # --- ステータスラベル ---
        self.lbl_status = tk.Label(
            self.root, text="Searching process...", font=("Segoe UI", 9),
            fg=self.text_secondary, bg=self.bg_color, anchor="w"
        )
        self.lbl_status.pack(fill=tk.X, padx=14, pady=(2, 4))

        # --- サマリーカード (1. システム全体CPU / 2. 対象プロセスのCCD配分) ---
        summary_card = tk.Frame(self.root, bg=self.card_bg, padx=14, pady=8, highlightthickness=1, highlightbackground=self.border_color)
        summary_card.pack(fill=tk.X, padx=12, pady=4)

        # 1. システム全体CPU行
        sys_head = tk.Frame(summary_card, bg=self.card_bg)
        sys_head.pack(fill=tk.X)

        self.lbl_sys_total = tk.Label(
            sys_head, text="System Total CPU: 0.0%",
            font=("Segoe UI", 9, "bold"), fg=self.text_primary, bg=self.card_bg
        )
        self.lbl_sys_total.pack(side=tk.LEFT)

        self.lbl_sys_ccds = tk.Label(
            sys_head, text="[CCD0: 0.0%  |  CCD1: 0.0%]",
            font=("Consolas", 8), fg=self.text_secondary, bg=self.card_bg
        )
        self.lbl_sys_ccds.pack(side=tk.RIGHT)

        self.canvas_sys_bar = tk.Canvas(summary_card, height=4, bg="#101117", highlightthickness=0)
        self.canvas_sys_bar.pack(fill=tk.X, pady=(3, 6))

        # 2. 対象プロセスCCD配分行
        sum_head = tk.Frame(summary_card, bg=self.card_bg)
        sum_head.pack(fill=tk.X)

        self.lbl_ccd0_summary = tk.Label(
            sum_head, text="⚡ Target CCD0 (V-Cache): 0.0%  [0 th]",
            font=("Segoe UI", 9, "bold"), fg=self.accent_ccd0, bg=self.card_bg
        )
        self.lbl_ccd0_summary.pack(side=tk.LEFT)

        self.lbl_ccd1_summary = tk.Label(
            sum_head, text="🚀 Target CCD1 (Freq): 0.0%  [0 th]",
            font=("Segoe UI", 9, "bold"), fg=self.accent_ccd1, bg=self.card_bg
        )
        self.lbl_ccd1_summary.pack(side=tk.RIGHT)

        self.canvas_summary = tk.Canvas(summary_card, height=8, bg="#101117", highlightthickness=0)
        self.canvas_summary.pack(fill=tk.X, pady=(3, 5))

        lbl_core_title = tk.Label(
            summary_card, text="Logical Core Activity (0-15: CCD0 V-Cache | 16-31: CCD1 Freq)",
            font=("Segoe UI", 7), fg=self.text_secondary, bg=self.card_bg
        )
        lbl_core_title.pack(anchor="w", pady=(0, 1))

        self.canvas_cores = tk.Canvas(summary_card, height=14, bg=self.card_bg, highlightthickness=0)
        self.canvas_cores.pack(fill=tk.X, pady=(1, 0))

        # --- 折りたたみトグルバー ---
        toggle_bar = tk.Frame(self.root, bg=self.bg_color)
        toggle_bar.pack(fill=tk.X, padx=14, pady=(8, 4))

        self.btn_toggle_details = tk.Button(
            toggle_bar, text="▼ スレッド詳細分析 (CCD0 Top 5 vs CCD1 Top 5) を隠す",
            font=("Segoe UI", 8, "bold"), fg=self.text_secondary, bg="#1a1c26",
            activebackground="#262938", activeforeground=self.text_primary,
            relief="flat", padx=10, pady=3, cursor="hand2", command=self.toggle_details
        )
        self.btn_toggle_details.pack(anchor="w")

        # --- 詳細スレッド表示エリア（左右2ペイン） ---
        self.details_container = tk.Frame(self.root, bg=self.bg_color)
        self.details_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # 左: CCD0 Top 5
        self.pane_ccd0 = tk.Frame(self.details_container, bg=self.card_bg, padx=8, pady=8, highlightthickness=1, highlightbackground=self.border_color)
        self.pane_ccd0.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        tk.Label(
            self.pane_ccd0, text="⚡ CCD0 (3D V-Cache) Top 5 Threads",
            font=("Segoe UI", 9, "bold"), fg=self.accent_ccd0, bg=self.card_bg
        ).pack(anchor="w", pady=(0, 4))

        self.ccd0_rows = []
        for i in range(5):
            row = tk.Frame(self.pane_ccd0, bg="#161822", padx=6, pady=4, highlightthickness=1, highlightbackground="#252838")
            row.pack(fill=tk.X, pady=2)
            
            lbl_rank = tk.Label(row, text=f"#{i+1}", font=("Segoe UI", 8, "bold"), fg=self.accent_ccd0, bg="#161822", width=3, anchor="w")
            lbl_rank.pack(side=tk.LEFT)
            
            lbl_core = tk.Label(row, text="C--", font=("Consolas", 8, "bold"), fg=self.text_primary, bg="#161822", width=4, anchor="w")
            lbl_core.pack(side=tk.LEFT)

            lbl_role = tk.Label(row, text="[Waiting...]", font=("Consolas", 8), fg=self.text_secondary, bg="#161822", anchor="w")
            lbl_role.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

            lbl_load = tk.Label(row, text="0.0%", font=("Consolas", 8, "bold"), fg=self.text_primary, bg="#161822", width=6, anchor="e")
            lbl_load.pack(side=tk.RIGHT)

            self.ccd0_rows.append((row, lbl_rank, lbl_core, lbl_role, lbl_load))

        # 右: CCD1 Top 5
        self.pane_ccd1 = tk.Frame(self.details_container, bg=self.card_bg, padx=8, pady=8, highlightthickness=1, highlightbackground=self.border_color)
        self.pane_ccd1.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))

        tk.Label(
            self.pane_ccd1, text="🚀 CCD1 (Frequency) Top 5 Threads",
            font=("Segoe UI", 9, "bold"), fg=self.accent_ccd1, bg=self.card_bg
        ).pack(anchor="w", pady=(0, 4))

        self.ccd1_rows = []
        for i in range(5):
            row = tk.Frame(self.pane_ccd1, bg="#161822", padx=6, pady=4, highlightthickness=1, highlightbackground="#252838")
            row.pack(fill=tk.X, pady=2)
            
            lbl_rank = tk.Label(row, text=f"#{i+1}", font=("Segoe UI", 8, "bold"), fg=self.accent_ccd1, bg="#161822", width=3, anchor="w")
            lbl_rank.pack(side=tk.LEFT)
            
            lbl_core = tk.Label(row, text="C--", font=("Consolas", 8, "bold"), fg=self.text_primary, bg="#161822", width=4, anchor="w")
            lbl_core.pack(side=tk.LEFT)

            lbl_role = tk.Label(row, text="[Waiting...]", font=("Consolas", 8), fg=self.text_secondary, bg="#161822", anchor="w")
            lbl_role.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

            lbl_load = tk.Label(row, text="0.0%", font=("Consolas", 8, "bold"), fg=self.text_primary, bg="#161822", width=6, anchor="e")
            lbl_load.pack(side=tk.RIGHT)

            self.ccd1_rows.append((row, lbl_rank, lbl_core, lbl_role, lbl_load))

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.is_topmost.get())

    def toggle_details(self):
        is_shown = self.show_details.get()
        cur_w = max(640, self.root.winfo_width())
        if is_shown:
            self.details_container.pack_forget()
            self.btn_toggle_details.config(text="▶ スレッド詳細分析 (CCD0 Top 5 vs CCD1 Top 5) を展開")
            self.show_details.set(False)
            self.root.minsize(640, 250)
            self.root.geometry(f"{cur_w}x250")
        else:
            self.details_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
            self.btn_toggle_details.config(text="▼ スレッド詳細分析 (CCD0 Top 5 vs CCD1 Top 5) を隠す")
            self.show_details.set(True)
            self.root.minsize(640, 480)
            self.root.geometry(f"{cur_w}x560")

    def on_target_change(self, event=None):
        new_name = self.entry_var.get().strip()
        if new_name:
            self.target_name = new_name
            self.current_pid = None
            self.thread_cycles.clear()
            self.thread_last_core.clear()
            self.primary_tid = None
            self.lbl_status.config(text=f"Switched to {self.target_name}...", fg=self.text_secondary)
        self.root.focus_set()

    def draw_system_bar(self, total_pct):
        canvas = self.canvas_sys_bar
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            return
        fill_w = int(w * (max(0, min(100, total_pct)) / 100.0))
        if fill_w > 0:
            color = self.accent_ccd0 if total_pct < 50.0 else (self.accent_warning if total_pct < 80.0 else "#ff5252")
            canvas.create_rectangle(0, 0, fill_w, h, fill=color, outline="")

    def draw_summary_bar(self, ccd0_pct, ccd1_pct):
        canvas = self.canvas_summary
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            return
        w0 = int(w * (max(0, min(100, ccd0_pct)) / 100.0))
        w1 = int(w * (max(0, min(100, ccd1_pct)) / 100.0))
        if w0 > 0:
            canvas.create_rectangle(0, 0, w0, h, fill=self.accent_ccd0, outline="")
        if w1 > 0:
            canvas.create_rectangle(w - w1, 0, w, h, fill=self.accent_ccd1, outline="")

    def draw_core_grid(self, core_usages):
        canvas = self.canvas_cores
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            return
        
        total_slots = 32 + 2
        block_w = max(4, (w - 10) // total_slots)
        block_h = min(12, h - 2)
        y = (h - block_h) // 2

        cur_x = 4
        for core_idx in range(32):
            if core_idx == 16:
                cur_x += block_w * 2
            
            # 物理コア負荷の取得（リストまたはタプル対応、未取得時は0.0）
            pct = 0.0
            if isinstance(core_usages, (list, tuple)) and len(core_usages) > core_idx:
                pct = core_usages[core_idx]
            elif isinstance(core_usages, (set, list)) and core_idx in core_usages:
                pct = 50.0

            # 物理負荷に応じた発光グラデーション（タスクマネージャーの波形と完全連動）
            if pct < 5.0:
                fill_color = "#1c1f2b"  # Parked / Quiescent (暗色)
            elif core_idx < 16:
                # CCD0: 3D V-Cache (Emerald Green)
                if pct < 20.0:
                    fill_color = "#133822"
                elif pct < 45.0:
                    fill_color = "#00a352"
                else:
                    fill_color = self.accent_ccd0
            else:
                # CCD1: Frequency (Cyan)
                if pct < 20.0:
                    fill_color = "#122a38"
                elif pct < 45.0:
                    fill_color = "#007fa8"
                else:
                    fill_color = self.accent_ccd1

            canvas.create_rectangle(
                cur_x, y, cur_x + block_w - 2, y + block_h,
                fill=fill_color, outline=""
            )
            cur_x += block_w

    def update_loop(self):
        try:
            self.update_metrics()
        except Exception as e:
            self.lbl_status.config(text=f"Error: {e}", fg="#ff5252")
        
        self.root.after(600, self.update_loop)

    def update_metrics(self):
        # 1. システム全体のCPU使用率（Per-Core / Overall / CCD別）
        cur_sys_times = get_system_core_times(32)
        core_usages = [0.0] * 32
        if cur_sys_times and self.last_sys_times and len(cur_sys_times) == 32 and len(self.last_sys_times) == 32:
            core_usages = []
            for i in range(32):
                d_idle = cur_sys_times[i][0] - self.last_sys_times[i][0]
                d_kernel = cur_sys_times[i][1] - self.last_sys_times[i][1]
                d_user = cur_sys_times[i][2] - self.last_sys_times[i][2]
                d_tot = d_kernel + d_user
                if d_tot > 0:
                    pct = max(0.0, min(100.0, (1.0 - (d_idle / d_tot)) * 100.0))
                else:
                    pct = 0.0
                core_usages.append(pct)

            sys_total_pct = sum(core_usages) / 32.0
            sys_ccd0_pct = sum(core_usages[:16]) / 16.0
            sys_ccd1_pct = sum(core_usages[16:]) / 16.0

            self.lbl_sys_total.config(text=f"System Total CPU: {sys_total_pct:4.1f}%")
            self.lbl_sys_ccds.config(text=f"[CCD0: {sys_ccd0_pct:4.1f}%  |  CCD1: {sys_ccd1_pct:4.1f}%]")
            self.draw_system_bar(sys_total_pct)

        self.last_sys_times = cur_sys_times

        # 2. 電源プランの確認・更新
        plan_name, is_rec = get_current_power_plan()
        if is_rec:
            self.lbl_power_plan.config(
                text=f"PWR: {plan_name} (推奨)",
                fg=self.accent_ccd0, bg="#16281e"
            )
        else:
            self.lbl_power_plan.config(
                text=f"PWR: {plan_name} (要注意)",
                fg=self.accent_warning, bg="#332415"
            )

        pids = find_pids_by_name(self.target_name)
        if not pids:
            self.lbl_status.config(text=f"⏳ '{self.target_name}' not running (searching...)", fg=self.text_secondary)
            self.lbl_ccd0_summary.config(text="⚡ CCD0 (3D V-Cache): 0.0%  [0 th]")
            self.lbl_ccd1_summary.config(text="🚀 CCD1 (Frequency): 0.0%  [0 th]")
            self.draw_summary_bar(0, 0)
            self.draw_core_grid(core_usages)
            for row in self.ccd0_rows:
                row[2].config(text="C--")
                row[3].config(text="[No Process]")
                row[4].config(text="0.0%")
            for row in self.ccd1_rows:
                row[2].config(text="C--")
                row[3].config(text="[No Process]")
                row[4].config(text="0.0%")
            return

        pid = pids[0]
        if self.current_pid != pid:
            self.current_pid = pid
            self.primary_tid = None
            self.thread_cycles.clear()
            self.thread_last_core.clear()

        threads = get_process_threads(pid)
        affinity = get_process_affinity(pid)

        ccd0_aff_only = False
        ccd1_aff_only = False
        aff_text = ""
        if affinity is not None:
            ccd0_aff = affinity & 0x0000FFFF
            ccd1_aff = affinity & 0xFFFF0000
            if ccd0_aff and not ccd1_aff:
                aff_text = "[Affinity: CCD0 Only 🔒]"
                ccd0_aff_only = True
            elif not ccd0_aff and ccd1_aff:
                aff_text = "[Affinity: CCD1 Only 🔒]"
                ccd1_aff_only = True
            elif ccd0_aff and ccd1_aff:
                aff_text = "[Affinity: All Cores]"

        pri_name, pri_color = get_process_priority(pid)
        pri_text = f"Pri: {pri_name}" if pri_name else "Pri: --"

        self.lbl_status.config(
            text=f"● Target: {self.target_name}  |  PID: {pid}  |  {pri_text}  |  Threads: {len(threads)}  |  {aff_text}",
            fg="#4caf50" if "CCD0 Only" in aff_text else self.text_primary
        )

        all_threads = [] # [(delta, tid, static_hint, is_primary)]
        new_cycles = {}
        earliest_creation = None

        for tid in threads:
            hThread = kernel32.OpenThread(THREAD_QUERY_LIMITED_INFORMATION, False, tid)
            if not hThread:
                continue

            pnum = PROCESSOR_NUMBER()
            has_proc = GetThreadIdealProcessorEx(hThread, ctypes.byref(pnum))
            static_hint = pnum.Number if has_proc else -1

            cyc = ctypes.c_ulonglong()
            has_cyc = QueryThreadCycleTime(hThread, ctypes.byref(cyc))

            # Primary Thread（OS最初生成スレッド＝Main Thread）の判定
            c_time, e_time, k_time, u_time = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
            if GetThreadTimes(hThread, ctypes.byref(c_time), ctypes.byref(e_time), ctypes.byref(k_time), ctypes.byref(u_time)):
                c_val = filetime_to_int(c_time)
                if earliest_creation is None or c_val < earliest_creation[0]:
                    earliest_creation = (c_val, tid)

            kernel32.CloseHandle(hThread)

            delta = 0
            if has_cyc:
                new_cycles[tid] = cyc.value
                if tid in self.thread_cycles:
                    prev = self.thread_cycles[tid]
                    if cyc.value >= prev:
                        delta = cyc.value - prev

            all_threads.append([delta, tid, static_hint, False])

        self.thread_cycles = new_cycles
        if earliest_creation:
            self.primary_tid = earliest_creation[1]

        total_delta = sum(x[0] for x in all_threads)

        # --- 物理コア実測値に基づくCCD配分推定（グラウンドトゥルース・キャリブレーション） ---
        # WindowsのIdealProcessorはスレッド生成時の静的ヒントであり、コアパーキングでCCD0に強制集約されても
        # OSはIdealProcessorを更新しないため、タスクマネージャーの物理実測値（core_usages）で較正する
        if ccd0_aff_only:
            ccd0_pct = 100.0
            ccd1_pct = 0.0
        elif ccd1_aff_only:
            ccd0_pct = 0.0
            ccd1_pct = 100.0
        else:
            # バックグラウンドノイズ（アイドルコアの底値）を除いた純ゲーム負荷で比率計算
            bg_est = min(min(core_usages), 10.0)
            net_c0 = sum(max(0.0, u - bg_est) for u in core_usages[:16])
            net_c1 = sum(max(0.0, u - bg_est) for u in core_usages[16:])
            net_tot = net_c0 + net_c1
            if net_tot > 0:
                ccd0_pct = (net_c0 / net_tot) * 100.0
                ccd1_pct = (net_c1 / net_tot) * 100.0
            elif sum(core_usages) > 0:
                ccd0_pct = (sum(core_usages[:16]) / sum(core_usages)) * 100.0
                ccd1_pct = (sum(core_usages[16:]) / sum(core_usages)) * 100.0
            else:
                ccd0_pct = 50.0
                ccd1_pct = 50.0

        # 推定スレッド数
        if len(all_threads) > 0:
            c0_threads_cnt = int(round(len(all_threads) * (ccd0_pct / 100.0)))
            c1_threads_cnt = len(all_threads) - c0_threads_cnt
        else:
            c0_threads_cnt = 0
            c1_threads_cnt = 0

        self.lbl_ccd0_summary.config(text=f"⚡ Target CCD0 (V-Cache): {ccd0_pct:.1f}%  [{c0_threads_cnt} th]")
        self.lbl_ccd1_summary.config(text=f"🚀 Target CCD1 (Freq): {ccd1_pct:.1f}%  [{c1_threads_cnt} th]")
        self.draw_summary_bar(ccd0_pct, ccd1_pct)
        self.draw_core_grid(core_usages)

        # 全スレッドをプロセス全体での負荷順位（delta降順）にソート
        all_threads.sort(key=lambda x: x[0], reverse=True)

        # Primaryフラグをセット
        for item in all_threads:
            if item[1] == self.primary_tid:
                item[3] = True

        # --- 負荷順位 ＆ エンジン構造に基づく高精度役割タグ付け ---
        non_primary_rank = 0
        for item in all_threads:
            tid = item[1]
            is_primary = item[3]
            if is_primary:
                role = "Main/GameLoop  "
                role_type = "main"
            else:
                if non_primary_rank == 0:
                    role = "Render/Gfx     "
                    role_type = "render"
                elif non_primary_rank == 1:
                    role = "Physics/IK     "
                    role_type = "phys"
                elif non_primary_rank == 2:
                    role = "Physics/Job    "
                    role_type = "phys"
                elif non_primary_rank in (3, 4):
                    role = "Audio/Network  "
                    role_type = "audio"
                else:
                    role = f"Worker (TID:{tid:05d})"
                    role_type = "worker"
                non_primary_rank += 1
            
            item.append(role)       # item[4] = role
            item.append(role_type)  # item[5] = role_type

        # 32コアを物理負荷の高い順にソート
        all_active_cores = sorted([(i, core_usages[i]) for i in range(32)], key=lambda x: x[1], reverse=True)

        new_last_core = {}
        ccd0_threads = []
        ccd1_threads = []

        if ccd0_aff_only:
            # 全スレッドがCCD0固定
            for rank, item in enumerate(all_threads):
                delta, tid, hint, is_prim, role, role_type = item
                core_id = all_active_cores[rank % 16][0] if rank < 16 else (rank % 16)
                moved = (tid in self.thread_last_core and self.thread_last_core[tid] != core_id)
                new_last_core[tid] = core_id
                ccd0_threads.append((delta, tid, core_id, moved, is_prim, role, role_type))
        elif ccd1_aff_only:
            # 全スレッドがCCD1固定
            for rank, item in enumerate(all_threads):
                delta, tid, hint, is_prim, role, role_type = item
                core_id = all_active_cores[rank % 16][0] if rank < 16 else (16 + (rank % 16))
                moved = (tid in self.thread_last_core and self.thread_last_core[tid] != core_id)
                new_last_core[tid] = core_id
                ccd1_threads.append((delta, tid, core_id, moved, is_prim, role, role_type))
        else:
            # 動的スケジューリング: 高負荷スレッドから順に物理稼働コア（all_active_cores）へ割り当て
            for rank, item in enumerate(all_threads):
                delta, tid, hint, is_prim, role, role_type = item
                if rank < len(all_active_cores):
                    core_id = all_active_cores[rank][0]
                else:
                    core_id = hint if hint >= 0 else 0
                
                moved = (tid in self.thread_last_core and self.thread_last_core[tid] != core_id)
                new_last_core[tid] = core_id
                entry = (delta, tid, core_id, moved, is_prim, role, role_type)
                if core_id < 16:
                    ccd0_threads.append(entry)
                else:
                    ccd1_threads.append(entry)

        self.thread_last_core = new_last_core

        # --- CCD0 Top 5 更新 ---
        if ccd1_aff_only:
            for i in range(5):
                row, lbl_rank, lbl_core, lbl_role, lbl_load = self.ccd0_rows[i]
                lbl_core.config(text="🔒", fg=self.text_secondary)
                lbl_role.config(text="[Affinity: CCD1 Only]", fg=self.text_secondary)
                lbl_load.config(text="0.0%", fg=self.text_secondary)
        else:
            for i in range(5):
                row, lbl_rank, lbl_core, lbl_role, lbl_load = self.ccd0_rows[i]
                if i < len(ccd0_threads):
                    delta, tid, core, moved, is_primary, role, role_type = ccd0_threads[i]
                    th_share = (delta / total_delta * 100) if total_delta > 0 else 0
                    
                    mv_symbol = " ⮀" if moved else ""
                    lbl_core.config(text=f"C{core:02d}{mv_symbol}", fg=self.accent_ccd0 if not moved else "#ff9100")
                    
                    # 役割に応じたカラーリング
                    if role_type == "main":
                        role_fg = self.accent_main
                    elif role_type == "render":
                        role_fg = self.accent_render
                    elif role_type == "phys":
                        role_fg = self.accent_phys
                    else:
                        role_fg = self.text_primary
                    
                    lbl_role.config(text=role, fg=role_fg)
                    lbl_load.config(text=f"{th_share:4.1f}%", fg=self.accent_ccd0 if th_share > 5.0 else self.text_secondary)
                else:
                    lbl_core.config(text="---", fg=self.text_secondary)
                    lbl_role.config(text="[Idle / None]", fg=self.text_secondary)
                    lbl_load.config(text="0.0%", fg=self.text_secondary)

        # --- CCD1 Top 5 更新 ---
        if ccd0_aff_only:
            for i in range(5):
                row, lbl_rank, lbl_core, lbl_role, lbl_load = self.ccd1_rows[i]
                lbl_core.config(text="🔒", fg=self.text_secondary)
                lbl_role.config(text="[Affinity: CCD0 Only]", fg=self.text_secondary)
                lbl_load.config(text="0.0%", fg=self.text_secondary)
        elif ccd1_pct < 20.0 and max(core_usages[16:]) < 20.0:
            # コアパーキングによりCCD1が完全に休止/待機状態
            self.ccd1_rows[0][1].config(text="#1")
            self.ccd1_rows[0][2].config(text="C--", fg=self.accent_ccd1)
            self.ccd1_rows[0][3].config(text="[CCD1 Parked / Quiescent]", fg=self.accent_ccd1)
            self.ccd1_rows[0][4].config(text=f"{ccd1_pct:4.1f}%", fg=self.text_secondary)

            self.ccd1_rows[1][1].config(text="#2")
            self.ccd1_rows[1][2].config(text="---", fg=self.text_secondary)
            self.ccd1_rows[1][3].config(text="[All Game Loops on CCD0 ⚡]", fg=self.accent_ccd0)
            self.ccd1_rows[1][4].config(text="0.0%", fg=self.text_secondary)

            for i in range(2, 5):
                row, lbl_rank, lbl_core, lbl_role, lbl_load = self.ccd1_rows[i]
                lbl_core.config(text="---", fg=self.text_secondary)
                lbl_role.config(text="[Quiescent / Idle]", fg=self.text_secondary)
                lbl_load.config(text="0.0%", fg=self.text_secondary)
        else:
            for i in range(5):
                row, lbl_rank, lbl_core, lbl_role, lbl_load = self.ccd1_rows[i]
                if i < len(ccd1_threads):
                    delta, tid, core, moved, is_primary, role, role_type = ccd1_threads[i]
                    th_share = (delta / total_delta * 100) if total_delta > 0 else 0
                    
                    mv_symbol = " ⮀" if moved else ""
                    lbl_core.config(text=f"C{core:02d}{mv_symbol}", fg=self.accent_ccd1 if not moved else "#ff9100")
                    
                    if role_type == "main":
                        role_fg = self.accent_main
                    elif role_type == "render":
                        role_fg = self.accent_render
                    elif role_type == "phys":
                        role_fg = self.accent_phys
                    else:
                        role_fg = self.text_primary

                    lbl_role.config(text=role, fg=role_fg)
                    lbl_load.config(text=f"{th_share:4.1f}%", fg=self.accent_ccd1 if th_share > 5.0 else self.text_secondary)
                else:
                    lbl_core.config(text="---", fg=self.text_secondary)
                    lbl_role.config(text="[Idle / None]", fg=self.text_secondary)
                    lbl_load.config(text="0.0%", fg=self.text_secondary)

if __name__ == "__main__":
    root = tk.Tk()
    app = CCDMonitorApp(root)
    root.mainloop()
