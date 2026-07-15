import shutil
import os
import glob
import subprocess
import sys
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.install_lib import install_lib

library = None
PYTHON = sys.executable

# Default project name
project_name = 'essentia'

var_project_name = 'ESSENTIA_PROJECT_NAME'
if var_project_name in os.environ:
    project_name = os.environ[var_project_name]


def _is_mingw():
    """Check if we are running in MSYS2/MinGW environment on Windows."""
    if sys.platform != 'win32':
        return False
    if 'MSYSTEM' in os.environ:
        return True
    try:
        result = subprocess.run(['g++', '-dumpmachine'],
                                capture_output=True, text=True, timeout=5)
        if 'mingw' in result.stdout.lower():
            return True
    except Exception:
        pass
    return False


class EssentiaInstall(install_lib):
    def install(self):
        global library
        # If already installed to site-packages (MinGW), skip the move
        if library and os.path.dirname(library) == self.install_dir:
            print('  Already installed to %s, skipping move' % self.install_dir)
            if os.name != 'nt':
                os.system("ls -l %s" % self.install_dir)
            return [library]
        install_dir = os.path.join(self.install_dir, library.split(os.sep)[-1])
        res = shutil.move(library, install_dir)
        if os.name != 'nt':
            os.system("ls -l %s" % self.install_dir)
        return [install_dir]


class EssentiaBuildExtension(build_ext):
    def run(self):
        global library
        is_mingw = _is_mingw()

        # Clean and create temp build directory
        tmp_dir = 'tmp'
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)

        # Env vars to control build
        var_skip_3rdparty = 'ESSENTIA_WHEEL_SKIP_3RDPARTY'
        var_only_python = 'ESSENTIA_WHEEL_ONLY_PYTHON'

        # macOS ARM64 flags
        var_macos_arm64 = os.getenv('ESSENTIA_MACOSX_ARM64')
        extra_flags = []
        if var_macos_arm64 == '1':
            extra_flags = ['--arch=arm64', '--no-msse']

        # Build 3rdparty dependencies (Linux only)
        if is_mingw:
            print('Windows/MinGW detected: skipping 3rdparty static build')
        elif var_skip_3rdparty in os.environ and os.environ[var_skip_3rdparty] == '1':
            print('Skipping building static 3rdparty dependencies (%s=1)' % var_skip_3rdparty)
        else:
            subprocess.run('./packaging/build_3rdparty_static_debian.sh', check=True)

        # Build waf configure command
        waf_configure = [PYTHON, 'waf', 'configure', '--prefix=' + tmp_dir]

        if is_mingw:
            print('Configuring for Windows/MinGW')
            waf_configure += ['--build-static', '--with-python']
            # Use shared DLLs from pacman on MinGW (no --static-dependencies)
        elif var_only_python in os.environ and os.environ[var_only_python] == '1':
            print('Skipping building the core libessentia library (%s=1)' % var_only_python)
            waf_configure += ['--only-python', '--static-dependencies']
        else:
            waf_configure += ['--build-static', '--static-dependencies', '--with-python']

        waf_configure += extra_flags
        subprocess.run(waf_configure, check=True)
        subprocess.run([PYTHON, 'waf'], check=True)
        subprocess.run([PYTHON, 'waf', 'install'], check=True)

        # Find installed library path
        if is_mingw:
            # On MinGW, waf install puts .pyd/.py directly in PYTHONDIR
            cache_file = os.path.join('build', 'c4che', '_cache.py')
            pythondir = None
            if os.path.isfile(cache_file):
                with open(cache_file) as f:
                    for line in f:
                        if line.startswith('PYTHONDIR'):
                            pythondir = line.split('=', 1)[1].strip().strip("'\"")
                            break
            if pythondir:
                pkg = os.path.join(pythondir, 'essentia')
                if os.path.isdir(pkg):
                    library = pkg
            # Resolve DLL dependencies on Windows
            resolve_script = os.path.join(os.path.dirname(__file__),
                                          'windows', 'resolve_dlls.py')
            if os.path.isfile(resolve_script):
                print('Resolving DLL dependencies...')
                subprocess.run([PYTHON, resolve_script], check=True)
            # Install pre-generated .pyi type stubs (PEP 561)
            stubs_out = os.path.join(os.path.dirname(__file__),
                                     'essentia-stubs')
            if os.path.isdir(stubs_out) and pythondir:
                stubs_dest = os.path.join(pythondir, 'essentia-stubs')
                if os.path.isdir(stubs_dest):
                    shutil.rmtree(stubs_dest)
                shutil.copytree(stubs_out, stubs_dest)
                print(f'  -> Installed stubs to {stubs_dest}')
        if library is None:
            results = glob.glob('tmp/lib/python*/*-packages/essentia')
            if results:
                library = results[0]
            else:
                # Last resort: files may already be installed directly
                for p in sys.path:
                    candidate = os.path.join(p, 'essentia', '__init__.py')
                    if os.path.isfile(candidate):
                        library = os.path.dirname(candidate)
                        break


def get_git_version():
    """ try grab the current version number from git"""
    version = None
    if os.path.exists(".git"):
        try:
            version = os.popen("git describe --always --tags").read().strip()
        except Exception as e:
            print(e)
    return version


def get_version():
    version = open('.essentia-version', 'r').read().strip('\n')
    if version.count('-dev'):
        # Development version. Get the number of commits after the last release
        git_version = get_git_version()
        print('git describe:', git_version)
        dev_commits = '0'
        if git_version:
            parts = git_version.split('-')
            if len(parts) >= 2 and parts[-2].isdigit():
                dev_commits = parts[-2]
            else:
                print('Warning: could not parse dev commits from "%s", using 0' % git_version)
        version += dev_commits
    return version


classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Topic :: Software Development :: Libraries',
    'Topic :: Multimedia :: Sound/Audio :: Analysis',
    'Topic :: Multimedia :: Sound/Audio :: Sound Synthesis',
    'Operating System :: POSIX',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: Microsoft :: Windows',
    'Programming Language :: C++',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
]

description = 'Library for audio and music analysis, description and synthesis'
long_description = '''
Essentia is an open-source C++ library with Python bindings for audio analysis and audio-based music information retrieval. It contains an extensive collection of algorithms, including audio input/output functionality, standard digital signal processing blocks, statistical characterization of data, a large variety of spectral, temporal, tonal, and high-level music descriptors, and tools for inference with deep learning models. Designed with a focus on optimization in terms of robustness, computational speed, low memory usage, as well as flexibility, it is efficient for many industrial applications and allows fast prototyping and setting up research experiments very rapidly.

Website: https://essentia.upf.edu
'''

# Require tensorflow for the package essentia-tensorflow
# We are using version 2.5.0 as it is the newest version supported by the C API
# https://www.tensorflow.org/guide/versions
if project_name == 'essentia-tensorflow':
    description += ', with TensorFlow support'

module = Extension('name', sources=[])

setup(
    version=get_version(),
    description=description,
    long_description=long_description,
    author='Dmitry Bogdanov',
    author_email='dmitry.bogdanov@upf.edu',
    url='http://essentia.upf.edu',
    project_urls={
        "Documentation": "http://essentia.upf.edu",
        "Source Code": "https://github.com/MTG/essentia"
    },
    keywords='audio music sound dsp MIR',
    license='AGPLv3',
    platforms='any',
    classifiers=classifiers,
    ext_modules=[module],
    cmdclass={
        'build_ext': EssentiaBuildExtension,
        'install_lib': EssentiaInstall
    }
)
