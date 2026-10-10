#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UnlockAntivirus 7.0 — антивирус + память + диск + трей + автозапуск."""

import os, sys, json, time, math, queue, hashlib, shutil, threading, ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

APP = "UnlockAntivirus"
VER = "7.0"
SD = os.path.dirname(os.path.abspath(__file__))


def _w(p):
    try:
        os.makedirs(p, exist_ok=True)
        t = os.path.join(p, ".t")
        open(t, "w").close()
        os.remove(t)
        return True
    except Exception:
        return False


BASE = SD if _w(SD) else os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), APP)
os.makedirs(BASE, exist_ok=True)

SIG = os.path.join(BASE, "signatures.json")
CFG = os.path.join(BASE, "config.json")
QUAR = os.path.join(BASE, "quarantine")
CACHE = os.path.join(BASE, "cache.json")
LOGF = os.path.join(BASE, "log.txt")
os.makedirs(QUAR, exist_ok=True)

# Цвета
BG, ELEV, SB, INP = "#0b0f14", "#0f1620", "#0a0e13", "#0a0e13"
BR, TX, DIM, MUT = "#1c2634", "#e7edf3", "#93a1af", "#6b7a89"
AC, AC2, ACS = "#22d3a5", "#14b8a6", "#10332b"
BL, RD, YL, GR = "#38bdf8", "#ff5f57", "#febc2e", "#28c840"
FN, FM = "Segoe UI", "Consolas"


def F(s, w="normal", m=False):
    return (FM if m else FN, s, w)


WIN = sys.platform == "win32"

DEFAULT_CFG = {
    "sources": [
        "https://bazaar.abuse.ch/export/txt/sha256/recent/",
        "https://threatfox.abuse.ch/export/csv/sha256/recent/",
        "https://urlhaus.abuse.ch/downloads/text/",
    ],
    "extensions_scan": [],
    "skip_system_dirs": False,
    "heuristics": True,
    "max_file_size_mb": 500,
    "scan_threads": 4,
    "auto_update_hours": 24,
    "last_update": None,
    "autostart": False,
    "start_minimized": False,
    "close_to_tray": True,
    "whitelist": [],
}


# ===================== HELPERS =====================
def lj(p, d):
    if not os.path.exists(p):
        return d
    try:
        return json.load(open(p, "r", encoding="utf-8"))
    except Exception:
        return d


def sj(p, d):
    try:
        json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def log(msg):
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


def sha256_file(p):
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    except Exception:
        return None


def md5_file(p):
    h = hashlib.md5()
    try:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    except Exception:
        return None


def hs(n):
    for u in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024:
            return f"{n:.0f} {u}"
        n /= 1024
    return f"{n:.1f} ПБ"


def rr(cv, x1, y1, x2, y2, r=10, **k):
    pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
           x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
           x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **k)


def dpi():
    if WIN:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def round_win(root):
    if not WIN:
        return
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
    except Exception:
        pass


def dir_size(path):
    total = 0
    if not path or not os.path.isdir(path):
        return 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except Exception:
                pass
    return total


def clean_dir(path):
    if not path or not os.path.isdir(path):
        return 0, 0
    freed, err = 0, 0
    try:
        for it in os.listdir(path):
            fp = os.path.join(path, it)
            try:
                if os.path.isdir(fp):
                    sz = dir_size(fp)
                    shutil.rmtree(fp, ignore_errors=True)
                    freed += sz
                else:
                    sz = os.path.getsize(fp)
                    os.remove(fp)
                    freed += sz
            except Exception:
                err += 1
    except Exception:
        pass
    return freed, err


def list_drives():
    if not WIN:
        try:
            t, u, f = shutil.disk_usage("/")
            return [{"m": "/", "t": t, "u": u, "f": f,
                     "p": u / t * 100 if t else 0}]
        except Exception:
            return []
    out = []
    try:
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if mask & (1 << i):
                d = chr(65 + i) + ":\\"
                try:
                    if ctypes.windll.kernel32.GetDriveTypeW(d) == 3:
                        t, u, f = shutil.disk_usage(d)
                        out.append({"m": d, "t": t, "u": u, "f": f,
                                    "p": u / t * 100 if t else 0})
                except Exception:
                    pass
    except Exception:
        pass
    return out


def clean_targets():
    w = os.environ.get("SystemRoot", "C:\\Windows")
    la = os.environ.get("LOCALAPPDATA", "")
    ro = os.environ.get("APPDATA", "")
    te = os.environ.get("TEMP", "")
    return {
        "ut": {"p": te, "n": "Временные файлы"},
        "wt": {"p": os.path.join(w, "Temp"), "n": "Системный temp"},
        "pf": {"p": os.path.join(w, "Prefetch"), "n": "Prefetch"},
        "wu": {"p": os.path.join(w, "SoftwareDistribution", "Download"),
               "n": "Windows Update"},
        "ch": {"p": os.path.join(la, "Google", "Chrome", "User Data",
                                 "Default", "Cache"),
               "n": "Chrome кэш"},
        "ed": {"p": os.path.join(la, "Microsoft", "Edge", "User Data",
                                 "Default", "Cache"),
               "n": "Edge кэш"},
        "op": {"p": os.path.join(ro, "Opera Software", "Opera Stable", "Cache"),
               "n": "Opera кэш"},
        "d3": {"p": os.path.join(la, "D3DSCache"), "n": "DirectX шейдеры"},
    }


# ===================== WINDOWS API =====================
if WIN:
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x02
    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("pid", wintypes.DWORD), ("heap", ctypes.c_void_p),
                    ("mod", wintypes.DWORD), ("thr", wintypes.DWORD),
                    ("ppid", wintypes.DWORD), ("pri", ctypes.c_long),
                    ("flags", wintypes.DWORD), ("exe", wintypes.WCHAR * 260)]

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("pf", wintypes.DWORD),
                    ("peak", ctypes.c_size_t), ("work", ctypes.c_size_t),
                    ("qp", ctypes.c_size_t), ("qpp", ctypes.c_size_t),
                    ("qnp", ctypes.c_size_t), ("qnp2", ctypes.c_size_t),
                    ("pg", ctypes.c_size_t), ("pgp", ctypes.c_size_t)]

    class MS(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("load", wintypes.DWORD),
                    ("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong),
                    ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                    ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                    ("aex", ctypes.c_ulonglong)]

    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.GlobalMemoryStatusEx.argtypes = [ctypes.c_void_p]
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]

PROTECTED = {
    "system", "system idle process", "registry", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "dwm.exe", "fontdrvhost.exe", "explorer.exe", "sihost.exe",
    "ctfmon.exe", "taskhostw.exe", "startmenuexperiencehost.exe",
    "shellexperiencehost.exe", "searchhost.exe", "searchindexer.exe",
    "audiodg.exe", "spoolsv.exe", "conhost.exe", "msmpeng.exe",
    "securityhealthservice.exe", "applicationframehost.exe",
    "textinputhost.exe", "unlockantivirus.exe",
}


def mem_info():
    if not WIN:
        return None
    try:
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return None
        return {"total": m.total, "free": m.free,
                "used": m.total - m.free, "pct": m.load}
    except Exception:
        return None


def proc_mem(pid):
    if not WIN:
        return 0
    h = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return 0
    try:
        pm = PMC()
        pm.cb = ctypes.sizeof(PMC)
        if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pm), pm.cb):
            return pm.work
        return 0
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def list_procs():
    if not WIN:
        return []
    out = []
    try:
        h = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h == -1 or not h:
            return out
        try:
            e = PE()
            e.dwSize = ctypes.sizeof(PE)
            if not ctypes.windll.kernel32.Process32FirstW(h, ctypes.byref(e)):
                return out
            while True:
                if e.pid and e.exe:
                    out.append({"pid": e.pid, "name": e.exe,
                                "mem": proc_mem(e.pid)})
                if not ctypes.windll.kernel32.Process32NextW(h, ctypes.byref(e)):
                    break
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        pass
    out.sort(key=lambda x: x["mem"], reverse=True)
    return out


def kill_proc(pid):
    if not WIN:
        return False
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h:
        return False
    try:
        return bool(ctypes.windll.kernel32.TerminateProcess(h, 1))
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def is_prot(n):
    return n.lower() in PROTECTED


# ===================== ЭВРИСТИКА =====================
HEUR = [
    (b"powershell.exe -enc", "PowerShell base64", "high"),
    (b"powershell -enc", "PowerShell base64", "high"),
    (b"cmd.exe /c powershell", "cmd→powershell", "high"),
    (b"WScript.Shell", "WScript.Shell", "medium"),
    (b"eval(base64_decode", "eval(base64_decode)", "high"),
    (b"ActiveXObject", "ActiveXObject", "medium"),
    (b"vssadmin delete shadows", "Удаление теневых копий", "high"),
    (b"cipher /w:", "Затирание данных", "medium"),
    (b"taskkill /f /im", "Убийство процессов", "low"),
]
DOUBLE_EXT = [".pdf.exe", ".doc.exe", ".docx.exe", ".jpg.exe", ".png.exe",
              ".txt.exe", ".mp3.exe", ".mp4.exe", ".avi.exe",
              ".pdf.scr", ".doc.scr", ".jpg.scr"]


