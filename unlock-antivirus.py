#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UnlockAntivirus 11.3 — Hypervisual + оптимизация интернета (fix)."""
import os, sys, json, time, math, queue, hashlib, shutil, threading, ctypes, random
import subprocess, socket, re
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

APP, VER = "UnlockAntivirus", "11.3"
BASE = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP)
os.makedirs(BASE, exist_ok=True)
SIG = os.path.join(BASE, "signatures.json")
CFG = os.path.join(BASE, "config.json")
QUAR = os.path.join(BASE, "quarantine")
os.makedirs(QUAR, exist_ok=True)
WIN = sys.platform == "win32"
CF = 0x08000000 if WIN else 0

THEMES = {
    "Mint":    {"ac":"#22d3a5","ac2":"#14b8a6","acs":"#10332b","bl":"#38bdf8","pu":"#a78bfa","rd":"#ff5f57","yl":"#febc2e","gr":"#28c840"},
    "Ocean":   {"ac":"#38bdf8","ac2":"#0ea5e9","acs":"#0c2a3e","bl":"#22d3a5","pu":"#818cf8","rd":"#f87171","yl":"#fbbf24","gr":"#34d399"},
    "Purple":  {"ac":"#a78bfa","ac2":"#8b5cf6","acs":"#2a1e4a","bl":"#60a5fa","pu":"#e879f9","rd":"#fb7185","yl":"#fbbf24","gr":"#34d399"},
    "Sunset":  {"ac":"#fb923c","ac2":"#f97316","acs":"#3a1f0a","bl":"#f472b6","pu":"#c084fc","rd":"#ef4444","yl":"#facc15","gr":"#4ade80"},
    "Matrix":  {"ac":"#22c55e","ac2":"#16a34a","acs":"#0a2e15","bl":"#84cc16","pu":"#a3e635","rd":"#ef4444","yl":"#eab308","gr":"#22c55e"},
    "Cyber":   {"ac":"#f0abfc","ac2":"#e879f9","acs":"#3a1043","bl":"#22d3ee","pu":"#a78bfa","rd":"#f43f5e","yl":"#facc15","gr":"#4ade80"},
    "Nord":    {"ac":"#88c0d0","ac2":"#81a1c1","acs":"#1c2b33","bl":"#5e81ac","pu":"#b48ead","rd":"#bf616a","yl":"#ebcb8b","gr":"#a3be8c"},
    "Dracula": {"ac":"#bd93f9","ac2":"#9b6df2","acs":"#2a1f3d","bl":"#8be9fd","pu":"#ff79c6","rd":"#ff5555","yl":"#f1fa8c","gr":"#50fa7b"},
    "Rose":    {"ac":"#f43f5e","ac2":"#e11d48","acs":"#3a0a1a","bl":"#fb7185","pu":"#ec4899","rd":"#dc2626","yl":"#fbbf24","gr":"#4ade80"},
    "Gold":    {"ac":"#facc15","ac2":"#eab308","acs":"#3a2f08","bl":"#fb923c","pu":"#f472b6","rd":"#ef4444","yl":"#fde047","gr":"#84cc16"},
    "Emerald": {"ac":"#10b981","ac2":"#059669","acs":"#083328","bl":"#06b6d4","pu":"#8b5cf6","rd":"#ef4444","yl":"#eab308","gr":"#34d399"},
    "Crimson": {"ac":"#dc2626","ac2":"#b91c1c","acs":"#3a0808","bl":"#f97316","pu":"#ec4899","rd":"#991b1b","yl":"#facc15","gr":"#22c55e"},
}
BC = {"bg":"#070a0e","bg1":"#0b0f14","bg2":"#0f1620","bg3":"#131b26",
      "br":"#1c2634","br2":"#2a3a4d","tx":"#e7edf3","dim":"#93a1af","mut":"#6b7a89"}

def lj(p, d):
    if not os.path.exists(p): return d
    try: return json.load(open(p, "r", encoding="utf-8"))
    except: return d

def sj(p, d):
    try: json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False); return True
    except: return False

class Theme:
    def __init__(self):
        cfg = lj(CFG, {}); n = cfg.get("theme","Mint"); c = cfg.get("custom", {})
        if n == "Custom" and c:
            self.set_custom(c.get("ac","#22d3a5"), c.get("ac2","#14b8a6"),
                            c.get("acs","#10332b"), c.get("bl","#38bdf8"),
                            c.get("pu","#a78bfa"))
        else:
            self.apply(n if n in THEMES else "Mint")
    def apply(self, name):
        if name not in THEMES: name = "Mint"
        t = THEMES[name]; self.name = name
        self.BG, self.BG1, self.BG2, self.BG3 = BC["bg"], BC["bg1"], BC["bg2"], BC["bg3"]
        self.BR, self.BR2 = BC["br"], BC["br2"]
        self.TX, self.DIM, self.MUT = BC["tx"], BC["dim"], BC["mut"]
        self.AC, self.AC2, self.ACS = t["ac"], t["ac2"], t["acs"]
        self.BL, self.PU, self.RD, self.YL, self.GR = t["bl"], t["pu"], t["rd"], t["yl"], t["gr"]
    def set_custom(self, ac, ac2, acs, bl, pu):
        self.name = "Custom"
        self.BG, self.BG1, self.BG2, self.BG3 = BC["bg"], BC["bg1"], BC["bg2"], BC["bg3"]
        self.BR, self.BR2 = BC["br"], BC["br2"]
        self.TX, self.DIM, self.MUT = BC["tx"], BC["dim"], BC["mut"]
        self.AC, self.AC2, self.ACS = ac, ac2, acs
        self.BL, self.PU = bl, pu
        self.RD, self.YL, self.GR = "#ff5f57", "#febc2e", "#28c840"
    def save(self):
        cfg = lj(CFG, {}); cfg["theme"] = self.name
        cfg["custom"] = {"ac":self.AC,"ac2":self.AC2,"acs":self.ACS,"bl":self.BL,"pu":self.PU}
        sj(CFG, cfg)

TH = Theme()
def BG(): return TH.BG
def BG1(): return TH.BG1
def BG2(): return TH.BG2
def BG3(): return TH.BG3
def BR(): return TH.BR
def BR2(): return TH.BR2
def TX(): return TH.TX
def DIM(): return TH.DIM
def MUT(): return TH.MUT
def AC(): return TH.AC
def AC2(): return TH.AC2
def ACS(): return TH.ACS
def BL(): return TH.BL
def PU(): return TH.PU
def RD(): return TH.RD
def YL(): return TH.YL
def GR(): return TH.GR

FN, FM = "Segoe UI", "Consolas"
def F(s, w="normal", m=False): return (FM if m else FN, s, w)

def hs(n):
    for u in ("Б","КБ","МБ","ГБ","ТБ"):
        if n < 1024: return f"{n:.0f} {u}"
        n /= 1024
    return f"{n:.1f} ПБ"

def h2r(h):
    h = h.lstrip("#"); return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
def r2h(r,g,b): return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
def lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    r1,g1,b1 = h2r(c1); r2,g2,b2 = h2r(c2)
    return r2h(r1+(r2-r1)*t, g1+(g2-g1)*t, b1+(b2-b1)*t)

def rr(cv, x1, y1, x2, y2, r=10, **k):
    pts = [x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,
           x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
    return cv.create_polygon(pts, smooth=True, **k)

def round_win(root):
    if not WIN: return
    try:
        root.update_idletasks()
        h = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        ctypes.windll.dwmapi.DwmSetWindowAttribute(h, 33, ctypes.byref(ctypes.c_int(2)), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(h, 20, ctypes.byref(ctypes.c_int(1)), 4)
    except: pass

if WIN:
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.OpenProcess.restype = wintypes.HANDLE
    PT, PQ = 0x0001, 0x1000
    class PE(ctypes.Structure):
        _fields_ = [("s",wintypes.DWORD),("c",wintypes.DWORD),("pid",wintypes.DWORD),
                    ("h",ctypes.c_void_p),("m",wintypes.DWORD),("t",wintypes.DWORD),
                    ("pp",wintypes.DWORD),("pc",ctypes.c_long),("f",wintypes.DWORD),
                    ("e",wintypes.WCHAR*260)]
    class PMC(ctypes.Structure):
        _fields_ = [("cb",wintypes.DWORD),("pf",wintypes.DWORD),
                    ("pk",ctypes.c_size_t),("wk",ctypes.c_size_t),
                    ("qp",ctypes.c_size_t),("qpp",ctypes.c_size_t),
                    ("qnp",ctypes.c_size_t),("qnp2",ctypes.c_size_t),
                    ("pg",ctypes.c_size_t),("pgp",ctypes.c_size_t)]
    class FT(ctypes.Structure):
        _fields_ = [("lo",wintypes.DWORD),("hi",wintypes.DWORD)]
    class MS(ctypes.Structure):
        _fields_ = [("dl",wintypes.DWORD),("ld",wintypes.DWORD),
                    ("tt",ctypes.c_ulonglong),("fr",ctypes.c_ulonglong),
                    ("tp",ctypes.c_ulonglong),("ap",ctypes.c_ulonglong),
                    ("tv",ctypes.c_ulonglong),("av",ctypes.c_ulonglong),
                    ("aex",ctypes.c_ulonglong)]

def list_procs():
    if not WIN: return []
    out = []
    h = k32.CreateToolhelp32Snapshot(0x02, 0)
    if h == -1 or not h: return out
    try:
        e = PE(); e.s = ctypes.sizeof(PE)
        if not k32.Process32FirstW(h, ctypes.byref(e)): return out
        while True:
            if e.pid and e.e:
                mem = 0
                ph = k32.OpenProcess(PQ, False, e.pid)
                if ph:
                    try:
                        pm = PMC(); pm.cb = ctypes.sizeof(PMC)
                        if ctypes.windll.psapi.GetProcessMemoryInfo(ph, ctypes.byref(pm), pm.cb):
                            mem = pm.wk
                    finally: k32.CloseHandle(ph)
                out.append({"pid":e.pid,"name":e.e,"mem":mem,"ppid":e.pp})
            if not k32.Process32NextW(h, ctypes.byref(e)): break
    finally: k32.CloseHandle(h)
    return out

def kill_proc(pid):
    if not WIN: return False
    h = k32.OpenProcess(PT, False, pid)
    if not h: return False
    try: return bool(k32.TerminateProcess(h, 1))
    finally: k32.CloseHandle(h)

def mem_info():
    if not WIN: return None
    try:
        m = MS(); m.dl = ctypes.sizeof(MS)
        if not k32.GlobalMemoryStatusEx(ctypes.byref(m)): return None
        return {"total":m.tt, "free":m.fr, "used":m.tt-m.fr, "pct":m.ld}
    except: return None

def cpu_snap():
    if not WIN: return (0,0,0)
    try:
        i,k,u = FT(),FT(),FT()
        k32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
        def ti(ft): return (ft.hi << 32) | ft.lo
        return (ti(i), ti(k), ti(u))
    except: return (0,0,0)

def cpu_pct(p, c):
    try:
        di,dk,du = c[0]-p[0], c[1]-p[1], c[2]-p[2]
        tot = dk + du
        return max(0.0, min(100.0, (tot-di)/tot*100)) if tot>0 else 0.0
    except: return 0.0

def list_drives():
    if not WIN:
        try:
            t,u,f = shutil.disk_usage("/")
            return [{"m":"/","t":t,"u":u,"f":f,"p":u/t*100 if t else 0}]
        except: return []
    out = []
    try:
        mask = k32.GetLogicalDrives()
        for i in range(26):
            if mask & (1<<i):
                d = chr(65+i) + ":\\"
                try:
                    if k32.GetDriveTypeW(d) == 3:
                        t,u,f = shutil.disk_usage(d)
                        out.append({"m":d,"t":t,"u":u,"f":f,"p":u/t*100 if t else 0})
                except: pass
    except: pass
    return out

def dir_size(path):
    t = 0
    if not path or not os.path.isdir(path): return 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try: t += os.path.getsize(os.path.join(root, f))
            except: pass
    return t

def clean_dir(path):
    if not path or not os.path.isdir(path): return 0
    freed = 0
    for it in os.listdir(path):
        fp = os.path.join(path, it)
        try:
            if os.path.isdir(fp):
                sz = dir_size(fp); shutil.rmtree(fp, ignore_errors=True); freed += sz
            else:
                freed += os.path.getsize(fp); os.remove(fp)
        except: pass
    return freed

def clean_targets():
    w = os.environ.get("SystemRoot", "C:\\Windows")
    la = os.environ.get("LOCALAPPDATA",""); ro = os.environ.get("APPDATA","")
    te = os.environ.get("TEMP","")
    return {
        "temp":{"p":te,"n":"Временные файлы"},
        "win":{"p":os.path.join(w,"Temp"),"n":"Системный temp"},
        "pf":{"p":os.path.join(w,"Prefetch"),"n":"Prefetch"},
        "wu":{"p":os.path.join(w,"SoftwareDistribution","Download"),"n":"Windows Update"},
        "chrome":{"p":os.path.join(la,"Google","Chrome","User Data","Default","Cache"),"n":"Chrome кэш"},
        "edge":{"p":os.path.join(la,"Microsoft","Edge","User Data","Default","Cache"),"n":"Edge кэш"},
        "d3d":{"p":os.path.join(la,"D3DSCache"),"n":"DirectX шейдеры"},
    }

def run(args, timeout=60, enc="cp866"):
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout, creationflags=CF,
                           text=True, encoding=enc, errors="ignore")
        return r.returncode, r.stdout or "", r.stderr or ""
    except Exception as e: return -1, "", str(e)

def fetch(url, timeout=60):
    with urlopen(Request(url, headers={"User-Agent":f"{APP}/{VER}"}), timeout=timeout) as r:
        return r.read()

class DB:
    def __init__(self):
        d = lj(SIG, {"sha256":[],"md5":[],"updated":None})
        self.sha = set(x.lower() for x in d.get("sha256",[]))
        self.md5 = set(x.lower() for x in d.get("md5",[]))
        self.upd = d.get("updated")
    def save(self):
        sj(SIG, {"sha256":sorted(self.sha),"md5":sorted(self.md5),"updated":self.upd})
    def add(self, hs_, k="sha256"):
        t = self.sha if k=="sha256" else self.md5
        ln = 64 if k=="sha256" else 32
        n = len(t)
        for h in hs_:
            h = h.strip().lower()
            if len(h)==ln and all(c in "0123456789abcdef" for c in h): t.add(h)
        return len(t)-n
    def match(self, s):
        if s and s.lower() in self.sha: return "sha256"
        return None

def parse_hashes(text):
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"): continue
        for sep in (",",";","\t"," "):
            if sep in ln:
                for tok in ln.split(sep):
                    t = tok.strip().strip('"\'').lower()
                    if len(t) in (32,64) and all(c in "0123456789abcdef" for c in t):
                        out.append(t)
                break
    return out

def update_sig(cfg, lg=print):
    db = DB()
    for i, u in enumerate(cfg.get("sources",[])):
        try:
            lg(f"[{i+1}] {u.split('/')[2]}")
            hashes = parse_hashes(fetch(u).decode("utf-8","ignore"))
            s = [h for h in hashes if len(h)==64]
            m = [h for h in hashes if len(h)==32]
            db.add(s,"sha256"); db.add(m,"md5")
            lg(f"  +{len(s)} SHA256")
        except Exception as e: lg(f"  ! {e}")
    db.upd = datetime.now(timezone.utc).isoformat()
    db.save(); cfg["last_update"] = db.upd; sj(CFG, cfg)
    lg(f"✓ Всего: {len(db.sha):,}")
    return db

def quarantine_file(path, reason="malware"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(QUAR, f"{ts}_{os.path.basename(path)}.q")
    try:
        sz = os.path.getsize(path)
        shutil.move(path, dst)
        sj(dst+".json", {"orig":os.path.abspath(path),"r":reason,"s":sz,"t":ts})
        return dst
    except: return None

HEUR = [(b"powershell.exe -enc","PS base64"),(b"powershell -enc","PS base64"),
        (b"cmd.exe /c powershell","cmd→ps"),(b"WScript.Shell","WScript"),
        (b"eval(base64_decode","eval b64"),(b"vssadmin delete shadows","Удаление теней")]
DOUBLE_EXT = [".pdf.exe",".doc.exe",".jpg.exe",".png.exe",".txt.exe",".mp3.exe"]

def heuristic(path):
    f = []
    low = path.lower()
    for e in DOUBLE_EXT:
        if low.endswith(e): f.append(f"Двойное {e}")
    try:
        if os.path.getsize(path) > 5<<20: return f
        with open(path,"rb") as fh: data = fh.read(512*1024)
    except: return f
    for pat, desc in HEUR:
        if pat in data: f.append(desc)
    return f

class Scan:
    def __init__(self, db, cfg, of=None, ot=None, od=None, op=None):
        self.db, self.cfg = db, cfg
        self.of = of or (lambda *a: None)
        self.ot = ot or (lambda *a: None)
        self.od = od or (lambda *a: None)
        self.op = op or (lambda *a: None)
        self.stop = threading.Event()
        self.stats = {"sc":0,"th":0,"er":0}
        self.total = 0; self.t0 = time.time()
    def halt(self): self.stop.set()
    def collect(self, paths):
        out = []
        max_sz = self.cfg.get("max_file_size_mb",500) * 1024 * 1024
        for p in paths:
            if self.stop.is_set(): break
            if os.path.isfile(p): out.append(p); continue
            if not os.path.isdir(p): continue
            for root, _, files in os.walk(p, onerror=lambda e: None):
                if self.stop.is_set(): break
                for n in files:
                    if self.stop.is_set(): break
                    fp = os.path.join(root, n)
                    try:
                        if os.path.getsize(fp) > max_sz: continue
                    except: continue
                    out.append(fp)
        return out
    def one(self, fp):
        if self.stop.is_set(): return
        self.of(fp)
        try:
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                for b in iter(lambda: f.read(1<<20), b""): h.update(b)
            s = h.hexdigest()
        except: self.stats["er"] += 1; return
        self.stats["sc"] += 1
        if self.db.match(s):
            self.stats["th"] += 1
            self.ot(fp, "sha256", s); quarantine_file(fp, "hash")
        elif self.cfg.get("heuristics", True):
            f = heuristic(fp)
            if f:
                self.stats["th"] += 1
                self.ot(fp, f"эврика: {', '.join(f[:2])}", s)
                quarantine_file(fp, "heuristic")
        el = max(0.001, time.time()-self.t0)
        eta = (self.total - self.stats["sc"]) / max(self.stats["sc"]/el, 0.1) if self.total else 0
        self.op({"done":self.stats["sc"],"total":self.total,
                 "speed":self.stats["sc"]/el,"eta":eta,"stats":dict(self.stats)})
    def run(self, paths):
        self.t0 = time.time()
        files = self.collect(paths)
        self.total = len(files)
        self.op({"done":0,"total":self.total,"speed":0,"eta":0,"stats":dict(self.stats)})
        th = max(1, int(self.cfg.get("scan_threads",4)))
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
    def enabled():
        if not WIN: return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Auto.RK, 0, winreg.KEY_READ) as k:
                winreg.QueryValueEx(k, APP); return True
        except: return False
    @staticmethod
    def toggle():
        if not WIN: return False
        try:
            import winreg
            if Auto.enabled():
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Auto.RK, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.DeleteValue(k, APP)
                return False
            else:
                p = sys.executable
                if not getattr(sys,"frozen",False):
                    pw = os.path.join(os.path.dirname(p), "pythonw.exe")
                    if os.path.isfile(pw): p = pw
                cmd = f'"{p}" "{os.path.abspath(sys.argv[0])}"'
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, Auto.RK, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, cmd)
                return True
        except: return False

