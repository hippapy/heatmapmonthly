@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   섹터 로테이션 히트맵 - 데이터 수집 및 자동 게시
echo ============================================================
echo.

REM ---- 0) git 저장소인지 확인 (자동 push에 필요) ----
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [오류] 이 폴더는 git 저장소가 아닙니다.
  echo        먼저 저장소를 clone 한 폴더 안에서 실행하세요:
  echo        git clone https://github.com/hippapy/heatmapmonthly.git
  echo.
  pause
  exit /b 1
)

REM ---- 1) 토스 API 키 로드 (toss_secret.txt는 .gitignore로 커밋 제외) ----
if not exist toss_secret.txt (
  echo 토스증권 Open API 키를 처음 한 번만 입력합니다. ^(toss_secret.txt에 저장^)
  set /p CID=API Key ^(client_id^):
  set /p CSEC=Secret Key ^(client_secret^):
  > toss_secret.txt echo !CID!
  >> toss_secret.txt echo !CSEC!
  echo 저장했습니다. 다음 실행부터는 자동으로 불러옵니다.
  echo.
)
set _i=0
for /f "usebackq delims=" %%L in ("toss_secret.txt") do (
  set /a _i+=1
  if !_i!==1 set TOSS_CLIENT_ID=%%L
  if !_i!==2 set TOSS_CLIENT_SECRET=%%L
)
if "!TOSS_CLIENT_ID!"=="" ( echo [오류] toss_secret.txt 형식이 잘못됨 & pause & exit /b 1 )

REM ---- 2) 의존성 ----
python -m pip install --quiet requests
if errorlevel 1 ( echo [오류] python/pip 를 찾을 수 없습니다. python.org에서 설치하세요. & pause & exit /b 1 )

REM ---- 3) 데이터 수집 ----
echo [1/3] 토스 API에서 데이터 수집 중... ^(수 분 소요될 수 있음^)
python scripts\fetch_toss_data.py --since 2023-12-01 --out data\sector_monthly_returns.json
if errorlevel 1 ( echo [오류] 데이터 수집 실패 ^(위 메시지 확인 - 403이면 IP 화이트리스트^) & pause & exit /b 1 )

REM ---- 4) 변경분만 커밋 & 푸시 ----
echo [2/3] 변경사항 확인 및 커밋...
git add data\sector_monthly_returns.json
git diff --cached --quiet
if not errorlevel 1 ( echo 데이터에 변경이 없어 게시를 생략합니다. & pause & exit /b 0 )
git commit -m "Update sector monthly returns (%date% %time%)"

echo [3/3] GitHub에 push...
git push
if errorlevel 1 ( echo [오류] git push 실패 ^(GitHub 로그인/권한 확인^) & pause & exit /b 1 )

echo.
echo ============================================================
echo   완료! GitHub Pages가 1~2분 내 자동 갱신됩니다.
echo   대시보드: https://hippapy.github.io/heatmapmonthly/
echo ============================================================
pause
