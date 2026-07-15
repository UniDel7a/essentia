# Essentia Unofficial Fork (Experimental)

---
This fork is an **very experimental version** of Essentia that aims to provide a more user-friendly installation process, especially for *Windows* users. It includes simplified build instructions to help users get started quickly without the need for complex dependency management.

Stable builds of Essentia for Linux can be found at the **official repository**.

Please do not use this fork for production purposes, as it may contain bugs and is not guaranteed to be stable.

---

```txt
# 0.Prepare (scoop+git+uv+msys2) 

cd path/to/project
uv venv --python 3.11
uv pip install "numpy==2.4.6"
git clone https://github.com/UniDel7a/essentia.git
scoop install main/msys2
msys2 #initial installation
exit #if msys is running, exit it and run mingw64 shell instead

# 1. Install dependencies 
# Use Mingw64 shell instead of MSYS2 shell, because the latter will cause some problems when compiling essentia

mingw64 
pacman -S mingw-w64-x86_64-toolchain
pacman -S mingw-w64-x86_64-pkgconf
pacman -S mingw-w64-x86_64-eigen3
pacman -S mingw-w64-x86_64-fftw
pacman -S mingw-w64-x86_64-ffmpeg
pacman -S mingw-w64-x86_64-taglib
pacman -S mingw-w64-x86_64-libsamplerate
pacman -S mingw-w64-x86_64-libyaml
pacman -S mingw-w64-x86_64-chromaprint

# 2. Enter project directory

mingw64
cd /path/to/essentia

# 3. Configure

/path/to/.venv/Scripts/python waf configure --build-static --with-examples --with-python -o my_build_dir

# 4. Build
/path/to/.venv/Scripts/python waf

# Python bindings filename should look like this:
# my_build_dir\src\python\_essentia.cp311-win_amd64.pyd

# 5. Install
# Tested on Windows 11 + MSYS2/MINGW64 + MinGW GCC 16.1.0 + CPython 3.11 (cp311-win_amd64)
/path/to/.venv/Scripts/python waf install
```

---

[![Build wheels status](https://github.com/MTG/essentia/actions/workflows/build-wheels-cibuildwheel.yml/badge.svg)](https://github.com/MTG/essentia/actions/workflows/build-wheels-cibuildwheel.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![PyPI downloads: essentia](https://img.shields.io/pypi/dm/essentia.svg?label=PyPI%20downloads:%20essentia)](https://pypi.org/project/essentia/)
[![PyPI downloads: essentia-tensorflow](https://img.shields.io/pypi/dm/essentia-tensorflow.svg?label=PyPI%20downloads:%20essentia-tensorflow)](https://pypi.org/project/essentia-tensorflow/)


Essentia is an open-source C++ library for audio analysis and audio-based music information retrieval released under the Affero GPLv3 license. It contains an extensive collection of reusable algorithms which implement audio input/output functionality, standard digital signal processing blocks, statistical characterization of data, and a large set of spectral, temporal, tonal and high-level music descriptors. The library is also wrapped in Python and includes a number of predefined executable extractors for the available music descriptors, which facilitates its use for fast prototyping and allows setting up research experiments very rapidly. Furthermore, it includes a Vamp plugin to be used with Sonic Visualiser for visualization purposes. Essentia is designed with a focus on the robustness of the provided music descriptors and is optimized in terms of the computational cost of the algorithms. The provided functionality, specifically the music descriptors included in-the-box and signal processing algorithms, is easily expandable and allows for both research experiments and development of large-scale industrial applications.

Documentation online: http://essentia.upf.edu


Installation
------------

The library is cross-platform and currently supports Linux, macOS, Windows, iOS and Android systems. Read installation instructions:
-  http://essentia.upf.edu/documentation/installing.html 
-  [doc/sphinxdoc/installing.rst](doc/sphinxdoc/installing.rst)

Install from master for the latest updates.

To use in Python (Linux `x86_64`, `i686`): `pip install essentia` or `pip install essentia-tensorflow`.

Docker images: https://hub.docker.com/r/mtgupf/essentia/


You can download and use prebuilt static binaries for a number of Essentia's command-line music extractors instead of installing the complete library
- [doc/sphinxdoc/extractors_out_of_box.rst](doc/sphinxdoc/extractors_out_of_box.rst)


Quick start
-----------

Quick start using Python:
- http://essentia.upf.edu/documentation/essentia_python_tutorial.html
- [Jupyter Notebook Essentia tutorial](/src/examples/python/essentia_python_tutorial.ipynb)

Command-line tools to compute common music descriptors:
- [doc/sphinxdoc/extractors_out_of_box.rst](doc/sphinxdoc/extractors_out_of_box.rst)


Asking for help
---------------

[Read frequently asked questions](FAQ.md).

[Create an issue on github](https://github.com/MTG/essentia/issues) or [open a new discussion](https://github.com/MTG/essentia/discussions) if your question was not answered before.


Versions
--------

Official releases: https://github.com/MTG/essentia/releases

Github branches:
- [master](https://github.com/MTG/essentia/tree/master): latest updates; if you got any problem, try it first.

If you use example extractors (located in src/examples), or your own code employing Essentia algorithms to compute descriptors, you should be aware of possible incompatibilities when using different versions of Essentia.

How to contribute
-----------------
We are more than happy to collaborate and receive your contributions to Essentia. The best practice of submitting your code is by creating pull requests to [our GitHub repository](https://github.com/MTG/essentia) following our contribution policy. By submitting your code you authorize that it complies with the Developer's Certificate of Origin. For more details see: http://essentia.upf.edu/documentation/contribute.html

You are also more than welcome to [suggest any improvements](https://github.com/MTG/essentia/issues/254), including proposals for new algorithms, etc.

