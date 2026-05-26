$Endpoint = if ($env:CONDITION_INGEST_ENDPOINT) { $env:CONDITION_INGEST_ENDPOINT } else { "https://sentinelaindustrial.com.br/condition/ingest" }
$Token = $env:CONDITION_INGEST_TOKEN

$Headers = @{
    "Content-Type" = "application/json"
}

if ($Token) {
    $Headers["X-API-Key"] = $Token
}

$Payload = @{
    tenant_id = if ($env:CONDITION_TENANT_ID) { $env:CONDITION_TENANT_ID } else { "cliente_demo" }
    plant_id = if ($env:CONDITION_PLANT_ID) { $env:CONDITION_PLANT_ID } else { "lab_virtual" }
    asset_id = if ($env:CONDITION_ASSET_ID) { $env:CONDITION_ASSET_ID } else { "motor_001" }
    asset_name = if ($env:CONDITION_ASSET_NAME) { $env:CONDITION_ASSET_NAME } else { "Motor Principal" }
    source = if ($env:CONDITION_SOURCE) { $env:CONDITION_SOURCE } else { "condition_gateway_01" }
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    metrics = @(
        @{ name = "rpm"; value = 1778.0; unit = "rpm" },
        @{ name = "vibration_rms_mm_s"; value = 4.4; unit = "mm/s" },
        @{ name = "vibration_peak_g"; value = 0.82; unit = "g" },
        @{ name = "temperature_c"; value = 62.8; unit = "C" },
        @{ name = "ultrasound_db"; value = 33.1; unit = "dB" },
        @{ name = "kurtosis"; value = 3.2; unit = "index" },
        @{ name = "crest_factor"; value = 3.1; unit = "index" },
        @{ name = "health_score"; value = 67.6; unit = "score" },
        @{ name = "severity_score"; value = 32.4; unit = "score" }
    )
    quality = @{
        source = "powershell_remote_test"
        sample_rate_hz = 1
    }
}

Invoke-RestMethod -Method Post -Uri $Endpoint -Headers $Headers -Body ($Payload | ConvertTo-Json -Depth 8) | ConvertTo-Json -Depth 12
