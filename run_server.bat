@echo off
:: Set Environment Variables
set LUMINA_ROMANA_AI_ENABLED=true
set LUMINA_ROMANA_AI_PROVIDER=google
set LUMINA_ROMANA_AI_MODEL=gemini-2.5-flash
set LUMINA_ROMANA_AI_API_KEY=AIzaSyC2mCeluucZqb1JtEV0rpVeZD36XjCpv88

:: Log status (Optional)
echo Starting Lumina Romana Server...
echo Provider: %LUMINA_ROMANA_AI_PROVIDER%
echo Model:    %LUMINA_ROMANA_AI_MODEL%

:: Run the Python server
python main.py serve

:: Keep window open if the server crashes
pause