def heuristic(path):
    findings = []
    low = path.lower()
    for e in DOUBLE_EXT:
        if low.endswith(e):
            findings.append((f"Двойное расширение {e}", "high"))
    try:
        if os.path.getsize(path) > 5 << 20:
            return findings
        with open(path, "rb") as f:
            data = f.read(512 * 1024)
    except Exception:
        return findings
    for pat, desc, lvl in HEUR:
        if pat in data:
            findings.append((desc, lvl))
    return findings


def quarantine_file(path, reason="malware"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(QUAR, f"{ts}_{os.path.basename(path)}.q")
    try:
        size = os.path.getsize(path)
        sha = sha256_file(path)
        shutil.move(path, dst)
        sj(dst + ".json", {"orig": os.path.abspath(path),
                            "r": reason, "s": size, "h": sha, "t": ts})
        log(f"QUARANTINE {path} ({reason})")
        return dst
    except Exception as e:
        log(f"QUAR FAIL {path}: {e}")
        return None


# ===================== БАЗА =====================
class DB:
    def __init__(self):
        d = lj(SIG, {"sha256": [], "md5": [], "updated": None})
        self.sha = set(x.lower() for x in d.get("sha256", []))
        self.md5 = set(x.lower() for x in d.get("md5", []))
        self.upd = d.get("updated")

    def save(self):
        sj(SIG, {"sha256": sorted(self.sha),
                 "md5": sorted(self.md5),
                 "updated": self.upd})

    def add(self, hashes, kind="sha256"):
        t = self.sha if kind == "sha256" else self.md5
        ln = 64 if kind == "sha256" else 32
        n = len(t)
        for h in hashes:
            h = h.strip().lower()
            if len(h) == ln and all(c in "0123456789abcdef" for c in h):
                t.add(h)
        return len(t) - n

    def match(self, s, m):
        if s and s.lower() in self.sha:
            return "sha256"
        if m and m.lower() in self.md5:
            return "md5"
        return None


def parse_hashes(text):
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        for sep in (",", ";", "\t", " "):
            if sep in ln:
                for tok in ln.split(sep):
                    t = tok.strip().strip('"\'').lower()
                    if len(t) in (32, 64) and all(
                            c in "0123456789abcdef" for c in t):
                        out.append(t)
                break
        else:
            t = ln.strip().strip('"\'').lower()
            if len(t) in (32, 64) and all(
                    c in "0123456789abcdef" for c in t):
                out.append(t)
    return out


def fetch(url):
    r = Request(url, headers={"User-Agent": f"{APP}/{VER}"})
    with urlopen(r, timeout=60) as x:
        raw = x.read()
    return raw.decode("utf-8", "ignore")


def update_signatures(cfg, lg=print):
    db = DB()
    srcs = cfg.get("sources", [])
    for i, u in enumerate(srcs):
        try:
            lg(f"[{i+1}/{len(srcs)}] {u}")
            hashes = parse_hashes(fetch(u))
            s = [h for h in hashes if len(h) == 64]
            m = [h for h in hashes if len(h) == 32]
            db.add(s, "sha256")
            db.add(m, "md5")
            lg(f"  +{len(s)} SHA256, +{len(m)} MD5")
        except Exception as e:
            lg(f"  ! {e}")
    db.upd = datetime.now(timezone.utc).isoformat()
    db.save()
    cfg["last_update"] = db.upd
    sj(CFG, cfg)
    lg(f"ИТОГО: {len(db.sha):,} SHA256, {len(db.md5):,} MD5")
    return db


# ===================== СКАНЕР =====================
class Scan:
    def __init__(self, db, cfg, on_file=None, on_threat=None,
                 on_done=None, on_prog=None):
        self.db = db
        self.cfg = cfg
        self.of = on_file or (lambda *a: None)
        self.ot = on_threat or (lambda *a: None)
        self.od = on_done or (lambda *a: None)
        self.op = on_prog or (lambda *a: None)
        self.stop = threading.Event()
        self.stats = {"sc": 0, "th": 0, "er": 0, "sk": 0, "cache": 0, "heur": 0}
        self.total = 0
        self.t0 = time.time()
        self.cache = lj(CACHE, {})

    def halt(self):
        self.stop.set()

    def collect(self, paths):
        out = []
        exts = set(e.lower() for e in self.cfg.get("extensions_scan", []))
        skip = self.cfg.get("skip_system_dirs", False)
        wl = set(w.lower() for w in self.cfg.get("whitelist", []))
        max_sz = self.cfg.get("max_file_size_mb", 500) * 1024 * 1024
        skip_names = {"windows", "$recycle.bin", "system volume information",
                      "appdata", "programdata", "system32", "syswow64",
                      "__pycache__", "node_modules", ".git"}

        for p in paths:
            if self.stop.is_set():
                break
            try:
                p = os.path.normpath(p)
            except Exception:
                pass

            if os.path.isfile(p):
                out.append(p)
                continue

            if not os.path.isdir(p):
                continue

            for root, dirs, files in os.walk(p, onerror=lambda e: None):
                if self.stop.is_set():
                    break
                if skip:
                    dirs[:] = [d for d in dirs if d.lower() not in skip_names]
                for n in files:
                    if self.stop.is_set():
                        break
                    fp = os.path.join(root, n)
                    if wl and fp.lower() in wl:
                        continue
                    if exts:
                        if os.path.splitext(n)[1].lower() not in exts:
                            continue
                    try:
                        if os.path.getsize(fp) > max_sz:
                            self.stats["sk"] += 1
                            continue
                    except OSError:
                        continue
                    out.append(fp)
        return out

    def one(self, fp):
        if self.stop.is_set():
            return
        try:
            st = os.stat(fp)
            sz, mt = st.st_size, st.st_mtime
        except OSError:
            self.stats["er"] += 1
            return

        self.of(fp)

        # Проверка кэша
        ck = f"{fp}|{mt}|{sz}"
        cached = self.cache.get(ck)
        if cached:
            self.stats["cache"] += 1
            self.stats["sc"] += 1
            if cached == "threat":
                self.stats["th"] += 1
                self.ot(fp, "cache", "")
            self.op({"done": self.stats["sc"], "total": self.total,
                     "speed": 0, "stats": dict(self.stats)})
            return

        s = sha256_file(fp)
        m = md5_file(fp)
        if s is None:
            self.stats["er"] += 1
            return

        self.stats["sc"] += 1
        match = self.db.match(s, m)
        if match:
            self.stats["th"] += 1
            self.cache[ck] = "threat"
            self.ot(fp, match, s)
            quarantine_file(fp, f"hash/{match}")
        elif self.cfg.get("heuristics", True):
            findings = heuristic(fp)
            if findings and any(x[1] == "high" for x in findings):
                self.stats["th"] += 1
                self.stats["heur"] += 1
                self.cache[ck] = "threat"
                desc = ", ".join(x[0] for x in findings[:3])
                self.ot(fp, f"эвристика: {desc}", s)
                quarantine_file(fp, "heuristic")
            else:
                self.cache[ck] = "clean"
        else:
            self.cache[ck] = "clean"

        el = max(0.001, time.time() - self.t0)
        self.op({"done": self.stats["sc"], "total": self.total,
                 "speed": self.stats["sc"] / el,
                 "stats": dict(self.stats)})

    def run(self, paths):
        self.t0 = time.time()
        files = self.collect(paths)
        self.total = len(files)
        self.op({"done": 0, "total": self.total, "speed": 0,
                 "stats": dict(self.stats)})

        th = max(1, int(self.cfg.get("scan_threads", 4)))
        if th == 1 or len(files) < 10:
            for fp in files:
                if self.stop.is_set():
                    break
                self.one(fp)
        else:
            with ThreadPoolExecutor(max_workers=th) as ex:
                futs = [ex.submit(self.one, fp) for fp in files]
                for _ in as_completed(futs):
                    if self.stop.is_set():
                        break

        # Сохраняем кэш
        if len(self.cache) > 200_000:
            keys = list(self.cache.keys())[-150_000:]
            self.cache = {k: self.cache[k] for k in keys}
        sj(CACHE, self.cache)

        self.od(dict(self.stats), self.total)


# ===================== АВТОЗАГРУЗКА =====================
class Auto:
    RK = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @staticmethod
    def _pyw():
        if not WIN:
            return None
        if getattr(sys, "frozen", False):
            return sys.executable
        b = os.path.dirname(sys.executable)
        for c in (os.path.join(b, "pythonw.exe"),
                  os.path.join(b, "pythonw"),
                  sys.executable.replace("python.exe", "pythonw.exe")):
            if c and os.path.isfile(c):
                return c
        return None

    @staticmethod
    def _cmd():
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --tray'
        p = Auto._pyw()
        if p:
            return f'"{p}" "{os.path.abspath(sys.argv[0])}" --tray'
        return ""

    @staticmethod
    def enabled():
        if not WIN:
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Auto.RK, 0,
                                winreg.KEY_READ) as k:
                winreg.QueryValueEx(k, APP)
                return True
        except Exception:
            return False

    @staticmethod
    def enable():
        if not WIN:
            return False, "Только Windows"
        try:
            import winreg
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, Auto.RK, 0,
                                    winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, Auto._cmd())
            return True, "Автозагрузка включена"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def disable():
        if not WIN:
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Auto.RK, 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, APP)
            return True
        except Exception:
            return False


