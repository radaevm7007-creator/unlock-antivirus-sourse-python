#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UnlockAntivirus 9.2"""
import os, sys, json, time, math, queue, hashlib, shutil, threading, ctypes
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

APP, VER = "UnlockAntivirus", "9.2"
BASE = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP)
os.makedirs(BASE, exist_ok=True)
SIG = os.path.join(BASE, "signatures.json")
CFG = os.path.join(BASE, "config.json")
QUAR = os.path.join(BASE, "quarantine")
os.makedirs(QUAR, exist_ok=True)

BG, BG1, BG2, BG3 = "#070a0e", "#0b0f14", "#0f1620", "#131b26"
BR, BR2 = "#1c2634", "#2a3a4d"
TX, DIM, MUT = "#e7edf3", "#93a1af", "#6b7a89"
AC, AC2, ACS = "#22d3a5", "#14b8a6", "#10332b"
BL, RD, YL, GR = "#38bdf8", "#ff5f57", "#febc2e", "#28c840"
FN, FM = "Segoe UI", "Consolas"

def F(s, w="normal", m=False):
    return (FM if m else FN, s, w)

WIN = sys.platform == "win32"

DEFAULT = {
    "sources": [
        "https://bazaar.abuse.ch/export/txt/sha256/recent/",
        "https://threatfox.abuse.ch/export/csv/sha256/recent/",
        "https://urlhaus.abuse.ch/downloads/text/",
    ],
    "extensions_scan": [], "skip_system_dirs": False, "heuristics": True,
    "max_file_size_mb": 500, "scan_threads": 4, "auto_update_hours": 24,
    "last_update": None, "autostart": False, "close_to_tray": True,
    "start_minimized": False,
    "game_kill_list": ["OneDrive.exe", "Teams.exe", "Discord.exe", "chrome.exe",
                       "firefox.exe", "msedge.exe", "Steam.exe", "Spotify.exe"],
    "game_boost_power": True, "game_boost_priority": True,
}

def lj(p, d):
    if not os.path.exists(p): return d
    try: return json.load(open(p, "r", encoding="utf-8"))
    except Exception: return d

def sj(p, d):
    try:
        json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        return True
    except Exception: return False

def sha256_file(p):
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
        return h.hexdigest()
    except Exception: return None

def hs(n):
    for u in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024: return f"{n:.0f} {u}"
        n /= 1024
    return f"{n:.1f} ПБ"

def hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def rgb_to_hex(r,g,b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def lerp_color(c1, c2, t):
    r1,g1,b1 = hex_to_rgb(c1); r2,g2,b2 = hex_to_rgb(c2)
    return rgb_to_hex(r1+(r2-r1)*t, g1+(g2-g1)*t, b1+(b2-b1)*t)

def rr(cv, x1, y1, x2, y2, r=10, **k):
    pts = [x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,
           x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
    return cv.create_polygon(pts, smooth=True, **k)

def dpi():
    if WIN:
        try: ctypes.windll.shcore.SetProcessDpiAwareness(2); return
        except Exception: pass
        try: ctypes.windll.user32.SetProcessDPIAware()
        except Exception: pass

def round_win(root):
    if not WIN: return
    try:
        root.update_idletasks()
        h = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        ctypes.windll.dwmapi.DwmSetWindowAttribute(h, 33, ctypes.byref(ctypes.c_int(2)), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(h, 20, ctypes.byref(ctypes.c_int(1)), 4)
    except Exception: pass

if WIN:
    from ctypes import wintypes
    PROC_TERM, PROC_QUERY, PROC_SET, HIGH_PRI = 0x0001, 0x1000, 0x0200, 0x0080
    NORMAL_PRI = 0x0020

    class PE(ctypes.Structure):
        _fields_ = [("s", wintypes.DWORD), ("c", wintypes.DWORD),
                    ("pid", wintypes.DWORD), ("h", ctypes.c_void_p),
                    ("m", wintypes.DWORD), ("t", wintypes.DWORD),
                    ("pp", wintypes.DWORD), ("pc", ctypes.c_long),
                    ("f", wintypes.DWORD), ("e", wintypes.WCHAR * 260)]

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("pf", wintypes.DWORD),
                    ("pk", ctypes.c_size_t), ("wk", ctypes.c_size_t),
                    ("qp", ctypes.c_size_t), ("qpp", ctypes.c_size_t),
                    ("qnp", ctypes.c_size_t), ("qnp2", ctypes.c_size_t),
                    ("pg", ctypes.c_size_t), ("pgp", ctypes.c_size_t)]

    class MS(ctypes.Structure):
        _fields_ = [("dl", wintypes.DWORD), ("ld", wintypes.DWORD),
                    ("tt", ctypes.c_ulonglong), ("fr", ctypes.c_ulonglong),
                    ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                    ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                    ("aex", ctypes.c_ulonglong)]

    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.OpenProcess.restype = wintypes.HANDLE

PROT = {"system", "system idle process", "registry", "memory compression",
        "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
        "lsass.exe", "dwm.exe", "fontdrvhost.exe", "explorer.exe", "sihost.exe",
        "ctfmon.exe", "taskhostw.exe", "conhost.exe", "msmpeng.exe",
        "audiodg.exe", "spoolsv.exe", "unlockantivirus.exe"}

def mem_info():
    if not WIN: return None
    try:
        m = MS(); m.dl = ctypes.sizeof(MS)
        if not k32.GlobalMemoryStatusEx(ctypes.byref(m)): return None
        return {"total": m.tt, "free": m.fr, "used": m.tt-m.fr, "pct": m.ld}
    except Exception: return None

def proc_mem(pid):
    if not WIN: return 0
    h = k32.OpenProcess(PROC_QUERY, False, pid)
    if not h: return 0
    try:
        pm = PMC(); pm.cb = ctypes.sizeof(PMC)
        if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pm), pm.cb):
            return pm.wk
        return 0
    finally: k32.CloseHandle(h)

def list_procs():
    if not WIN: return []
    out = []
    try:
        h = k32.CreateToolhelp32Snapshot(0x02, 0)
        if h == -1 or not h: return out
        try:
            e = PE(); e.s = ctypes.sizeof(PE)
            if not k32.Process32FirstW(h, ctypes.byref(e)): return out
            while True:
                if e.pid and e.e:
                    out.append({"pid": e.pid, "name": e.e, "mem": proc_mem(e.pid)})
                if not k32.Process32NextW(h, ctypes.byref(e)): break
        finally: k32.CloseHandle(h)
    except Exception: pass
    out.sort(key=lambda x: x["mem"], reverse=True)
    return out

def kill_proc(pid):
    if not WIN: return False
    h = k32.OpenProcess(PROC_TERM, False, pid)
    if not h: return False
    try: return bool(k32.TerminateProcess(h, 1))
    finally: k32.CloseHandle(h)

def set_priority(pid, high=True):
    if not WIN: return False
    h = k32.OpenProcess(PROC_SET, False, pid)
    if not h: return False
    try: return bool(k32.SetPriorityClass(h, HIGH_PRI if high else NORMAL_PRI))
    finally: k32.CloseHandle(h)

def list_drives():
    if not WIN:
        try:
            t,u,f = shutil.disk_usage("/")
            return [{"m":"/","t":t,"u":u,"f":f,"p":u/t*100 if t else 0}]
        except Exception: return []
    out = []
    try:
        mask = k32.GetLogicalDrives()
        for i in range(26):
            if mask & (1 << i):
                d = chr(65+i) + ":\\"
                try:
                    if k32.GetDriveTypeW(d) == 3:
                        t,u,f = shutil.disk_usage(d)
                        out.append({"m":d,"t":t,"u":u,"f":f,"p":u/t*100 if t else 0})
                except Exception: pass
    except Exception: pass
    return out

def dir_size(path):
    t = 0
    if not path or not os.path.isdir(path): return 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try: t += os.path.getsize(os.path.join(root, f))
            except Exception: pass
    return t

def clean_dir(path):
    if not path or not os.path.isdir(path): return 0, 0
    freed = 0
    for it in os.listdir(path):
        fp = os.path.join(path, it)
        try:
            if os.path.isdir(fp):
                sz = dir_size(fp); shutil.rmtree(fp, ignore_errors=True); freed += sz
            else:
                freed += os.path.getsize(fp); os.remove(fp)
        except Exception: pass
    return freed, 0

def clean_targets():
    w = os.environ.get("SystemRoot", "C:\\Windows")
    la = os.environ.get("LOCALAPPDATA", ""); ro = os.environ.get("APPDATA", "")
    te = os.environ.get("TEMP", "")
    return {
        "temp":   {"p": te, "n": "Временные файлы"},
        "win":    {"p": os.path.join(w, "Temp"), "n": "Системный temp"},
        "pf":     {"p": os.path.join(w, "Prefetch"), "n": "Prefetch"},
        "wu":     {"p": os.path.join(w, "SoftwareDistribution", "Download"), "n": "Windows Update"},
        "chrome": {"p": os.path.join(la, "Google", "Chrome", "User Data", "Default", "Cache"), "n": "Chrome кэш"},
        "edge":   {"p": os.path.join(la, "Microsoft", "Edge", "User Data", "Default", "Cache"), "n": "Edge кэш"},
        "opera":  {"p": os.path.join(ro, "Opera Software", "Opera Stable", "Cache"), "n": "Opera кэш"},
        "d3d":    {"p": os.path.join(la, "D3DSCache"), "n": "DirectX шейдеры"},
    }

