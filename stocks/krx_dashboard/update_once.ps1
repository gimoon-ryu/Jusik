$ErrorActionPreference = "Stop"

Set-Location (Resolve-Path "$PSScriptRoot\..\..")
python -m stocks.krx_dashboard.cli update

