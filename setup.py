import sys
import os
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

try:
    import pybind11
    from pybind11.setup_helpers import Pybind11Extension, build_ext
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pybind11"])
    import pybind11
    from pybind11.setup_helpers import Pybind11Extension, build_ext

__version__ = "0.0.1"

if sys.platform == "win32":
    compile_args = [
        "/O2",
        "/Oi",
        "/Ot",
        "/Ob3",  # /Ob2 -> /Ob3 (더 공격적인 인라인)
        "/GL",
        "/arch:AVX2",
        "/favor:AMD64",
        "/fp:fast",
        "/GS-",
        "/Gy",
        "/GT",
        "/GF",
        "/Gw",
        "/Qpar",  # 자동 병렬화
    ]
    link_args = ["/LTCG", "/OPT:REF", "/OPT:ICF"]
else:
    compile_args = [
        "-O3",
        "-march=native",
        "-mtune=native",
        "-ffast-math",
        "-funroll-loops",
        "-finline-functions",
        "-flto",
        "-fomit-frame-pointer",
        "-fno-rtti",
        "-fdata-sections",
        "-ffunction-sections",
    ]
    link_args = ["-flto", "-Wl,--gc-sections"]

ext_modules = [
    Pybind11Extension(
        "chess_cpp",
        ["chess_cpp.cpp", "engine.cpp", "chessAi.cpp"],
        define_macros=[("VERSION_INFO", __version__)],
        cxx_std=20,
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    ),
]

setup(
    name="chess_cpp",
    version=__version__,
    author="Chess AI Developer",
    description="C++ Chess Engine and AI with Python bindings",
    long_description="",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.7",
)
