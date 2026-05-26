$Endpoint = if ($env:CONDITION_HEALTH_ENDPOINT) { $env:CONDITION_HEALTH_ENDPOINT } else { "https://sentinelaindustrial.com.br/condition/health" }

Invoke-RestMethod -Method Get -Uri $Endpoint | ConvertTo-Json -Depth 8
