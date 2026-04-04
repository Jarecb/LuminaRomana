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
set "LUMINA_ROMANA_AI_API_KEY=AIzaSyC2mCeluucZqb1JtEV0rpVeZD36XjCpv88"
rem set "LUMINA_ROMANA_AI_BASE_URL=https://api.openai.com/v1"
rem set "LUMINA_ROMANA_AI_TIMEOUT_SECONDS=30"
rem set "LUMINA_ROMANA_AI_MAX_RETRIES=2"

if /I "%LUMINA_ROMANA_AI_ENABLED%"=="true" if "%LUMINA_ROMANA_AI_API_KEY%"=="" (
    echo LUMINA_ROMANA_AI_API_KEY is empty in run_server.bat.
    echo Edit run_server.bat and set your Gemini or Copilot/OpenAI-compatible API key first.
    pause
    exit /b 1
)

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

set "LUMINA_COMMAND=%*"
if "%LUMINA_COMMAND%"=="" (
    set "LUMINA_COMMAND=serve"
)

echo Starting Lumina Romana...
echo Host:     %LUMINA_ROMANA_WEB_HOST%
echo Port:     %LUMINA_ROMANA_WEB_PORT%
echo Data dir: %LUMINA_ROMANA_DATA_DIR%
echo Provider: %LUMINA_ROMANA_AI_PROVIDER%
echo Model:    %LUMINA_ROMANA_AI_MODEL%
echo Command:  %LUMINA_COMMAND%

"%PYTHON_EXE%" main.py %LUMINA_COMMAND%
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo Server exited with code %EXIT_CODE%.
    pause
)

endlocal & exit /b %EXIT_CODE%
