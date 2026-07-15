"""
Generate precise .pyi type stubs for the essentia Python module.

Scrapes https://essentia.upf.edu/reference/ for each algorithm to
extract exact parameter names, types, defaults, and return types.

Usage:
    python windows/generate_stubs.py

Produces: essentia-stubs/  (PEP 561 compliant stub package)
  __init__.py     - package marker
  __init__.pyi    - essentia.standard stubs (251+ algorithms)
  streaming.pyi   - essentia.streaming stubs (245+ algorithms)
  cache.json      - scraped data cache (to speed up re-runs)
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

CACHE_FILE = "doc_cache.json"
BASE_URL = "https://essentia.upf.edu/reference"
USER_AGENT = "Mozilla/5.0 (compatible; essentia-stub-generator/1.0)"

# Essentia to Python type mapping
ESSENTIA_TYPE_MAP = {
    "real": "float",
    "integer": "int",
    "string": "str",
    "complex": "complex",
    "bool": "bool",
    "vector_real": "np.ndarray",
    "vector_complex": "np.ndarray",
    "vector_int": "list[int]",
    "vector_string": "list[str]",
    "matrix_real": "np.ndarray",
    "matrix_complex": "np.ndarray",
    "tensor_real": "np.ndarray",
    "pool": "Pool",
}


def _py_type(ess_type):
    """Map an essentia type string to a Python type annotation."""
    t = ess_type.strip()
    m = re.match(r"^vector<(\w+)>$", t)
    if m:
        inner = _py_type(m.group(1))
        return "list[{}]".format(inner)
    m = re.match(r"^matrix<(\w+)>$", t)
    if m:
        return "np.ndarray"
    return ESSENTIA_TYPE_MAP.get(t, "Any")


def _fetch(url):
    """Fetch a URL and return HTML text, or None on failure."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.5)
    return None


_PARAM_RE = re.compile(
    r"<code[^>]*>(?:<[^>]+>)*\s*(\w+)\s*(?:<[^>]+>)*</code>\s*\(<em>([^<]+)</em>\)\s*:"
)
_IO_RE = re.compile(
    r"<code[^>]*>(?:<[^>]+>)*\s*(\w+)\s*(?:<[^>]+>)*</code>\s*\(<em>([^<]+)</em>\)"
)
_DEFAULT_RE = re.compile(r"default\s*=\s*(\S+)")


def _extract_section(html, section):
    """Return the HTML content between <h2>section</h2> and next <h2>."""
    m = re.search(
        r"<h2>\s*{}\s*<a[^>]*>.*?</h2>(.*?)(?=<h2>|<div[^>]*footer|<footer)".format(section),
        html, re.DOTALL | re.IGNORECASE,
    )
    return m.group(1) if m else ""


def _parse_param_typeinfo(info):
    """Parse parameter type info like 'integer \u2208 [0,\u221e), default = 0'.

    Returns (python_type, default_value) where default_value may be None.
    """
    info = info.strip()
    ess_type = info.split("\u2208")[0].split("(")[0].split(",")[0].strip()
    py_t = _py_type(ess_type)

    dm = _DEFAULT_RE.search(info)
    if dm:
        raw_default = dm.group(1).rstrip(",")
        if raw_default.lower() in ("true", "false"):
            default = raw_default.capitalize()
        elif ess_type in ("string",) or not _is_numeric(raw_default):
            default = repr(raw_default)
        else:
            default = raw_default
    else:
        default = None

    return py_t, default


def _is_numeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _parse_params(section_html):
    """Parse HTML of the Parameters section."""
    items = []
    for m in _PARAM_RE.finditer(section_html):
        name = m.group(1)
        info = m.group(2)
        py_t, default = _parse_param_typeinfo(info)
        items.append((name, py_t, default))
    return items


def _parse_io(section_html):
    """Parse HTML of Inputs or Outputs section."""
    items = []
    for m in _IO_RE.finditer(section_html):
        name = m.group(1)
        info = m.group(2).strip().split(",")[0].split("\u2208")[0].strip()
        py_t = _py_type(info)
        items.append((name, py_t))
    return items


def _scrape_std(name):
    """Scrape a standard algorithm's doc page."""
    url = "{}/std_{}.html".format(BASE_URL, name)
    html = _fetch(url)
    if not html:
        return {"params": [], "inputs": [], "outputs": []}
    return {
        "params": _parse_params(_extract_section(html, "Parameters")),
        "inputs": _parse_io(_extract_section(html, "Inputs")),
        "outputs": _parse_io(_extract_section(html, "Outputs")),
    }