# ═══════ ВИДЖЕТЫ ═══════
class AuroraBG(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self._t = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(50, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                self._t += 0.012; self._draw()
        except: pass
        self.after(60, self._tick)
    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20: return
        self.delete("all")
        blobs = [
            (w*(0.20+0.15*math.sin(self._t*0.6)), h*(0.15+0.10*math.cos(self._t*0.5)), 400, AC(), 0.16),
            (w*(0.80+0.10*math.cos(self._t*0.7)), h*(0.40+0.15*math.sin(self._t*0.9)), 380, BL(), 0.11),
            (w*(0.50+0.20*math.sin(self._t*0.4)), h*(0.85+0.08*math.cos(self._t*1.1)), 360, PU(), 0.09),
            (w*(0.35+0.18*math.cos(self._t*0.8)), h*(0.60+0.12*math.sin(self._t*0.6)), 320, AC2(), 0.08),
        ]
        for cx, cy, r, col, alpha in blobs:
            for i in range(18, 0, -1):
                t = i/18
                c = lerp(BG(), col, (1-t)*alpha + 0.008)
                self.create_oval(cx-r*t, cy-r*t, cx+r*t, cy+r*t, fill=c, outline="")

class ParticleField(tk.Canvas):
    def __init__(self, master, count=30, color_fn=None, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self.count = count; self.color_fn = color_fn or AC
        self._alive = True
        self.parts = []
        self.bind("<Configure>", lambda e: self._init())
        self.bind("<Destroy>", self._on_destroy)
        self._init()
        self.after(50, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _init(self):
        w = self.winfo_width() or 1000; h = self.winfo_height() or 700
        self.parts = [[random.uniform(0,w),random.uniform(0,h),
                       random.uniform(-0.6,0.6),random.uniform(-0.6,0.6),
                       random.uniform(1.2,3.2)] for _ in range(self.count)]
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                w, h = self.winfo_width(), self.winfo_height()
                if w > 20 and h > 20:
                    for p in self.parts:
                        p[0] += p[2]; p[1] += p[3]
                        if p[0] < 0 or p[0] > w: p[2] = -p[2]
                        if p[1] < 0 or p[1] > h: p[3] = -p[3]
                    self._draw(w, h)
        except: pass
        self.after(45, self._tick)
    def _draw(self, w, h):
        self.delete("all")
        col = self.color_fn()
        n = len(self.parts)
        for i in range(n):
            x1, y1 = self.parts[i][0], self.parts[i][1]
            for j in range(i+1, n):
                x2, y2 = self.parts[j][0], self.parts[j][1]
                dx, dy = x1-x2, y1-y2
                d2 = dx*dx + dy*dy
                if d2 < 20000:
                    d = math.sqrt(d2); alpha = 1 - d/141
                    c = lerp(BG(), col, alpha*0.45)
                    self.create_line(x1,y1,x2,y2,fill=c,width=1)
        for p in self.parts:
            r = p[4]
            c = lerp(BG(), col, 0.8)
            self.create_oval(p[0]-r,p[1]-r,p[0]+r,p[1]+r,fill=c,outline="")
            c2 = lerp(BG(), col, 0.25)
            self.create_oval(p[0]-r*2.5,p[1]-r*2.5,p[0]+r*2.5,p[1]+r*2.5,fill="",outline=c2)

class StarField(tk.Canvas):
    def __init__(self, master, count=50, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self.count = count
        self._alive = True
        self.stars = []
        self.bind("<Configure>", lambda e: self._init())
        self.bind("<Destroy>", self._on_destroy)
        self._init()
        self.after(60, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _init(self):
        w = self.winfo_width() or 800; h = self.winfo_height() or 600
        self.stars = [[random.uniform(0,w), random.uniform(0,h),
                       random.uniform(0.15,1.2), random.choice([0.5,0.8,1.2,1.6])]
                      for _ in range(self.count)]
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                w, h = self.winfo_width(), self.winfo_height()
                for s in self.stars:
                    s[0] += s[2]
                    if s[0] > w: s[0] = 0; s[1] = random.uniform(0,h)
                self._draw()
        except: pass
        self.after(70, self._tick)
    def _draw(self):
        self.delete("all")
        col = AC()
        for x, y, v, r in self.stars:
            alpha = min(1.0, v*0.5)
            c = lerp(BG(), col, alpha)
            self.create_oval(x-r, y-r, x+r, y+r, fill=c, outline="")
            self.create_line(x, y, x-v*4, y, fill=c, width=1)

class CometTrail(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self._alive = True
        self.comets = [self._new() for _ in range(4)]
        self.bind("<Destroy>", self._on_destroy)
        self.after(40, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _new(self):
        return {"x":-100, "y":random.uniform(0,700),
                "vx":random.uniform(4,8), "vy":random.uniform(-1,1),
                "life":random.randint(150,300), "trail":[]}
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            w, h = self.winfo_width(), self.winfo_height()
            for i, c in enumerate(self.comets):
                c["x"] += c["vx"]; c["y"] += c["vy"]; c["life"] -= 1
                c["trail"].append((c["x"], c["y"]))
                if len(c["trail"]) > 25: c["trail"].pop(0)
                if c["x"] > w+50 or c["life"] <= 0:
                    self.comets[i] = self._new()
            self._draw()
        except: pass
        self.after(45, self._tick)
    def _draw(self):
        self.delete("all")
        col = AC()
        for c in self.comets:
            for i, (x, y) in enumerate(c["trail"]):
                t = i/len(c["trail"]) if c["trail"] else 0
                alpha = t*0.7
                r = max(1, 4*t)
                cc = lerp(BG(), col, alpha)
                self.create_oval(x-r, y-r, x+r, y+r, fill=cc, outline="")

class Nebula(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self._t = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(100, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                self._t += 0.008; self._draw()
        except: pass
        self.after(110, self._tick)
    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 40: return
        self.delete("all")
        for i in range(6):
            cx = w*(0.5 + 0.3*math.sin(self._t + i*1.0))
            cy = h*(0.5 + 0.3*math.cos(self._t*0.8 + i*1.2))
            r = 180 + i*40
            col = [AC(), BL(), PU(), AC2(), BL(), PU()][i]
            alpha = 0.04 + 0.02*math.sin(self._t*2+i)
            for j in range(10, 0, -1):
                t = j/10
                c = lerp(BG(), col, alpha*t)
                self.create_oval(cx-r*t, cy-r*t, cx+r*t, cy+r*t, fill=c, outline="")

class GridPulse(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self._t = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(60, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                self._t += 0.05; self._draw()
        except: pass
        self.after(70, self._tick)
    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20: return
        self.delete("all")
        base = 50; col = AC()
        for x in range(0, w+base, base):
            alpha = (math.sin(self._t + x*0.02)+1)/2
            c = lerp(BG(), col, 0.04 + alpha*0.03)
            self.create_line(x, 0, x, h, fill=c)
        for y in range(0, h+base, base):
            alpha = (math.sin(self._t + y*0.02)+1)/2
            c = lerp(BG(), col, 0.04 + alpha*0.03)
            self.create_line(0, y, w, y, fill=c)

class ScanLine(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self._y = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(30, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                self._y = (self._y + 4) % (self.winfo_height() or 1)
                self._draw()
        except: pass
        self.after(35, self._tick)
    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20: return
        self.delete("all")
        col = AC()
        for i in range(20):
            y = self._y - i*3
            if 0 <= y <= h:
                alpha = (1 - i/20) * 0.5
                c = lerp(BG(), col, alpha)
                self.create_line(0, y, w, y, fill=c, width=max(1, 3-i//7))

class Crosshair(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG(), **kw)
        self._t = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(60, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                self._t += 0.03; self._draw()
        except: pass
        self.after(70, self._tick)
    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 30 or h < 30: return
        self.delete("all")
        cx, cy = w/2, h/2
        r = min(w,h)*0.4
        col = lerp(BG(), AC(), 0.15)
        for off, gap in [(0,12),(90,12),(180,12),(270,12)]:
            a = math.radians(off + self._t*30)
            x1 = cx + r*math.cos(a); y1 = cy + r*math.sin(a)
            x2 = cx + (r-gap)*math.cos(a); y2 = cy + (r-gap)*math.sin(a)
            self.create_line(x1,y1,x2,y2,fill=col,width=1)
        rp = (math.sin(self._t*3)+1)/2
        c2 = lerp(BG(), AC(), rp*0.5)
        self.create_oval(cx-8, cy-8, cx+8, cy+8, outline=c2, width=1)
        self.create_oval(cx-2, cy-2, cx+2, cy+2, fill=c2, outline="")

class ShieldCanvas(tk.Canvas):
    def __init__(self, master, size=200):
        super().__init__(master, width=size, height=size, bg=BG2(), highlightthickness=0)
        self.size = size; self.state = "idle"; self.angle = 0; self.pulse = 0
        self.ripple = 1.0; self._shake = 0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(40, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def set_state(self, st):
        if st == self.state: return
        self.state = st; self.ripple = 0.0
        if st == "threat": self._shake = 8
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            self.angle = (self.angle + 8) % 360
            self.pulse = (math.sin(time.time()*3)+1)/2
            if self.ripple < 1.0: self.ripple = min(1.0, self.ripple + 0.05)
            if self._shake > 0: self._shake = max(0, self._shake - 0.6)
            self._draw()
        except: pass
        self.after(40, self._tick)
    def _draw(self):
        self.delete("all")
        s = self.size; cx = cy = s/2
        if self._shake > 0:
            cx += random.uniform(-self._shake, self._shake)
            cy += random.uniform(-self._shake, self._shake)
        r = s*0.32; base_r = s*0.44
        if self.ripple < 1.0:
            rp = base_r*(0.5 + self.ripple*0.7)
            alpha = (1-self.ripple)*0.75
            col_base = {"idle":MUT(),"scanning":AC(),"safe":AC(),"threat":RD()}[self.state]
            self.create_oval(cx-rp, cy-rp, cx+rp, cy+rp,
                             outline=lerp(BG2(), col_base, alpha), width=2)
        for i in range(7):
            t = i/7
            rr_ = base_r*(1-t*0.16) + self.pulse*base_r*0.05*(1-t)
            col_base = {"idle":MUT(),"scanning":AC(),"safe":AC(),"threat":RD()}[self.state]
            col = lerp(BG2(), col_base, 0.12*(1-t))
            self.create_oval(cx-rr_, cy-rr_, cx+rr_, cy+rr_, fill=col, outline="")
        if self.state in ("scanning","idle"):
            for off in (0, 120, 240):
                col = AC() if self.state=="scanning" else MUT()
                self.create_arc(cx-s*0.4, cy-s*0.4, cx+s*0.4, cy+s*0.4,
                                start=self.angle+off, extent=70,
                                outline=col, width=3, style="arc")
            for a in range(0, 360, 20):
                rad = math.radians(a)
                self.create_line(cx+s*0.46*math.cos(rad), cy+s*0.46*math.sin(rad),
                                 cx+s*0.48*math.cos(rad), cy+s*0.48*math.sin(rad),
                                 fill=lerp(BG2(), MUT(), 0.4), width=1)
        else:
            for a in range(0, 360, 20):
                rad = math.radians(a)
                self.create_line(cx+s*0.46*math.cos(rad), cy+s*0.46*math.sin(rad),
                                 cx+s*0.48*math.cos(rad), cy+s*0.48*math.sin(rad),
                                 fill=lerp(BG2(), BR(), 0.8), width=1)
        color = {"idle":MUT(),"scanning":AC(),"safe":AC(),"threat":RD()}[self.state]
        cy_s = cy - 0.025*r
        self.create_arc(cx-r, cy_s-r, cx+r, cy_s+r*0.55, start=0, extent=180,
                        fill=color, outline="", style="chord")
        pts = [cx-r,cy_s+r*0.05, cx-r*0.5,cy_s+r*0.55,
               cx,cy_s+r*1.05, cx+r*0.5,cy_s+r*0.55, cx+r,cy_s+r*0.05]
        self.create_polygon(pts, fill=color, outline="", smooth=True)
        self.create_arc(cx-r*0.75, cy_s-r*0.7, cx+r*0.75, cy_s+r*0.3, start=0, extent=180,
                        fill=lerp(color, "#ffffff", 0.22), outline="", style="chord")
        if self.state == "safe":
            self.create_line(cx-r*0.35,cy_s+r*0.05, cx-r*0.05,cy_s+r*0.32,
                             cx+r*0.4,cy_s-r*0.25, fill="#04120e", width=5,
                             capstyle="round", joinstyle="round")
        elif self.state == "threat":
            for off in (-0.25, 0.25):
                self.create_line(cx-r*off, cy_s-r*0.25, cx+r*off, cy_s+r*0.25,
                                 fill="#04120e", width=5, capstyle="round")
        elif self.state == "scanning":
            for i in range(3):
                a = self.angle + i*120
                x = cx + r*0.35*math.cos(math.radians(a))
                y = cy_s + r*0.35*math.sin(math.radians(a))
                self.create_oval(x-4,y-4,x+4,y+4, fill="#04120e", outline="")

class RingGauge(tk.Canvas):
    def __init__(self, master, size=130, label="CPU", color_fn=None):
        super().__init__(master, width=size, height=size, bg=BG2(), highlightthickness=0)
        self.size = size; self.label = label
        self.color_fn = color_fn or AC
        self.val = 0.0; self.target = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(40, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def set(self, v): self.target = max(0.0, min(1.0, v))
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            self.val += (self.target - self.val) * 0.12
            self._draw()
        except: pass
        self.after(40, self._tick)
    def _draw(self):
        self.delete("all")
        s = self.size; cx = cy = s/2; r = s*0.38
        col = self.color_fn()
        pulse = (math.sin(time.time()*3)+1)/2
        for i in range(10, 0, -1):
            t = i/10
            c = lerp(BG2(), col, (1-t)*0.14 + pulse*0.03*(1-t))
            self.create_oval(cx-r*t*1.1, cy-r*t*1.1, cx+r*t*1.1, cy+r*t*1.1, fill=c, outline="")
        self.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=-360,
                        outline=BG1(), width=9, style="arc")
        if self.val > 0:
            self.create_arc(cx-r, cy-r, cx+r, cy+r, start=90,
                            extent=-360*self.val,
                            outline=col, width=9, style="arc")
            glow_col = lerp(col, "#ffffff", 0.4)
            self.create_arc(cx-r, cy-r, cx+r, cy+r, start=90,
                            extent=-360*self.val,
                            outline=glow_col, width=3, style="arc")
        for a in range(0, 360, 30):
            rad = math.radians(a)
            x1 = cx+(r-13)*math.cos(rad); y1 = cy+(r-13)*math.sin(rad)
            x2 = cx+(r-7)*math.cos(rad); y2 = cy+(r-7)*math.sin(rad)
            self.create_line(x1,y1,x2,y2, fill=lerp(BG2(), MUT(), 0.6), width=1)
        self.create_text(cx, cy-6, text=f"{int(self.val*100)}%", fill=TX(), font=F(20,"bold"))
        self.create_text(cx, cy+16, text=self.label, fill=MUT(), font=F(9))

class SparkLine(tk.Canvas):
    def __init__(self, master, height=70, color_fn=None, samples=60):
        super().__init__(master, height=height, bg=BG2(), highlightthickness=0)
        self.color_fn = color_fn or AC
        self.samples = samples
        self.data = [0.0]*samples
        self.bind("<Configure>", lambda e: self._draw())
    def push(self, v):
        self.data = self.data[1:] + [max(0.0, min(1.0, v))]
        self._draw()
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10: return
        col = self.color_fn()
        for i in range(1, 4):
            y = h*i/4
            self.create_line(0, y, w, y, fill=lerp(BG2(), MUT(), 0.15), dash=(2,4))
        step = w/(self.samples-1) if self.samples>1 else w
        poly = [(0,h)]
        for i, v in enumerate(self.data):
            poly.append((i*step, h - v*(h-4) - 2))
        poly.append((w,h))
        flat = []
        for p in poly: flat.extend(p)
        if len(flat) >= 6:
            self.create_polygon(flat, fill=lerp(BG2(), col, 0.2), outline="")
        for i in range(len(self.data)-1):
            x1, y1 = i*step, h - self.data[i]*(h-4) - 2
            x2, y2 = (i+1)*step, h - self.data[i+1]*(h-4) - 2
            self.create_line(x1,y1,x2,y2, fill=col, width=2)

class WaveViz(tk.Canvas):
    def __init__(self, master, height=60, color_fn=None):
        super().__init__(master, height=height, bg=BG2(), highlightthickness=0)
        self.color_fn = color_fn or AC
        self._t = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(50, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                self._t += 0.15; self._draw()
        except: pass
        self.after(55, self._tick)
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20: return
        col = self.color_fn()
        n = 60
        bar_w = w/n - 2
        for i in range(n):
            x = i*(bar_w+2)
            phase = self._t + i*0.3
            v = (math.sin(phase)*0.5 + 0.5) * (0.3 + 0.7*random.random())
            bh = v * h * 0.9
            y = (h-bh)/2
            c = lerp(BG2(), col, 0.4 + v*0.4)
            self.create_rectangle(x, y, x+bar_w, y+bh, fill=c, outline="")

class GradientProgress(tk.Canvas):
    def __init__(self, master, height=12):
        super().__init__(master, height=height, highlightthickness=0, bg=BG2())
        self._val = 0.0; self._offset = 0; self._running = False
        self._alive = True
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Destroy>", self._on_destroy)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def set(self, v):
        self._val = max(0, min(1, v)); self._draw()
    def start(self):
        if self._running: return
        self._running = True; self._loop()
    def stop(self):
        self._running = False
    def _loop(self):
        if not self._alive or not self.winfo_exists() or not self._running: return
        self._offset = (self._offset + 4) % 100
        self._draw()
        self.after(40, self._loop)
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4: return
        r = h/2
        rr(self, 0, 0, w, h, r=r, fill=BG1(), outline=BR())
        if self._val <= 0: return
        fw = max(h, int(w*self._val))
        steps = 25
        for i in range(steps):
            t = i/steps
            col = lerp(AC(), BL(), t)
            self.create_rectangle(t*fw, 1, (t+1/steps)*fw, h-1, fill=col, outline="")
        if self._running:
            sx = int((self._offset/100)*fw)
            for k in range(14):
                tt = k/14
                alpha = math.sin(tt*math.pi) * 0.3
                col = lerp(BG1(), "#ffffff", alpha)
                xp = sx - 22 + k*3
                if 0 <= xp < fw:
                    self.create_rectangle(xp, 1, xp+3, h-1, fill=col, outline="")

class HeatBar(tk.Canvas):
    def __init__(self, master, height=14, color_fn=None):
        super().__init__(master, height=height, bg=BG2(), highlightthickness=0)
        self.color_fn = color_fn or AC
        self._val = 0.0; self._disp = 0.0
        self._alive = True
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Destroy>", self._on_destroy)
        self.after(40, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def set(self, v): self._val = max(0, min(1, v))
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            self._disp += (self._val - self._disp) * 0.15
            self._draw()
        except: pass
        self.after(40, self._tick)
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4: return
        rr(self, 0, 0, w, h, r=h/2, fill=BG1(), outline=BR())
        fw = int(w*self._disp)
        if fw > 0:
            steps = 30
            for i in range(steps):
                t = i/steps
                if t > self._disp: break
                col = GR() if self._disp<0.6 else (YL() if self._disp<0.85 else RD())
                self.create_rectangle(t*fw, 1, (t+1/steps)*fw, h-1, fill=col, outline="")

class StatusPulse(tk.Canvas):
    def __init__(self, master, size=18, color_fn=None):
        super().__init__(master, width=size, height=size, bg=BG2(), highlightthickness=0)
        self.size = size; self.color_fn = color_fn or GR
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(60, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable(): self._draw()
        except: pass
        self.after(65, self._tick)
    def _draw(self):
        self.delete("all")
        s = self.size; cx = cy = s/2
        t = (time.time()*2) % 1.0
        col = self.color_fn()
        rp = 3 + t*5
        alpha = (1-t)*0.7
        self.create_oval(cx-rp, cy-rp, cx+rp, cy+rp,
                         outline=lerp(BG2(), col, alpha), width=1)
        self.create_oval(cx-4, cy-4, cx+4, cy+4, fill=col, outline="")

class LoadingDots(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, width=60, height=20, bg=BG2(), highlightthickness=0, **kw)
        self._t = 0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(70, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            if self.winfo_viewable():
                self._t += 1; self._draw()
        except: pass
        self.after(75, self._tick)
    def _draw(self):
        self.delete("all")
        for i in range(3):
            phase = self._t*0.15 + i*0.7
            y = 10 - abs(math.sin(phase)) * 6
            col = lerp(BG2(), AC(), 0.4 + 0.6*abs(math.sin(phase)))
            self.create_oval(10+i*18-4, y-4, 10+i*18+4, y+4, fill=col, outline="")

class TypewriterLabel(tk.Label):
    def __init__(self, master, text, delay=40, **kw):
        super().__init__(master, text="", **kw)
        self._full = text; self._delay = delay; self._i = 0
        self.after(300, self._step)
    def _step(self):
        if not self.winfo_exists(): return
        if self._i <= len(self._full):
            self.configure(text=self._full[:self._i])
            self._i += 1
            self.after(self._delay, self._step)

class AnimatedCounter(tk.Label):
    def __init__(self, master, value=0, fmt=None, **kw):
        f = fmt or (lambda v: f"{int(v):,}")
        super().__init__(master, text=f(0), **kw)
        self._val = 0.0; self._target = value; self._fmt = f
        self.after(30, self._step)
    def set(self, v): self._target = v
    def _step(self):
        if not self.winfo_exists(): return
        try:
            if abs(self._val - self._target) > 0.5:
                self._val += (self._target - self._val) * 0.15
                self.configure(text=self._fmt(self._val))
            else:
                self._val = self._target
                self.configure(text=self._fmt(self._val))
        except: pass
        self.after(30, self._step)

class Card(tk.Frame):
    def __init__(self, m, r=12, bgc=None, bc=None, px=14, py=12, **kw):
        try: pb = m.cget("bg")
        except: pb = BG()
        super().__init__(m, bg=pb, **kw)
        self._r = r; self._bg = bgc or BG2(); self._bc = bc or BR()
        self._hover_bc = self._bc; self._cur_bc = self._bc
        self._anim = None
        self._cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=pb)
        self._cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=self._bg)
        self.body.pack(fill="both", expand=True, padx=px, pady=py)
        self.bind("<Configure>", self._rd)
        self.bind("<Enter>", lambda e: self._seth(True))
        self.bind("<Leave>", lambda e: self._seth(False))
    def set_hover(self, bc): self._hover_bc = bc
    def _seth(self, v):
        tgt = self._hover_bc if v else self._bc
        if self._cur_bc == tgt: return
        src = self._cur_bc
        if self._anim:
            try: self.after_cancel(self._anim)
            except: pass
        def step(i):
            if not self.winfo_exists(): return
            self._cur_bc = lerp(src, tgt, i/6); self._rd()
            if i < 6: self._anim = self.after(16, lambda: step(i+1))
            else: self._anim = None
        step(0)
    def _rd(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 6 or h < 6: return
        c = self._cv; c.delete("all"); r = self._r
        pts = [r+1,1, w-r-1,1, w-1,1, w-1,r+1, w-1,h-r-1, w-1,h-1,
               w-r-1,h-1, r+1,h-1, 1,h-1, 1,h-r-1, 1,r+1, 1,1]
        c.create_polygon(pts, smooth=True, fill=self._bg, outline=self._cur_bc, width=1)

class Btn(tk.Canvas):
    def __init__(self, m, text, cmd=None, w=180, h=40, bg=None, fg=None,
                 hov=None, bd=None, fnt=None, r=10, pbg=None):
        try: pb = pbg or m.cget("bg")
        except: pb = BG()
        super().__init__(m, width=w, height=h, bg=pb, highlightthickness=0, cursor="hand2")
        self.w, self.h = w, h
        self.bg_c = bg if bg else AC()
        self.fg_c = fg if fg else "#04120e"
        self.hov = hov if hov else AC2()
        self.bd = bd; self.r = r; self.cmd = cmd; self.t = text
        self.fnt = fnt or F(11, "bold")
        self.en = True
        self._cur = self.bg_c
        self._anim = None
        self._ripples = []
        self._draw()
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._animate(self.hov if self.en else self.bg_c))
        self.bind("<Leave>", lambda e: self._animate(self.bg_c))
    def _animate(self, tgt, steps=8):
        if self._anim:
            try: self.after_cancel(self._anim)
            except: pass
        src = self._cur
        if src == tgt: return
        def step(i):
            if not self.winfo_exists(): return
            self._cur = lerp(src, tgt, i/steps); self._draw()
            if i < steps: self._anim = self.after(14, lambda: step(i+1))
            else: self._anim = None
        step(0)
    def _draw(self):
        self.delete("all")
        c = self._cur if self.en else BR()
        rr(self, 1, 1, self.w-1, self.h-1, self.r, fill=c, outline=self.bd or c)
        self.create_text(self.w/2, self.h/2-1, text=self.t,
                         fill=self.fg_c if self.en else MUT(), font=self.fnt)
        for (rx, ry, rr_, age) in self._ripples:
            if age < 1.0:
                alpha = 1-age; col = lerp(c, "#ffffff", alpha*0.5)
                self.create_oval(rx-rr_, ry-rr_, rx+rr_, ry+rr_,
                                 outline=col, width=2)
    def _click(self, e):
        if not self.en or not self.cmd: return
        self._ripples = [(e.x, e.y, 1, 0.0)]
        def anim():
            if not self.winfo_exists(): return
            new = []
            for (rx, ry, rr_, age) in self._ripples:
                age += 0.18; rr_ += 9
                if age < 1.0: new.append((rx, ry, rr_, age))
            self._ripples = new; self._draw()
            if new: self.after(20, anim)
        anim(); self.cmd()
    def on(self, v):
        self.en = v; self._cur = self.bg_c; self._draw()
    def txt(self, t): self.t = t; self._draw()

class NavBtn(tk.Frame):
    def __init__(self, m, ic, txt, cmd):
        super().__init__(m, bg=BG1(), height=38, cursor="hand2")
        self.pack_propagate(False)
        self.cmd, self._act = cmd, False
        self.ind = tk.Frame(self, bg=BG1(), width=3); self.ind.pack(side="left", fill="y")
        self.il = tk.Label(self, text=ic, bg=BG1(), fg=DIM(), font=F(13), width=3)
        self.il.pack(side="left")
        self.tl = tk.Label(self, text=txt, bg=BG1(), fg=DIM(), font=F(10), anchor="w")
        self.tl.pack(side="left", fill="x", expand=True, padx=(4, 8))
        for w in (self, self.il, self.tl, self.ind):
            w.bind("<Button-1>", lambda e: self.cmd())
            w.bind("<Enter>", self._on); w.bind("<Leave>", self._off)
    def _on(self, _):
        if not self._act: self._paint(BG2())
    def _off(self, _):
        if not self._act: self._paint(BG1())
    def _paint(self, c):
        for w in (self, self.il, self.tl, self.ind):
            try: w.configure(bg=c)
            except: pass
    def act(self, v):
        self._act = v
        ws = (self, self.il, self.tl, self.ind)
        if v:
            for w in ws: w.configure(bg=ACS())
            self.ind.configure(bg=AC()); self.il.configure(fg=AC()); self.tl.configure(fg=TX())
        else:
            for w in ws: w.configure(bg=BG1())
            self.ind.configure(bg=BG1()); self.il.configure(fg=DIM()); self.tl.configure(fg=MUT())

class Toast(tk.Toplevel):
    def __init__(self, parent, text, kind="info"):
        super().__init__(parent)
        self.overrideredirect(True); self.attributes("-topmost", True)
        self.configure(bg=BG2())
        try: self.attributes("-alpha", 0.0)
        except: pass
        icons = {"info":"i","ok":"✓","warn":"!","error":"✕"}
        colors = {"info":BL(),"ok":AC(),"warn":YL(),"error":RD()}
        col = colors[kind]
        wrap = tk.Frame(self, bg=BG2(), highlightthickness=1, highlightbackground=col)
        wrap.pack(fill="both", expand=True)
        tk.Label(wrap, text=icons[kind], bg=BG2(), fg=col, font=F(14,"bold"))\
            .pack(side="left", padx=(14,10), pady=12)
        tk.Label(wrap, text=text, bg=BG2(), fg=TX(), font=F(11))\
            .pack(side="left", padx=(0,18), pady=12)
        self.update_idletasks()
        w, h = wrap.winfo_reqwidth(), wrap.winfo_reqheight()
        try:
            px = parent.winfo_rootx() + parent.winfo_width() - w - 30
            py = parent.winfo_rooty() + parent.winfo_height() - h - 30
            sx = px + 80
        except: px = py = sx = 100
        self.geometry(f"{w}x{h}+{sx}+{py}")
        self._tx = px
        self._fi(0.0, sx)
        self.after(2700, self._fo)
    def _fi(self, a, x):
        a = min(1.0, a+0.15)
        x = x - (x - self._tx) * 0.3
        try:
            self.attributes("-alpha", a)
            self.geometry(f"+{int(x)}+{self.winfo_y()}")
        except: pass
        if a < 1.0: self.after(20, lambda: self._fi(a, x))
    def _fo(self):
        def go(a):
            if not self.winfo_exists(): return
            a -= 0.15
            try: self.attributes("-alpha", max(0.0, a))
            except: pass
            if a > 0: self.after(20, lambda: go(a))
            else:
                try: self.destroy()
                except: pass
        go(1.0)

# ═══════ СТРАНИЦЫ ═══════
class Page(tk.Frame):
    def __init__(self, m, app, title, desc=""):
        super().__init__(m, bg=BG()); self.app = app
        head = tk.Frame(self, bg=BG()); head.pack(fill="x", padx=26, pady=(18, 8))
        tk.Label(head, text=title, bg=BG(), fg=TX(), font=F(22,"bold"), anchor="w")\
            .pack(anchor="w")
        if desc:
            tk.Label(head, text=desc, bg=BG(), fg=DIM(), font=F(10), anchor="w")\
                .pack(anchor="w", pady=(2,0))
    def refresh(self): pass

class DashboardPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app, "Обзор системы", "Живой мониторинг и защита")
        hero = Card(self, r=16, py=20); hero.pack(fill="x", padx=26, pady=(12,0))
        hero.set_hover(AC())
        inner = hero.body
        self.shield = ShieldCanvas(inner, size=180)
        self.shield.pack(side="left", padx=(4, 22))
        self.shield.set_state("safe")
        info = tk.Frame(inner, bg=BG2()); info.pack(side="left", fill="both", expand=True)
        TypewriterLabel(info, "Система защищена", delay=45,
                        bg=BG2(), fg=TX(), font=F(20,"bold"), anchor="w").pack(anchor="w")
        tk.Label(info, text=f"Сигнатуры: {len(app.db.sha):,}   ·   Обновлено: {(app.db.upd or '—')[:10]}",
                 bg=BG2(), fg=DIM(), font=F(10), anchor="w").pack(anchor="w", pady=(4,12))
        btns = tk.Frame(info, bg=BG2()); btns.pack(anchor="w")
        Btn(btns, "⚡ Быстрая проверка", w=210, h=44, pbg=BG2(), cmd=self._quick).pack(side="left", padx=(0,10))
        Btn(btns, "🌐 Интернет", w=210, h=44, bg=BG3(), fg=DIM(), hov=BR2(),
            bd=BR(), pbg=BG2(), cmd=lambda: app.go("net")).pack(side="left")

        live = tk.Frame(self, bg=BG()); live.pack(fill="x", padx=26, pady=(12,0))
        for i in range(3): live.grid_columnconfigure(i, weight=1, uniform="l")
        gc = Card(live, r=12, py=12); gc.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        gc.set_hover(AC())
        tk.Label(gc.body, text="CPU", bg=BG2(), fg=MUT(), font=F(9)).pack(anchor="w")
        self.g_cpu = RingGauge(gc.body, size=120, label="CPU", color_fn=AC)
        self.g_cpu.pack(pady=4)
        rc = Card(live, r=12, py=12); rc.grid(row=0, column=1, sticky="nsew", padx=5)
        rc.set_hover(BL())
        tk.Label(rc.body, text="RAM", bg=BG2(), fg=MUT(), font=F(9)).pack(anchor="w")
        self.g_ram = RingGauge(rc.body, size=120, label="RAM", color_fn=BL)
        self.g_ram.pack(pady=4)
        dc = Card(live, r=12, py=12); dc.grid(row=0, column=2, sticky="nsew", padx=(5,0))
        dc.set_hover(PU())
        tk.Label(dc.body, text="Диск C:", bg=BG2(), fg=MUT(), font=F(9)).pack(anchor="w")
        self.g_disk = RingGauge(dc.body, size=120, label="Disk", color_fn=PU)
        self.g_disk.pack(pady=4)

        row2 = tk.Frame(self, bg=BG()); row2.pack(fill="x", padx=26, pady=(12,0))
        for i in range(2): row2.grid_columnconfigure(i, weight=1)
        sp = Card(row2, r=12, py=10); sp.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        tk.Label(sp.body, text="История CPU (60 сек)", bg=BG2(), fg=TX(), font=F(11,"bold"), anchor="w").pack(anchor="w")
        self.spark = SparkLine(sp.body, height=70, color_fn=AC); self.spark.pack(fill="x", pady=(4,0))
        wv = Card(row2, r=12, py=10); wv.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        tk.Label(wv.body, text="Активность", bg=BG2(), fg=TX(), font=F(11,"bold"), anchor="w").pack(anchor="w")
        self.wave = WaveViz(wv.body, height=70, color_fn=BL); self.wave.pack(fill="x", pady=(4,0))

        stats = tk.Frame(self, bg=BG()); stats.pack(fill="x", padx=26, pady=(12,0))
        for i in range(4): stats.grid_columnconfigure(i, weight=1, uniform="s")
        cards = [
            ("Σ", len(app.db.sha), "SHA256", AC),
            ("μ", len(app.db.md5), "MD5", BL),
            ("▣", self._qc(), "Карантин", YL),
            ("⛨", 1 if Auto.enabled() else 0, "Автозагрузка", GR),
        ]
        self.stats = {}
        for i, (ic, val, label, colf) in enumerate(cards):
            c = Card(stats, r=12, py=14, px=14)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i==0 else 6, 0 if i==3 else 6))
            c.set_hover(colf())
            hdr = tk.Frame(c.body, bg=BG2()); hdr.pack(fill="x")
            tk.Label(hdr, text=ic, bg=BG2(), fg=colf(), font=F(22)).pack(side="left")
            StatusPulse(hdr, size=14, color_fn=colf).pack(side="right")
            cnt = AnimatedCounter(c.body, value=val, bg=BG2(), fg=TX(),
                                  font=F(20,"bold"), anchor="w",
                                  fmt=(lambda v: "Вкл" if v >= 1 else "Выкл") if label=="Автозагрузка"
                                       else (lambda v: f"{int(v):,}"))
            cnt.pack(anchor="w", pady=(6,2))
            tk.Label(c.body, text=label, bg=BG2(), fg=MUT(), font=F(10), anchor="w").pack(anchor="w")
            self.stats[label] = cnt

        lg = Card(self, r=12, py=12); lg.pack(fill="both", expand=True, padx=26, pady=(12,20))
        hdr = tk.Frame(lg.body, bg=BG2()); hdr.pack(fill="x")
        tk.Label(hdr, text="События", bg=BG2(), fg=TX(), font=F(12,"bold")).pack(side="left")
        LoadingDots(hdr).pack(side="right")
        self.ev = tk.Text(lg.body, bg=BG1(), fg=DIM(), bd=0, font=F(9,m=True),
                          wrap="word", insertbackground=TX(), highlightthickness=0, padx=8, pady=6)
        self.ev.pack(fill="both", expand=True, pady=(6,0))
        self.ev.configure(state="disabled")
        self._log(f"[i] {APP} {VER} запущен")

        self._prev = cpu_snap()
        self._live()

    def _live(self):
        if not self.winfo_exists(): return
        try:
            cur = cpu_snap()
            pct = cpu_pct(self._prev, cur)/100.0
            self._prev = cur
            self.g_cpu.set(pct); self.spark.push(pct)
            info = mem_info()
            if info: self.g_ram.set(info["pct"]/100.0)
            d = list_drives()
            if d: self.g_disk.set(d[0]["p"]/100.0)
        except: pass
        self.after(1000, self._live)

    def _qc(self):
        try: return len([f for f in os.listdir(QUAR) if f.endswith(".q")])
        except: return 0
    def _log(self, t):
        def do():
            self.ev.configure(state="normal")
            self.ev.insert("end", t+"\n"); self.ev.see("end")
            self.ev.configure(state="disabled")
        self.after(0, do)
    def refresh(self):
        self.stats["SHA256"].set(len(self.app.db.sha))
        self.stats["MD5"].set(len(self.app.db.md5))
        self.stats["Карантин"].set(self._qc())
        self.stats["Автозагрузка"].set(1 if Auto.enabled() else 0)
    def _quick(self):
        h = os.path.expanduser("~")
        ts = [os.path.join(h,n) for n in ("Downloads","Documents","Desktop")
              if os.path.isdir(os.path.join(h,n))] or [h]
        self.app.go("scan"); self.app.pages["scan"].start(ts)

class ScanPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app, "Сканирование", "Проверка файлов и папок")
        self.sc = None
        top = Card(self, r=14, py=18); top.pack(fill="x", padx=26, pady=(12,0))
        inner = top.body
        self.shield = ShieldCanvas(inner, size=140); self.shield.pack(side="left", padx=(0,18))
        col = tk.Frame(inner, bg=BG2()); col.pack(side="left", fill="both", expand=True)
        self.status = tk.Label(col, text="Готов к сканированию", bg=BG2(), fg=TX(),
                               font=F(15,"bold"), anchor="w")
        self.status.pack(anchor="w")
        self.cur = tk.Label(col, text="", bg=BG2(), fg=MUT(), font=F(9),
                             anchor="w", wraplength=600, justify="left")
        self.cur.pack(anchor="w", pady=(4,10))
        self.progress = GradientProgress(col, height=10); self.progress.pack(fill="x")
        cnt_row = tk.Frame(col, bg=BG2()); cnt_row.pack(fill="x", pady=(6,0))
        self.counter = tk.Label(cnt_row, text="", bg=BG2(), fg=DIM(), font=F(9), anchor="w")
        self.counter.pack(side="left")
        self.eta = tk.Label(cnt_row, text="", bg=BG2(), fg=MUT(), font=F(9), anchor="e")
        self.eta.pack(side="right")
        btns = tk.Frame(self, bg=BG()); btns.pack(fill="x", padx=26, pady=(12,0))
        Btn(btns, "📁 Папка", w=150, h=42, cmd=self._pf).pack(side="left", padx=(0,8))
        Btn(btns, "📄 Файл", w=150, h=42, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(),
            cmd=self._pfile).pack(side="left", padx=(0,8))
        self.stb = Btn(btns, "⏹ Стоп", w=130, h=42, bg=BG3(), fg=MUT(),
                       hov=BR2(), bd=BR(), cmd=self._stop)
        self.stb.pack(side="left"); self.stb.on(False)
        lg = Card(self, r=12, py=12); lg.pack(fill="both", expand=True, padx=26, pady=(12,20))
        tk.Label(lg.body, text="Журнал", bg=BG2(), fg=TX(), font=F(12,"bold"), anchor="w").pack(anchor="w")
        self.lg = tk.Text(lg.body, bg=BG1(), fg=DIM(), bd=0, font=F(9,m=True),
                          wrap="word", insertbackground=TX(), highlightthickness=0, padx=8, pady=6)
        self.lg.pack(fill="both", expand=True, pady=(6,0))
        self.lg.tag_config("ok", foreground=AC())
        self.lg.tag_config("err", foreground=RD())
        self.lg.tag_config("info", foreground=BL())

    def _pf(self):
        p = filedialog.askdirectory()
        if p: self.start([p])
    def _pfile(self):
        p = filedialog.askopenfilename()
        if p: self.start([p])
    def _stop(self):
        if self.sc: self.sc.halt()
    def _log(self, t, tag=None):
        def do(): self.lg.insert("end", t+"\n", tag or ""); self.lg.see("end")
        self.after(0, do)
    def start(self, paths):
        if self.sc and not self.sc.stop.is_set(): return
        self.lg.delete("1.0","end")
        self.progress.set(0); self.progress.start()
        self.status.configure(text="Сканирование...", fg=TX())
        self.shield.set_state("scanning"); self.stb.on(True)
        self._log(f"=== {paths} ===", "info")
        def of(fp):
            s = fp if len(fp)<90 else "..."+fp[-87:]
            self._log(f"  → {s}")
        def ot(fp, k, h): self._log(f"  ⚠ УГРОЗА ({k}): {fp}", "err")
        def op(p):
            def do():
                if p["total"]: self.progress.set(p["done"]/p["total"])
                self.counter.configure(text=f"{p['done']}/{p['total']}   {p['speed']:.0f} ф/с")
                if p.get("eta"):
                    m, s = divmod(int(p["eta"]), 60)
                    self.eta.configure(text=f"ETA: {m}м {s}с")
            self.after(0, do)
        def od(s, total):
            def do():
                self.progress.set(1.0); self.progress.stop()
                if s["th"]:
                    self.shield.set_state("threat")
                    self.status.configure(text=f"Готово · Угроз: {s['th']}", fg=RD())
                else:
                    self.shield.set_state("safe")
                    self.status.configure(text="Готово · Чисто", fg=AC())
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
        super().__init__(m, app, "Очистка памяти", "Управление процессами")
        self.procs = []; self.sel = set(); self.rows = {}
        mc = Card(self, r=14, py=16); mc.pack(fill="x", padx=26, pady=(12,0))
        tk.Label(mc.body, text="▦", bg=BG2(), fg=AC(), font=F(30,"bold")).pack(side="left", padx=(0,18))
        mid = tk.Frame(mc.body, bg=BG2()); mid.pack(side="left", fill="both", expand=True)
        self.mt = tk.Label(mid, text="Загрузка...", bg=BG2(), fg=TX(), font=F(18,"bold"), anchor="w")
        self.mt.pack(anchor="w")
        self.ms = tk.Label(mid, text="", bg=BG2(), fg=DIM(), font=F(10), anchor="w")
        self.ms.pack(anchor="w", pady=(2,8))
        self.mbar = GradientProgress(mid, height=10); self.mbar.pack(fill="x")
        Btn(mc.body, "↻", w=50, h=42, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(),
            pbg=BG2(), cmd=self._load).pack(side="right", padx=(18,0))
        b = tk.Frame(self, bg=BG()); b.pack(fill="x", padx=26, pady=(10,6))
        Btn(b, "Снять всё", w=120, h=34, r=8, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(),
            fnt=F(10), cmd=self._none).pack(side="right", padx=(0,8))
        Btn(b, ">100 МБ", w=120, h=34, r=8, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(),
            fnt=F(10), cmd=self._big).pack(side="right")
        lc = Card(self, r=12, px=8, py=8); lc.pack(fill="both", expand=True, padx=26, pady=(6,0))
        self.cv = tk.Canvas(lc.body, bg=BG2(), highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lc.body, command=self.cv.yview); sb.pack(side="right", fill="y")
        self.cv.configure(yscrollcommand=sb.set)
        self.lf = tk.Frame(self.cv, bg=BG2())
        self.cv.create_window((0,0), window=self.lf, anchor="nw")
        self.lf.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        bot = tk.Frame(self, bg=BG()); bot.pack(fill="x", padx=26, pady=(10,20))
        self.sl = tk.Label(bot, text="Выбрано: 0", bg=BG(), fg=DIM(), font=F(10), anchor="w")
        self.sl.pack(side="left")
        Btn(bot, "✕ Завершить", w=220, h=42, bg=RD(), fg="#fff", hov="#e04b43",
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
            tk.Label(self.lf, text="Нет данных", bg=BG2(), fg=MUT(), font=F(11)).pack(pady=40); return
        PROT = {"system","registry","smss.exe","csrss.exe","wininit.exe","winlogon.exe",
                "services.exe","lsass.exe","dwm.exe","explorer.exe","sihost.exe",
                "ctfmon.exe","conhost.exe","unlockantivirus.exe"}
        for p in self.procs[:200]:
            pid, n, mem = p["pid"], p["name"], p["mem"]
            pr = n.lower() in PROT
            row = tk.Frame(self.lf, bg=BG2()); row.pack(fill="x", pady=1, padx=2)
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(row, variable=var, bg=BG2(), activebackground=BG2(),
                           selectcolor=BG2(), highlightthickness=0, bd=0,
                           state=("disabled" if pr else "normal"),
                           command=lambda pp=pid: self._chk(pp)).pack(side="left", padx=(6,0))
            tk.Label(row, text=n, bg=BG2(), fg=MUT() if pr else TX(), font=F(10),
                     anchor="w", width=38).pack(side="left", padx=(4,0), pady=6)
            if pr: tk.Label(row, text="система", bg=BG2(), fg=YL(), font=F(8)).pack(side="left", padx=(6,0))
            tk.Label(row, text=str(pid), bg=BG2(), fg=DIM(), font=F(9,m=True),
                     width=10, anchor="w").pack(side="left")
            c = RD() if mem>300*1024*1024 else (YL() if mem>100*1024*1024 else DIM())
            tk.Label(row, text=hs(mem) if mem else "—", bg=BG2(), fg=c,
                     font=F(9,m=True), width=14, anchor="e").pack(side="right", padx=(0,12))
            self.rows[pid] = {"v":var,"p":pr,"m":mem}
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
            self.sl.configure(text=f"Выбрано: {n}   ~{hs(freed)}", fg=AC())
        else: self.sl.configure(text="Выбрано: 0", fg=DIM())
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
        if not self.sel: Toast(self.app, "Ничего не выбрано", "warn"); return
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
        super().__init__(m, app, "Очистка диска", "Освобождение места")
        self.ch = {}
        self.dh = tk.Frame(self, bg=BG()); self.dh.pack(fill="x", padx=26, pady=(12,0))
        cc = Card(self, r=14, py=14); cc.pack(fill="both", expand=True, padx=26, pady=(10,0))
        tk.Label(cc.body, text="Что чистить", bg=BG2(), fg=TX(), font=F(12,"bold"), anchor="w").pack(anchor="w", pady=(0,8))
        self.ch_holder = tk.Frame(cc.body, bg=BG2()); self.ch_holder.pack(fill="both", expand=True)
        bot = tk.Frame(self, bg=BG()); bot.pack(fill="x", padx=26, pady=(12,20))
        self.fl = tk.Label(bot, text="Освобождено: —", bg=BG(), fg=DIM(), font=F(10), anchor="w")
        self.fl.pack(side="left")
        Btn(bot, "🧹 Очистить", w=160, h=42, cmd=self._clr).pack(side="right", padx=(0,8))
        Btn(bot, "Всё", w=100, h=42, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(), cmd=self._all).pack(side="right")
        self.after(200, self.refresh)
    def refresh(self):
        for w in self.dh.winfo_children(): w.destroy()
        for w in self.ch_holder.winfo_children(): w.destroy()
        for d in list_drives():
            c = Card(self.dh, r=12, py=12); c.pack(fill="x", pady=4)
            c.set_hover(AC())
            tk.Label(c.body, text="▦", bg=BG2(), fg=AC(), font=F(20,"bold")).pack(side="left", padx=(0,12))
            col = tk.Frame(c.body, bg=BG2()); col.pack(side="left", fill="both", expand=True)
            pct = d["p"]; cl = RD() if pct>=85 else (YL() if pct>=65 else AC())
            tk.Label(col, text=d["m"], bg=BG2(), fg=TX(), font=F(13,"bold"), anchor="w").pack(anchor="w")
            tk.Label(col, text=f"{hs(d['u'])} / {hs(d['t'])}   ·   Свободно: {hs(d['f'])}",
                     bg=BG2(), fg=DIM(), font=F(9), anchor="w").pack(anchor="w", pady=(2,4))
            hb = HeatBar(col, height=10); hb.pack(fill="x"); hb.set(pct/100.0)
            tk.Label(c.body, text=f"{pct:.0f}%", bg=BG2(), fg=cl, font=F(14,"bold"), width=6).pack(side="right")
        self.ch = {}
        for k, t in clean_targets().items():
            if not t.get("p") or not os.path.isdir(t["p"]): continue
            r = tk.Frame(self.ch_holder, bg=BG2()); r.pack(fill="x", pady=3)
            v = tk.BooleanVar(value=True)
            self.ch[k] = {"v":v, "p":t["p"], "n":t["n"]}
            tk.Checkbutton(r, text=t["n"], variable=v, bg=BG2(), fg=TX(),
                           activebackground=BG2(), activeforeground=TX(),
                           selectcolor=BG1(), font=F(10), anchor="w", bd=0,
                           highlightthickness=0).pack(side="left", padx=(4,0))
            try: tk.Label(r, text=hs(dir_size(t["p"])), bg=BG2(), fg=AC(),
                          font=F(9,"bold")).pack(side="right", padx=(0,8))
            except: pass
    def _all(self):
        s = list(self.ch.keys())
        if not s: return
        if not messagebox.askyesno("Очистка", f"Очистить всё ({len(s)})?"): return
        self._run(s)
    def _clr(self):
        s = [k for k, v in self.ch.items() if v["v"].get()]
        if not s: Toast(self.app, "Ничего не выбрано", "warn"); return
        if not messagebox.askyesno("Очистка", f"Очистить {len(s)} категорий?"): return
        self._run(s)
    def _run(self, keys):
        self.fl.configure(text="Очистка...", fg=DIM())
        def w():
            total = 0
            for k in keys:
                v = self.ch.get(k)
                if not v: continue
                total += clean_dir(v["p"])
            def d():
                self.fl.configure(text=f"Освобождено: {hs(total)}", fg=AC())
                Toast(self.app, f"Освобождено: {hs(total)}", "ok")
                self.after(500, self.refresh)
            self.after(0, d)
        threading.Thread(target=w, daemon=True).start()

class GamePage(Page):
    def __init__(self, m, app):
        super().__init__(m, app, "Игровой буст", "Освобождение ресурсов")
        self.boosted = False
        bc = Card(self, r=14, py=20); bc.pack(fill="x", padx=26, pady=(12,0))
        inner = bc.body
        tk.Label(inner, text="🎮", bg=BG2(), fg=BL(), font=F(48)).pack(side="left", padx=(8,22))
        col = tk.Frame(inner, bg=BG2()); col.pack(side="left", fill="both", expand=True)
        self.title_lbl = tk.Label(col, text="Игровой режим выключен", bg=BG2(), fg=TX(),
                                   font=F(18,"bold"), anchor="w")
        self.title_lbl.pack(anchor="w")
        self.sub_lbl = tk.Label(col, text="Нажмите для освобождения ОЗУ",
                                 bg=BG2(), fg=DIM(), font=F(10), anchor="w")
        self.sub_lbl.pack(anchor="w", pady=(4,12))
        self.boost_btn = Btn(col, "🎮 Включить буст", w=260, h=46, bg=BL(), fg="#04120e",
                              hov="#0ea5e9", pbg=BG2(), cmd=self._boost)
        self.boost_btn.pack(anchor="w")
        sc = Card(self, r=12, py=12); sc.pack(fill="x", padx=26, pady=(12,0))
        tk.Label(sc.body, text="Что делать", bg=BG2(), fg=TX(), font=F(12,"bold"), anchor="w").pack(anchor="w", pady=(0,6))
        self.v_p = tk.BooleanVar(value=True); self.v_pr = tk.BooleanVar(value=True)
        tk.Checkbutton(sc.body, text="План питания High Performance", variable=self.v_p,
                       bg=BG2(), fg=TX(), activebackground=BG2(), selectcolor=BG1(),
                       font=F(10), bd=0, highlightthickness=0).pack(anchor="w")
        tk.Checkbutton(sc.body, text="Повысить приоритет игры", variable=self.v_pr,
                       bg=BG2(), fg=TX(), activebackground=BG2(), selectcolor=BG1(),
                       font=F(10), bd=0, highlightthickness=0).pack(anchor="w")
        kc = Card(self, r=12, py=12); kc.pack(fill="both", expand=True, padx=26, pady=(12,0))
        tk.Label(kc.body, text="Процессы для закрытия (по одному в строке)",
                 bg=BG2(), fg=TX(), font=F(12,"bold"), anchor="w").pack(anchor="w", pady=(0,6))
        self.kb = tk.Text(kc.body, bg=BG1(), fg=TX(), bd=0, height=6, font=F(9,m=True),
                          wrap="none", highlightthickness=1, highlightbackground=BR(),
                          insertbackground=TX(), padx=6, pady=4)
        self.kb.pack(fill="both", expand=True)
        self.kb.insert("1.0", "\n".join(app.cfg.get("game_kill_list",
            ["OneDrive.exe","Teams.exe","Discord.exe","chrome.exe","Steam.exe"])))
        bot = tk.Frame(self, bg=BG()); bot.pack(fill="x", padx=26, pady=(12,20))
        self.info = tk.Label(bot, text="Готов", bg=BG(), fg=DIM(), font=F(10), anchor="w")
        self.info.pack(side="left")
        Btn(bot, "💾 Сохранить", w=160, h=40, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(), cmd=self._save).pack(side="right", padx=(0,8))
        self.unboost_btn = Btn(bot, "⏹ Выключить", w=160, h=40, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(), cmd=self._unboost)
        self.unboost_btn.pack(side="right"); self.unboost_btn.on(False)
    def _save(self):
        lst = [s.strip() for s in self.kb.get("1.0","end").splitlines() if s.strip()]
        self.app.cfg["game_kill_list"] = lst; sj(CFG, self.app.cfg)
        Toast(self.app, "Сохранено", "ok")
    def _boost(self):
        if self.boosted: Toast(self.app, "Уже включено", "warn"); return
        self._save(); self.info.configure(text="Оптимизация...", fg=BL())
        def w():
            kl = set(s.lower() for s in self.app.cfg.get("game_kill_list", []))
            procs = list_procs(); k = 0; freed = 0
            for p in procs:
                if p["name"].lower() in kl and p["name"].lower() not in ("explorer.exe","dwm.exe"):
                    if kill_proc(p["pid"]): k += 1; freed += p["mem"]
            if self.v_p.get():
                try:
                    subprocess.run(["powercfg","/setactive","8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                                   capture_output=True, timeout=5, creationflags=CF)
                except: pass
            def d():
                self.boosted = True
                self.title_lbl.configure(text="🎮 Режим включён", fg=GR())
                self.sub_lbl.configure(text=f"Освобождено: {hs(freed)} · Закрыто: {k}")
                self.info.configure(text="Готово", fg=AC())
                self.unboost_btn.on(True)
                Toast(self.app, f"Освобождено: {hs(freed)}", "ok")
            self.after(0, d)
        threading.Thread(target=w, daemon=True).start()
    def _unboost(self):
        if not self.boosted: return
        try:
            subprocess.run(["powercfg","/setactive","381b4222-f694-41f0-9685-ff5bb260df2e"],
                           capture_output=True, timeout=5, creationflags=CF)
        except: pass
        self.boosted = False
        self.title_lbl.configure(text="Игровой режим выключен", fg=TX())
        self.sub_lbl.configure(text="Система возвращена в обычный режим")
        self.unboost_btn.on(False)
        Toast(self.app, "Буст выключен", "info")

class QuarPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app, "Карантин", "Изолированные файлы")
        w = tk.Frame(self, bg=BG()); w.pack(fill="both", expand=True, padx=26, pady=(12,0))
        self.cv = tk.Canvas(w, bg=BG(), highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(w, command=self.cv.yview); sb.pack(side="right", fill="y")
        self.cv.configure(yscrollcommand=sb.set)
        self.lf = tk.Frame(self.cv, bg=BG())
        self.cv.create_window((0,0), window=self.lf, anchor="nw")
        self.lf.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        Btn(self, "↻ Обновить", w=160, h=42, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(),
            cmd=self.refresh).pack(anchor="e", padx=26, pady=(12,20))
        self.after(200, self.refresh)
    def refresh(self):
        for w in self.lf.winfo_children(): w.destroy()
        if not os.path.isdir(QUAR):
            tk.Label(self.lf, text="Пусто", bg=BG(), fg=MUT(), font=F(11)).pack(pady=40); return
        its = sorted([f for f in os.listdir(QUAR) if f.endswith(".q")], reverse=True)
        if not its:
            tk.Label(self.lf, text="Пусто", bg=BG(), fg=MUT(), font=F(11)).pack(pady=40); return
        for n in its:
            f = os.path.join(QUAR, n); meta = lj(f+".json", {})
            c = Card(self.lf, r=12, py=10); c.pack(fill="x", pady=4)
            tk.Label(c.body, text=os.path.basename(meta.get("orig", n)),
                     bg=BG2(), fg=TX(), font=F(11,"bold"), anchor="w").pack(anchor="w")
            tk.Label(c.body, text=meta.get("orig",""), bg=BG2(), fg=DIM(),
                     font=F(8,m=True), anchor="w").pack(anchor="w", pady=(2,4))
            r = tk.Frame(c.body, bg=BG2()); r.pack(fill="x")
            tk.Label(r, text=f"{meta.get('r','?')}   {hs(meta.get('s',0))}",
                     bg=BG2(), fg=YL(), font=F(9)).pack(side="left")
            Btn(r, "↩", w=36, h=26, r=6, bg=BG3(), fg=AC(), hov=ACS(), bd=BR(),
                fnt=F(10), cmd=lambda ff=f,mm=meta: self._r(ff,mm)).pack(side="right", padx=2)
            Btn(r, "✕", w=36, h=26, r=6, bg=BG3(), fg=RD(), hov=ACS(), bd=BR(),
                fnt=F(10), cmd=lambda ff=f: self._d(ff)).pack(side="right", padx=2)
    def _r(self, f, m):
        o = m.get("orig")
        if not o or not messagebox.askyesno("Восстановить", f"В:\n{o}?"): return
        try:
            os.makedirs(os.path.dirname(o), exist_ok=True)
            shutil.move(f, o)
            if os.path.exists(f+".json"): os.remove(f+".json")
            Toast(self.app, "Восстановлено", "warn"); self.refresh()
        except Exception as e: messagebox.showerror("Ошибка", str(e))
    def _d(self, f):
        if not messagebox.askyesno("Удалить", "Навсегда?"): return
        try:
            os.remove(f)
            if os.path.exists(f+".json"): os.remove(f+".json")
            Toast(self.app, "Удалено", "ok"); self.refresh()
        except Exception as e: messagebox.showerror("Ошибка", str(e))

class UpdPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app, "Обновления", "Загрузка сигнатур")
        c = Card(self, r=14, py=18); c.pack(fill="x", padx=26, pady=(12,0))
        tk.Label(c.body, text="Σ", bg=BG2(), fg=AC(), font=F(32,"bold")).pack(side="left", padx=(0,18))
        col = tk.Frame(c.body, bg=BG2()); col.pack(side="left", fill="both", expand=True)
        self.t = tk.Label(col, text="", bg=BG2(), fg=TX(), font=F(14,"bold"), anchor="w")
        self.t.pack(anchor="w")
        self.s = tk.Label(col, text="", bg=BG2(), fg=DIM(), font=F(10), anchor="w")
        self.s.pack(anchor="w", pady=(2,0))
        self.b = Btn(c.body, "⬇ Обновить", w=180, h=42, pbg=BG2(), cmd=self._go)
        self.b.pack(side="right")
        lg = Card(self, r=12, py=12); lg.pack(fill="both", expand=True, padx=26, pady=(12,20))
        tk.Label(lg.body, text="Лог", bg=BG2(), fg=TX(), font=F(12,"bold"), anchor="w").pack(anchor="w")
        self.l = tk.Text(lg.body, bg=BG1(), fg=DIM(), bd=0, font=F(9,m=True),
                          wrap="word", insertbackground=TX(), highlightthickness=0, padx=8, pady=6)
        self.l.pack(fill="both", expand=True, pady=(6,0))
        self.after(200, self.refresh)
    def refresh(self):
        db = self.app.db
        self.t.configure(text=f"SHA256: {len(db.sha):,}   ·   MD5: {len(db.md5):,}")
        self.s.configure(text=f"Обновлено: {db.upd or 'никогда'}")
    def _go(self):
        self.b.on(False); self.b.txt("Загрузка...")
        self.l.delete("1.0","end")
        def w():
            def lg(m):
                self.after(0, lambda: (self.l.insert("end", m+"\n"), self.l.see("end")))
            try:
                update_sig(self.app.cfg, lg)
                self.app.db = DB()
                self.after(0, self.app.refresh_side)
                self.after(0, self.refresh)
                self.after(0, self.app.pages["dashboard"].refresh)
                self.after(0, lambda: (self.b.on(True), self.b.txt("⬇ Обновить")))
                self.after(0, lambda: Toast(self.app, "База обновлена", "ok"))
            except Exception as e:
                lg(f"! {e}")
                self.after(0, lambda: (self.b.on(True), self.b.txt("⬇ Обновить")))
        threading.Thread(target=w, daemon=True).start()

class SettingsPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app, "Настройки", "Темы, автозапуск, источники")
        w = tk.Frame(self, bg=BG()); w.pack(fill="both", expand=True, padx=26, pady=(12,20))
        cv = tk.Canvas(w, bg=BG(), highlightthickness=0)
        cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(w, command=cv.yview); sb.pack(side="right", fill="y")
        cv.configure(yscrollcommand=sb.set)
        body = tk.Frame(cv, bg=BG()); cv.create_window((0,0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))

        tc = Card(body, r=12, py=14); tc.pack(fill="x", pady=(0,10))
        tk.Label(tc.body, text="🎨 Тема оформления", bg=BG2(), fg=TX(), font=F(13,"bold"), anchor="w").pack(anchor="w", pady=(0,10))
        grid = tk.Frame(tc.body, bg=BG2()); grid.pack(fill="x")
        for i, name in enumerate(THEMES.keys()):
            t = THEMES[name]
            b = tk.Frame(grid, bg=BG2(), cursor="hand2")
            b.grid(row=i//6, column=i%6, padx=4, pady=4)
            cv_ = tk.Canvas(b, width=70, height=44, highlightthickness=0, bg=BG2())
            cv_.pack()
            rr(cv_, 1, 1, 69, 43, r=8, fill=t["ac"], outline=t["ac2"], width=2)
            cv_.create_text(35, 22, text=name, fill="#04120e", font=F(9,"bold"))
            cv_.bind("<Button-1>", lambda e, n=name: self._apply(n))
            tk.Label(b, text=name, bg=BG2(), fg=DIM(), font=F(8)).pack()
        cc = tk.Frame(tc.body, bg=BG2()); cc.pack(fill="x", pady=(12,0))
        tk.Label(cc, text="Свой цвет:", bg=BG2(), fg=TX(), font=F(10)).pack(side="left", padx=(0,8))
        self.col_prev = tk.Canvas(cc, width=44, height=28, highlightthickness=0, bg=BG2())
        self.col_prev.pack(side="left", padx=(0,8))
        rr(self.col_prev, 1, 1, 43, 27, r=6, fill=TH.AC, outline=TH.AC2, width=2)
        Btn(cc, "Выбрать цвет…", w=160, h=32, bg=BG3(), fg=TX(), hov=BR2(), bd=BR(),
            fnt=F(10), cmd=self._pick_color).pack(side="left", padx=(0,8))
        Btn(cc, "Сохранить тему", w=160, h=32, bg=AC(), fg="#04120e", hov=AC2(),
            fnt=F(10), cmd=self._save_theme).pack(side="left")
        self._pick_col = [TH.AC, TH.AC2, TH.ACS, TH.BL, TH.PU]

        s1 = Card(body, r=12, py=14); s1.pack(fill="x", pady=(0,10))
        tk.Label(s1.body, text="Система", bg=BG2(), fg=TX(), font=F(13,"bold"), anchor="w").pack(anchor="w", pady=(0,8))
        self.v_auto = tk.BooleanVar(value=Auto.enabled())
        tk.Checkbutton(s1.body, text="Запускать при входе", variable=self.v_auto,
                       command=self._tga, bg=BG2(), fg=TX(), activebackground=BG2(),
                       selectcolor=BG1(), font=F(10), bd=0, highlightthickness=0).pack(anchor="w")
        self.v_heur = tk.BooleanVar(value=bool(app.cfg.get("heuristics", True)))
        tk.Checkbutton(s1.body, text="Эвристика при сканировании", variable=self.v_heur,
                       bg=BG2(), fg=TX(), activebackground=BG2(),
                       selectcolor=BG1(), font=F(10), bd=0, highlightthickness=0).pack(anchor="w")
        self.v_fx = tk.BooleanVar(value=bool(app.cfg.get("fx_heavy", True)))
        tk.Checkbutton(s1.body, text="Тяжёлые эффекты (Небула, Кометы)",
                       variable=self.v_fx, bg=BG2(), fg=TX(), activebackground=BG2(),
                       selectcolor=BG1(), font=F(10), bd=0, highlightthickness=0).pack(anchor="w")

        s3 = Card(body, r=12, py=14); s3.pack(fill="x", pady=(0,10))
        tk.Label(s3.body, text="Источники сигнатур", bg=BG2(), fg=TX(), font=F(13,"bold"), anchor="w").pack(anchor="w", pady=(0,8))
        self.src = tk.Text(s3.body, bg=BG1(), fg=TX(), bd=0, height=6, font=F(9,m=True),
                            wrap="none", highlightthickness=1, highlightbackground=BR(),
                            insertbackground=TX(), padx=6, pady=4)
        self.src.pack(fill="x")
        self.src.insert("1.0", "\n".join(app.cfg.get("sources", [
            "https://bazaar.abuse.ch/export/txt/sha256/recent/",
            "https://threatfox.abuse.ch/export/csv/sha256/recent/",
            "https://urlhaus.abuse.ch/downloads/text/"])))
        act = tk.Frame(body, bg=BG()); act.pack(fill="x", pady=(16,10))
        Btn(act, "💾 Сохранить", w=160, cmd=self._save).pack(side="left", padx=(0,10))
        Btn(act, "↻ Сброс", w=120, bg=BG3(), fg=DIM(), hov=BR2(), bd=BR(), cmd=self.refresh).pack(side="left")
    def _apply(self, name):
        TH.apply(name); TH.save()
        Toast(self.app, f"Тема: {name}", "info")
        self.app.apply_theme_later()
    def _pick_color(self):
        col = colorchooser.askcolor(initialcolor=TH.AC, title="Акцентный цвет")[1]
        if not col: return
        self._pick_col[0] = col
        self._pick_col[1] = lerp(col, "#000000", 0.2)
        self._pick_col[2] = lerp(col, "#000000", 0.75)
        self.col_prev.delete("all")
        rr(self.col_prev, 1, 1, 43, 27, r=6, fill=col, outline=self._pick_col[1], width=2)
    def _save_theme(self):
        TH.set_custom(self._pick_col[0], self._pick_col[1], self._pick_col[2],
                      self._pick_col[3], self._pick_col[4])
        TH.save()
        Toast(self.app, "Своя тема сохранена", "ok")
        self.app.apply_theme_later()
    def _tga(self):
        Auto.toggle()
        self.v_auto.set(Auto.enabled())
        Toast(self.app, "Включено" if Auto.enabled() else "Выключено", "ok")
    def refresh(self):
        self.v_auto.set(Auto.enabled())
        self.v_heur.set(bool(self.app.cfg.get("heuristics", True)))
        self.v_fx.set(bool(self.app.cfg.get("fx_heavy", True)))
        self.src.delete("1.0","end")
        self.src.insert("1.0", "\n".join(self.app.cfg.get("sources", [])))
    def _save(self):
        self.app.cfg["heuristics"] = bool(self.v_heur.get())
        self.app.cfg["fx_heavy"] = bool(self.v_fx.get())
        self.app.cfg["sources"] = [s.strip() for s in self.src.get("1.0","end").splitlines() if s.strip()]
        if sj(CFG, self.app.cfg): Toast(self.app, "Сохранено", "ok")

# ═══════ NET PAGE (ИСПРАВЛЕНО) ═══════
class NetPage(Page):
    def __init__(self, m, app):
        super().__init__(m, app, "Оптимизация интернета",
                         "DNS, TCP/IP, Winsock, пинг, speedtest")
        self.adapter = ""

        info = Card(self, r=14, py=14); info.pack(fill="x", padx=26, pady=(12,0))
        info.set_hover(AC())
        hdr = tk.Frame(info.body, bg=BG2()); hdr.pack(fill="x")
        tk.Label(hdr, text="Текущее соединение", bg=BG2(), fg=TX(),
                 font=F(12,"bold")).pack(side="left")
        StatusPulse(hdr, size=14, color_fn=GR).pack(side="right")
        self.info_lbl = tk.Label(info.body, text="Загрузка...", bg=BG2(), fg=DIM(),
                                 font=F(9, m=True), anchor="w", justify="left")
        self.info_lbl.pack(anchor="w", pady=(6,0))

        grid = tk.Frame(self, bg=BG()); grid.pack(fill="x", padx=26, pady=(12,0))
        for i in range(3): grid.grid_columnconfigure(i, weight=1)
        btns = [
            ("🧹 Flush DNS",      AC(),    lambda: self._do("flush_dns")),
            ("🔄 Reset Winsock",  YL(),    lambda: self._do("reset_winsock")),
            ("🔄 Reset TCP/IP",   YL(),    lambda: self._do("reset_tcp")),
            ("⚡ Cloudflare DNS", BL(),    lambda: self._do("dns_cf")),
            ("🅖 Google DNS",     BL(),    lambda: self._do("dns_goog")),
            ("↩ DNS Auto",        BG3(),   lambda: self._do("dns_auto")),
            ("🚀 TCP Optimize",   PU(),    lambda: self._do("tcp_opt")),
            ("📡 Reset ARP",      BG3(),   lambda: self._do("arp_reset")),
            ("🔌 Адаптер",        RD(),    lambda: self._do("adapter_reset")),
            ("📶 Speedtest",      GR(),    lambda: self._do("speedtest")),
            ("🏓 Ping test",      BL(),    lambda: self._do("ping")),
            ("🌐 Обновить инфо",  AC(),    lambda: self._do("info")),
        ]
        for i, (label, colf, cmd) in enumerate(btns):
            if colf == BG3():
                fg = DIM(); hov = BR2(); bd_c = BR()
            elif colf == AC():
                fg = "#04120e"; hov = AC2(); bd_c = None
            elif colf == YL():
                fg = "#1a1204"; hov = "#d9a017"; bd_c = None
            elif colf == RD():
                fg = "#ffffff"; hov = "#e04b43"; bd_c = None
            else:
                fg = "#04120e"; hov = colf; bd_c = None
            Btn(grid, label, w=200, h=42, bg=colf, fg=fg, hov=hov,
                bd=bd_c, cmd=cmd).grid(row=i//3, column=i%3,
                                       padx=4, pady=4, sticky="ew")

        lg = Card(self, r=12, py=12); lg.pack(fill="both", expand=True, padx=26, pady=(12,20))
        tk.Label(lg.body, text="Лог", bg=BG2(), fg=TX(), font=F(12,"bold"), anchor="w").pack(anchor="w")
        self.lg = tk.Text(lg.body, bg=BG1(), fg=DIM(), bd=0, font=F(9,m=True),
                          wrap="word", insertbackground=TX(), highlightthickness=0,
                          padx=8, pady=6)
        self.lg.pack(fill="both", expand=True, pady=(6,0))
        self.lg.tag_config("ok", foreground=AC())
        self.lg.tag_config("err", foreground=RD())
        self.lg.tag_config("warn", foreground=YL())
        self.lg.tag_config("info", foreground=BL())
        self.lg.tag_config("cmd", foreground=PU())

        self.after(200, self._detect_adapter)
        self.after(300, self._do, "info")

    def _log(self, t, tag=None):
        def do():
            try:
                self.lg.insert("end", t+"\n", tag or ""); self.lg.see("end")
            except: pass
        self.after(0, do)

    def _detect_adapter(self):
        def w():
            try:
                rc, out, _ = run(["wmic","nic","where","NetEnabled=true",
                                   "get","NetConnectionID"], timeout=10)
                names = [l.strip() for l in out.splitlines()
                         if l.strip() and "NetConnection" not in l]
                self.adapter = names[0] if names else "Wi-Fi"
                self._log(f"▸ Активный адаптер: {self.adapter}", "info")
            except:
                self.adapter = "Wi-Fi"
        threading.Thread(target=w, daemon=True).start()

    def _do(self, action):
        def w():
            try:
                if action == "info":
                    self._info()
                elif action == "flush_dns":
                    self._log("→ ipconfig /flushdns", "cmd")
                    rc, out, err = run(["ipconfig","/flushdns"], timeout=15)
                    self._log(out.strip() or err or "ok", "ok" if rc==0 else "err")
                elif action == "reset_winsock":
                    self._log("→ netsh winsock reset (треб. админ)", "cmd")
                    rc, out, err = run(["netsh","winsock","reset"], timeout=30)
                    self._log(out.strip() or err, "ok" if rc==0 else "err")
                    if rc == 0: self._log("⚠ Перезагрузка рекомендуется", "warn")
                elif action == "reset_tcp":
                    self._log("→ netsh int ip reset (треб. админ)", "cmd")
                    rc, out, err = run(["netsh","int","ip","reset"], timeout=30)
                    self._log(out.strip() or err, "ok" if rc==0 else "err")
                    if rc == 0: self._log("⚠ Перезагрузка рекомендуется", "warn")
                elif action in ("dns_cf","dns_goog","dns_auto"):
                    if not self.adapter: self._detect_adapter(); time.sleep(0.5)
                    if action == "dns_cf":
                        d1, d2, label = "1.1.1.1", "1.0.0.1", "Cloudflare"
                    elif action == "dns_goog":
                        d1, d2, label = "8.8.8.8", "8.8.4.4", "Google"
                    else:
                        self._log(f"→ DNS auto для {self.adapter}", "cmd")
                        rc1,_,e1 = run(["netsh","interface","ip","set","dns",
                                        self.adapter,"dhcp"], timeout=15)
                        rc2,_,e2 = run(["netsh","interface","ipv6","set","dns",
                                        self.adapter,"dhcp"], timeout=15)
                        self._log(f"DNS auto: {'ok' if rc1==0 else e1}", "ok" if rc1==0 else "err")
                        return
                    self._log(f"→ DNS {label}: {d1}, {d2} на {self.adapter}", "cmd")
                    rc1,_,e1 = run(["netsh","interface","ip","set","dns",
                                    self.adapter,"static",d1,"primary"], timeout=15)
                    rc2,_,e2 = run(["netsh","interface","ip","add","dns",
                                    self.adapter,d2,"index=2"], timeout=15)
                    self._log(f"Primary: {'ok' if rc1==0 else e1}  |  Secondary: {'ok' if rc2==0 else e2}",
                              "ok" if rc1==0 else "err")
                    run(["ipconfig","/flushdns"], timeout=10)
                elif action == "tcp_opt":
                    self._log("→ TCP optimizer", "cmd")
                    steps = [
                        (["netsh","int","tcp","set","global","autotuninglevel=normal"], "Auto-tuning normal"),
                        (["netsh","int","tcp","set","global","rss=enabled"], "RSS enabled"),
                        (["netsh","int","tcp","set","heuristics","disabled"], "Heuristics off"),
                        (["netsh","int","tcp","set","global","ecncapability=enabled"], "ECN on"),
                    ]
                    for args, label in steps:
                        rc, _, err = run(args, timeout=10)
                        self._log(f"  {'✓' if rc==0 else '✗'} {label}", "ok" if rc==0 else "err")
                    try:
                        import winreg
                        base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
                            i = 0
                            while True:
                                try: sub = winreg.EnumKey(root, i); i += 1
                                except OSError: break
                                try:
                                    with winreg.OpenKey(root, sub, 0,
                                                        winreg.KEY_SET_VALUE) as k:
                                        winreg.SetValueEx(k, "TcpAckFrequency", 0,
                                                          winreg.REG_DWORD, 1)
                                        winreg.SetValueEx(k, "TCPNoDelay", 0,
                                                          winreg.REG_DWORD, 1)
                                except: pass
                        self._log("  ✓ Nagle off (TcpAckFrequency=1, TCPNoDelay=1)", "ok")
                    except Exception as e:
                        self._log(f"  ✗ Nagle: {e} (нужен админ)", "err")
                    self._log("⚠ Перезагрузка рекомендуется", "warn")
                elif action == "arp_reset":
                    self._log("→ arp -d *", "cmd")
                    rc, out, err = run(["arp","-d","*"], timeout=10)
                    self._log("ok" if rc==0 else (err or "ошибка"), "ok" if rc==0 else "err")
                elif action == "adapter_reset":
                    if not self.adapter: self._detect_adapter(); time.sleep(0.5)
                    if not messagebox.askyesno("Перезапуск адаптера",
                        f"Отключить и включить «{self.adapter}»?\nСоединение пропадёт на ~5 сек."):
                        return
                    self._log(f"→ disable {self.adapter}", "cmd")
                    run(["netsh","interface","set","interface",
                         self.adapter,"admin=disable"], timeout=15)
                    time.sleep(3)
                    self._log(f"→ enable {self.adapter}", "cmd")
                    rc,_,err = run(["netsh","interface","set","interface",
                                    self.adapter,"admin=enable"], timeout=15)
                    self._log("ok" if rc==0 else err, "ok" if rc==0 else "err")
                elif action == "speedtest":
                    self._speedtest()
                elif action == "ping":
                    self._ping()
            except Exception as e:
                self._log(f"! {e}", "err")
        threading.Thread(target=w, daemon=True).start()

    def _info(self):
        rc, out, _ = run(["ipconfig","/all"], timeout=15)
        keep = []
        for ln in out.splitlines():
            if any(k in ln for k in ("Адаптер","adapter","IPv4","IP Address",
                                      "DNS","Шлюз","Gateway","Основной",
                                      "Маска","Subnet","DHCP")):
                keep.append(ln.rstrip())
        text = "\n".join(keep[:12])
        def do():
            self.info_lbl.configure(text=text or "Нет данных")
            self._log("── Информация о сети ──", "info")
            self._log(text or "Нет данных")
        self.after(0, do)

    def _speedtest(self):
        self._log("── Speedtest (20 МБ с Cloudflare) ──", "info")
        try:
            url = "https://speed.cloudflare.com/__down?bytes=20000000"
            t0 = time.time(); total = 0
            with urlopen(Request(url, headers={"User-Agent": f"{APP}/{VER}"}),
                          timeout=60) as r:
                while True:
                    b = r.read(65536)
                    if not b: break
                    total += len(b)
                    if time.time()-t0 > 30: break
            dt = time.time() - t0
            mbps = (total * 8 / 1_000_000) / dt if dt > 0 else 0
            self._log(f"  Скачано: {hs(total)}  за  {dt:.2f} с", "ok")
            self._log(f"  Скорость: {mbps:.2f} Мбит/с  ({mbps/8:.2f} МБ/с)", "ok")
            try: Toast(self.app, f"{mbps:.1f} Мбит/с", "ok")
            except: pass
        except Exception as e:
            self._log(f"  ✗ {e}", "err")

    def _ping(self):
        self._log("── Ping test ──", "info")
        for host in ("8.8.8.8", "1.1.1.1", "ya.ru", "google.com"):
            try:
                rc, out, _ = run(["ping","-n","2",host], timeout=10)
                if rc == 0:
                    times = re.findall(r"(?:time|время)[=<]\s*(\d+)\s*ms", out, re.I)
                    avg = int(sum(int(t) for t in times)/len(times)) if times else "?"
                    tag = "ok" if isinstance(avg, int) and avg < 100 else "warn"
                    self._log(f"  {host:16}  {avg} ms", tag)
                else:
                    self._log(f"  {host:16}  ✗ нет ответа", "err")
            except Exception as e:
                self._log(f"  {host:16}  ✗ {e}", "err")

# ═══════ APP ═══════
class App(tk.Tk):
    def __init__(self, cfg, db):
        super().__init__()
        self.cfg, self.db = cfg, db
        self._restart_id = None
        self.title(f"{APP} {VER}")
        self.geometry("1320x840"); self.minsize(1150, 720)
        self.configure(bg=BG())
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self._side(); self._content()
        self.after(200, lambda: round_win(self))
        self.go("dashboard")
    def _side(self):
        sb = tk.Frame(self, bg=BG1(), width=240)
        sb.grid(row=0, column=0, sticky="nsw"); sb.pack_propagate(False)
        lg = tk.Frame(sb, bg=BG1()); lg.pack(fill="x", padx=18, pady=(20, 18))
        lc = tk.Canvas(lg, width=40, height=40, bg=BG1(), highlightthickness=0)
        lc.pack(side="left")
        for i in range(5):
            lc.create_oval(2+i*4, 2+i*4, 38-i*4, 38-i*4,
                           fill=lerp(BG1(), AC(), 0.08+i*0.14), outline="")
        lc.create_text(20, 20, text="⛨", fill="#04120e", font=F(18,"bold"))
        box = tk.Frame(lg, bg=BG1()); box.pack(side="left", padx=(10,0))
        tk.Label(box, text="Unlock", bg=BG1(), fg=TX(), font=F(15,"bold")).pack(anchor="w")
        tk.Label(box, text="Antivirus", bg=BG1(), fg=AC(), font=F(12)).pack(anchor="w")
        self.navs = {}
        items = [
            ("dashboard","⌂","Главная"),
            ("scan","⌕","Сканирование"),
            ("net","🌐","Интернет"),
            ("games","🎮","Игры"),
            ("memory","▦","Память"),
            ("disk","⛁","Диск"),
            ("quarantine","▣","Карантин"),
            ("updates","↓","Обновления"),
            ("settings","⚙","Настройки"),
        ]
        for k, ic, t in items:
            b = NavBtn(sb, ic, t, cmd=lambda kk=k: self.go(kk))
            b.pack(fill="x", padx=10, pady=2)
            self.navs[k] = b
        bot = tk.Frame(sb, bg=BG1()); bot.pack(side="bottom", fill="x", padx=18, pady=16)
        tk.Frame(bot, bg=BR(), height=1).pack(fill="x", pady=(0,10))
        self.ss = tk.Label(bot, text="", bg=BG1(), fg=MUT(), font=F(9), anchor="w", justify="left")
        self.ss.pack(fill="x")
        self.refresh_side()
    def _content(self):
        self.cont = tk.Frame(self, bg=BG())
        self.cont.grid(row=0, column=1, sticky="nsew")
        self.cont.grid_rowconfigure(0, weight=1); self.cont.grid_columnconfigure(0, weight=1)
        self.aurora = AuroraBG(self.cont); self.aurora.place(x=0, y=0, relwidth=1, relheight=1)
        heavy = self.cfg.get("fx_heavy", True)
        self.nebula = None
        self.comets = None
        if heavy:
            self.nebula = Nebula(self.cont)
            self.nebula.place(x=0, y=0, relwidth=1, relheight=1)
        self.stars = StarField(self.cont, count=50)
        self.stars.place(x=0, y=0, relwidth=1, relheight=1)
        self.particles = ParticleField(self.cont, count=30)
        self.particles.place(x=0, y=0, relwidth=1, relheight=1)
        if heavy:
            self.comets = CometTrail(self.cont)
            self.comets.place(x=0, y=0, relwidth=1, relheight=1)
        self.grid_pulse = GridPulse(self.cont); self.grid_pulse.place(x=0, y=0, relwidth=1, relheight=1)
        self.scanline = ScanLine(self.cont); self.scanline.place(x=0, y=0, relwidth=1, relheight=1)
        self.crosshair = Crosshair(self.cont); self.crosshair.place(x=0, y=0, relwidth=1, relheight=1)
        self.pages_holder = tk.Frame(self.cont, bg=BG())
        self.pages_holder.place(x=0, y=0, relwidth=1, relheight=1)
        self.pages_holder.grid_rowconfigure(0, weight=1); self.pages_holder.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for k, cls in [("dashboard",DashboardPage),("scan",ScanPage),("net",NetPage),
                       ("games",GamePage),("memory",MemPage),("disk",DiskPage),
                       ("quarantine",QuarPage),("updates",UpdPage),("settings",SettingsPage)]:
            p = cls(self.pages_holder, self); p.grid(row=0, column=0, sticky="nsew")
            self.pages[k] = p
    def go(self, k):
        if k not in self.pages: return
        self.pages[k].tkraise()
        for kk, b in self.navs.items(): b.act(kk == k)
        if hasattr(self.pages[k], "refresh"): self.pages[k].refresh()
    def refresh_side(self):
        u = (self.db.upd or "—")[:10]
        self.ss.configure(text=f"База: {u}\nSHA256: {len(self.db.sha):,}\nТема: {TH.name}")
    def apply_theme_later(self):
        if self._restart_id:
            try: self.after_cancel(self._restart_id)
            except: pass
        try:
            self.deiconify(); self.lift()
        except: pass
        Toast(self, "Тема применится после перезапуска", "info")
        self._restart_id = self.after(1500, self._ask_restart)
    def _ask_restart(self):
        self._restart_id = None
        if messagebox.askyesno("Перезапуск", "Закрыть приложение для применения темы?"):
            self.destroy()
            os.execl(sys.executable, sys.executable, *sys.argv)

# ═══════ SPLASH ═══════
class Splash(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} {VER}")
        w, h = 600, 460
        self.configure(bg=BG())
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        round_win(self)
        self.bg1 = AuroraBG(self); self.bg1.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg2 = ParticleField(self, count=25); self.bg2.place(x=0, y=0, relwidth=1, relheight=1)
        main = tk.Frame(self, bg=BG2(), highlightthickness=1, highlightbackground=BR())
        main.place(x=1, y=1, width=w-2, height=h-2)
        self.canvas = tk.Canvas(main, width=140, height=140, bg=BG2(), highlightthickness=0)
        self.canvas.pack(pady=(40,0))
        title = tk.Frame(main, bg=BG2()); title.pack(pady=(14,0))
        tk.Label(title, text="Unlock", bg=BG2(), fg=TX(), font=F(30,"bold")).pack(side="left")
        tk.Label(title, text="Antivirus", bg=BG2(), fg=AC(), font=F(30,"bold")).pack(side="left")
        tk.Label(main, text=f"Версия {VER}  ·  Hypervisual  ·  Open Source",
                 bg=BG2(), fg=MUT(), font=F(10)).pack(pady=(8,24))
        self.status = tk.Label(main, text="Инициализация...", bg=BG2(), fg=DIM(), font=F(11))
        self.status.pack()
        self.progress = GradientProgress(main, height=6)
        self.progress.pack(fill="x", padx=60, pady=(14,8))
        self.pct = tk.Label(main, text="0%", bg=BG2(), fg=AC(), font=F(10,"bold"))
        self.pct.pack()
        tk.Label(main, text="Спасибо, что пользуетесь!",
                 bg=BG2(), fg=MUT(), font=F(9)).pack(side="bottom", pady=14)
        self._angle = 0; self._prog = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(30, self._tick)
    def _on_destroy(self, e=None):
        if e and e.widget is not self: return
        self._alive = False
    def _tick(self):
        if not self._alive or not self.winfo_exists(): return
        try:
            self._angle = (self._angle + 6) % 360
            self._draw_logo(); self.progress.set(self._prog)
            self.pct.configure(text=f"{int(self._prog*100)}%")
        except: pass
        self.after(35, self._tick)
    def _draw_logo(self):
        c = self.canvas; c.delete("all")
        cx = cy = 70; r = 40
        for off, col in ((0, AC()), (180, BL())):
            c.create_arc(cx-58, cy-58, cx+58, cy+58, start=self._angle+off, extent=70,
                         outline=col, width=4, style="arc")
        pulse = (math.sin(time.time()*4)+1)/2
        for i in range(8, 0, -1):
            t = i/8
            rr_ = (r+12)*(1+pulse*0.08)*t
            col = lerp(BG2(), AC(), 0.13*(1-t)+0.03)
            c.create_oval(cx-rr_, cy-rr_, cx+rr_, cy+rr_, fill=col, outline="")
        cy_s = cy - 0.025*r
        c.create_arc(cx-r, cy_s-r, cx+r, cy_s+r*0.55, start=0, extent=180,
                     fill=AC(), outline="", style="chord")
        pts = [cx-r,cy_s+r*0.05, cx-r*0.5,cy_s+r*0.55, cx,cy_s+r*1.05,
               cx+r*0.5,cy_s+r*0.55, cx+r,cy_s+r*0.05]
        c.create_polygon(pts, fill=AC(), outline="", smooth=True)
        c.create_line(cx-r*0.35,cy_s+r*0.05, cx-r*0.05,cy_s+r*0.32,
                      cx+r*0.4,cy_s-r*0.25, fill="#04120e", width=5,
                      capstyle="round", joinstyle="round")
    def set_status(self, txt, prog=None):
        try:
            self.status.configure(text=txt)
            if prog is not None: self._prog = prog
            self.update_idletasks()
        except: pass
    def finish(self, cb):
        self._alive = False
        try: self.destroy()
        except: pass
        cb()

# ═══════ MAIN ═══════
def main():
    if WIN:
        try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except: pass
    if not os.path.exists(CFG):
        sj(CFG, {"sources": [
            "https://bazaar.abuse.ch/export/txt/sha256/recent/",
            "https://threatfox.abuse.ch/export/csv/sha256/recent/",
            "https://urlhaus.abuse.ch/downloads/text/"],
            "heuristics": True, "max_file_size_mb": 500, "scan_threads": 4,
            "last_update": None, "theme": "Mint", "fx_heavy": True})
    cfg = lj(CFG, {})
    for k, v in {"heuristics":True,"max_file_size_mb":500,"scan_threads":4,
                 "fx_heavy":True,"theme":"Mint"}.items():
        cfg.setdefault(k, v)
    db = DB()

    splash = Splash()
    stages = [
        (0.05, "Инициализация..."),
        (0.18, "Загрузка конфигурации..."),
        (0.32, f"Сигнатур в базе: {len(db.sha):,}"),
        (0.55, "Проверка источников..."),
        (0.72, "Запуск интерфейса..."),
        (0.88, "Подготовка модулей..."),
        (1.00, "Готово!"),
    ]
    def animate(i=0):
        if i >= len(stages):
            def start():
                app = App(cfg, db)
                app.mainloop()
            try: splash.finish(start)
            except Exception as e:
                print("Splash finish error:", e)
                app = App(cfg, db)
                app.mainloop()
            return
        prog, txt = stages[i]
        try: splash.set_status(txt, prog)
        except: pass
        try: splash.after(280, lambda: animate(i+1))
        except: pass
    splash.after(400, animate)
    splash.mainloop()

if __name__ == "__main__":
    main()
