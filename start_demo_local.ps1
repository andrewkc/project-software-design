$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$data = Join-Path $project '.local-postgres\data'
$logs = Join-Path $project '.local-postgres'
$pgCtl = 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe'
$python = Join-Path $project '.venv\Scripts\python.exe'
$vite = Join-Path $project 'frontend\node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $data)) { throw 'No existe la base local de la demo.' }
if (-not (Test-Path -LiteralPath $pgCtl)) { throw 'No se encuentra PostgreSQL 18.' }
if (-not (Test-Path -LiteralPath $python)) { throw 'No existe el entorno Python .venv.' }
if (-not (Test-Path -LiteralPath $vite)) { throw 'Faltan las dependencias del frontend.' }
if (-not (Get-NetTCPConnection -State Listen -LocalPort 55432 -ErrorAction SilentlyContinue)) {
    & $pgCtl -D $data -l (Join-Path $logs 'server.log') -o '-h 127.0.0.1 -p 55432' -w start
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar PostgreSQL.' }
}
if (-not (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $python -ArgumentList @('backend\manage.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory $project -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'django.out.log') -RedirectStandardError (Join-Path $logs 'django.err.log') | Out-Null
}
if (-not (Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @('node_modules\vite\bin\vite.js','--host','127.0.0.1','--port','5173','--strictPort') -WorkingDirectory (Join-Path $project 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'vite.out.log') -RedirectStandardError (Join-Path $logs 'vite.err.log') | Out-Null
}
Write-Output 'Demo disponible en http://127.0.0.1:5173/'