# ===================== ТРЕЙ =====================
if WIN:
    from ctypes import wintypes as wt
    u32 = ctypes.windll.user32
    sh32 = ctypes.windll.shell32
    k32 = ctypes.windll.kernel32
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
                    ("ic", wt.HICON), ("cu", wt.HANDLE),
                    ("br", wt.HBRUSH), ("mn", wt.LPCWSTR),
                    ("cn", wt.LPCWSTR)]


class Tray:
    def __init__(self, tip, on_l, on_r):
        self.tip = tip[:127]
        self.on_l, self.on_r = on_l, on_r
        self.hw = None
        self._nid = None
        self._p = None
        self._rdy = threading.Event()
        self._stp = threading.Event()

    def start(self):
        if not WIN:
            return
        threading.Thread(target=self._run, daemon=True).start()
        self._rdy.wait(timeout=3)

    def stop(self):
        if not WIN:
            return
        self._stp.set()
        if self._nid is not None:
            try:
                sh32.Shell_NotifyIconW(2, ctypes.byref(self._nid))
            except Exception:
                pass
            self._nid = None
        if self.hw:
            try:
                u32.PostMessageW(self.hw, 2, 0, 0)
            except Exception:
                pass
            self.hw = None

    def tip_set(self, t):
        if not WIN or self._nid is None:
            return
        self.tip = t[:127]
        self._nid.tip = self.tip
        try:
            sh32.Shell_NotifyIconW(1, ctypes.byref(self._nid))
        except Exception:
            pass

    def _run(self):
        hi = k32.GetModuleHandleW(None)
        cn = f"AV_{id(self)}"
        self._p = WNDP(self._proc)
        wc = WC()
        wc.lp = self._p
        wc.hi = hi
        wc.cn = cn
        u32.RegisterClassW(ctypes.byref(wc))
        self.hw = u32.CreateWindowExW(0, cn, cn, 0, 0, 0, 0, 0,
                                       None, None, hi, None)
        if not self.hw:
            self._rdy.set()
            return
        ic = u32.LoadIconW(None, wt.LPCWSTR(32512))
        nid = NID()
        nid.cb = ctypes.sizeof(NID)
        nid.h = self.hw
        nid.id = 1
        nid.fl = 1 | 2 | 4
        nid.msg = 0x0400 + 20
        nid.ic = ic
        nid.tip = self.tip
        self._nid = nid
        sh32.Shell_NotifyIconW(0, ctypes.byref(nid))
        self._rdy.set()
        m = wt.MSG()
        while not self._stp.is_set():
            r = u32.GetMessageW(ctypes.byref(m), None, 0, 0)
            if r <= 0:
                break
            u32.TranslateMessage(ctypes.byref(m))
            u32.DispatchMessageW(ctypes.byref(m))

    def _proc(self, h, m, w, l):
        if m == 0x0400 + 20:
            if l in (0x0202, 0x0203):
                self.on_l()
            elif l == 0x0205:
                self.on_r()
            return 0
        if m == 2:
            u32.PostQuitMessage(0)
            return 0
        return u32.DefWindowProcW(wt.HWND(h), wt.UINT(m),
                                   wt.WPARAM(w), wt.LPARAM(l))


