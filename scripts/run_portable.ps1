param([string]$Script = 'tests/integration_blender.py', [switch]$Gui)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PortfolioRoot = Split-Path -Parent (Split-Path -Parent $ProjectRoot)
$SharedEnvironment = Join-Path $PortfolioRoot 'portfolio/env.ps1'
if (Test-Path -LiteralPath $SharedEnvironment) { . $SharedEnvironment }
Set-Location -LiteralPath $ProjectRoot
$PrivateHome = Join-Path $ProjectRoot '.runtime/home'
$env:HOME = $PrivateHome
$env:USERPROFILE = $PrivateHome
$env:APPDATA = Join-Path $PrivateHome 'AppData/Roaming'
$env:LOCALAPPDATA = Join-Path $PrivateHome 'AppData/Local'
$env:TEMP = Join-Path $ProjectRoot '.runtime/tmp'
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
$env:BLENDER_USER_CONFIG = Join-Path $ProjectRoot '.runtime/user/config'
$env:BLENDER_USER_SCRIPTS = Join-Path $ProjectRoot '.runtime/user/scripts'
$env:BLENDER_USER_DATAFILES = Join-Path $ProjectRoot '.runtime/user/datafiles'
$env:XDG_CONFIG_HOME = Join-Path $ProjectRoot '.runtime/xdg/config'
$env:XDG_CACHE_HOME = Join-Path $ProjectRoot '.runtime/xdg/cache'
$env:XDG_DATA_HOME = Join-Path $ProjectRoot '.runtime/xdg/data'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPYCACHEPREFIX = Join-Path $ProjectRoot '.runtime/pycache'
$env:INVARIANT_LEDGER_ROOT = $ProjectRoot
New-Item -ItemType Directory -Force -Path $env:HOME,$env:APPDATA,$env:LOCALAPPDATA,$env:TEMP,$env:BLENDER_USER_CONFIG,$env:BLENDER_USER_SCRIPTS,$env:BLENDER_USER_DATAFILES,$env:XDG_CONFIG_HOME,$env:XDG_CACHE_HOME,$env:XDG_DATA_HOME | Out-Null
$Application = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot '.runtime/blender') -Recurse -Filter blender.exe | Select-Object -First 1
if (-not $Application) { throw 'Acquire the official portable runtime first' }
$ResolvedScript = (Resolve-Path -LiteralPath $Script).Path
if (-not $ResolvedScript.StartsWith($ProjectRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Test script must remain inside project' }
$Report = Join-Path $ProjectRoot 'artifacts/integration-results.json'
if ($Script -eq 'tests/integration_blender.py' -and (Test-Path -LiteralPath $Report)) { Remove-Item -LiteralPath $Report }
if ($Gui) {
    $GuiReport = Join-Path $ProjectRoot 'artifacts/gui-results.json'
    if (Test-Path -LiteralPath $GuiReport) { Remove-Item -LiteralPath $GuiReport }
    $Arguments = @('--factory-startup','--disable-autoexec','--gpu-backend','opengl','--threads','1','--python-exit-code','1','--python',('"' + $ResolvedScript + '"'))
    $Process = Start-Process -FilePath $Application.FullName -ArgumentList $Arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $ProjectRoot '.runtime/gui.stdout.log') -RedirectStandardError (Join-Path $ProjectRoot '.runtime/gui.stderr.log')
    if (-not $Process.WaitForExit(60000)) { $Process.Kill(); throw 'Owned GUI test process exceeded 60 seconds' }
    if (-not (Test-Path -LiteralPath $GuiReport)) { throw 'GUI smoke produced no report; inspect project .runtime/gui.stderr.log' }
    $Result = Get-Content -LiteralPath $GuiReport -Raw | ConvertFrom-Json
    if ($Result.errors.Count -gt 0) { throw 'GUI smoke report contains errors' }
    Write-Output "Native GUI checks passed: $($Result.passed)"
} else {
    & $Application.FullName --background --factory-startup --disable-autoexec --threads 1 --python-exit-code 1 --python $ResolvedScript
    if ($LASTEXITCODE) { throw "Blender exited with $LASTEXITCODE" }
}
if ($Script -eq 'tests/integration_blender.py') {
    if (-not (Test-Path -LiteralPath $Report)) { throw 'Native integration did not produce a report' }
    $Result = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
    if ($Result.passed -ne $Result.total -or $Result.total -lt 8) { throw 'Native integration report contains failures' }
}