def boost_power_plan():
    if not WIN: return False
    try:
        r = subprocess.run(["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                           capture_output=True, timeout=5, creationflags=0x08000000)
        return r.returncode == 0
    except Exception: return False

def reset_power_plan():
    if not WIN: return False
    try:
        r = subprocess.run(["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"],
                           capture_output=True, timeout=5, creationflags=0x08000000)
        return r.returncode == 0
    except Exception: return False

class DB:
    def __init__(self):
        d = lj(SIG, {"sha256": [], "md5": [], "updated": None})
        self.sha = set(x.lower() for x in d.get("sha256", []))
        self.md5 = set(x.lower() for x in d.get("md5", []))
        self.upd = d.get("updated")
    def save(self):
        sj(SIG, {"sha256": sorted(self.sha), "md5": sorted(self.md5), "updated": self.upd})
    def add(self, hs_, k="sha256"):
        t = self.sha if k == "sha256" else self.md5
        ln = 64 if k == "sha256" else 32
        n = len(t)
        for h in hs_:
            h = h.strip().lower()
            if len(h) == ln and all(c in "0123456789abcdef" for c in h): t.add(h)
        return len(t) - n
    def match(self, s, m=None):
        if s and s.lower() in self.sha: return "sha256"
        if m and m.lower() in self.md5: return "md5"
        return None

def parse_hashes(text):
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"): continue
        for sep in (",", ";", "\t", " "):
            if sep in ln:
                for tok in ln.split(sep):
                    t = tok.strip().strip('"\'').lower()
                    if len(t) in (32, 64) and all(c in "0123456789abcdef" for c in t):
                        out.append(t)
                break
    return out

def fetch(url):
    r = Request(url, headers={"User-Agent": f"{APP}/{VER}"})
    with urlopen(r, timeout=60) as x: raw = x.read()
    return raw.decode("utf-8", "ignore")

def update_sig(cfg, lg=print):
    db = DB()
    srcs = cfg.get("sources", [])
    for i, u in enumerate(srcs):
        try:
            lg(f"[{i+1}/{len(srcs)}] {u.split('/')[2]}")
            hashes = parse_hashes(fetch(u))
            s = [h for h in hashes if len(h) == 64]
            m = [h for h in hashes if len(h) == 32]
            db.add(s, "sha256"); db.add(m, "md5")
            lg(f"  +{len(s)} SHA256, +{len(m)} MD5")
        except Exception as e:
            lg(f"  ! {e}")
    db.upd = datetime.now(timezone.utc).isoformat()
    db.save()
    cfg["last_update"] = db.upd
    sj(CFG, cfg)
    lg(f"✓ Всего: {len(db.sha):,} SHA256, {len(db.md5):,} MD5")
    return db

def quarantine_file(path, reason="malware"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(QUAR, f"{ts}_{os.path.basename(path)}.q")
    try:
        sz = os.path.getsize(path)
        shutil.move(path, dst)
        sj(dst + ".json", {"orig": os.path.abspath(path), "r": reason, "s": sz, "t": ts})
        return dst
    except Exception: return None

HEUR = [(b"powershell.exe -enc", "PowerShell base64"),
        (b"powershell -enc", "PowerShell base64"),
        (b"cmd.exe /c powershell", "cmd→powershell"),
        (b"WScript.Shell", "WScript.Shell"),
        (b"eval(base64_decode", "eval base64"),
        (b"vssadmin delete shadows", "Удаление теней")]
DOUBLE_EXT = [".pdf.exe", ".doc.exe", ".jpg.exe", ".png.exe", ".txt.exe",
              ".mp3.exe", ".mp4.exe", ".pdf.scr", ".jpg.scr"]

def heuristic(path):
    f = []
    low = path.lower()
    for e in DOUBLE_EXT:
        if low.endswith(e): f.append(f"Двойное {e}")
    try:
        if os.path.getsize(path) > 5 << 20: return f
        with open(path, "rb") as fh: data = fh.read(512 * 1024)
    except Exception: return f
    for pat, desc in HEUR:
        if pat in data: f.append(desc)
    return f

class Scan:
    def __init__(self, db, cfg, on_file=None, on_threat=None, on_done=None, on_prog=None):
        self.db, self.cfg = db, cfg
        self.of = on_file or (lambda *a: None)
        self.ot = on_threat or (lambda *a: None)
        self.od = on_done or (lambda *a: None)
        self.op = on_prog or (lambda *a: None)
        self.stop = threading.Event()
        self.stats = {"sc": 0, "th": 0, "er": 0}
        self.total = 0; self.t0 = time.time()
    def halt(self): self.stop.set()
    def collect(self, paths):
        out = []
        exts = set(e.lower() for e in self.cfg.get("extensions_scan", []))
        max_sz = self.cfg.get("max_file_size_mb", 500) * 1024 * 1024
        for p in paths:
            if self.stop.is_set(): break
            if os.path.isfile(p): out.append(p); continue
            if not os.path.isdir(p): continue
            for root, dirs, files in os.walk(p, onerror=lambda e: None):
                if self.stop.is_set(): break
                for n in files:
                    if self.stop.is_set(): break
                    fp = os.path.join(root, n)
                    if exts and os.path.splitext(n)[1].lower() not in exts: continue
                    try:
                        if os.path.getsize(fp) > max_sz: continue
                    except OSError: continue
                    out.append(fp)
        return out
    def one(self, fp):
        if self.stop.is_set(): return
        self.of(fp)
        s = sha256_file(fp)
        if s is None: self.stats["er"] += 1; return
        self.stats["sc"] += 1
        m = self.db.match(s)
        if m:
            self.stats["th"] += 1
            self.ot(fp, m, s); quarantine_file(fp, f"hash/{m}")
        elif self.cfg.get("heuristics", True):
            f = heuristic(fp)
            if f:
                self.stats["th"] += 1
                self.ot(fp, f"эвристика: {', '.join(f[:2])}", s)
                quarantine_file(fp, "heuristic")
        el = max(0.001, time.time() - self.t0)
        self.op({"done": self.stats["sc"], "total": self.total,
                 "speed": self.stats["sc"]/el, "stats": dict(self.stats)})
    def run(self, paths):
        self.t0 = time.time()
        files = self.collect(paths)
        self.total = len(files)
        self.op({"done": 0, "total": self.total, "speed": 0, "stats": dict(self.stats)})
        th = max(1, int(self.cfg.get("scan_threads", 4)))
        if th == 1 or len(files) < 10:
            for fp in files:
                if self.stop.is_set(): break
                self.one(fp)
        else:
            with ThreadPoolExecutor(max_workers=th) as ex:
                futs = [ex.submit(self.one, fp) for fp in files]
                for _ in as_completed(futs):
                    if self.stop.is_set(): break
        self.od(dict(self.stats), self.total)

class Auto:
    RK = r"Software\Microsoft\Windows\CurrentVersion\Run"
    @staticmethod
    def _pythonw():
        if not WIN: return None
        if getattr(sys, "frozen", False): return sys.executable
        b = os.path.dirname(sys.executable)
        for c in (os.path.join(b, "pythonw.exe"), os.path.join(b, "pythonw"),
                  sys.executable.replace("python.exe", "pythonw.exe")):
            if c and os.path.isfile(c): return c
        return None
    @staticmethod
    def _cmd():
        if getattr(sys, "frozen", False): return f'"{sys.executable}" --tray'
        p = Auto._pythonw()
        if p: return f'"{p}" "{os.path.abspath(sys.argv[0])}" --tray'
        return ""
    @staticmethod
    def enabled():
        if not WIN: return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Auto.RK, 0, winreg.KEY_READ) as k:
                winreg.QueryValueEx(k, APP); return True
        except Exception: return False
    @staticmethod
    def enable():
        if not WIN: return False, "Только Windows"
        try:
            import winreg
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, Auto.RK, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, Auto._cmd())
            return True, "Включено"
        except Exception as e: return False, str(e)
    @staticmethod
    def disable():
        if not WIN: return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Auto.RK, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, APP)
            return True
        except Exception: return False

