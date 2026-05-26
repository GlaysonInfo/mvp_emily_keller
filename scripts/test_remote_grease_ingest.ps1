$Endpoint = $env:GREASE_INGEST_ENDPOINT
if (-not $Endpoint) {
  $Endpoint = "https://sentinelaindustrial.com.br/grease/ingest"
}

$Headers = @{ "Content-Type" = "application/json" }

if ($env:GREASE_INGEST_TOKEN) {
  $Headers["X-API-Key"] = $env:GREASE_INGEST_TOKEN
}

$Payload = @{
  tenant_id = "cliente_demo"
  plant_id = "lab_virtual"
  asset_id = "sistema_lubrificacao_01"
  source_id = "grease_gateway_01"
  timestamp_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  cycle_id = "cycle_remote_test_" + (Get-Date -Format "yyyyMMdd_HHmmss")
  metrics = @{
    pressure_saida_graxa_01_bar = 84.2
    pressure_saida_graxa_02_bar = 91.7
    pressure_saida_graxa_03_bar = 7.8
    pressure_saida_graxa_04_bar = 146.5
    peak_saida_graxa_01_bar = 103.3
    peak_saida_graxa_02_bar = 112.1
    peak_saida_graxa_03_bar = 9.2
    peak_saida_graxa_04_bar = 181.2
    min_saida_graxa_01_bar = 2.0
    min_saida_graxa_02_bar = 2.0
    min_saida_graxa_03_bar = 0.0
    min_saida_graxa_04_bar = 4.0
    rise_time_saida_graxa_01_sec = 2.7
    rise_time_saida_graxa_02_sec = 3.6
    rise_time_saida_graxa_03_sec = 8.5
    rise_time_saida_graxa_04_sec = 2.1
    decay_time_saida_graxa_01_sec = 4.7
    decay_time_saida_graxa_02_sec = 4.9
    decay_time_saida_graxa_03_sec = 2.3
    decay_time_saida_graxa_04_sec = 18.6
  }
  quality = @{
    source = "remote_powershell_test"
    sensor_range_bar = 250
    note = "teste remoto EC2"
  }
}

$Json = $Payload | ConvertTo-Json -Depth 10

Write-Host "POST $Endpoint"

Invoke-RestMethod -Uri $Endpoint -Method POST -Headers $Headers -Body $Json