# ===================== ВИДЖЕТЫ =====================
class Card(tk.Frame):
    def __init__(self, m, radius=14, bgc=ELEV, bc=BR, px=16, py=14, **kw):
        try:
            pb = m.cget("bg")
        except Exception:
            pb = BG
        super().__init__(m, bg=pb, **kw)
        self._r, self._bg, self._bc = radius, bgc, bc
        self._cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=pb)
        self._cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=bgc)
        self.body.pack(fill="both", expand=True, padx=px, pady=py)
        self.bind("<Configure>", self._rd)

    def _rd(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 8:
            return
        c = self._cv
        c.delete("all")
        r = self._r
        pts = [r+1, 1, w-r-1, 1, w-1, 1, w-1, r+1, w-1, h-r-1, w-1, h-1,
               w-r-1, h-1, r+1, h-1, 1, h-1, 1, h-r-1, 1, r+1, 1, 1]
        c.create_polygon(pts, smooth=True, fill=self._bg,
                          outline=self._bc, width=1)


class Btn(tk.Canvas):
    def __init__(self, m, text, cmd=None, w=180, h=42, bg=AC, fg="#04120e",
                 hov=AC2, bd=None, fnt=None, r=10, pbg=None):
        try:
            pb = pbg or m.cget("bg")
        except Exception:
            pb = ELEV
        super().__init__(m, width=w, height=h, bg=pb,
                          highlightthickness=0, cursor="hand2")
        self.w, self.h = w, h
        self.bg_c, self.fg_c, self.hov = bg, fg, hov
        self.bd, self.r = bd, r
        self.cmd, self.t = cmd, text
        self.fnt = fnt or F(13, "bold")
        self.en = True
        self._dr()
        self.bind("<Button-1>", self._cl)
        self.bind("<Enter>", lambda e: self._dr(True))
        self.bind("<Leave>", lambda e: self._dr(False))

    def _dr(self, hov=False):
        self.delete("all")
        c = self.hov if hov else self.bg_c
        if not self.en:
            c = "#1c2634"
        rr(self, 1, 1, self.w-1, self.h-1, self.r,
           fill=c, outline=self.bd or c)
        self.create_text(self.w/2, self.h/2-1, text=self.t,
                         fill=self.fg_c if self.en else MUT, font=self.fnt)

    def _cl(self, _):
        if self.en and self.cmd:
            self.cmd()

    def on(self, v):
        self.en = v
        self._dr()

    def txt(self, t):
        self.t = t
        self._dr()


class Ent(tk.Frame):
    def __init__(self, m, var=None, w=20, r=8, bgc=INP, bc=BR, **kw):
        try:
            pb = m.cget("bg")
        except Exception:
            pb = BG
        super().__init__(m, bg=pb, width=w, **kw)
        self._r, self._bg, self._bc = r, bgc, bc
        self._cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=pb)
        self._cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.entry = tk.Entry(self, bg=bgc, fg=TX, bd=0, relief="flat",
                               insertbackground=TX, font=F(11),
                               textvariable=var, highlightthickness=0)
        self.entry.pack(fill="both", expand=True, padx=12, pady=7)
        self.bind("<Configure>", self._rd)

    def _rd(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 8:
            return
        c = self._cv
        c.delete("all")
        r = self._r
        pts = [r+1, 1, w-r-1, 1, w-1, 1, w-1, r+1, w-1, h-r-1, w-1, h-1,
               w-r-1, h-1, r+1, h-1, 1, h-1, 1, h-r-1, 1, r+1, 1, 1]
        c.create_polygon(pts, smooth=True, fill=self._bg,
                          outline=self._bc, width=1)


class Chk(tk.Frame):
    def __init__(self, m, text="", var=None, cmd=None, **kw):
        bgc = kw.pop("bg", ELEV)
        super().__init__(m, bg=bgc, cursor="hand2", **kw)
        self.var = var or tk.BooleanVar()
        self.cmd = cmd
        self.sz = 20
        self._cv = tk.Canvas(self, width=self.sz, height=self.sz,
                              bg=bgc, highlightthickness=0, cursor="hand2")
        self._cv.pack(side="left", padx=(0, 10))
        self._lbl = tk.Label(self, text=text, bg=bgc, fg=TX,
                              font=F(11), cursor="hand2")
        self._lbl.pack(side="left")
        for w in (self, self._cv, self._lbl):
            w.bind("<Button-1>", self._tg)
        self._dr()

    def _dr(self):
        c = self._cv
        c.delete("all")
        s = self.sz
        r = 6
        on = self.var.get()
        f = AC if on else INP
        o = AC if on else BR
        pts = [r+1, 1, s-r-1, 1, s-1, 1, s-1, r+1, s-1, s-r-1, s-1, s-1,
               s-r-1, s-1, r+1, s-1, 1, s-1, 1, s-r-1, 1, r+1, 1, 1]
        c.create_polygon(pts, smooth=True, fill=f, outline=o, width=1)
        if on:
            c.create_line(s*0.25, s*0.5, s*0.45, s*0.7, s*0.75, s*0.3,
                          fill="#04120e", width=2,
                          capstyle="round", joinstyle="round")

    def _tg(self, _):
        self.var.set(not self.var.get())
        self._dr()
        if self.cmd:
            self.cmd()


class NavBtn(tk.Frame):
    def __init__(self, m, ic, txt, cmd):
        super().__init__(m, bg=SB, height=44, cursor="hand2")
        self.pack_propagate(False)
        self.cmd = cmd
        self._act = False
        self.ind = tk.Frame(self, bg=SB, width=3)
        self.ind.pack(side="left", fill="y")
        self.iw = tk.Frame(self, bg=SB, width=36, height=44)
        self.iw.pack(side="left")
        self.iw.pack_propagate(False)
        self.il = tk.Label(self.iw, text=ic, bg=SB, fg=DIM, font=F(15))
        self.il.place(relx=0.5, rely=0.5, anchor="center")
        self.tl = tk.Label(self, text=txt, bg=SB, fg=DIM,
                            font=F(12), anchor="w")
        self.tl.pack(side="left", fill="x", expand=True, padx=(4, 12))
        for w in (self, self.iw, self.il, self.tl, self.ind):
            w.bind("<Button-1>", lambda e: self.cmd())
            w.bind("<Enter>", self._on)
            w.bind("<Leave>", self._off)

    def _on(self, _):
        if not self._act:
            for w in (self, self.iw, self.il, self.tl, self.ind):
                w.configure(bg=ELEV)

    def _off(self, _):
        if not self._act:
            for w in (self, self.iw, self.il, self.tl, self.ind):
                w.configure(bg=SB)

    def act(self, v):
        self._act = v
        ws = (self, self.iw, self.il, self.tl, self.ind)
        if v:
            for w in ws:
                w.configure(bg=ACS)
            self.ind.configure(bg=AC)
            self.il.configure(fg=AC)
            self.tl.configure(fg=TX)
        else:
            for w in ws:
                w.configure(bg=SB)
            self.ind.configure(bg=SB)
            self.il.configure(fg=DIM)
            self.tl.configure(fg=DIM)


def toast(m, text, k="i"):
    t = tk.Toplevel(m)
    t.overrideredirect(True)
    t.attributes("-topmost", True)
    t.configure(bg=ELEV)
    icons = {"i": "i", "ok": "✓", "w": "!", "e": "✕"}
    cols = {"i": BL, "ok": AC, "w": YL, "e": RD}
    f = tk.Frame(t, bg=ELEV, highlightthickness=1, highlightbackground=cols[k])
    f.pack(fill="both", expand=True)
    tk.Label(f, text=icons[k], bg=ELEV, fg=cols[k], font=F(15, "bold")
             ).pack(side="left", padx=(14, 8), pady=12)
    tk.Label(f, text=text, bg=ELEV, fg=TX, font=F(11)
             ).pack(side="left", padx=(0, 18), pady=12)
    t.update_idletasks()
    w, h = f.winfo_reqwidth(), f.winfo_reqheight()
    try:
        x = m.winfo_rootx() + m.winfo_width() - w - 24
        y = m.winfo_rooty() + m.winfo_height() - h - 24
    except Exception:
        x = y = 100
    t.geometry(f"{w}x{h}+{x}+{y}")
    t.after(2800, t.destroy)


# ===================== СТРАНИЦЫ =====================
class Page(tk.Frame):
    def __init__(self, m, app):
        super().__init__(m, bg=BG)
        self.app = app

    def refresh(self):
        pass


class DashPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        hd = tk.Frame(self, bg=BG)
        hd.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hd, text="Главная", bg=BG, fg=TX,
                 font=F(22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hd, text="Состояние защиты", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))

        # Кнопки быстрого действия
        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=30, pady=(20, 0))
        Btn(btns, "⚡  Быстрая проверка", w=220, cmd=self._quick).pack(
            side="left", padx=(0, 10))
        Btn(btns, "📁  Сканировать папку", w=220, bg=ELEV, fg=DIM,
            hov=BR, bd=BR, cmd=self._folder).pack(side="left")

        # Карточки статистики
        s = tk.Frame(self, bg=BG)
        s.pack(fill="x", padx=30, pady=(20, 0))
        for i in range(4):
            s.grid_columnconfigure(i, weight=1, uniform="s")

        self.cards = {}
        info = [
            ("Σ", "SHA256", str(len(app.db.sha)), AC),
            ("μ", "MD5", str(len(app.db.md5)), BL),
            ("▣", "В карантине", str(self._qcount()), YL),
            ("⛨", "Автозагрузка", "Вкл" if Auto.enabled() else "Выкл", GR),
        ]
        for i, (ic, lb, val, col) in enumerate(info):
            c = Card(s, radius=14)
            c.grid(row=0, column=i, sticky="nsew",
                   padx=(0 if i == 0 else 6, 0 if i == 3 else 6))
            tk.Label(c.body, text=ic, bg=ELEV, fg=col, font=F(22)
                     ).pack(side="left", padx=(0, 10))
            col_f = tk.Frame(c.body, bg=ELEV)
            col_f.pack(side="left")
            vl = tk.Label(col_f, text=val, bg=ELEV, fg=TX,
                          font=F(20, "bold"), anchor="w")
            vl.pack(anchor="w")
            tk.Label(col_f, text=lb, bg=ELEV, fg=MUT,
                     font=F(10), anchor="w").pack(anchor="w")
            self.cards[lb] = vl

        # Журнал
        lg = Card(self, radius=14)
        lg.pack(fill="both", expand=True, padx=30, pady=(20, 30))
        tk.Label(lg.body, text="Последние события", bg=ELEV, fg=TX,
                 font=F(13, "bold"), anchor="w").pack(anchor="w", pady=(0, 8))
        self.ev = tk.Text(lg.body, bg=BG, fg=DIM, bd=0, font=F(10, m=True),
                          wrap="word", insertbackground=TX,
                          height=8, highlightthickness=0)
        self.ev.pack(fill="both", expand=True)
        self.ev.configure(state="disabled")
        self.log(f"[i] {APP} {VER} запущен")
        self.log(f"[i] Папка данных: {BASE}")

    def _qcount(self):
        try:
            return len([f for f in os.listdir(QUAR) if f.endswith(".q")])
        except Exception:
            return 0

    def log(self, t):
        def do():
            self.ev.configure(state="normal")
            self.ev.insert("end", t + "\n")
            self.ev.see("end")
            self.ev.configure(state="disabled")
        self.after(0, do)

    def refresh(self):
        self.cards["SHA256"].configure(text=str(len(self.app.db.sha)))
        self.cards["MD5"].configure(text=str(len(self.app.db.md5)))
        self.cards["В карантине"].configure(text=str(self._qcount()))
        self.cards["Автозагрузка"].configure(
            text="Вкл" if Auto.enabled() else "Выкл")

    def _quick(self):
        home = os.path.expanduser("~")
        ts = [os.path.join(home, n) for n in
              ("Downloads", "Documents", "Desktop")
              if os.path.isdir(os.path.join(home, n))] or [home]
        self.app.go("scan")
        self.app.pages["scan"].start(ts)

    def _folder(self):
        p = filedialog.askdirectory()
        if p:
            self.app.go("scan")
            self.app.pages["scan"].start([p])


class ScanPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        self.sc = None
        self.pv = 0

        hd = tk.Frame(self, bg=BG)
        hd.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hd, text="Сканирование", bg=BG, fg=TX,
                 font=F(22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hd, text="Проверьте файлы и папки на угрозы", bg=BG,
                 fg=DIM, font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))

        # Верхняя карточка
        top = Card(self, radius=14)
        top.pack(fill="x", padx=30, pady=(16, 0))
        self.st = tk.Label(top.body, text="Готов к работе", bg=ELEV, fg=TX,
                            font=F(14, "bold"), anchor="w")
        self.st.pack(anchor="w")
        self.cur = tk.Label(top.body, text="", bg=ELEV, fg=MUT,
                             font=F(10), anchor="w", wraplength=800)
        self.cur.pack(anchor="w", pady=(4, 12))
        self.pb = tk.Canvas(top.body, height=8, bg=ELEV, highlightthickness=0)
        self.pb.pack(fill="x")
        self.pb.bind("<Configure>", lambda e: self._draw_pb())
        self.cnt = tk.Label(top.body, text="", bg=ELEV, fg=DIM,
                             font=F(10), anchor="w")
        self.cnt.pack(anchor="w", pady=(8, 0))

        # Кнопки
        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=30, pady=(14, 0))
        Btn(btns, "📁  Папка", w=140, cmd=self._pf).pack(side="left", padx=(0, 10))
        Btn(btns, "📄  Файл", w=140, bg=ELEV, fg=DIM, hov=BR, bd=BR,
            cmd=self._pfile).pack(side="left", padx=(0, 10))
        self.stb = Btn(btns, "⏹  Стоп", w=120, bg=ELEV, fg=MUT,
                       hov=BR, bd=BR, cmd=self._stop)
        self.stb.pack(side="left")
        self.stb.on(False)

        # Лог
        lg = Card(self, radius=14)
        lg.pack(fill="both", expand=True, padx=30, pady=(14, 30))
        tk.Label(lg.body, text="Журнал", bg=ELEV, fg=TX,
                 font=F(12, "bold"), anchor="w").pack(anchor="w", pady=(0, 8))
        self.lg = tk.Text(lg.body, bg=BG, fg=DIM, bd=0, font=F(10, m=True),
                          wrap="word", insertbackground=TX,
                          highlightthickness=0)
        self.lg.pack(fill="both", expand=True)
        self.lg.tag_config("ok", foreground=AC)
        self.lg.tag_config("err", foreground=RD)
        self.lg.tag_config("warn", foreground=YL)

    def _draw_pb(self):
        self.pb.delete("all")
        w = self.pb.winfo_width()
        h = self.pb.winfo_height()
        if w < 4:
            return
        rr(self.pb, 0, 0, w, h, 4, fill=BG, outline=BG)
        if self.pv > 0:
            rr(self.pb, 0, 0, max(8, int(w * self.pv)), h, 4,
               fill=AC, outline=AC)

    def _pf(self):
        p = filedialog.askdirectory()
        if p:
            self.start([p])

    def _pfile(self):
        p = filedialog.askopenfilename()
        if p:
            self.start([p])

    def _stop(self):
        if self.sc:
            self.sc.halt()

    def _log(self, t, tag=None):
        def do():
            self.lg.insert("end", t + "\n", tag or "")
            self.lg.see("end")
        self.after(0, do)

    def start(self, paths):
        if self.sc and not self.sc.stop.is_set():
            self._log("Уже сканируется", "warn")
            return

        self.lg.delete("1.0", "end")
        self.pv = 0
        self._draw_pb()
        self.cnt.configure(text="")
        self.st.configure(text="Сканирование...", fg=TX)
        self.stb.on(True)
        self._log(f"=== Запуск: {paths} ===")

        def of(fp):
            short = fp if len(fp) < 90 else "..." + fp[-87:]
            self._log(f"  → {short}")

        def ot(fp, k, h):
            self._log(f"  ⚠ УГРОЗА ({k}): {fp}", "err")

        def op(p):
            def do():
                self.pv = p["done"] / p["total"] if p["total"] else 0
                self._draw_pb()
                self.cnt.configure(text=(
                    f"{p['done']}/{p['total']}   "
                    f"{p['speed']:.0f} ф/с"))
            self.after(0, do)

        def od(s, total):
            def do():
                self.pv = 1.0
                self._draw_pb()
                self.st.configure(
                    text=f"Готово · Угроз: {s['th']}",
                    fg=RD if s["th"] else AC)
                self._log("=== ИТОГО ===")
                self._log(f"Всего: {total}")
                self._log(f"Проверено: {s['sc']}")
                self._log(f"Из кэша: {s['cache']}")
                self._log(f"Угроз: {s['th']}",
                          "err" if s["th"] else "ok")
                self._log(f"Эвристика: {s['heur']}")
                self._log(f"Пропущено: {s['sk']}")
                self._log(f"Ошибок: {s['er']}")
                self.stb.on(False)
                self.app.refresh_side()
                self.app.pages["dashboard"].refresh()
                self.app.pages["dashboard"].log(
                    f"[✓] Скан: {s['sc']} файлов, {s['th']} угроз")
                toast(self.app,
                      f"Угроз: {s['th']}" if s["th"] else "Чисто",
                      "e" if s["th"] else "ok")
            self.after(0, do)

        self.sc = Scan(self.app.db, self.app.cfg, of, ot, od, op)
        threading.Thread(target=self.sc.run, args=(paths,), daemon=True).start()


class MemPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        self.procs = []
        self.sel = set()
        self.rows = {}

        hd = tk.Frame(self, bg=BG)
        hd.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hd, text="Очистка памяти", bg=BG, fg=TX,
                 font=F(22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hd, text="Выберите процессы для завершения", bg=BG,
                 fg=DIM, font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))

        # RAM
        mc = Card(self, radius=14)
        mc.pack(fill="x", padx=30, pady=(16, 0))
        mi = mc.body
        tk.Label(mi, text="▦", bg=ELEV, fg=AC, font=F(32, "bold")
                 ).pack(side="left", padx=(0, 20))
        mid = tk.Frame(mi, bg=ELEV)
        mid.pack(side="left", fill="both", expand=True)
        self.mt = tk.Label(mid, text="Загрузка...", bg=ELEV, fg=TX,
                            font=F(20, "bold"), anchor="w")
        self.mt.pack(anchor="w")
        self.ms = tk.Label(mid, text="", bg=ELEV, fg=DIM,
                            font=F(11), anchor="w")
        self.ms.pack(anchor="w", pady=(2, 10))
        self.mb = tk.Canvas(mid, height=10, bg=ELEV, highlightthickness=0)
        self.mb.pack(fill="x")
        self.mb.bind("<Configure>", lambda e: self._draw_mem())
        self.mp = 0.0
        self.mc_ = AC

        Btn(mi, "↻  Обновить", w=160, bg=ELEV, fg=DIM, hov=BR, bd=BR,
            cmd=self._load).pack(side="right", padx=(20, 0))

        # Управление
        b = tk.Frame(self, bg=BG)
        b.pack(fill="x", padx=30, pady=(14, 8))
        tk.Label(b, text="Поиск:", bg=BG, fg=DIM, font=F(11)).pack(side="left")
        self.sv = tk.StringVar()
        self.sv.trace_add("write", lambda *a: self._rend())
        Ent(b, var=self.sv, w=28).pack(side="left", padx=(8, 20))
        Btn(b, "Выбрать все", w=140, h=34, r=8, bg=ELEV, fg=DIM,
            hov=BR, bd=BR, fnt=F(11), cmd=self._all).pack(side="left", padx=(0, 8))
        Btn(b, "Снять", w=120, h=34, r=8, bg=ELEV, fg=DIM,
            hov=BR, bd=BR, fnt=F(11), cmd=self._none).pack(side="left", padx=(0, 8))
        Btn(b, ">100 МБ", w=120, h=34, r=8, bg=ELEV, fg=DIM,
            hov=BR, bd=BR, fnt=F(11), cmd=self._big).pack(side="left")

        # Список
        lc = Card(self, radius=14, px=10, py=10)
        lc.pack(fill="both", expand=True, padx=30, pady=(8, 0))
        self.cv = tk.Canvas(lc.body, bg=ELEV, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lc.body, command=self.cv.yview)
        sb.pack(side="right", fill="y")
        self.cv.configure(yscrollcommand=sb.set)
        self.lf = tk.Frame(self.cv, bg=ELEV)
        self.cv.create_window((0, 0), window=self.lf, anchor="nw")
        self.lf.bind("<Configure>",
                     lambda e: self.cv.configure(
                         scrollregion=self.cv.bbox("all")))

        bot = tk.Frame(self, bg=BG)
        bot.pack(fill="x", padx=30, pady=(10, 26))
        self.sl = tk.Label(bot, text="Выбрано: 0", bg=BG, fg=DIM,
                            font=F(11), anchor="w")
        self.sl.pack(side="left")
        Btn(bot, "✕  Завершить выбранные", w=240, h=42, bg=RD, fg="#fff",
            hov="#e04b43", cmd=self._kill).pack(side="right")

        self.after(300, self._load)

    def _draw_mem(self):
        self.mb.delete("all")
        w = self.mb.winfo_width()
        h = self.mb.winfo_height()
        if w < 4:
            return
        rr(self.mb, 0, 0, w, h, 5, fill=ELEV, outline=ELEV)
        if self.mp > 0:
            rr(self.mb, 0, 0, max(10, int(w * self.mp)), h, 5,
               fill=self.mc_, outline=self.mc_)

    def _load(self):
        def w():
            info = mem_info()
            pr = list_procs()
            self.after(0, lambda: self._done(info, pr))
        threading.Thread(target=w, daemon=True).start()

    def _done(self, info, pr):
        if info:
            pct = info["pct"] / 100.0
            self.mp = pct
            self.mc_ = RD if pct >= 0.85 else (YL if pct >= 0.65 else AC)
            self.mt.configure(
                text=f"{hs(info['used'])} / {hs(info['total'])}   "
                     f"({info['pct']}%)")
            self.ms.configure(text=f"Свободно: {hs(info['free'])}")
            self._draw_mem()
        self.procs = pr
        self.sel.clear()
        self._rend()

    def _rend(self):
        for w in self.lf.winfo_children():
            w.destroy()
        self.rows.clear()
        if not self.procs:
            tk.Label(self.lf, text="Нет данных", bg=ELEV, fg=MUT,
                     font=F(12)).pack(pady=40)
            return
        q = (self.sv.get() or "").lower().strip()
        for p in self.procs[:300]:
            if q and q not in p["name"].lower() and q not in str(p["pid"]):
                continue
            pid, n, mem = p["pid"], p["name"], p["mem"]
            pr = is_prot(n)
            row = tk.Frame(self.lf, bg=ELEV)
            row.pack(fill="x", pady=1, padx=2)
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(row, variable=var, bg=ELEV, activebackground=ELEV,
                            selectcolor=ELEV, highlightthickness=0, bd=0,
                            state=("disabled" if pr else "normal"),
                            command=lambda pp=pid: self._chk(pp)
                            ).pack(side="left", padx=(4, 0))
            tk.Label(row, text=n, bg=ELEV, fg=MUT if pr else TX,
                     font=F(11), anchor="w", width=38
                     ).pack(side="left", padx=(4, 0), pady=6)
            if pr:
                tk.Label(row, text="система", bg=ELEV, fg=YL,
                         font=F(9)).pack(side="left", padx=(6, 0))
            tk.Label(row, text=str(pid), bg=ELEV, fg=DIM,
                     font=F(10, m=True), width=10, anchor="w"
                     ).pack(side="left")
            c = RD if mem > 300*1024*1024 else (
                YL if mem > 100*1024*1024 else DIM)
            tk.Label(row, text=hs(mem) if mem else "—", bg=ELEV, fg=c,
                     font=F(10, m=True), width=14, anchor="e"
                     ).pack(side="right", padx=(0, 12))
            self.rows[pid] = {"v": var, "p": pr, "m": mem}

    def _chk(self, pid):
        e = self.rows.get(pid)
        if not e:
            return
        if e["v"].get():
            self.sel.add(pid)
        else:
            self.sel.discard(pid)
        self._usel()

    def _usel(self):
        n = len(self.sel)
        if n:
            freed = sum(self.rows[p]["m"] for p in self.sel if p in self.rows)
            self.sl.configure(text=f"Выбрано: {n}   ~{hs(freed)}", fg=AC)
        else:
            self.sl.configure(text="Выбрано: 0", fg=DIM)

    def _all(self):
        for pid, e in self.rows.items():
            if e["p"]:
                continue
            e["v"].set(True)
            self.sel.add(pid)
        self._usel()

    def _none(self):
        for e in self.rows.values():
            e["v"].set(False)
        self.sel.clear()
        self._usel()

    def _big(self):
        self.sel.clear()
        for pid, e in self.rows.items():
            e["v"].set(False)
            if not e["p"] and e["m"] > 100 * 1024 * 1024:
                e["v"].set(True)
                self.sel.add(pid)
        self._usel()

    def _kill(self):
        if not self.sel:
            toast(self.app, "Ничего не выбрано", "i")
            return
        if not messagebox.askyesno(
                "Завершить",
                f"Завершить {len(self.sel)} процессов?\n\n"
                f"Несохранённые данные будут потеряны."):
            return
        k = 0
        freed = 0
        for pid in list(self.sel):
            e = self.rows.get(pid)
            if not e or e["p"]:
                continue
            if kill_proc(pid):
                k += 1
                freed += e["m"]
        toast(self.app, f"Завершено: {k}   ~{hs(freed)}",
              "ok" if k else "e")
        self.app.pages["dashboard"].log(
            f"[i] Память: завершено {k}, ~{hs(freed)}")
        self.after(500, self._load)


class DiskPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        self.tg = {}
        self.ch = {}
        self.bv = 0.0

        hd = tk.Frame(self, bg=BG)
        hd.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hd, text="Очистка диска", bg=BG, fg=TX,
                 font=F(22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hd, text="Освободите место на SSD/HDD", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))

        self.dh = tk.Frame(self, bg=BG)
        self.dh.pack(fill="x", padx=30, pady=(16, 0))

        self.cc = Card(self, radius=14)
        self.cc.pack(fill="both", expand=True, padx=30, pady=(10, 0))
        tk.Label(self.cc.body, text="Что чистить", bg=ELEV, fg=TX,
                 font=F(13, "bold"), anchor="w").pack(anchor="w", pady=(0, 8))
        self.cat_holder = tk.Frame(self.cc.body, bg=ELEV)
        self.cat_holder.pack(fill="both", expand=True)

        self.pl = tk.Label(self, bg=BG, fg=DIM, font=F(10), anchor="w")
        self.pl.pack(fill="x", padx=30, pady=(6, 0))
        self.br = tk.Canvas(self, height=10, bg=BG, highlightthickness=0)
        self.br.pack(fill="x", padx=30, pady=(4, 0))
        self.br.bind("<Configure>", lambda e: self._db())

        bot = tk.Frame(self, bg=BG)
        bot.pack(fill="x", padx=30, pady=(14, 26))
        self.fl = tk.Label(bot, text="Освобождено: —", bg=BG, fg=DIM,
                            font=F(11), anchor="w")
        self.fl.pack(side="left")
        Btn(bot, "Очистить выбранное", w=200, h=42,
            cmd=self._clr).pack(side="right", padx=(0, 8))
        Btn(bot, "Все безопасные", w=180, h=42, bg=ELEV, fg=DIM,
            hov=BR, bd=BR, cmd=self._all).pack(side="right")

        self.after(300, self.refresh)

    def _db(self):
        self.br.delete("all")
        w = self.br.winfo_width()
        h = self.br.winfo_height()
        if w < 4:
            return
        rr(self.br, 0, 0, w, h, 5, fill=BG, outline=BG)
        if self.bv > 0:
            rr(self.br, 0, 0, max(10, int(w * self.bv)), h, 5,
               fill=AC, outline=AC)

    def refresh(self):
        for w in self.dh.winfo_children():
            w.destroy()
        for w in self.cat_holder.winfo_children():
            w.destroy()
        # Диски
        for d in list_drives():
            c = Card(self.dh, radius=12, py=10)
            c.pack(fill="x", pady=4)
            tk.Label(c.body, text="▦", bg=ELEV, fg=AC, font=F(20, "bold")
                     ).pack(side="left", padx=(0, 14))
            col = tk.Frame(c.body, bg=ELEV)
            col.pack(side="left", fill="both", expand=True)
            pct = d["p"]
            cl = RD if pct >= 85 else (YL if pct >= 65 else AC)
            tk.Label(col, text=d["m"], bg=ELEV, fg=TX,
                     font=F(13, "bold"), anchor="w").pack(anchor="w")
            tk.Label(col, text=f"{hs(d['u'])} / {hs(d['t'])}   "
                               f"Свободно: {hs(d['f'])}",
                     bg=ELEV, fg=DIM, font=F(10), anchor="w"
                     ).pack(anchor="w", pady=(2, 6))
            bar = tk.Canvas(col, height=8, bg=ELEV, highlightthickness=0)
            bar.pack(fill="x")

            def dbr(b=bar, cc=cl, pp=pct):
                b.delete("all")
                w, h = b.winfo_width(), b.winfo_height()
                if w < 4:
                    return
                rr(b, 0, 0, w, h, 4, fill=BG, outline=BG)
                if pp > 0:
                    rr(b, 0, 0, max(8, int(w * pp / 100)), h, 4,
                       fill=cc, outline=cc)
            bar.bind("<Configure>", lambda e, db=dbr: db())
            tk.Label(c.body, text=f"{pct:.0f}%", bg=ELEV, fg=cl,
                     font=F(14, "bold"), width=6).pack(side="right")

        # Категории
        self.tg = clean_targets()
        self.ch = {}
        for k, t in self.tg.items():
            if not t.get("p") or not os.path.isdir(t["p"]):
                continue
            r = tk.Frame(self.cat_holder, bg=ELEV)
            r.pack(fill="x", pady=2)
            v = tk.BooleanVar(value=True)
            self.ch[k] = {"v": v, "p": t["p"], "n": t["n"]}
            Chk(r, text=t["n"], var=v, bg=ELEV).pack(side="left")
            try:
                sz = dir_size(t["p"])
                tk.Label(r, text=hs(sz), bg=ELEV, fg=AC,
                         font=F(10, "bold")).pack(side="right")
            except Exception:
                pass

    def _all(self):
        s = list(self.ch.keys())
        if not s:
            toast(self.app, "Нечего чистить", "i")
            return
        if not messagebox.askyesno(
                "Очистка", f"Очистить всё ({len(s)} категорий)?"):
            return
        self._run(s)

    def _clr(self):
        s = [k for k, v in self.ch.items() if v["v"].get()]
        if not s:
            toast(self.app, "Ничего не выбрано", "i")
            return
        if not messagebox.askyesno("Очистка", f"Очистить {len(s)} категорий?"):
            return
        self._run(s)

    def _run(self, keys):
        self.fl.configure(text="Очистка...", fg=DIM)

        def w():
            total = 0
            for i, k in enumerate(keys):
                v = self.ch.get(k)
                if not v:
                    continue
                self.after(0, lambda pp=(i+1)/len(keys): self._setp(pp))
                self.after(0, lambda nn=v["n"], ii=i: self.pl.configure(
                    text=f"[{ii+1}/{len(keys)}] {nn}..."))
                f, _ = clean_dir(v["p"])
                total += f

            def d():
                self.bv = 1.0
                self._db()
                self.fl.configure(text=f"Освобождено: {hs(total)}", fg=AC)
                self.pl.configure(text="Готово", fg=AC)
                toast(self.app, f"Освобождено: {hs(total)}", "ok")
                self.after(500, self.refresh)
            self.after(0, d)
        threading.Thread(target=w, daemon=True).start()

    def _setp(self, v):
        self.bv = v
        self._db()


class QuarPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        hd = tk.Frame(self, bg=BG)
        hd.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hd, text="Карантин", bg=BG, fg=TX,
                 font=F(22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hd, text="Изолированные файлы", bg=BG, fg=DIM,
                 font=F(11), anchor="w").pack(anchor="w", pady=(2, 0))

        w = tk.Frame(self, bg=BG)
        w.pack(fill="both", expand=True, padx=30, pady=(16, 0))
        self.cv = tk.Canvas(w, bg=BG, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(w, command=self.cv.yview)
        sb.pack(side="right", fill="y")
        self.cv.configure(yscrollcommand=sb.set)
        self.lf = tk.Frame(self.cv, bg=BG)
        self.cv.create_window((0, 0), window=self.lf, anchor="nw")
        self.lf.bind("<Configure>",
                     lambda e: self.cv.configure(
                         scrollregion=self.cv.bbox("all")))

        Btn(self, "↻  Обновить", w=160, bg=ELEV, fg=DIM, hov=BR, bd=BR,
            cmd=self.refresh).pack(anchor="e", padx=30, pady=(10, 26))

    def refresh(self):
        for w in self.lf.winfo_children():
            w.destroy()
        if not os.path.isdir(QUAR):
            tk.Label(self.lf, text="Пусто", bg=BG, fg=MUT,
                     font=F(12)).pack(pady=40)
            return
        its = sorted([f for f in os.listdir(QUAR) if f.endswith(".q")],
                     reverse=True)
        if not its:
            tk.Label(self.lf, text="Пусто", bg=BG, fg=MUT,
                     font=F(12)).pack(pady=40)
            return
        for n in its:
            f = os.path.join(QUAR, n)
            meta = lj(f + ".json", {})
            c = Card(self.lf, radius=12, py=10)
            c.pack(fill="x", pady=4)
            tk.Label(c.body, text=os.path.basename(meta.get("orig", n)),
                     bg=ELEV, fg=TX, font=F(12, "bold"), anchor="w"
                     ).pack(anchor="w")
            tk.Label(c.body, text=meta.get("orig", ""), bg=ELEV, fg=DIM,
                     font=F(9, m=True), anchor="w").pack(anchor="w")
            r = tk.Frame(c.body, bg=ELEV)
            r.pack(fill="x", pady=(4, 0))
            tk.Label(r, text=f"{meta.get('r', '?')}   {hs(meta.get('s', 0))}",
                     bg=ELEV, fg=YL, font=F(9)).pack(side="left")
            Btn(r, "↩", w=36, h=26, r=6, bg=ELEV, fg=AC, hov=ACS, bd=BR,
                fnt=F(11), cmd=lambda f=f, m=meta: self._rest(f, m)
                ).pack(side="right", padx=2)
            Btn(r, "✕", w=36, h=26, r=6, bg=ELEV, fg=RD, hov=ACS, bd=BR,
                fnt=F(11), cmd=lambda f=f: self._del(f)
                ).pack(side="right", padx=2)

    def _rest(self, f, m):
        o = m.get("orig")
        if not o or not messagebox.askyesno(
                "Восстановить", f"Восстановить в:\n{o}?"):
            return
        try:
            os.makedirs(os.path.dirname(o), exist_ok=True)
            shutil.move(f, o)
            if os.path.exists(f + ".json"):
                os.remove(f + ".json")
            toast(self.app, "Восстановлено", "w")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _del(self, f):
        if not messagebox.askyesno("Удалить", "Навсегда?"):
            return
        try:
            os.remove(f)
            if os.path.exists(f + ".json"):
                os.remove(f + ".json")
            toast(self.app, "Удалено", "ok")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


class UpdPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        hd = tk.Frame(self, bg=BG)
        hd.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hd, text="Обновления", bg=BG, fg=TX,
                 font=F(22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hd, text="Загрузка сигнатур из интернета",
                 bg=BG, fg=DIM, font=F(11), anchor="w"
                 ).pack(anchor="w", pady=(2, 0))

        c = Card(self, radius=14)
        c.pack(fill="x", padx=30, pady=(16, 0))
        self.t = tk.Label(c.body, text="", bg=ELEV, fg=TX,
                           font=F(14, "bold"), anchor="w")
        self.t.pack(anchor="w")
        self.s = tk.Label(c.body, text="", bg=ELEV, fg=DIM,
                           font=F(11), anchor="w")
        self.s.pack(anchor="w", pady=(2, 10))
        self.b = Btn(c.body, "⬇  Обновить сейчас", w=220, cmd=self._go)
        self.b.pack(anchor="w")

        lg = Card(self, radius=14)
        lg.pack(fill="both", expand=True, padx=30, pady=(14, 30))
        tk.Label(lg.body, text="Лог", bg=ELEV, fg=TX,
                 font=F(12, "bold"), anchor="w").pack(anchor="w", pady=(0, 8))
        self.l = tk.Text(lg.body, bg=BG, fg=DIM, bd=0, font=F(10, m=True),
                          wrap="word", insertbackground=TX,
                          highlightthickness=0)
        self.l.pack(fill="both", expand=True)

    def refresh(self):
        db = self.app.db
        self.t.configure(
            text=f"SHA256: {len(db.sha):,}   ·   MD5: {len(db.md5):,}")
        self.s.configure(text=f"Обновлено: {db.upd or 'никогда'}")

    def _go(self):
        self.b.on(False)
        self.b.txt("Загрузка...")
        self.l.delete("1.0", "end")

        def w():
            def lg(m):
                self.after(0, lambda: (self.l.insert("end", m + "\n"),
                                        self.l.see("end")))
            try:
                update_signatures(self.app.cfg, lg)
                self.app.db = DB()
                self.after(0, self.app.refresh_side)
                self.after(0, self.refresh)
                self.after(0, self.app.pages["dashboard"].refresh)
                self.after(0, lambda: (self.b.on(True),
                                        self.b.txt("⬇  Обновить сейчас")))
                self.after(0, lambda: toast(self.app, "База обновлена", "ok"))
            except Exception as e:
                lg(f"! {e}")
                self.after(0, lambda: (self.b.on(True),
                                        self.b.txt("⬇  Обновить сейчас")))
        threading.Thread(target=w, daemon=True).start()


class SetPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app)
        hd = tk.Frame(self, bg=BG)
        hd.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hd, text="Настройки", bg=BG, fg=TX,
                 font=F(22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hd, text="Автозапуск, сканирование, источники",
                 bg=BG, fg=DIM, font=F(11), anchor="w"
                 ).pack(anchor="w", pady=(2, 0))

        w = tk.Frame(self, bg=BG)
        w.pack(fill="both", expand=True, padx=30, pady=(16, 20))
        cv = tk.Canvas(w, bg=BG, highlightthickness=0)
        cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(w, command=cv.yview)
        sb.pack(side="right", fill="y")
        cv.configure(yscrollcommand=sb.set)
        body = tk.Frame(cv, bg=BG)
        cv.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
                  lambda e: cv.configure(scrollregion=cv.bbox("all")))

        # Система
        s1 = Card(body, radius=14)
        s1.pack(fill="x", pady=(0, 10))
        tk.Label(s1.body, text="Система", bg=ELEV, fg=TX,
                 font=F(13, "bold"), anchor="w").pack(anchor="w", pady=(0, 8))
        self.v_auto = tk.BooleanVar(value=bool(app.cfg.get("autostart", False)))
        Chk(s1.body, "Запускать при входе в систему", var=self.v_auto,
            cmd=self._tga).pack(anchor="w", pady=3)
        self.v_close = tk.BooleanVar(
            value=bool(app.cfg.get("close_to_tray", True)))
        Chk(s1.body, "Сворачивать в трей при закрытии",
            var=self.v_close).pack(anchor="w", pady=3)
        self.v_min = tk.BooleanVar(
            value=bool(app.cfg.get("start_minimized", False)))
        Chk(s1.body, "Запускать свёрнутым", var=self.v_min).pack(
            anchor="w", pady=3)

        # Сканирование
        s2 = Card(body, radius=14)
        s2.pack(fill="x", pady=(0, 10))
        tk.Label(s2.body, text="Сканирование", bg=ELEV, fg=TX,
                 font=F(13, "bold"), anchor="w").pack(anchor="w", pady=(0, 8))
        self.v_skip = tk.BooleanVar(
            value=bool(app.cfg.get("skip_system_dirs", False)))
        Chk(s2.body, "Пропускать системные папки",
            var=self.v_skip).pack(anchor="w", pady=3)
        self.v_heur = tk.BooleanVar(
            value=bool(app.cfg.get("heuristics", True)))
        Chk(s2.body, "Эвристика (подозрительные паттерны)",
            var=self.v_heur).pack(anchor="w", pady=3)
        tk.Label(s2.body, text=f"Потоков сканирования (ядер: "
                               f"{os.cpu_count() or 1})",
                 bg=ELEV, fg=DIM, font=F(11), anchor="w"
                 ).pack(anchor="w", pady=(8, 4))
        self.v_th = tk.StringVar(value=str(app.cfg.get("scan_threads", 4)))
        Ent(s2.body, var=self.v_th, w=10).pack(anchor="w", pady=(0, 8))

        tk.Label(s2.body, text="Расширения (пусто = все)",
                 bg=ELEV, fg=DIM, font=F(11), anchor="w"
                 ).pack(anchor="w", pady=(8, 4))
        self.ext_box = tk.Text(s2.body, bg=INP, fg=TX, bd=0, height=3,
                                font=F(10, m=True), wrap="word",
                                highlightthickness=1,
                                highlightbackground=BR,
                                insertbackground=TX)
        self.ext_box.pack(fill="x")
        self.ext_box.insert("1.0", ", ".join(
            app.cfg.get("extensions_scan", [])))

        # Источники
        s3 = Card(body, radius=14)
        s3.pack(fill="x", pady=(0, 10))
        tk.Label(s3.body, text="Источники сигнатур (URL по одному в строке)",
                 bg=ELEV, fg=TX, font=F(13, "bold"), anchor="w"
                 ).pack(anchor="w", pady=(0, 8))
        self.src_box = tk.Text(s3.body, bg=INP, fg=TX, bd=0, height=7,
                                font=F(10, m=True), wrap="none",
                                highlightthickness=1,
                                highlightbackground=BR,
                                insertbackground=TX)
        self.src_box.pack(fill="x")
        self.src_box.insert("1.0", "\n".join(app.cfg.get("sources", [])))

        # Кнопки
        act = tk.Frame(body, bg=BG)
        act.pack(fill="x", pady=(20, 10))
        Btn(act, "💾  Сохранить", w=180, cmd=self._save).pack(
            side="left", padx=(0, 10))
        Btn(act, "↻  Сбросить", w=160, bg=ELEV, fg=DIM, hov=BR, bd=BR,
            cmd=self.refresh).pack(side="left")

    def _tga(self):
        w = bool(self.v_auto.get())
        if w and not Auto.enabled():
            ok, msg = Auto.enable()
            toast(self.app, msg, "ok" if ok else "e")
            if not ok:
                self.v_auto.set(False)
        elif not w and Auto.enabled():
            Auto.disable()
        self.app.cfg["autostart"] = Auto.enabled()
        sj(CFG, self.app.cfg)

    def refresh(self):
        self.v_auto.set(Auto.enabled())
        self.v_close.set(bool(self.app.cfg.get("close_to_tray", True)))
        self.v_min.set(bool(self.app.cfg.get("start_minimized", False)))
        self.v_skip.set(bool(self.app.cfg.get("skip_system_dirs", False)))
        self.v_heur.set(bool(self.app.cfg.get("heuristics", True)))
        self.v_th.set(str(self.app.cfg.get("scan_threads", 4)))
        self.ext_box.delete("1.0", "end")
        self.ext_box.insert("1.0", ", ".join(
            self.app.cfg.get("extensions_scan", [])))
        self.src_box.delete("1.0", "end")
        self.src_box.insert("1.0", "\n".join(
            self.app.cfg.get("sources", [])))

    def _save(self):
        try:
            th = max(1, min(32, int(self.v_th.get())))
        except ValueError:
            messagebox.showerror("Ошибка", "Числовое поле неверно")
            return
        self.app.cfg["autostart"] = Auto.enabled()
        self.app.cfg["close_to_tray"] = bool(self.v_close.get())
        self.app.cfg["start_minimized"] = bool(self.v_min.get())
        self.app.cfg["skip_system_dirs"] = bool(self.v_skip.get())
        self.app.cfg["heuristics"] = bool(self.v_heur.get())
        self.app.cfg["scan_threads"] = th
        self.app.cfg["extensions_scan"] = [
            e.strip() for e in self.ext_box.get("1.0", "end").split(",")
            if e.strip()]
        self.app.cfg["sources"] = [
            s.strip() for s in self.src_box.get("1.0", "end").splitlines()
            if s.strip()]
        if sj(CFG, self.app.cfg):
            toast(self.app, "Сохранено", "ok")
        else:
            toast(self.app, "Ошибка сохранения", "e")