if WIN:
    from ctypes import wintypes as wt
    u32, sh32, k32t = ctypes.windll.user32, ctypes.windll.shell32, ctypes.windll.kernel32
    LRES = ctypes.c_ssize_t
    u32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    u32.DefWindowProcW.restype = LRES
    u32.CreateWindowExW.restype = wt.HWND
    u32.RegisterClassW.restype = wt.ATOM
    u32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
    u32.LoadIconW.argtypes = [wt.HINSTANCE, wt.LPCWSTR]
    sh32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.c_void_p]
    class NID(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("h", wt.HWND), ("id", wt.UINT),
                    ("fl", wt.UINT), ("msg", wt.UINT), ("ic", wt.HICON),
                    ("tip", wt.WCHAR * 128)]
    WNDP = ctypes.WINFUNCTYPE(LRES, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
    class WC(ctypes.Structure):
        _fields_ = [("st", wt.UINT), ("lp", WNDP), ("ce", ctypes.c_int),
                    ("we", ctypes.c_int), ("hi", wt.HINSTANCE),
                    ("ic", wt.HICON), ("cu", wt.HANDLE), ("br", wt.HBRUSH),
                    ("mn", wt.LPCWSTR), ("cn", wt.LPCWSTR)]

class Tray:
    def __init__(self, tip, on_l, on_r):
        self.tip = tip[:127]; self.on_l, self.on_r = on_l, on_r
        self.hw = None; self._nid = None; self._p = None
        self._rdy = threading.Event(); self._stp = threading.Event()
    def start(self):
        if not WIN: return
        threading.Thread(target=self._run, daemon=True).start()
        self._rdy.wait(timeout=3)
    def stop(self):
        if not WIN: return
        self._stp.set()
        if self._nid is not None:
            try: sh32.Shell_NotifyIconW(2, ctypes.byref(self._nid))
            except Exception: pass
            self._nid = None
        if self.hw:
            try: u32.PostMessageW(self.hw, 2, 0, 0)
            except Exception: pass
            self.hw = None
    def tip_set(self, t):
        if not WIN or self._nid is None: return
        self.tip = t[:127]; self._nid.tip = self.tip
        try: sh32.Shell_NotifyIconW(1, ctypes.byref(self._nid))
        except Exception: pass
    def _run(self):
        hi = k32t.GetModuleHandleW(None); cn = f"AV_{id(self)}"
        self._p = WNDP(self._proc)
        wc = WC(); wc.lp = self._p; wc.hi = hi; wc.cn = cn
        u32.RegisterClassW(ctypes.byref(wc))
        self.hw = u32.CreateWindowExW(0, cn, cn, 0, 0, 0, 0, 0, None, None, hi, None)
        if not self.hw: self._rdy.set(); return
        ic = u32.LoadIconW(None, wt.LPCWSTR(32512))
        nid = NID(); nid.cb = ctypes.sizeof(NID); nid.h = self.hw; nid.id = 1
        nid.fl = 1|2|4; nid.msg = 0x0400+20; nid.ic = ic; nid.tip = self.tip
        self._nid = nid
        sh32.Shell_NotifyIconW(0, ctypes.byref(nid))
        self._rdy.set()
        m = wt.MSG()
        while not self._stp.is_set():
            r = u32.GetMessageW(ctypes.byref(m), None, 0, 0)
            if r <= 0: break
            u32.TranslateMessage(ctypes.byref(m))
            u32.DispatchMessageW(ctypes.byref(m))
    def _proc(self, h, m, w, l):
        if m == 0x0400+20:
            if l in (0x0202, 0x0203): self.on_l()
            elif l == 0x0205: self.on_r()
            return 0
        if m == 2: u32.PostQuitMessage(0); return 0
        return u32.DefWindowProcW(wt.HWND(h), wt.UINT(m), wt.WPARAM(w), wt.LPARAM(l))

# ==================== SPLASH (без fade) ====================
class Splash(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} {VER}")
        w, h = 520, 380
        self.configure(bg=BG)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        round_win(self)

        self._angle = 0
        self._progress = 0.0
        self._status = "Инициализация..."
        self._anim = None
        self._closing = False

        self._build()
        self.after(30, self._anim_loop)

    def _build(self):
        self.bg_canvas = GlowCanvas(self)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        main = tk.Frame(self, bg=BG2, highlightthickness=1, highlightbackground=BR)
        main.place(x=1, y=1, width=518, height=378)
        self.logo_cv = tk.Canvas(main, width=90, height=90, bg=BG2,
                                  highlightthickness=0)
        self.logo_cv.pack(pady=(36, 0))
        title = tk.Frame(main, bg=BG2); title.pack(pady=(10, 0))
        tk.Label(title, text="Unlock", bg=BG2, fg=TX,
                 font=F(24, "bold")).pack(side="left")
        tk.Label(title, text="Antivirus", bg=BG2, fg=AC,
                 font=F(24, "bold")).pack(side="left")
        tk.Label(main, text=f"Версия {VER}  ·  Open Source  ·  MIT",
                 bg=BG2, fg=MUT, font=F(10)).pack(pady=(6, 20))
        self.status_lbl = tk.Label(main, text="Запуск...", bg=BG2, fg=DIM,
                                     font=F(11))
        self.status_lbl.pack()
        self.progress_cv = tk.Canvas(main, width=380, height=6, bg=BG2,
                                       highlightthickness=0)
        self.progress_cv.pack(pady=(14, 8))
        self.pct_lbl = tk.Label(main, text="0%", bg=BG2, fg=AC,
                                 font=F(10, "bold"))
        self.pct_lbl.pack()
        tk.Label(main, text="Спасибо, что пользуетесь!",
                 bg=BG2, fg=MUT, font=F(9)).pack(side="bottom", pady=14)

    def _anim_loop(self):
        if self._closing: return
        self._angle = (self._angle + 8) % 360
        self._draw_logo()
        self._draw_progress()
        self._anim = self.after(30, self._anim_loop)

    def _draw_logo(self):
        c = self.logo_cv
        c.delete("all")
        cx = cy = 45
        r = 26
        for off, col in ((0, AC), (180, BL)):
            c.create_arc(cx-38, cy-38, cx+38, cy+38,
                         start=self._angle+off, extent=70,
                         outline=col, width=3, style="arc")
        pulse = (math.sin(time.time()*4)+1)/2
        for i in range(5, 0, -1):
            t = i/5
            r_glow = (r + 8) * (1 + pulse * 0.1) * t
            col = lerp_color(BG2, AC, 0.1 * (1-t) + 0.05)
            c.create_oval(cx-r_glow, cy-r_glow, cx+r_glow, cy+r_glow,
                          fill=col, outline="")
        cy_s = cy - 0.025*r
        c.create_arc(cx-r, cy_s-r, cx+r, cy_s+r*0.55, start=0, extent=180,
                     fill=AC, outline="", style="chord")
        pts = [cx-r, cy_s+r*0.05, cx-r*0.5, cy_s+r*0.55,
               cx, cy_s+r*1.05, cx+r*0.5, cy_s+r*0.55, cx+r, cy_s+r*0.05]
        c.create_polygon(pts, fill=AC, outline="", smooth=True)
        c.create_line(cx-r*0.35, cy_s+r*0.05, cx-r*0.05, cy_s+r*0.32,
                      cx+r*0.4, cy_s-r*0.25, fill="#04120e",
                      width=4, capstyle="round", joinstyle="round")

    def _draw_progress(self):
        c = self.progress_cv
        c.delete("all")
        w, h = 380, 6
        rr(c, 0, 0, w, h, r=3, fill=BG1, outline=BR)
        if self._progress > 0:
            fw = max(6, int(w * self._progress))
            steps = 40
            for i in range(steps):
                t1 = i/steps; t2 = (i+1)/steps
                x1 = t1 * fw; x2 = t2 * fw
                col = lerp_color(AC, BL, t1)
                c.create_rectangle(x1, 1, x2, h-1, fill=col, outline="")

    def set_status(self, text, progress=None):
        self._status = text
        self.status_lbl.configure(text=text)
        if progress is not None:
            self._progress = max(0, min(1, progress))
            self.pct_lbl.configure(text=f"{int(self._progress*100)}%")
        self.update_idletasks()

    def finish(self, callback):
        """Без fade — мгновенно закрыть splash и запустить главное окно."""
        self._closing = True
        if self._anim:
            try: self.after_cancel(self._anim)
            except Exception: pass
            self._anim = None
        try: self.destroy()
        except Exception: pass
        callback()

# ==================== ВИДЖЕТЫ ====================
class GlowCanvas(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG, **kw)
        self._last = (0, 0)
        self.bind("<Configure>", self._redraw)
    def _redraw(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10 or (w, h) == self._last: return
        self._last = (w, h); self.delete("all")
        glows = [(w*0.15, h*0.1, 260, AC, 0.14), (w*0.85, h*0.4, 260, BL, 0.09)]
        for cx, cy, r, col, alpha in glows:
            for i in range(12, 0, -1):
                t = i/12
                c = lerp_color(BG, col, (1-t)*alpha + 0.02)
                self.create_oval(cx-r*t, cy-r*t, cx+r*t, cy+r*t, fill=c, outline="")
        grid = 40; gc = lerp_color(BG, "#ffffff", 0.025)
        for x in range(0, w+grid, grid): self.create_line(x, 0, x, h, fill=gc)
        for y in range(0, h+grid, grid): self.create_line(0, y, w, y, fill=gc)

class Card(tk.Frame):
    def __init__(self, m, r=16, bgc=BG2, bc=BR, px=18, py=16, **kw):
        try: pb = m.cget("bg")
        except Exception: pb = BG
        super().__init__(m, bg=pb, **kw)
        self._r, self._bg, self._bc = r, bgc, bc
        self._cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=pb)
        self._cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=bgc)
        self.body.pack(fill="both", expand=True, padx=px, pady=py)
        self._hovered = False; self._hover_bc = bc
        self.bind("<Configure>", self._rd)
        self.bind("<Enter>", lambda e: (setattr(self, "_hovered", True), self._rd()))
        self.bind("<Leave>", lambda e: (setattr(self, "_hovered", False), self._rd()))
    def set_hover_color(self, bc): self._hover_bc = bc
    def _rd(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 8: return
        c = self._cv; c.delete("all"); r = self._r
        bc = self._hover_bc if self._hovered else self._bc
        pts = [r+1,1,w-r-1,1,w-1,1,w-1,r+1,w-1,h-r-1,w-1,h-1,
               w-r-1,h-1,r+1,h-1,1,h-1,1,h-r-1,1,r+1,1,1]
        c.create_polygon(pts, smooth=True, fill=self._bg, outline=bc, width=1)

class Btn(tk.Canvas):
    def __init__(self, m, text, cmd=None, w=200, h=48, bg=AC, fg="#04120e",
                 hov=AC2, bd=None, fnt=None, r=12, pbg=None):
        try: pb = pbg or m.cget("bg")
        except Exception: pb = BG
        super().__init__(m, width=w, height=h, bg=pb, highlightthickness=0, cursor="hand2")
        self.w, self.h = w, h
        self.bg_c, self.fg_c, self.hov = bg, fg, hov
        self.bd, self.r, self.cmd, self.t = bd, r, cmd, text
        self.fnt = fnt or F(13, "bold")
        self.en = True; self._hov = False
        self._draw()
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._seth(True))
        self.bind("<Leave>", lambda e: self._seth(False))
    def _seth(self, v): self._hov = v; self._draw()
    def _draw(self):
        self.delete("all")
        c = self.hov if self._hov else self.bg_c
        if not self.en: c = BR
        rr(self, 1, 1, self.w-1, self.h-1, self.r, fill=c, outline=self.bd or c)
        self.create_text(self.w/2, self.h/2-1, text=self.t,
                         fill=self.fg_c if self.en else MUT, font=self.fnt)
    def _click(self, _):
        if self.en and self.cmd: self.cmd()
    def on(self, v): self.en = v; self._draw()
    def txt(self, t): self.t = t; self._draw()

class NavBtn(tk.Frame):
    def __init__(self, m, ic, txt, cmd):
        super().__init__(m, bg=BG1, height=46, cursor="hand2")
        self.pack_propagate(False); self.cmd, self._act = cmd, False
        self.ind = tk.Frame(self, bg=BG1, width=3); self.ind.pack(side="left", fill="y")
        self.iw = tk.Frame(self, bg=BG1, width=38, height=46)
        self.iw.pack(side="left"); self.iw.pack_propagate(False)
        self.il = tk.Label(self.iw, text=ic, bg=BG1, fg=DIM, font=F(15))
        self.il.place(relx=0.5, rely=0.5, anchor="center")
        self.tl = tk.Label(self, text=txt, bg=BG1, fg=DIM, font=F(12), anchor="w")
        self.tl.pack(side="left", fill="x", expand=True, padx=(4, 12))
        for w in (self, self.iw, self.il, self.tl, self.ind):
            w.bind("<Button-1>", lambda e: self.cmd())
            w.bind("<Enter>", self._on); w.bind("<Leave>", self._off)
    def _on(self, _):
        if not self._act:
            for w in (self, self.iw, self.il, self.tl, self.ind):
                try: w.configure(bg=BG2)
                except Exception: pass
    def _off(self, _):
        if not self._act:
            for w in (self, self.iw, self.il, self.tl, self.ind):
                try: w.configure(bg=BG1)
                except Exception: pass
    def act(self, v):
        self._act = v
        ws = (self, self.iw, self.il, self.tl, self.ind)
        if v:
            for w in ws: w.configure(bg=ACS)
            self.ind.configure(bg=AC); self.il.configure(fg=AC); self.tl.configure(fg=TX)
        else:
            for w in ws: w.configure(bg=BG1)
            self.ind.configure(bg=BG1); self.il.configure(fg=DIM); self.tl.configure(fg=MUT)

