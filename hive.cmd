@echo off
rem TestHive launcher for Windows (PowerShell or cmd). Finds Git Bash and runs a TestHive script.
rem   .\hive stage status SIGNUP          same as: bash scripts/stage.sh status SIGNUP
rem   .\hive demo/phase0/run.sh           runs any .sh file
rem   .\hive                              lists the scripts
setlocal
set "HB="
for %%G in (git.exe) do set "GITEXE=%%~$PATH:G"
if defined GITEXE for %%D in ("%GITEXE%\..\..") do if exist "%%~fD\bin\bash.exe" set "HB=%%~fD\bin\bash.exe"
if not defined HB if exist "%ProgramFiles%\Git\bin\bash.exe" set "HB=%ProgramFiles%\Git\bin\bash.exe"
if not defined HB if exist "%LocalAppData%\Programs\Git\bin\bash.exe" set "HB=%LocalAppData%\Programs\Git\bin\bash.exe"
if not defined HB (
  echo Git Bash was not found. Install Git, then open a new terminal:  winget install --id Git.Git -e
  exit /b 1
)
cd /d "%~dp0"
"%HB%" scripts/hive.sh %*
exit /b %ERRORLEVEL%