def _scrape_streaming(name):
    """Scrape a streaming algorithm's doc page."""
    url = "{}/streaming_{}.html".format(BASE_URL, name)
    html = _fetch(url)
    if not html:
        return {"params": [], "inputs": [], "outputs": []}
    return {
        "params": _parse_params(_extract_section(html, "Parameters")),
        "inputs": _parse_io(_extract_section(html, "Inputs")),
        "outputs": _parse_io(_extract_section(html, "Outputs")),
    }


def _param_sig(params):
    """Build __init__ parameter signature string from param list."""
    parts = ["self"]
    for name, py_t, default in params:
        if default is not None:
            parts.append("{}: {} = {}".format(name, py_t, default))
        else:
            parts.append("{}: {}".format(name, py_t))
    return ", ".join(parts)


def _call_sig(inputs, outputs):
    """Build __call__ signature and return annotation."""
    args = ["self"]
    for name, py_t in inputs:
        args.append("{}: {}".format(name, py_t))

    if not outputs:
        return_type = "None"
    elif len(outputs) == 1:
        return_type = outputs[0][1]
    else:
        inner = ", ".join(t for _, t in outputs)
        return_type = "tuple[{}]".format(inner)

    return ", ".join(args), return_type


def _generate_essentia_stubs():
    """Generate __init__.pyi for the top-level essentia package."""
    return """\"\"\"
Type stubs for the essentia top-level package.
\"\"\"

from typing import Any, Tuple
from essentia._essentia import Algorithm, StreamingAlgorithm, reset
from essentia.common import Pool

class EssentiaError(Exception):
    error: str
    filename: str | None
    def __init__(self, error, filename=None) -> None: ...

class DebuggingModule:
    EAlgorithm: int = 1
    EConnectors: int = 2
    EFactory: int = 4
    ENetwork: int = 8
    EGraph: int = 16
    EExecution: int = 32
    EMemory: int = 64
    EScheduler: int = 128
    EPython: int = 1048576
    EPyBindings: int = 2097152

def reset() -> None: ...
"""


def _generate_essentia_compiled_stubs():
    """Generate _essentia.pyi for the essentia._essentia compiled module."""
    return """\"\"\"
Type stubs for essentia._essentia (C++ extension).
\"\"\"

from typing import Any
import numpy as np
import numpy.typing as npt

class Algorithm:
    name: str
    def __init__(self, name: str) -> None: ...

class StreamingAlgorithm:
    name: str
    def __init__(self, name: str) -> None: ...

def version() -> str: ...
def version_git_sha() -> str: ...
def keys() -> list[str]: ...
def info(name: str) -> dict[str, Any]: ...
def reset() -> None: ...
"""


def _generate_std_stubs(algos, sorted_names):
    """Generate standard.pyi content for essentia.standard."""
    lines = [
        '"""',
        "Type stubs for essentia.standard algorithms.",
        "",
        "Auto-generated -- {} algorithms.".format(len(sorted_names)),
        '"""',
        "",
        "from typing import Any, Tuple",
        "import numpy.typing as npt",
        "import numpy as np",
        "from essentia._essentia import Algorithm",
        "from essentia import Pool",
        "",
    ]

    for name in sorted_names:
        info = algos.get(name, {})
        params = info.get("params", [])
        inputs = info.get("inputs", [])
        outputs = info.get("outputs", [])

        sig = _param_sig(params)
        call_args, ret_type = _call_sig(inputs, outputs)

        lines.append("class {}(Algorithm):".format(name))
        lines.append("    def __init__({}) -> None: ...".format(sig))
        if call_args == "self":
            lines.append("    def __call__(self) -> {}: ...".format(ret_type))
        else:
            lines.append("    def __call__({}) -> {}: ...".format(call_args, ret_type))
        lines.append("")

    return "\n".join(lines)


def _generate_streaming_stubs(algos, sorted_names):
    """Generate the streaming.pyi content for streaming algorithms."""
    lines = [
        '"""',
        "Type stubs for essentia.streaming algorithms.",
        "",
        "Auto-generated -- {} algorithms.".format(len(sorted_names)),
        '"""',
        "",
        "from typing import Any, Tuple",
        "import numpy.typing as npt",
        "import numpy as np",
        "from essentia._essentia import StreamingAlgorithm as Algo",
        "from essentia import Pool",
        "",
    ]

    for name in sorted_names:
        info = algos.get(name, {})
        params = info.get("params", [])
        sig = _param_sig(params)

        lines.append("class {}(Algo):".format(name))
        lines.append("    def __init__({}) -> None: ...".format(sig))
        lines.append("    def configure(self, **kwargs) -> None: ...")
        lines.append("")

    return "\n".join(lines)


