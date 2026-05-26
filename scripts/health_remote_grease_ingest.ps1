$Endpoint = $env:GREASE_HEALTH_ENDPOINT
if (-not $Endpoint) {
  $Endpoint = "https://sentinelaindustrial.com.br/grease/health"
}

Write-Host "GET $Endpoint"

Invoke-RestMethod -Uri $Endpoint -Method GET