class ShieldCanvas(tk.Canvas):
    def __init__(self, master, size=200):
        super().__init__(master, width=size, height=size, bg=BG2, highlightthickness=0)
        self.size = size; self.state = "idle"; self.angle = 0; self.pulse = 0
        self._anim = None; self._draw()
    def _draw(self):
        self.delete("all")
        s = self.size; cx = cy = s/2; r = s*0.32
        base_r = s*0.44
        for i in range(6):
            t = i/6
            rr_ = base_r*(1-t*0.15) + self.pulse*base_r*0.06*(1-t)
            col = lerp_color(BG2, AC, 0.15*(1-t))
            self.create_oval(cx-rr_, cy-rr_, cx+rr_, cy+rr_, fill=col, outline="")
        if self.state == "scanning":
            for off, col in ((0, AC), (120, BL), (240, AC)):
                self.create_arc(cx-s*0.4, cy-s*0.4, cx+s*0.4, cy+s*0.4,
                                start=self.angle+off, extent=70, outline=col,
                                width=3, style="arc")
            for a in range(0, 360, 20):
                rad = math.radians(a)
                self.create_line(cx+s*0.46*math.cos(rad), cy+s*0.46*math.sin(rad),
                                 cx+s*0.48*math.cos(rad), cy+s*0.48*math.sin(rad),
                                 fill=MUT, width=1)
        else:
            for a in range(0, 360, 30):
                rad = math.radians(a)
                self.create_line(cx+s*0.46*math.cos(rad), cy+s*0.46*math.sin(rad),
                                 cx+s*0.48*math.cos(rad), cy+s*0.48*math.sin(rad),
                                 fill=BR, width=1)
        color = {"idle": MUT, "scanning": AC, "safe": AC, "threat": RD}[self.state]
        cy_s = cy - 0.025*r
        self.create_arc(cx-r, cy_s-r, cx+r, cy_s+r*0.55, start=0, extent=180,
                        fill=color, outline="", style="chord")
        pts = [cx-r, cy_s+r*0.05, cx-r*0.5, cy_s+r*0.55,
               cx, cy_s+r*1.05, cx+r*0.5, cy_s+r*0.55, cx+r, cy_s+r*0.05]
        self.create_polygon(pts, fill=color, outline="", smooth=True)
        self.create_arc(cx-r*0.75, cy_s-r*0.7, cx+r*0.75, cy_s+r*0.3, start=0,
                        extent=180, fill=lerp_color(color, "#ffffff", 0.2),
                        outline="", style="chord")
        if self.state == "safe":
            self.create_line(cx-r*0.35, cy_s+r*0.05, cx-r*0.05, cy_s+r*0.32,
                             cx+r*0.4, cy_s-r*0.25, fill="#04120e", width=5,
                             capstyle="round", joinstyle="round")
        elif self.state == "threat":
            self.create_line(cx-r*0.25, cy_s-r*0.25, cx+r*0.25, cy_s+r*0.25,
                             fill="#04120e", width=5, capstyle="round")
            self.create_line(cx+r*0.25, cy_s-r*0.25, cx-r*0.25, cy_s+r*0.25,
                             fill="#04120e", width=5, capstyle="round")
        elif self.state == "scanning":
            for i in range(3):
                a = self.angle + i*120
                x = cx + r*0.35*math.cos(math.radians(a))
                y = cy_s + r*0.35*math.sin(math.radians(a))
                self.create_oval(x-4, y-4, x+4, y+4, fill="#04120e", outline="")
    def set_state(self, st): self.state = st; self._draw()
    def start_anim(self):
        self.stop_anim()
        def loop():
            self.angle = (self.angle + 15) % 360
            self.pulse = (math.sin(time.time()*3)+1)/2
            self._draw()
            self._anim = self.after(40, loop)
        loop()
    def stop_anim(self):
        if self._anim: self.after_cancel(self._anim); self._anim = None

class AnimatedProgress(tk.Canvas):
    def __init__(self, master, height=10):
        super().__init__(master, height=height, highlightthickness=0, bg=BG2)
        self._val = 0.0; self._anim_offset = 0; self._anim = None
        self._running = False
        self.bind("<Configure>", lambda e: self._draw())
    def set(self, v): self._val = max(0, min(1, v)); self._draw()
    def start_anim(self):
        if self._running: return
        self._running = True
        def loop():
            self._anim_offset = (self._anim_offset+4)%100
            self._draw()
            self._anim = self.after(40, loop)
        loop()
    def stop_anim(self):
        self._running = False
        if self._anim: self.after_cancel(self._anim); self._anim = None
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4: return
        r = h/2
        rr(self, 0, 0, w, h, r=r, fill=BG1, outline=BR)
        if self._val > 0:
            fw = max(h, int(w*self._val))
            steps = 20
            for i in range(steps):
                t = i/steps
                col = lerp_color(AC, BL, t)
                self.create_rectangle(t*fw, 1, (t+1/steps)*fw, h-1, fill=col, outline="")

class Toast(tk.Toplevel):
    def __init__(self, parent, text, kind="info"):
        super().__init__(parent)
        self.overrideredirect(True); self.attributes("-topmost", True)
        self.configure(bg=BG2)
        icons = {"info": "i", "ok": "✓", "warn": "!", "error": "✕"}
        colors = {"info": BL, "ok": AC, "warn": YL, "error": RD}
        col = colors[kind]
        wrap = tk.Frame(self, bg=BG2, highlightthickness=1, highlightbackground=col)
        wrap.pack(fill="both", expand=True)
        tk.Label(wrap, text=icons[kind], bg=BG2, fg=col,
                 font=F(14, "bold")).pack(side="left", padx=(14, 10), pady=12)
        tk.Label(wrap, text=text, bg=BG2, fg=TX,
                 font=F(11)).pack(side="left", padx=(0, 18), pady=12)
        self.update_idletasks()
        w, h = wrap.winfo_reqwidth(), wrap.winfo_reqheight()
        try:
            x = parent.winfo_rootx() + parent.winfo_width() - w - 30
            y = parent.winfo_rooty() + parent.winfo_height() - h - 30
        except Exception: x = y = 100
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.after(2800, self.destroy)

class Page(tk.Frame):
    def __init__(self, m, app):
        super().__init__(m, bg=BG); self.app = app
    def refresh(self): pass

class DashboardPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Обзор системы", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Состояние защиты", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        hero = Card(self, r=18, py=22); hero.pack(fill="x", padx=32, pady=(16, 0))
        inner = hero.body
        self.shield = ShieldCanvas(inner, size=180)
        self.shield.pack(side="left", padx=(4, 24))
        self.shield.start_anim(); self.shield.set_state("safe")
        info = tk.Frame(inner, bg=BG2); info.pack(side="left", fill="both", expand=True)
        tk.Label(info, text="Система защищена", bg=BG2, fg=TX,
                 font=F(20, "bold"), anchor="w").pack(anchor="w")
        tk.Label(info, text=f"Сигнатуры: {len(app.db.sha):,}", bg=BG2, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(4, 18))
        btns = tk.Frame(info, bg=BG2); btns.pack(anchor="w")
        Btn(btns, "⚡  Быстрая проверка", w=210, h=46, pbg=BG2,
            cmd=self._quick).pack(side="left", padx=(0, 10))
        Btn(btns, "🎮  Игровой буст", w=210, h=46, bg=BG3, fg=DIM, hov=BR2,
            bd=BR, pbg=BG2, cmd=lambda: app.go("games")).pack(side="left")
        stats = tk.Frame(self, bg=BG); stats.pack(fill="x", padx=32, pady=(16, 0))
        for i in range(4): stats.grid_columnconfigure(i, weight=1, uniform="s")
        cards_data = [("Σ", f"{len(app.db.sha):,}", "SHA256", AC),
                      ("μ", f"{len(app.db.md5):,}", "MD5", BL),
                      ("▣", str(self._qc()), "Карантин", YL),
                      ("⛨", "Вкл" if Auto.enabled() else "Выкл", "Автозагрузка", GR)]
        self.stat_vals = {}
        for i, (ic, val, label, col) in enumerate(cards_data):
            c = Card(stats, r=14, py=16, px=16)
            c.grid(row=0, column=i, sticky="nsew",
                   padx=(0 if i==0 else 6, 0 if i==3 else 6))
            c.set_hover_color(col)
            tk.Label(c.body, text=ic, bg=BG2, fg=col, font=F(22)).pack(anchor="w")
            vl = tk.Label(c.body, text=val, bg=BG2, fg=TX, font=F(20, "bold"), anchor="w")
            vl.pack(anchor="w", pady=(8, 2))
            tk.Label(c.body, text=label, bg=BG2, fg=MUT, font=F(10), anchor="w").pack(anchor="w")
            self.stat_vals[label] = vl
        lg = Card(self, r=16, py=16); lg.pack(fill="both", expand=True, padx=32, pady=(16, 28))
        tk.Label(lg.body, text="События", bg=BG2, fg=TX, font=F(13, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 8))
        self.ev = tk.Text(lg.body, bg=BG1, fg=DIM, bd=0, font=F(10, m=True),
                          wrap="word", insertbackground=TX, highlightthickness=0,
                          padx=8, pady=8)
        self.ev.pack(fill="both", expand=True)
        self.ev.configure(state="disabled")
        self.log(f"[i] {APP} {VER} запущен")
    def _qc(self):
        try: return len([f for f in os.listdir(QUAR) if f.endswith(".q")])
        except Exception: return 0
    def log(self, t):
        def do():
            self.ev.configure(state="normal")
            self.ev.insert("end", t+"\n"); self.ev.see("end")
            self.ev.configure(state="disabled")
        self.after(0, do)
    def refresh(self):
        self.stat_vals["SHA256"].configure(text=f"{len(self.app.db.sha):,}")
        self.stat_vals["MD5"].configure(text=f"{len(self.app.db.md5):,}")
        self.stat_vals["Карантин"].configure(text=str(self._qc()))
        self.stat_vals["Автозагрузка"].configure(text="Вкл" if Auto.enabled() else "Выкл")
    def _quick(self):
        h = os.path.expanduser("~")
        ts = [os.path.join(h, n) for n in ("Downloads","Documents","Desktop")
              if os.path.isdir(os.path.join(h, n))] or [h]
        self.app.go("scan"); self.app.pages["scan"].start(ts)

class ScanPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app); self.sc = None
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Сканирование", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Проверьте файлы и папки", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        top = Card(self, r=16, py=20); top.pack(fill="x", padx=32, pady=(16, 0))
        inner = top.body
        self.shield = ShieldCanvas(inner, size=130)
        self.shield.pack(side="left", padx=(0, 20))
        col = tk.Frame(inner, bg=BG2); col.pack(side="left", fill="both", expand=True)
        self.status = tk.Label(col, text="Готов к сканированию", bg=BG2, fg=TX,
                               font=F(15, "bold"), anchor="w")
        self.status.pack(anchor="w")
        self.cur = tk.Label(col, text="", bg=BG2, fg=MUT, font=F(10),
                             anchor="w", wraplength=620, justify="left")
        self.cur.pack(anchor="w", pady=(4, 12))
        self.progress = AnimatedProgress(col, height=10)
        self.progress.pack(fill="x")
        self.counter = tk.Label(col, text="", bg=BG2, fg=DIM, font=F(10), anchor="w")
        self.counter.pack(anchor="w", pady=(8, 0))
        btns = tk.Frame(self, bg=BG); btns.pack(fill="x", padx=32, pady=(16, 0))
        Btn(btns, "📁  Папка", w=150, h=44, cmd=self._pf).pack(side="left", padx=(0, 10))
        Btn(btns, "📄  Файл", w=150, h=44, bg=BG3, fg=DIM, hov=BR2, bd=BR,
            cmd=self._pfile).pack(side="left", padx=(0, 10))
        self.stb = Btn(btns, "⏹  Стоп", w=130, h=44, bg=BG3, fg=MUT,
                       hov=BR2, bd=BR, cmd=self._stop)
        self.stb.pack(side="left"); self.stb.on(False)
        lg = Card(self, r=16, py=16); lg.pack(fill="both", expand=True, padx=32, pady=(16, 28))
        tk.Label(lg.body, text="Журнал", bg=BG2, fg=TX, font=F(13, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 8))
        self.lg = tk.Text(lg.body, bg=BG1, fg=DIM, bd=0, font=F(10, m=True),
                          wrap="word", insertbackground=TX, highlightthickness=0,
                          padx=8, pady=8)
        self.lg.pack(fill="both", expand=True)
        self.lg.tag_config("ok", foreground=AC)
        self.lg.tag_config("err", foreground=RD)
        self.lg.tag_config("info", foreground=BL)
    def _pf(self):
        p = filedialog.askdirectory()
        if p: self.start([p])
    def _pfile(self):
        p = filedialog.askopenfilename()
        if p: self.start([p])
    def _stop(self):
        if self.sc: self.sc.halt()
    def _log(self, t, tag=None):
        def do():
            self.lg.insert("end", t+"\n", tag or ""); self.lg.see("end")
        self.after(0, do)
    def start(self, paths):
        if self.sc and not self.sc.stop.is_set(): return
        self.lg.delete("1.0", "end")
        self.progress.set(0); self.progress.start_anim()
        self.counter.configure(text="")
        self.status.configure(text="Сканирование...", fg=TX)
        self.shield.set_state("scanning"); self.stb.on(True)
        self._log(f"=== {paths} ===", "info")
        def of(fp):
            s = fp if len(fp) < 90 else "..."+fp[-87:]
            self._log(f"  → {s}")
        def ot(fp, k, h): self._log(f"  ⚠ УГРОЗА ({k}): {fp}", "err")
        def op(p):
            def do():
                if p["total"]: self.progress.set(p["done"]/p["total"])
                self.counter.configure(text=f"{p['done']}/{p['total']}   {p['speed']:.0f} ф/с")
            self.after(0, do)
        def od(s, total):
            def do():
                self.progress.set(1.0); self.progress.stop_anim()
                if s["th"]:
                    self.shield.set_state("threat")
                    self.status.configure(text=f"Готово · Угроз: {s['th']}", fg=RD)
                else:
                    self.shield.set_state("safe")
                    self.status.configure(text="Готово · Чисто", fg=AC)
                self._log(f"=== {total} файлов, {s['th']} угроз, {s['er']} ошибок ===",
                          "err" if s["th"] else "ok")
                self.stb.on(False)
                self.app.refresh_side()
                self.app.pages["dashboard"].refresh()
                Toast(self.app, f"Угроз: {s['th']}" if s["th"] else "Чисто",
                      "error" if s["th"] else "ok")
            self.after(0, do)
        self.sc = Scan(self.app.db, self.app.cfg, of, ot, od, op)
        threading.Thread(target=self.sc.run, args=(paths,), daemon=True).start()

class MemPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        self.procs = []; self.sel = set(); self.rows = {}
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Очистка памяти", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Завершайте ненужные процессы", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        mc = Card(self, r=16, py=18); mc.pack(fill="x", padx=32, pady=(16, 0))
        tk.Label(mc.body, text="▦", bg=BG2, fg=AC, font=F(32, "bold")
                 ).pack(side="left", padx=(0, 20))
        mid = tk.Frame(mc.body, bg=BG2); mid.pack(side="left", fill="both", expand=True)
        self.mt = tk.Label(mid, text="Загрузка...", bg=BG2, fg=TX,
                            font=F(20, "bold"), anchor="w")
        self.mt.pack(anchor="w")
        self.ms = tk.Label(mid, text="", bg=BG2, fg=DIM, font=F(11), anchor="w")
        self.ms.pack(anchor="w", pady=(2, 10))
        self.mbar = AnimatedProgress(mid, height=10); self.mbar.pack(fill="x")
        Btn(mc.body, "↻", w=50, h=44, bg=BG3, fg=DIM, hov=BR2, bd=BR,
            pbg=BG2, cmd=self._load).pack(side="right", padx=(20, 0))
        b = tk.Frame(self, bg=BG); b.pack(fill="x", padx=32, pady=(14, 8))
        Btn(b, "Снять", w=120, h=36, r=8, bg=BG3, fg=DIM, hov=BR2, bd=BR,
            fnt=F(11), cmd=self._none).pack(side="right", padx=(0, 8))
        Btn(b, ">100 МБ", w=120, h=36, r=8, bg=BG3, fg=DIM, hov=BR2, bd=BR,
            fnt=F(11), cmd=self._big).pack(side="right")
        lc = Card(self, r=16, px=10, py=10); lc.pack(fill="both", expand=True, padx=32, pady=(8, 0))
        self.cv = tk.Canvas(lc.body, bg=BG2, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lc.body, command=self.cv.yview); sb.pack(side="right", fill="y")
        self.cv.configure(yscrollcommand=sb.set)
        self.lf = tk.Frame(self.cv, bg=BG2)
        self.cv.create_window((0,0), window=self.lf, anchor="nw")
        self.lf.bind("<Configure>",
                     lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        bot = tk.Frame(self, bg=BG); bot.pack(fill="x", padx=32, pady=(10, 28))
        self.sl = tk.Label(bot, text="Выбрано: 0", bg=BG, fg=DIM,
                            font=F(11), anchor="w")
        self.sl.pack(side="left")
        Btn(bot, "✕  Завершить", w=230, h=44, bg=RD, fg="#fff", hov="#e04b43",
            cmd=self._kill).pack(side="right")
        self.after(300, self._load)
    def _load(self):
        def w():
            info = mem_info(); pr = list_procs()
            self.after(0, lambda: self._done(info, pr))
        threading.Thread(target=w, daemon=True).start()
    def _done(self, info, pr):
        if info:
            self.mt.configure(text=f"{hs(info['used'])} / {hs(info['total'])}  ({info['pct']}%)")
            self.ms.configure(text=f"Свободно: {hs(info['free'])}")
            self.mbar.set(info["pct"]/100.0)
        self.procs = pr; self.sel.clear(); self._rend()
    def _rend(self):
        for w in self.lf.winfo_children(): w.destroy()
        self.rows.clear()
        if not self.procs:
            tk.Label(self.lf, text="Нет данных", bg=BG2, fg=MUT, font=F(12)
                     ).pack(pady=40); return
        for p in self.procs[:200]:
            pid, n, mem = p["pid"], p["name"], p["mem"]
            pr = n.lower() in PROT
            row = tk.Frame(self.lf, bg=BG2); row.pack(fill="x", pady=1, padx=2)
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(row, variable=var, bg=BG2, activebackground=BG2,
                            selectcolor=BG2, highlightthickness=0, bd=0,
                            state=("disabled" if pr else "normal"),
                            command=lambda pp=pid: self._chk(pp)
                            ).pack(side="left", padx=(6, 0))
            tk.Label(row, text=n, bg=BG2, fg=MUT if pr else TX,
                     font=F(11), anchor="w", width=38
                     ).pack(side="left", padx=(4, 0), pady=6)
            if pr:
                tk.Label(row, text="система", bg=BG2, fg=YL, font=F(9)
                         ).pack(side="left", padx=(6, 0))
            tk.Label(row, text=str(pid), bg=BG2, fg=DIM, font=F(10, m=True),
                     width=10, anchor="w").pack(side="left")
            c = RD if mem > 300*1024*1024 else (YL if mem > 100*1024*1024 else DIM)
            tk.Label(row, text=hs(mem) if mem else "—", bg=BG2, fg=c,
                     font=F(10, m=True), width=14, anchor="e"
                     ).pack(side="right", padx=(0, 12))
            self.rows[pid] = {"v": var, "p": pr, "m": mem}
    def _chk(self, pid):
        e = self.rows.get(pid)
        if not e: return
        if e["v"].get(): self.sel.add(pid)
        else: self.sel.discard(pid)
        self._usel()
    def _usel(self):
        n = len(self.sel)
        if n:
            freed = sum(self.rows[p]["m"] for p in self.sel if p in self.rows)
            self.sl.configure(text=f"Выбрано: {n}   ~{hs(freed)}", fg=AC)
        else: self.sl.configure(text="Выбрано: 0", fg=DIM)
    def _none(self):
        for e in self.rows.values(): e["v"].set(False)
        self.sel.clear(); self._usel()
    def _big(self):
        self.sel.clear()
        for pid, e in self.rows.items():
            e["v"].set(False)
            if not e["p"] and e["m"] > 100*1024*1024:
                e["v"].set(True); self.sel.add(pid)
        self._usel()
    def _kill(self):
        if not self.sel:
            Toast(self.app, "Ничего не выбрано", "warn"); return
        if not messagebox.askyesno("Завершить", f"Завершить {len(self.sel)} процессов?"): return
        k = 0; freed = 0
        for pid in list(self.sel):
            e = self.rows.get(pid)
            if not e or e["p"]: continue
            if kill_proc(pid): k += 1; freed += e["m"]
        Toast(self.app, f"Завершено: {k}   ~{hs(freed)}", "ok" if k else "error")
        self.after(400, self._load)

class DiskPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        self.tg = {}; self.ch = {}
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Очистка диска", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Освободите место на диске", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        self.dh = tk.Frame(self, bg=BG); self.dh.pack(fill="x", padx=32, pady=(16, 0))
        cc = Card(self, r=16, py=16); cc.pack(fill="both", expand=True, padx=32, pady=(12, 0))
        tk.Label(cc.body, text="Что чистить", bg=BG2, fg=TX,
                 font=F(13, "bold"), anchor="w").pack(anchor="w", pady=(0, 10))
        self.cat_holder = tk.Frame(cc.body, bg=BG2); self.cat_holder.pack(fill="both", expand=True)
        bot = tk.Frame(self, bg=BG); bot.pack(fill="x", padx=32, pady=(14, 28))
        self.fl = tk.Label(bot, text="Освобождено: —", bg=BG, fg=DIM,
                            font=F(11), anchor="w")
        self.fl.pack(side="left")
        Btn(bot, "🧹 Очистить", w=170, h=44, cmd=self._clr).pack(side="right", padx=(0, 8))
        Btn(bot, "Всё", w=100, h=44, bg=BG3, fg=DIM, hov=BR2, bd=BR,
            cmd=self._all).pack(side="right")
        self.after(200, self.refresh)
    def refresh(self):
        for w in self.dh.winfo_children(): w.destroy()
        for w in self.cat_holder.winfo_children(): w.destroy()
        for d in list_drives():
            c = Card(self.dh, r=14, py=14); c.pack(fill="x", pady=5)
            tk.Label(c.body, text="▦", bg=BG2, fg=AC, font=F(22, "bold")
                     ).pack(side="left", padx=(0, 14))
            col = tk.Frame(c.body, bg=BG2); col.pack(side="left", fill="both", expand=True)
            pct = d["p"]; cl = RD if pct >= 85 else (YL if pct >= 65 else AC)
            tk.Label(col, text=d["m"], bg=BG2, fg=TX, font=F(14, "bold"),
                     anchor="w").pack(anchor="w")
            tk.Label(col, text=f"{hs(d['u'])} / {hs(d['t'])}   ·   Свободно: {hs(d['f'])}",
                     bg=BG2, fg=DIM, font=F(10), anchor="w"
                     ).pack(anchor="w", pady=(2, 6))
            bar = tk.Canvas(col, height=8, bg=BG2, highlightthickness=0); bar.pack(fill="x")
            def dbr(b=bar, cc=cl, pp=pct):
                b.delete("all")
                w, h = b.winfo_width(), b.winfo_height()
                if w < 4: return
                rr(b, 0, 0, w, h, r=4, fill=BG1, outline=BR)
                if pp > 0: rr(b, 0, 0, max(8, int(w*pp/100)), h, r=4, fill=cc, outline=cc)
            bar.bind("<Configure>", lambda e, db=dbr: db())
            tk.Label(c.body, text=f"{pct:.0f}%", bg=BG2, fg=cl,
                     font=F(14, "bold"), width=6).pack(side="right")
        self.tg = clean_targets(); self.ch = {}
        for k, t in self.tg.items():
            if not t.get("p") or not os.path.isdir(t["p"]): continue
            r = tk.Frame(self.cat_holder, bg=BG2); r.pack(fill="x", pady=3)
            v = tk.BooleanVar(value=True)
            self.ch[k] = {"v": v, "p": t["p"], "n": t["n"]}
            tk.Checkbutton(r, text=t["n"], variable=v, bg=BG2, fg=TX,
                            activebackground=BG2, activeforeground=TX,
                            selectcolor=BG1, font=F(11), anchor="w", bd=0,
                            highlightthickness=0).pack(side="left", padx=(4, 0))
            try: tk.Label(r, text=hs(dir_size(t["p"])), bg=BG2, fg=AC,
                          font=F(10, "bold")).pack(side="right", padx=(0, 8))
            except Exception: pass
    def _all(self):
        s = list(self.ch.keys())
        if not s: return
        if not messagebox.askyesno("Очистка", f"Очистить всё ({len(s)})?"): return
        self._run(s)
    def _clr(self):
        s = [k for k, v in self.ch.items() if v["v"].get()]
        if not s:
            Toast(self.app, "Ничего не выбрано", "warn"); return
        if not messagebox.askyesno("Очистка", f"Очистить {len(s)} категорий?"): return
        self._run(s)
    def _run(self, keys):
        self.fl.configure(text="Очистка...", fg=DIM)
        def w():
            total = 0
            for k in keys:
                v = self.ch.get(k)
                if not v: continue
                f, _ = clean_dir(v["p"]); total += f
            def d():
                self.fl.configure(text=f"Освобождено: {hs(total)}", fg=AC)
                Toast(self.app, f"Освобождено: {hs(total)}", "ok")
                self.after(500, self.refresh)
            self.after(0, d)
        threading.Thread(target=w, daemon=True).start()

class GamePage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        self.boosted = False; self.boosted_pids = []
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Оптимизация игр", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Освободите ресурсы перед запуском игры", bg=BG,
                 fg=DIM, font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        boost_card = Card(self, r=16, py=22)
        boost_card.pack(fill="x", padx=32, pady=(16, 0))
        inner = boost_card.body
        tk.Label(inner, text="🎮", bg=BG2, fg=BL, font=F(48)
                 ).pack(side="left", padx=(10, 24))
        col = tk.Frame(inner, bg=BG2); col.pack(side="left", fill="both", expand=True)
        self.title_lbl = tk.Label(col, text="Игровой режим выключен", bg=BG2,
                                   fg=TX, font=F(18, "bold"), anchor="w")
        self.title_lbl.pack(anchor="w")
        self.sub_lbl = tk.Label(col,
            text="Нажмите, чтобы освободить ОЗУ и повысить производительность",
            bg=BG2, fg=DIM, font=F(11), anchor="w", justify="left")
        self.sub_lbl.pack(anchor="w", pady=(4, 14))
        self.boost_btn = Btn(col, "🎮  Включить игровой режим", w=280, h=48,
                              bg=BL, fg="#04120e", hov="#0ea5e9",
                              pbg=BG2, cmd=self._boost)
        self.boost_btn.pack(anchor="w")
        set_card = Card(self, r=14, py=14); set_card.pack(fill="x", padx=32, pady=(14, 0))
        tk.Label(set_card.body, text="Что делать при бусте", bg=BG2, fg=TX,
                 font=F(13, "bold"), anchor="w").pack(anchor="w", pady=(0, 10))
        self.v_power = tk.BooleanVar(value=bool(app.cfg.get("game_boost_power", True)))
        tk.Checkbutton(set_card.body, text="План питания High Performance",
                       variable=self.v_power, bg=BG2, fg=TX, activebackground=BG2,
                       activeforeground=TX, selectcolor=BG1, font=F(11),
                       anchor="w", bd=0, highlightthickness=0).pack(anchor="w", pady=3)
        self.v_priority = tk.BooleanVar(value=bool(app.cfg.get("game_boost_priority", True)))
        tk.Checkbutton(set_card.body, text="Повысить приоритет игры",
                       variable=self.v_priority, bg=BG2, fg=TX, activebackground=BG2,
                       activeforeground=TX, selectcolor=BG1, font=F(11),
                       anchor="w", bd=0, highlightthickness=0).pack(anchor="w", pady=3)
        kill_card = Card(self, r=14, py=14)
        kill_card.pack(fill="both", expand=True, padx=32, pady=(14, 0))
        tk.Label(kill_card.body, text="Процессы, которые будут закрыты",
                 bg=BG2, fg=TX, font=F(13, "bold"), anchor="w"
                 ).pack(anchor="w", pady=(0, 8))
        tk.Label(kill_card.body, text="По одному в строке", bg=BG2, fg=DIM,
                 font=F(10), anchor="w").pack(anchor="w", pady=(0, 8))
        self.kill_box = tk.Text(kill_card.body, bg=BG1, fg=TX, bd=0, height=8,
                                 font=F(10, m=True), wrap="none",
                                 highlightthickness=1, highlightbackground=BR,
                                 insertbackground=TX, padx=8, pady=6)
        self.kill_box.pack(fill="both", expand=True)
        self.kill_box.insert("1.0", "\n".join(app.cfg.get("game_kill_list", [])))
        bot = tk.Frame(self, bg=BG); bot.pack(fill="x", padx=32, pady=(14, 28))
        self.info_lbl = tk.Label(bot, text="Готов", bg=BG, fg=DIM,
                                  font=F(11), anchor="w")
        self.info_lbl.pack(side="left")
        Btn(bot, "💾 Сохранить список", w=200, h=42, bg=BG3, fg=DIM,
            hov=BR2, bd=BR, cmd=self._save).pack(side="right", padx=(0, 8))
        self.unboost_btn = Btn(bot, "⏹  Выключить", w=160, h=42, bg=BG3,
                                fg=DIM, hov=BR2, bd=BR, cmd=self._unboost)
        self.unboost_btn.pack(side="right"); self.unboost_btn.on(False)
    def _save(self):
        lst = [s.strip() for s in self.kill_box.get("1.0","end").splitlines() if s.strip()]
        self.app.cfg["game_kill_list"] = lst
        self.app.cfg["game_boost_power"] = bool(self.v_power.get())
        self.app.cfg["game_boost_priority"] = bool(self.v_priority.get())
        sj(CFG, self.app.cfg)
        Toast(self.app, "Список сохранён", "ok")
    def _boost(self):
        if self.boosted:
            Toast(self.app, "Уже включено", "warn"); return
        self._save(); self.info_lbl.configure(text="Оптимизация...", fg=BL)
        def w():
            kill_list = set(s.lower() for s in self.app.cfg.get("game_kill_list", []))
            procs = list_procs(); killed = 0; freed = 0
            for p in procs:
                if p["name"].lower() in kill_list and not p["name"].lower() in PROT:
                    if kill_proc(p["pid"]): killed += 1; freed += p["mem"]
            if self.app.cfg.get("game_boost_power", True): boost_power_plan()
            bp = []
            if self.app.cfg.get("game_boost_priority", True):
                games = {"cs2.exe","csgo.exe","valorant.exe","dota2.exe",
                         "fortnite.exe","gta5.exe","minecraft.exe"}
                for p in procs:
                    if p["name"].lower() in games:
                        if set_priority(p["pid"], True): bp.append(p["pid"])
            self.boosted_pids = bp
            def d():
                self.boosted = True
                self.title_lbl.configure(text="🎮 Игровой режим ВКЛЮЧЁН", fg=GR)
                self.sub_lbl.configure(text=f"Освобождено: {hs(freed)}   ·   Закрыто: {killed}")
                self.info_lbl.configure(text="Готово", fg=AC)
                self.unboost_btn.on(True)
                Toast(self.app, f"Освобождено: {hs(freed)}", "ok")
            self.after(0, d)
        threading.Thread(target=w, daemon=True).start()
    def _unboost(self):
        if not self.boosted: return
        def w():
            reset_power_plan()
            for pid in self.boosted_pids: set_priority(pid, False)
            def d():
                self.boosted = False; self.boosted_pids = []
                self.title_lbl.configure(text="Игровой режим выключен", fg=TX)
                self.sub_lbl.configure(text="Система возвращена в обычный режим")
                self.info_lbl.configure(text="Готово", fg=AC)
                self.unboost_btn.on(False)
                Toast(self.app, "Буст выключен", "info")
            self.after(0, d)
        threading.Thread(target=w, daemon=True).start()

class QuarPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Карантин", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Изолированные файлы", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        w = tk.Frame(self, bg=BG); w.pack(fill="both", expand=True, padx=32, pady=(16, 0))
        self.cv = tk.Canvas(w, bg=BG, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(w, command=self.cv.yview); sb.pack(side="right", fill="y")
        self.cv.configure(yscrollcommand=sb.set)
        self.lf = tk.Frame(self.cv, bg=BG)
        self.cv.create_window((0,0), window=self.lf, anchor="nw")
        self.lf.bind("<Configure>",
                     lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        Btn(self, "↻  Обновить", w=160, h=44, bg=BG3, fg=DIM, hov=BR2, bd=BR,
            cmd=self.refresh).pack(anchor="e", padx=32, pady=(12, 28))
    def refresh(self):
        for w in self.lf.winfo_children(): w.destroy()
        if not os.path.isdir(QUAR):
            tk.Label(self.lf, text="Пусто", bg=BG, fg=MUT, font=F(12)
                     ).pack(pady=40); return
        its = sorted([f for f in os.listdir(QUAR) if f.endswith(".q")], reverse=True)
        if not its:
            tk.Label(self.lf, text="Пусто", bg=BG, fg=MUT, font=F(12)
                     ).pack(pady=40); return
        for n in its:
            f = os.path.join(QUAR, n); meta = lj(f + ".json", {})
            c = Card(self.lf, r=14, py=12); c.pack(fill="x", pady=5)
            tk.Label(c.body, text=os.path.basename(meta.get("orig", n)),
                     bg=BG2, fg=TX, font=F(12, "bold"), anchor="w"
                     ).pack(anchor="w")
            tk.Label(c.body, text=meta.get("orig", ""), bg=BG2, fg=DIM,
                     font=F(9, m=True), anchor="w").pack(anchor="w", pady=(2, 6))
            r = tk.Frame(c.body, bg=BG2); r.pack(fill="x")
            tk.Label(r, text=f"{meta.get('r','?')}   {hs(meta.get('s',0))}",
                     bg=BG2, fg=YL, font=F(9)).pack(side="left")
            Btn(r, "↩", w=40, h=28, r=6, bg=BG3, fg=AC, hov=ACS, bd=BR,
                fnt=F(11), cmd=lambda f=f, m=meta: self._r(f, m)
                ).pack(side="right", padx=3)
            Btn(r, "✕", w=40, h=28, r=6, bg=BG3, fg=RD, hov=ACS, bd=BR,
                fnt=F(11), cmd=lambda f=f: self._d(f)).pack(side="right", padx=3)
    def _r(self, f, m):
        o = m.get("orig")
        if not o or not messagebox.askyesno("Восстановить", f"Восстановить в:\n{o}?"): return
        try:
            os.makedirs(os.path.dirname(o), exist_ok=True)
            shutil.move(f, o)
            if os.path.exists(f + ".json"): os.remove(f + ".json")
            Toast(self.app, "Восстановлено", "warn"); self.refresh()
        except Exception as e: messagebox.showerror("Ошибка", str(e))
    def _d(self, f):
        if not messagebox.askyesno("Удалить", "Навсегда?"): return
        try:
            os.remove(f)
            if os.path.exists(f + ".json"): os.remove(f + ".json")
            Toast(self.app, "Удалено", "ok"); self.refresh()
        except Exception as e: messagebox.showerror("Ошибка", str(e))

class UpdPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Обновления", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Загрузка сигнатур из открытых источников",
                 bg=BG, fg=DIM, font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        c = Card(self, r=16, py=20); c.pack(fill="x", padx=32, pady=(16, 0))
        tk.Label(c.body, text="Σ", bg=BG2, fg=AC, font=F(32, "bold")
                 ).pack(side="left", padx=(0, 20))
        col = tk.Frame(c.body, bg=BG2); col.pack(side="left", fill="both", expand=True)
        self.t = tk.Label(col, text="", bg=BG2, fg=TX, font=F(15, "bold"), anchor="w")
        self.t.pack(anchor="w")
        self.s = tk.Label(col, text="", bg=BG2, fg=DIM, font=F(11), anchor="w")
        self.s.pack(anchor="w", pady=(2, 0))
        self.b = Btn(c.body, "⬇  Обновить", w=200, h=44, pbg=BG2, cmd=self._go)
        self.b.pack(side="right")
        lg = Card(self, r=16, py=16); lg.pack(fill="both", expand=True, padx=32, pady=(16, 28))
        tk.Label(lg.body, text="Лог", bg=BG2, fg=TX, font=F(13, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 8))
        self.l = tk.Text(lg.body, bg=BG1, fg=DIM, bd=0, font=F(10, m=True),
                          wrap="word", insertbackground=TX, highlightthickness=0,
                          padx=8, pady=8)
        self.l.pack(fill="both", expand=True)
    def refresh(self):
        db = self.app.db
        self.t.configure(text=f"SHA256: {len(db.sha):,}   ·   MD5: {len(db.md5):,}")
        self.s.configure(text=f"Обновлено: {db.upd or 'никогда'}")
    def _go(self):
        self.b.on(False); self.b.txt("Загрузка...")
        self.l.delete("1.0", "end")
        def w():
            def lg(m):
                self.after(0, lambda: (self.l.insert("end", m+"\n"), self.l.see("end")))
            try:
                update_sig(self.app.cfg, lg)
                self.app.db = DB()
                self.after(0, self.app.refresh_side)
                self.after(0, self.refresh)
                self.after(0, self.app.pages["dashboard"].refresh)
                self.after(0, lambda: (self.b.on(True), self.b.txt("⬇  Обновить")))
                self.after(0, lambda: Toast(self.app, "База обновлена", "ok"))
            except Exception as e:
                lg(f"! {e}")
                self.after(0, lambda: (self.b.on(True), self.b.txt("⬇  Обновить")))
        threading.Thread(target=w, daemon=True).start()

class SetPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=32, pady=(28, 12))
        tk.Label(head, text="Настройки", bg=BG, fg=TX,
                 font=F(24, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text="Автозапуск, сканирование, источники", bg=BG,
                 fg=DIM, font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))
        w = tk.Frame(self, bg=BG); w.pack(fill="both", expand=True, padx=32, pady=(16, 20))
        cv = tk.Canvas(w, bg=BG, highlightthickness=0)
        cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(w, command=cv.yview); sb.pack(side="right", fill="y")
        cv.configure(yscrollcommand=sb.set)
        body = tk.Frame(cv, bg=BG); cv.create_window((0,0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        s1 = Card(body, r=14, py=14); s1.pack(fill="x", pady=(0, 10))
        tk.Label(s1.body, text="Система", bg=BG2, fg=TX, font=F(13, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 8))
        self.v_auto = tk.BooleanVar(value=Auto.enabled())
        tk.Checkbutton(s1.body, text="Запускать при входе в систему",
                       variable=self.v_auto, command=self._tga, bg=BG2, fg=TX,
                       activebackground=BG2, activeforeground=TX,
                       selectcolor=BG1, font=F(11), anchor="w", bd=0,
                       highlightthickness=0).pack(anchor="w", pady=3)
        self.v_close = tk.BooleanVar(value=bool(app.cfg.get("close_to_tray", True)))
        tk.Checkbutton(s1.body, text="Сворачивать в трей при закрытии",
                       variable=self.v_close, bg=BG2, fg=TX, activebackground=BG2,
                       activeforeground=TX, selectcolor=BG1, font=F(11),
                       anchor="w", bd=0, highlightthickness=0).pack(anchor="w", pady=3)
        s2 = Card(body, r=14, py=14); s2.pack(fill="x", pady=(0, 10))
        tk.Label(s2.body, text="Сканирование", bg=BG2, fg=TX, font=F(13, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 8))
        self.v_skip = tk.BooleanVar(value=bool(app.cfg.get("skip_system_dirs", False)))
        tk.Checkbutton(s2.body, text="Пропускать системные папки",
                       variable=self.v_skip, bg=BG2, fg=TX, activebackground=BG2,
                       activeforeground=TX, selectcolor=BG1, font=F(11),
                       anchor="w", bd=0, highlightthickness=0).pack(anchor="w", pady=3)
        self.v_heur = tk.BooleanVar(value=bool(app.cfg.get("heuristics", True)))
        tk.Checkbutton(s2.body, text="Эвристика", variable=self.v_heur,
                       bg=BG2, fg=TX, activebackground=BG2, activeforeground=TX,
                       selectcolor=BG1, font=F(11), anchor="w", bd=0,
                       highlightthickness=0).pack(anchor="w", pady=3)
        s3 = Card(body, r=14, py=14); s3.pack(fill="x", pady=(0, 10))
        tk.Label(s3.body, text="Источники сигнатур (URL по одному в строке)",
                 bg=BG2, fg=TX, font=F(13, "bold"), anchor="w"
                 ).pack(anchor="w", pady=(0, 8))
        self.src = tk.Text(s3.body, bg=BG1, fg=TX, bd=0, height=6, font=F(10, m=True),
                            wrap="none", highlightthickness=1,
                            highlightbackground=BR, insertbackground=TX,
                            padx=8, pady=6)
        self.src.pack(fill="x")
        self.src.insert("1.0", "\n".join(app.cfg.get("sources", [])))
        act = tk.Frame(body, bg=BG); act.pack(fill="x", pady=(20, 10))
        Btn(act, "💾 Сохранить", w=180, cmd=self._save).pack(side="left", padx=(0, 10))
        Btn(act, "↻ Сброс", w=140, bg=BG3, fg=DIM, hov=BR2, bd=BR,
            cmd=self.refresh).pack(side="left")
    def _tga(self):
        w = bool(self.v_auto.get())
        if w and not Auto.enabled():
            ok, msg = Auto.enable()
            Toast(self.app, msg, "ok" if ok else "error")
            if not ok: self.v_auto.set(False)
        elif not w and Auto.enabled():
            Auto.disable()
        self.app.cfg["autostart"] = Auto.enabled()
        sj(CFG, self.app.cfg)
    def refresh(self):
        self.v_auto.set(Auto.enabled())
        self.v_close.set(bool(self.app.cfg.get("close_to_tray", True)))
        self.v_skip.set(bool(self.app.cfg.get("skip_system_dirs", False)))
        self.v_heur.set(bool(self.app.cfg.get("heuristics", True)))
        self.src.delete("1.0", "end")
        self.src.insert("1.0", "\n".join(self.app.cfg.get("sources", [])))
    def _save(self):
        self.app.cfg["close_to_tray"] = bool(self.v_close.get())
        self.app.cfg["skip_system_dirs"] = bool(self.v_skip.get())
        self.app.cfg["heuristics"] = bool(self.v_heur.get())
        self.app.cfg["sources"] = [s.strip() for s in
                                    self.src.get("1.0", "end").splitlines()
                                    if s.strip()]
        if sj(CFG, self.app.cfg): Toast(self.app, "Сохранено", "ok")

class App(tk.Tk):
    def __init__(self, cfg, db):
        super().__init__()
        self.cfg, self.db = cfg, db
        self.tray = None; self.tq = queue.Queue(); self._q = False
        self.title(f"{APP} {VER}")
        self.geometry("1240x800"); self.minsize(1100, 700)
        self.configure(bg=BG)
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self._side(); self._content()
        self.go("dashboard")
        self._tray_setup()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(2000, self._tpoll)
        self.after(200, lambda: round_win(self))
    def _tray_setup(self):
        if not WIN: return
        self.tray = Tray(f"{APP} {VER}", lambda: self.tq.put("t"),
                         lambda: self.tq.put("m"))
        self.tray.start()
    def _tpoll(self):
        try:
            while True:
                a = self.tq.get_nowait()
                if a == "t": self.toggle()
                elif a == "m": self._menu()
        except queue.Empty: pass
        self.after(2000, self._tpoll)
    def _menu(self):
        m = tk.Menu(self, tearoff=0, bg=BG2, fg=TX, activebackground=ACS,
                    activeforeground=TX, bd=0, font=F(11))
        m.add_command(label="Открыть", command=self.toggle)
        m.add_command(label="Память", command=lambda: (self.toggle(),
                     self.after(150, lambda: self.go("memory"))))
        m.add_command(label="Диск", command=lambda: (self.toggle(),
                     self.after(150, lambda: self.go("disk"))))
        m.add_command(label="Игры", command=lambda: (self.toggle(),
                     self.after(150, lambda: self.go("games"))))
        m.add_separator()
        m.add_command(label="Выход", command=self.quit_app)
        try: m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally: m.grab_release()
    def toggle(self):
        try:
            if self.state() == "withdrawn" or not self.winfo_viewable():
                self.deiconify(); self.lift(); self.focus_force()
            else: self.withdraw()
        except Exception: pass
    def _close(self):
        if self.cfg.get("close_to_tray", True) and WIN and self.tray: self.withdraw()
        else: self.quit_app()
    def quit_app(self):
        if self._q: return
        self._q = True
        try:
            if self.tray: self.tray.stop()
        except Exception: pass
        try: self.destroy()
        except Exception: pass
    def _side(self):
        sb = tk.Frame(self, bg=BG1, width=240)
        sb.grid(row=0, column=0, sticky="nsw"); sb.pack_propagate(False)
        lg = tk.Frame(sb, bg=BG1); lg.pack(fill="x", padx=20, pady=(22, 26))
        lc = tk.Canvas(lg, width=36, height=36, bg=BG1, highlightthickness=0)
        lc.pack(side="left")
        for i in range(4):
            lc.create_oval(2+i*4, 2+i*4, 34-i*4, 34-i*4,
                           fill=lerp_color(BG1, AC, 0.1+i*0.15), outline="")
        lc.create_text(18, 18, text="⛨", fill="#04120e", font=F(16, "bold"))
        tk.Label(lg, text="Unlock", bg=BG1, fg=TX, font=F(15, "bold")
                 ).pack(side="left", padx=(8, 0))
        tk.Label(lg, text="Antivirus", bg=BG1, fg=AC, font=F(15, "bold")
                 ).pack(side="left")
        self.navs = {}
        items = [("dashboard", "⌂", "Главная"),
                 ("scan", "⌕", "Сканирование"),
                 ("games", "🎮", "Игры"),
                 ("memory", "▦", "Память"),
                 ("disk", "⛁", "Диск"),
                 ("quarantine", "▣", "Карантин"),
                 ("updates", "↓", "Обновления"),
                 ("settings", "⚙", "Настройки")]
        for k, ic, t in items:
            b = NavBtn(sb, ic, t, cmd=lambda kk=k: self.go(kk))
            b.pack(fill="x", padx=12, pady=2)
            self.navs[k] = b
        bot = tk.Frame(sb, bg=BG1); bot.pack(side="bottom", fill="x", padx=20, pady=20)
        tk.Frame(bot, bg=BR, height=1).pack(fill="x", pady=(0, 14))
        self.ss = tk.Label(bot, text="", bg=BG1, fg=MUT, font=F(9),
                            anchor="w", justify="left")
        self.ss.pack(fill="x"); self.refresh_side()
    def _content(self):
        self.cont = tk.Frame(self, bg=BG)
        self.cont.grid(row=0, column=1, sticky="nsew")
        self.cont.grid_rowconfigure(0, weight=1); self.cont.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for k, cls in [("dashboard", DashboardPage), ("scan", ScanPage),
                       ("games", GamePage), ("memory", MemPage),
                       ("disk", DiskPage), ("quarantine", QuarPage),
                       ("updates", UpdPage), ("settings", SetPage)]:
            p = cls(self.cont, self); p.grid(row=0, column=0, sticky="nsew")
            self.pages[k] = p
    def go(self, k):
        self.pages[k].tkraise()
        for kk, b in self.navs.items(): b.act(kk == k)
        if hasattr(self.pages[k], "refresh"): self.pages[k].refresh()
    def refresh_side(self):
        u = (self.db.upd or "—")[:10]
        self.ss.configure(text=f"База: {u}\nSHA256: {len(self.db.sha):,}\n"
                                f"Авто: {'Вкл' if Auto.enabled() else 'Выкл'}")
    def _autoupd(self):
        last = self.cfg.get("last_update")
        hrs = self.cfg.get("auto_update_hours", 24)
        need = True
        if last:
            try:
                dt = datetime.fromisoformat(last)
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                need = (datetime.now(timezone.utc)-dt).total_seconds() > hrs*3600
            except Exception: need = True
        if need:
            def w():
                try:
                    update_sig(self.cfg)
                    self.db = DB()
                    self.after(0, self.refresh_side)
                    self.after(0, self.pages["dashboard"].refresh)
                except Exception: pass
            threading.Thread(target=w, daemon=True).start()

def main():
    dpi()
    if not os.path.exists(CFG): sj(CFG, DEFAULT)
    cfg = lj(CFG, DEFAULT)
    for k, v in DEFAULT.items(): cfg.setdefault(k, v)
    db = DB()

    splash = Splash()
    stages = [
        (0.05, "Инициализация..."),
        (0.15, "Загрузка конфигурации..."),
        (0.30, f"Сигнатур в базе: {len(db.sha):,}"),
        (0.50, "Проверка источников..."),
        (0.65, "Запуск интерфейса..."),
        (0.85, "Подготовка модулей..."),
        (1.00, "Готово!"),
    ]

    def animate_stages(i=0):
        if i >= len(stages):
            def start_main():
                app = App(cfg, db)
                app.after(100, lambda: app._autoupd())
                if "--tray" in sys.argv or cfg.get("start_minimized", False):
                    app.withdraw()
                app.mainloop()
            splash.finish(start_main)
            return
        prog, txt = stages[i]
        try: splash.set_status(txt, prog)
        except Exception: pass
        splash.after(280, lambda: animate_stages(i+1))

    splash.after(400, animate_stages)
    splash.mainloop()

if __name__ == "__main__":
    main()
