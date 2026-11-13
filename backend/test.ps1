Write-Host "========================================" -ForegroundColor Cyan
Write-Host " DIAGNOSTICO PUERTO 8000" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`n[1] NETSTAT COMPLETO" -ForegroundColor Yellow
netstat -ano | findstr :8000

Write-Host "`n[2] NETSTAT LISTENING" -ForegroundColor Yellow
netstat -ano | findstr :8000 | findstr LISTENING

Write-Host "`n[3] GET-NETTCP LISTEN" -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort, State, OwningProcess |
  Format-Table -AutoSize

Write-Host "`n[4] GET-NETTCP TODAS LAS CONEXIONES" -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State, OwningProcess |
  Format-Table -AutoSize

Write-Host "`n[5] PROCESOS DE LOS PID EN NETSTAT" -ForegroundColor Yellow

$netstatPids = netstat -ano |
  findstr :8000 |
  ForEach-Object {
    $parts = ($_ -split '\s+') | Where-Object { $_ -ne "" }

    if ($parts.Count -ge 5) {
      $parts[4]
    }
  } |
  Where-Object {
    $_ -match '^\d+$' -and $_ -ne '0'
  } |
  Sort-Object -Unique

foreach ($processId in $netstatPids) {
  Write-Host "`nPID encontrado: $processId"

  Get-Process -Id $processId -ErrorAction SilentlyContinue |
    Select-Object Id, ProcessName, Path |
    Format-List

  if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Windows NO encuentra este proceso." -ForegroundColor Red
  }
}

Write-Host "`n[6] PROCESOS RELACIONADOS CON PYTHON / UVICORN" -ForegroundColor Yellow

Get-Process |
  Where-Object {
    $_.ProcessName -match 'python|uvicorn'
  } |
  Select-Object Id, ProcessName, Path |
  Format-Table -AutoSize

Write-Host "`n[7] PROCESO 14856" -ForegroundColor Yellow

Get-Process -Id 14856 -ErrorAction SilentlyContinue |
  Select-Object Id, ProcessName, Path |
  Format-List

Write-Host "`n[8] CMD / POWERSHELL / PYTHON CON LINEA DE COMANDO" -ForegroundColor Yellow

Get-CimInstance Win32_Process |
  Where-Object {
    $_.ProcessId -in $netstatPids -or
    $_.ProcessId -eq 14856
  } |
  Select-Object ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine |
  Format-List

Write-Host "`n[9] PROCESOS PADRE" -ForegroundColor Yellow

$allProcessIds = @($netstatPids) + 14856

foreach ($processId in $allProcessIds) {
  $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue

  if ($processInfo) {
    Write-Host "`nPID: $processId"
    Write-Host "Proceso: $($processInfo.Name)"
    Write-Host "PID padre: $($processInfo.ParentProcessId)"

    Get-CimInstance Win32_Process -Filter "ProcessId = $($processInfo.ParentProcessId)" -ErrorAction SilentlyContinue |
      Select-Object ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine |
      Format-List
  }
}

Write-Host "`n[10] SERVICIOS RELACIONADOS CON PYTHON" -ForegroundColor Yellow

Get-CimInstance Win32_Service |
  Where-Object {
    $_.PathName -match 'python|uvicorn' -or
    $_.DisplayName -match 'python|uvicorn' -or
    $_.Name -match 'python|uvicorn'
  } |
  Select-Object Name, DisplayName, State, StartMode, ProcessId, PathName |
  Format-Table -AutoSize

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " FIN DEL DIAGNOSTICO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan