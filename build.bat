@echo off
echo Building C++ Chess Engine...
python -m pip install pybind11 --quiet
python setup.py build_ext --inplace
if %ERRORLEVEL% EQU 0 (
    echo Build successful!
) else (
    echo Build failed!
)
pause
