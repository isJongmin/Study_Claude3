@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist backend\.venv (
  echo [1/3] 파이썬 가상환경을 만듭니다...
  python -m venv backend\.venv || goto :err
  backend\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt || goto :err
)
if not exist frontend\node_modules (
  echo [2/3] 프런트 패키지를 설치합니다...
  call npm --prefix frontend ci || goto :err
)
echo [3/3] 서버를 시작합니다. 준비되면 브라우저가 열립니다.
start "" /b powershell -NoProfile -Command "for($i=0;$i -lt 120;$i++){try{Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing -TimeoutSec 2 | Out-Null}catch{ if($_.Exception.Response){}else{Start-Sleep 1;continue} }; try{Invoke-WebRequest http://127.0.0.1:5173 -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process http://127.0.0.1:5173; break}catch{Start-Sleep 1}}"
backend\.venv\Scripts\python.exe scripts\dev.py
goto :eof
:err
echo 설치 중 오류가 발생했습니다. 위 메시지를 확인하세요.
pause
