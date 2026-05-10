@echo off
:: ============================================================
::  Scout-2 Task Scheduler Setup
::  Creates 3 daily tasks: 7am, 12pm, 5pm
::  Run this ONCE as Administrator
:: ============================================================

echo.
echo ============================================================
echo  Scout-2 Task Scheduler Setup
echo  Creating 3 daily tasks...
echo ============================================================
echo.

:: ── Task 1: Morning 7am ──────────────────────────────────────
schtasks /create /tn "Scout-2 Morning Run" /tr "C:\InvestingWithSPACE\Scout2\run_scout2.bat" /sc daily /st 07:00 /rl highest /f

if %ERRORLEVEL% EQU 0 (
    echo [OK] Scout-2 Morning Run created - 7:00 AM
) else (
    echo [ERROR] Failed to create Morning Run task
)

:: ── Task 2: Midday 12pm ──────────────────────────────────────
schtasks /create /tn "Scout-2 Midday Run" /tr "C:\InvestingWithSPACE\Scout2\run_scout2.bat" /sc daily /st 12:00 /rl highest /f

if %ERRORLEVEL% EQU 0 (
    echo [OK] Scout-2 Midday Run created - 12:00 PM
) else (
    echo [ERROR] Failed to create Midday Run task
)

:: ── Task 3: Evening 5pm ──────────────────────────────────────
schtasks /create /tn "Scout-2 Evening Run" /tr "C:\InvestingWithSPACE\Scout2\run_scout2.bat" /sc daily /st 17:00 /rl highest /f

if %ERRORLEVEL% EQU 0 (
    echo [OK] Scout-2 Evening Run created - 5:00 PM
) else (
    echo [ERROR] Failed to create Evening Run task
)

:: ── Verify all 3 tasks exist ─────────────────────────────────
echo.
echo ============================================================
echo  Verifying tasks...
echo ============================================================
schtasks /query /tn "Scout-2 Morning Run" /fo list | findstr "Task Name\|Next Run"
schtasks /query /tn "Scout-2 Midday Run" /fo list | findstr "Task Name\|Next Run"
schtasks /query /tn "Scout-2 Evening Run" /fo list | findstr "Task Name\|Next Run"

echo.
echo ============================================================
echo  Done. All 3 Scout-2 tasks created.
echo  They will run at 7:00 AM, 12:00 PM, and 5:00 PM daily.
echo  GitHub will update automatically after each run.
echo ============================================================
echo.
pause
