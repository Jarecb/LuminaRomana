@echo off
setlocal

rem Runtime configuration for local browser use.
rem Edit these values for your machine before launching.
set "LUMINA_ROMANA_ENV=production"
set "LUMINA_ROMANA_LOG_LEVEL=INFO"
set "LUMINA_ROMANA_DATA_DIR=data"
set "LUMINA_ROMANA_WEB_HOST=127.0.0.1"
set "LUMINA_ROMANA_WEB_PORT=8000"

rem AI configuration.
rem Supported values include: gemini, google, copilot, openai.
set "LUMINA_ROMANA_AI_ENABLED=true"
set "LUMINA_ROMANA_AI_PROVIDER=gemini"
set "LUMINA_ROMANA_AI_MODEL=gemini-2.5-flash"
rem Do NOT hardcode API keys in this file. Set LUMINA_ROMANA_AI_API_KEY in your environment instead.
set "LUMINA_ROMANA_AI_API_KEY=AIzaSyC2mCeluucZqb1JtEV0rpVeZD36XjCpv88"

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

set "LUMINA_COMMAND=%*"
set "LUMINA_HAS_ARGS=true"
set "LUMINA_INTERACTIVE_MENU_CHOICE="
set "LUMINA_PRIMARY_COMMAND=%~1"
if "%LUMINA_COMMAND%"=="" (
    set "LUMINA_COMMAND=serve"
    set "LUMINA_HAS_ARGS=false"
    set "LUMINA_PRIMARY_COMMAND=serve"
)

rem Check if offline was already passed via command line arguments
set "LUMINA_ROMANA_AI_OFFLINE_ONLY=false"
for %%A in (%LUMINA_COMMAND%) do (
    if /I "%%~A"=="-o" set "LUMINA_ROMANA_AI_OFFLINE_ONLY=true"
    if /I "%%~A"=="-offline" set "LUMINA_ROMANA_AI_OFFLINE_ONLY=true"
    if /I "%%~A"=="--offline" set "LUMINA_ROMANA_AI_OFFLINE_ONLY=true"
)

rem Only prompt for startup mode when no explicit command-line args were supplied.
if /I "%LUMINA_HAS_ARGS%"=="false" if /I "%LUMINA_ROMANA_AI_OFFLINE_ONLY%"=="false" (
    echo.
    echo ========================================
    echo  Select Execution Mode:
    echo  [1] Online - AI Enabled
    echo  [2] Offline - Local Only
    echo  [3] Seed offline question bank, then start server
    echo ========================================
    choice /c 123 /n /m "Enter your choice (1, 2 or 3): "

    rem capture ERRORLEVEL because batch "if errorlevel" checks are >= comparisons
    set "USER_CHOICE=%ERRORLEVEL%"
    set "LUMINA_INTERACTIVE_MENU_CHOICE=%USER_CHOICE%"
    if "%USER_CHOICE%"=="3" (
        set "LUMINA_COMMAND=serve --seed-offline-questions"
        set "LUMINA_PRIMARY_COMMAND=serve"
    ) else (
        if "%USER_CHOICE%"=="2" (
            set "LUMINA_ROMANA_AI_OFFLINE_ONLY=true"
            set "LUMINA_COMMAND=serve"
            set "LUMINA_PRIMARY_COMMAND=serve"
        ) else (
            set "LUMINA_COMMAND=serve"
            set "LUMINA_PRIMARY_COMMAND=serve"
        )
    )
)

if /I not "%LUMINA_ROMANA_AI_OFFLINE_ONLY%"=="true" if /I "%LUMINA_ROMANA_AI_ENABLED%"=="true" if "%LUMINA_ROMANA_AI_API_KEY%"=="" (
    echo LUMINA_ROMANA_AI_API_KEY is empty in run_server.bat.
    echo Edit run_server.bat and set your Gemini or Copilot/OpenAI-compatible API key first.
    pause
    exit /b 1
)

set "LUMINA_MODE_LABEL=ai-enabled-or-fallback"
if /I "%LUMINA_ROMANA_AI_OFFLINE_ONLY%"=="true" (
    set "LUMINA_MODE_LABEL=offline-only"
)
if "%LUMINA_INTERACTIVE_MENU_CHOICE%"=="3" (
    set "LUMINA_MODE_LABEL=ai-seeding-before-startup"
)

echo.
echo Starting Lumina Romana...
echo Host:     %LUMINA_ROMANA_WEB_HOST%
echo Port:     %LUMINA_ROMANA_WEB_PORT%
echo Data dir: %LUMINA_ROMANA_DATA_DIR%
echo Mode:     %LUMINA_MODE_LABEL%
echo Provider: %LUMINA_ROMANA_AI_PROVIDER%
echo Model:    %LUMINA_ROMANA_AI_MODEL%
rem echo API key:  %LUMINA_ROMANA_AI_API_KEY%
echo Command:  %LUMINA_COMMAND%
echo.
rem echo NOTE: API key is displayed above. Avoid exposing this output in logs or shared terminals.

if "%LUMINA_INTERACTIVE_MENU_CHOICE%"=="3" (
    echo Seeding the offline question bank before the server starts. Review the summary below during startup.
    echo.
)

"%PYTHON_EXE%" main.py %LUMINA_COMMAND%
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo Server exited with code %EXIT_CODE%.
    pause
)

if "%EXIT_CODE%"=="0" if /I "%LUMINA_HAS_ARGS%"=="false" if /I not "%LUMINA_PRIMARY_COMMAND%"=="serve" (
    echo.
    echo Command completed successfully. Review the output above.
    pause
)

endlocal & exit /b %EXIT_CODE%