# ===================== APP =====================
class App(tk.Tk):
    def __init__(self, cfg, db):
        super().__init__()
        self.cfg = cfg
        self.db = db
        self.tray = None
        self.tq = queue.Queue()
        self._q = False

        self.title(f"{APP} {VER}")
        self.geometry("1200x760")
        self.minsize(1040, 660)
        self.configure(bg=BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._side()
        self._content()
        self.go("dashboard")
        self._tray_setup()

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(500, self._autoupd)
        self.after(2000, self._tpoll)
        self.after(200, lambda: round_win(self))

    def _tray_setup(self):
        if not WIN:
            return
        self.tray = Tray(f"{APP} {VER}",
                          on_l=lambda: self.tq.put("t"),
                          on_r=lambda: self.tq.put("m"))
        self.tray.start()

    def _tpoll(self):
        try:
            while True:
                a = self.tq.get_nowait()
                if a == "t":
                    self.toggle()
                elif a == "m":
                    self._menu()
        except queue.Empty:
            pass
        self.after(2000, self._tpoll)

    def _menu(self):
        m = tk.Menu(self, tearoff=0, bg=ELEV, fg=TX,
                    activebackground=ACS, activeforeground=TX,
                    bd=0, font=F(11))
        m.add_command(label="Открыть", command=self.toggle)
        m.add_command(label="Сканировать папку",
                      command=lambda: (self.toggle(),
                                       self.after(150, self._quick)))
        m.add_command(label="Память",
                      command=lambda: (self.toggle(),
                                       self.after(150,
                                                  lambda: self.go("memory"))))
        m.add_command(label="Диск",
                      command=lambda: (self.toggle(),
                                       self.after(150,
                                                  lambda: self.go("disk"))))
        m.add_separator()
        m.add_command(label="Выход", command=self.quit_app)
        try:
            m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            m.grab_release()

    def _quick(self):
        self.pages["dashboard"]._quick()

    def toggle(self):
        try:
            if self.state() == "withdrawn" or not self.winfo_viewable():
                self.deiconify()
                self.lift()
                self.focus_force()
            else:
                self.withdraw()
        except Exception:
            pass

    def _close(self):
        if self.cfg.get("close_to_tray", True) and WIN and self.tray:
            self.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        if self._q:
            return
        self._q = True
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _side(self):
        sb = tk.Frame(self, bg=SB, width=240)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.pack_propagate(False)
        lg = tk.Frame(sb, bg=SB)
        lg.pack(fill="x", padx=20, pady=(22, 26))
        tk.Label(lg, text="⛨", bg=SB, fg=AC, font=F(18)).pack(side="left")
        tk.Label(lg, text="Unlock", bg=SB, fg=TX, font=F(15, "bold")
                 ).pack(side="left", padx=(6, 0))
        tk.Label(lg, text="Antivirus", bg=SB, fg=AC, font=F(15, "bold")
                 ).pack(side="left")

        self.navs = {}
        items = [("dashboard", "⌂", "Главная"),
                 ("scan", "⌕", "Сканирование"),
                 ("memory", "▦", "Память"),
                 ("disk", "⛁", "Диск"),
                 ("quarantine", "▣", "Карантин"),
                 ("updates", "↓", "Обновления"),
                 ("settings", "⚙", "Настройки")]
        for k, ic, t in items:
            b = NavBtn(sb, ic, t, cmd=lambda kk=k: self.go(kk))
            b.pack(fill="x", padx=12, pady=2)
            self.navs[k] = b

        bot = tk.Frame(sb, bg=SB)
        bot.pack(side="bottom", fill="x", padx=20, pady=20)
        tk.Frame(bot, bg=BR, height=1).pack(fill="x", pady=(0, 14))
        self.ss = tk.Label(bot, text="", bg=SB, fg=MUT, font=F(9),
                            anchor="w", justify="left")
        self.ss.pack(fill="x")
        self.refresh_side()

    def _content(self):
        self.cont = tk.Frame(self, bg=BG)
        self.cont.grid(row=0, column=1, sticky="nsew")
        self.cont.grid_rowconfigure(0, weight=1)
        self.cont.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for k, cls in [("dashboard", DashPage), ("scan", ScanPage),
                       ("memory", MemPage), ("disk", DiskPage),
                       ("quarantine", QuarPage), ("updates", UpdPage),
                       ("settings", SetPage)]:
            p = cls(self.cont, self)
            p.grid(row=0, column=0, sticky="nsew")
            self.pages[k] = p

    def go(self, k):
        self.pages[k].tkraise()
        for kk, b in self.navs.items():
            b.act(kk == k)
        if hasattr(self.pages[k], "refresh"):
            self.pages[k].refresh()

    def refresh_side(self):
        u = (self.db.upd or "—")[:10]
        self.ss.configure(
            text=f"База: {u}\n"
                 f"SHA256: {len(self.db.sha):,}\n"
                 f"Авто: {'Вкл' if Auto.enabled() else 'Выкл'}")

    def _autoupd(self):
        last = self.cfg.get("last_update")
        hrs = self.cfg.get("auto_update_hours", 24)
        need = True
        if last:
            try:
                dt = datetime.fromisoformat(last)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                need = (datetime.now(timezone.utc) - dt).total_seconds() > hrs * 3600
            except Exception:
                need = True
        if need:
            def w():
                try:
                    update_signatures(self.cfg)
                    self.db = DB()
                    self.after(0, self.refresh_side)
                    self.after(0, self.pages["dashboard"].refresh)
                except Exception:
                    pass
            threading.Thread(target=w, daemon=True).start()


def main():
    dpi()
    if not os.path.exists(CFG):
        sj(CFG, DEFAULT_CFG)
    cfg = lj(CFG, DEFAULT_CFG)
    for k, v in DEFAULT_CFG.items():
        cfg.setdefault(k, v)

    if "--cli" in sys.argv:
        db = DB()
        if "--update" in sys.argv:
            update_signatures(cfg)
        tg = [a for a in sys.argv[1:] if not a.startswith("--")]
        if tg:
            sc = Scan(db, cfg,
                      on_threat=lambda f, k, h: print(f"[{k}] {f}"),
                      on_done=lambda s, t: print(f"Готово: {s}"))
            sc.run(tg)
        return

    app = App(cfg, DB())
    if "--tray" in sys.argv or cfg.get("start_minimized", False):
        app.withdraw()
    app.mainloop()


if __name__ == "__main__":
    main()