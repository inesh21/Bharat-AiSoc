@echo off
REM Push models and test vectors to connected Android device
REM Run from project root: app_android\push_models.bat

setlocal enabledelayedexpansion

set ADB=C:\Users\kaush\AppData\Local\Android\Sdk\platform-tools\adb.exe
set DEVICE_DIR=/data/local/tmp

echo === Pushing models to Android device ===

REM Check ADB
if not exist "%ADB%" (
    echo ERROR: ADB not found at %ADB%
    echo Please update the ADB path in this script
    exit /b 1
)

REM Check device connection
"%ADB%" devices | findstr "device$" >nul
if errorlevel 1 (
    echo ERROR: No Android device connected
    echo Connect device and enable USB debugging
    exit /b 1
)

echo Device connected

REM Create device directory
echo Creating device directory: %DEVICE_DIR%
"%ADB%" shell mkdir -p %DEVICE_DIR% 2>nul

REM Push vision model
echo.
echo Pushing vision_v1.pte (13.1 MB)...
if exist "models\vision_v1.pte" (
    "%ADB%" push models\vision_v1.pte %DEVICE_DIR%/vision_v1.pte
    echo √ Vision model pushed
) else (
    echo WARNING: models\vision_v1.pte not found
)

echo Pushing vision_v1.json sidecar...
if exist "models\vision_v1.json" (
    "%ADB%" push models\vision_v1.json %DEVICE_DIR%/vision_v1.json
    echo √ Vision sidecar pushed
) else (
    echo WARNING: models\vision_v1.json not found
)

REM Push LLM model
echo.
echo Pushing llama32_1b.pte (821 MB) - this will take ~2-3 minutes...
if exist "models\llama32_1b.pte" (
    "%ADB%" push models\llama32_1b.pte %DEVICE_DIR%/llama32_1b.pte
    echo √ LLM model pushed
) else (
    echo WARNING: models\llama32_1b.pte not found
)

echo Pushing tokenizer.model...
if exist "models_src\llama32_1b\tokenizer.model" (
    "%ADB%" push models_src\llama32_1b\tokenizer.model %DEVICE_DIR%/tokenizer.model
    echo √ Tokenizer pushed
) else (
    echo WARNING: models_src\llama32_1b\tokenizer.model not found
)

REM Push test vectors
echo.
echo Pushing test vectors...
if exist "test_vectors\vision\parity_test_vectors.json" (
    "%ADB%" push test_vectors\vision\parity_test_vectors.json %DEVICE_DIR%/
    echo √ Vision test vectors pushed
)

if exist "test_vectors\llm\parity.json" (
    "%ADB%" push test_vectors\llm\parity.json %DEVICE_DIR%/
    echo √ LLM test vectors pushed
)

REM Verify files on device
echo.
echo === Files on device ===
"%ADB%" shell ls -lh %DEVICE_DIR%/*.pte %DEVICE_DIR%/*.json %DEVICE_DIR%/*.model 2>nul

echo.
echo === Model push complete ===
echo Next steps:
echo 1. Build APK: cd app_android ^&^& gradlew assembleRelease
echo 2. Install: adb install app\build\outputs\apk\release\app-release.apk
echo 3. Test in airplane mode with 20 real photos (Milestone I4)

pause
