$ErrorActionPreference = "Stop"

$files = Get-ChildItem -LiteralPath $PSScriptRoot -Filter "*.docx" |
  Where-Object { $_.Name -like "0*-*.docx" } |
  Sort-Object Name

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
  foreach ($file in $files) {
    $docx = $file.FullName
    $pdf = [System.IO.Path]::ChangeExtension($docx, ".pdf")
    if (Test-Path $pdf) {
      Remove-Item -LiteralPath $pdf -Force
    }
    $doc = $word.Documents.Open($docx, $false, $true)
    try {
      $doc.ExportAsFixedFormat($pdf, 17)
      Write-Host "exported $pdf"
    }
    finally {
      $doc.Close($false)
    }
  }
}
finally {
  $word.Quit()
}
