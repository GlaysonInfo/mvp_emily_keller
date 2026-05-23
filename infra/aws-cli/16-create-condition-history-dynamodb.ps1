param(
    [string]$TableName = $(if ($env:CONDITION_HISTORY_TABLE) { $env:CONDITION_HISTORY_TABLE } else { "condition_history" }),
    [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } elseif ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }),
    [string]$Profile = $env:AWS_PROFILE
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI nao encontrado. Instale/configure a AWS CLI antes de criar a tabela."
}

$profileArgs = @()
if ($Profile) {
    $profileArgs = @("--profile", $Profile)
}

function Invoke-AwsCli {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    try {
        $output = & aws @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    [pscustomobject]@{
        ExitCode = $exitCode
        Output = (($output | Out-String).Trim())
    }
}

Write-Host "Tabela de historico: $TableName"
Write-Host "Regiao AWS: $Region"
if ($Profile) {
    Write-Host "Profile AWS: $Profile"
}

$describeArgs = @(
    "dynamodb", "describe-table",
    "--table-name", $TableName,
    "--region", $Region
) + $profileArgs

$describeResult = Invoke-AwsCli -Arguments $describeArgs

if ($describeResult.ExitCode -eq 0) {
    Write-Host "Tabela ja existe: $TableName"
} elseif ($describeResult.Output -match "ResourceNotFoundException") {
    Write-Host "Criando tabela: $TableName"

    $createArgs = @(
        "dynamodb", "create-table",
        "--table-name", $TableName,
        "--attribute-definitions",
        "AttributeName=tenant_asset,AttributeType=S",
        "AttributeName=ts_utc_minute,AttributeType=S",
        "--key-schema",
        "AttributeName=tenant_asset,KeyType=HASH",
        "AttributeName=ts_utc_minute,KeyType=RANGE",
        "--billing-mode", "PAY_PER_REQUEST",
        "--region", $Region
    ) + $profileArgs

    $createResult = Invoke-AwsCli -Arguments $createArgs
    if ($createResult.ExitCode -ne 0) {
        Write-Error $createResult.Output
        exit $createResult.ExitCode
    }

    $waitArgs = @(
        "dynamodb", "wait", "table-exists",
        "--table-name", $TableName,
        "--region", $Region
    ) + $profileArgs

    $waitResult = Invoke-AwsCli -Arguments $waitArgs
    if ($waitResult.ExitCode -ne 0) {
        Write-Error $waitResult.Output
        exit $waitResult.ExitCode
    }

    Write-Host "Tabela criada: $TableName"
} else {
    Write-Error $describeResult.Output
    exit $describeResult.ExitCode
}

Write-Host "Configurando TTL no atributo ttl_epoch..."

$ttlArgs = @(
    "dynamodb", "update-time-to-live",
    "--table-name", $TableName,
    "--time-to-live-specification", "Enabled=true,AttributeName=ttl_epoch",
    "--region", $Region
) + $profileArgs

$ttlResult = Invoke-AwsCli -Arguments $ttlArgs

if ($ttlResult.ExitCode -ne 0) {
    Write-Warning "Nao foi possivel configurar TTL agora. A tabela foi criada, mas vale tentar novamente depois."
    Write-Warning $ttlResult.Output
}

Write-Host ""
Write-Host "OK. Para o dashboard, mantenha no mesmo terminal:"
Write-Host "`$env:CONDITION_HISTORY_TABLE=`"$TableName`""
Write-Host "`$env:AWS_REGION=`"$Region`""
if ($Profile) {
    Write-Host "`$env:AWS_PROFILE=`"$Profile`""
}
