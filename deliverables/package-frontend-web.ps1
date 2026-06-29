Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend-web"
$zipPath = Join-Path $PSScriptRoot "frontend-web-dist.zip"

Push-Location $frontendDir
try {
  npm install
  npm run build
}
finally {
  Pop-Location
}

if (Test-Path $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -Path (Join-Path $frontendDir "dist\*") -DestinationPath $zipPath -Force
Write-Host "Packaged: $zipPath"
