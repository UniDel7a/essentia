"""
Recursively resolve and copy transitive DLL dependencies for the essentia
Python package on Windows/MSYS2.

After pip install (or setup.py install) on Windows, the _essentia.pyd
extension and its .py files are installed, but the runtime DLL dependencies
(libavcodec, libfftw3f, etc.) are NOT bundled -- they live in the MSYS2
MinGW bin directory.  This script finds every DLL transitively needed by
_essentia.pyd and copies them into the essentia site-package directory so
that ``import essentia`` works without adding MinGW to PATH.

Usage:
    python windows/resolve_dlls.py          # from the essentia repo root
    python resolve_dlls.py                  # if cwd is already the repo root
"""

import os
import shutil
import subprocess
import sys
import site


# ---------------------------------------------------------------------------
# 1. Locate the essentia package directory
# ---------------------------------------------------------------------------
def find_essentia_package():
    search_paths = []
    try:
        search_paths.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        search_paths.append(os.path.join(site.getuserbase(),
                                         'Lib', 'site-packages'))
    except Exception:
        pass
    search_paths.extend(sys.path)

    for p in search_paths:
        candidate = os.path.join(p, 'essentia')
        if os.path.isdir(candidate):
            return candidate
    return None


ESSENTIA_DIR = find_essentia_package()
if not ESSENTIA_DIR:
    print("ERROR: could not locate essentia package directory")
    sys.exit(1)
print(f"Essentia package: {ESSENTIA_DIR}")


# ---------------------------------------------------------------------------
# 2. Locate the MSYS2 MinGW bin directory
# ---------------------------------------------------------------------------
def find_mingw_bin():
    # Strategy A: MINGW_PREFIX is set inside MSYS2 MINGW64 shells
    mp = os.environ.get('MINGW_PREFIX', '')
    if mp:
        bindir = os.path.join(mp, 'bin')
        if os.path.isdir(bindir):
            return os.path.abspath(bindir)

    # Strategy B: g++ is on PATH, derive bin dir from it
    gpp = shutil.which('g++')
    if gpp:
        bindir = os.path.dirname(os.path.abspath(gpp))
        if os.path.isdir(bindir):
            return bindir

    return None


MINGW_BIN = find_mingw_bin()
if not MINGW_BIN:
    print("ERROR: could not locate MinGW bin directory")
    print("Make sure MSYS2 MinGW is installed and g++ is on your PATH,")
    print("or run this script from an MSYS2 MINGW64 shell.")
    sys.exit(1)

OBJDUMP = os.path.join(MINGW_BIN, 'objdump.exe')
if not os.path.isfile(OBJDUMP):
    print(f"ERROR: objdump not found at {OBJDUMP}")
    sys.exit(1)

print(f"MinGW bin:     {MINGW_BIN}")


# ---------------------------------------------------------------------------
# 3. System DLLs that ship with Windows and must NOT be copied
# ---------------------------------------------------------------------------
_SYSTEM_DLLS = frozenset(d.lower() for d in [
    'KERNEL32.dll', 'msvcrt.dll', 'ole32.dll', 'WS2_32.dll',
    'ADVAPI32.dll', 'GDI32.dll', 'USER32.dll', 'SHELL32.dll',
    'SHLWAPI.dll', 'OLEAUT32.dll', 'COMCTL32.dll', 'COMDLG32.dll',
    'WININET.dll', 'WINMM.dll', 'WINSPOOL.DRV', 'IMM32.dll',
    'MSACM32.dll', 'VERSION.dll', 'WLDAP32.dll', 'CRYPT32.dll',
    'BCRYPT.dll', 'NORMALIZ.dll', 'SECUR32.dll', 'DNSAPI.dll',
    'IPHLPAPI.dll', 'MPR.dll', 'NETAPI32.dll', 'PSAPI.dll',
    'RPCRT4.dll', 'SETUPAPI.dll', 'USERENV.dll',
    'UxTheme.dll', 'WINTRUST.dll', 'WTSAPI32.dll',
    'ntdll.dll', 'MSIMG32.dll', 'gdiplus.dll', 'DWrite.dll',
    'USP10.dll', 'WSOCK32.dll', 'ncrypt.dll', 'bcryptprimitives.dll',
])


def is_system_dll(name):
    nl = name.lower()
    if nl.startswith('python') or nl.startswith('api-ms-win-'):
        return True
    return nl in _SYSTEM_DLLS


# ---------------------------------------------------------------------------
# 4. Dependency scanning using objdump
# ---------------------------------------------------------------------------
def get_dll_dependencies(dll_path):
    """Return list of DLL names that *dll_path* links against."""
    try:
        result = subprocess.run(
            [OBJDUMP, '-p', dll_path],
            capture_output=True, text=True, timeout=30,
        )
        deps = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith('DLL Name:'):
                dep = line.split(':', 1)[1].strip()
                deps.append(dep)
        return deps
    except subprocess.TimeoutExpired:
        print(f"    [WARN] objdump timed out on {dll_path}")
        return []
    except Exception as exc:
        print(f"    [WARN] failed to scan {dll_path}: {exc}")
        return []


# ---------------------------------------------------------------------------
# 5. Recursive dependency resolution
# ---------------------------------------------------------------------------
already_copied = {f for f in os.listdir(ESSENTIA_DIR)
                  if f.lower().endswith('.dll')}

# Initialise queue with every .pyd and .dll already in the package dir
queue = []
for f in os.listdir(ESSENTIA_DIR):
    fp = os.path.join(ESSENTIA_DIR, f)
    if f.lower().endswith(('.pyd', '.dll')) and os.path.isfile(fp):
        queue.append((fp, f))

seen = set()
new_count = 0

print("Resolving DLL dependencies (this may take a minute)...")
while queue:
    fpath, label = queue.pop(0)
    if fpath in seen:
        continue
    seen.add(fpath)

    for dep in get_dll_dependencies(fpath):
        if is_system_dll(dep) or dep in already_copied:
            continue

        src = os.path.join(MINGW_BIN, dep)
        if os.path.isfile(src):
            dst = os.path.join(ESSENTIA_DIR, dep)
            shutil.copy2(src, dst)
            already_copied.add(dep)
            new_count += 1
            queue.append((dst, dep))
            print(f"  [+] {dep}")
        else:
            print(f"  [!] {dep} (needed by {label}) -- NOT FOUND in MinGW bin")

print()
print(f"Done. Copied {new_count} new DLL(s). "
      f"Total DLLs in essentia package: {len(already_copied)}")