def _introspect_standard():
    """Return sorted list of standard algorithm names via subprocess."""
    code = (
        "import essentia.standard as m\n"
        "from essentia._essentia import Algorithm\n"
        "result = []\n"
        "for name in dir(m):\n"
        "    try:\n"
        "        obj = getattr(m, name)\n"
        "        if isinstance(obj, type) and issubclass(obj, Algorithm):\n"
        "            result.append(name)\n"
        "    except Exception:\n"
        "        pass\n"
        "print(','.join(sorted(result)))\n"
    )
    out = subprocess.check_output([sys.executable], input=code, text=True)
    return [n for n in out.strip().split(",") if n]


def _introspect_streaming():
    """Return sorted list of streaming algorithm names via subprocess."""
    script = (
        "import essentia.streaming as m\n"
        "from essentia._essentia import StreamingAlgorithm\n"
        "result = []\n"
        "for name in dir(m):\n"
        "    try:\n"
        "        obj = getattr(m, name)\n"
        "        if isinstance(obj, type) and issubclass(obj, StreamingAlgorithm):\n"
        "            result.append(name)\n"
        "    except Exception:\n"
        "        pass\n"
        "print(','.join(sorted(result)))\n"
    )
    out = subprocess.check_output([sys.executable], input=script, text=True)
    return [n for n in out.strip().split(",") if n]


def _load_cache(cache_path):
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache_path, data):
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _write_stub(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    n = content.count("class ")
    print("  -> {}  ({} classes)".format(path, n))


def generate_stubs(stubs_dir):
    """Main entry point: introspect, scrape, and write all stub files."""
    cache_path = os.path.join(stubs_dir, CACHE_FILE)
    doc_cache = _load_cache(cache_path)

    print("Introspecting essentia.standard (subprocess)...")
    std_names = _introspect_standard()
    print("  standard: {} algorithms".format(len(std_names)))

    print("Introspecting essentia.streaming (subprocess)...")
    st_names = _introspect_streaming()
    print("  streaming: {} algorithms".format(len(st_names)))

    std_data = {}
    new_scraped = 0
    print("")
    print("Scraping standard algorithm docs...")
    for i, name in enumerate(std_names):
        if name in doc_cache.get("std", {}):
            std_data[name] = doc_cache["std"][name]
        else:
            std_data[name] = _scrape_std(name)
            doc_cache.setdefault("std", {})[name] = std_data[name]
            new_scraped += 1
            if new_scraped % 10 == 0:
                _save_cache(cache_path, doc_cache)
        if (i + 1) % 20 == 0 or i == len(std_names) - 1:
            cached = len(std_names) - new_scraped
            print("    [{}/{}]  new={} cached={}".format(i+1, len(std_names), new_scraped, cached))

    st_data = {}
    new_scraped = 0
    print("")
    print("Scraping streaming algorithm docs...")
    for i, name in enumerate(st_names):
        if name in doc_cache.get("streaming", {}):
            st_data[name] = doc_cache["streaming"][name]
        else:
            st_data[name] = _scrape_streaming(name)
            doc_cache.setdefault("streaming", {})[name] = st_data[name]
            new_scraped += 1
            if new_scraped % 10 == 0:
                _save_cache(cache_path, doc_cache)
        if (i + 1) % 20 == 0 or i == len(st_names) - 1:
            cached = len(st_names) - new_scraped
            print("    [{}/{}]  new={} cached={}".format(i+1, len(st_names), new_scraped, cached))

    _save_cache(cache_path, doc_cache)

    print("")
    print("Generating stub files...")

    # __init__.py (package marker)
    py_path = os.path.join(stubs_dir, "__init__.py")
    with open(py_path, "w", encoding="utf-8") as f:
        f.write('"""PEP 561 type stub package for essentia."""\n')
    print("  -> {}".format(py_path))

    # __init__.pyi (top-level essentia)
    content = _generate_essentia_stubs()
    _write_stub(os.path.join(stubs_dir, "__init__.pyi"), content)

    # _essentia.pyi (compiled C++ extension)
    content = _generate_essentia_compiled_stubs()
    _write_stub(os.path.join(stubs_dir, "_essentia.pyi"), content)

    # standard.pyi (essentia.standard)
    content = _generate_std_stubs(std_data, std_names)
    _write_stub(os.path.join(stubs_dir, "standard.pyi"), content)

    # streaming.pyi (essentia.streaming)
    content = _generate_streaming_stubs(st_data, st_names)
    _write_stub(os.path.join(stubs_dir, "streaming.pyi"), content)

    print("")
    print("Done!")
    print("  Standard:  {} algorithms with detailed signatures".format(len(std_names)))
    print("  Streaming: {} algorithms with detailed signatures".format(len(st_names)))


def main():
    try:
        import essentia
    except ImportError:
        print("ERROR: essentia must be installed to generate stubs")
        return

    stubs_dir = os.path.join(os.path.dirname(__file__), "..", "essentia-stubs")
    os.makedirs(stubs_dir, exist_ok=True)
    generate_stubs(stubs_dir)


if __name__ == "__main__":
    main()
