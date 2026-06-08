#requires -Version 5.1
<#
.SYNOPSIS
  Seta as variaveis de ambiente do backend no servico Railway linkado,
  lendo os valores de backend/.env e sobrescrevendo as 4 variaveis cujo
  valor de producao difere do ambiente local (APP_ENV, APP_DEBUG,
  BACKEND_URL, FRONTEND_URL).

.DESCRIPTION
  Evita copiar/colar ~11 secrets a mao (e o inferno de quoting do PowerShell).
  Os valores nunca aparecem no terminal — apenas as CHAVES sao listadas.

  Pre-requisitos:
    1. railway CLI instalado e logado na conta nova:  railway login
    2. Servico do backend ja criado e linkado:
         cd backend ; railway init ; railway up
       Rode ESTE script de dentro de backend/ OU passe -Service <nome>.

.PARAMETER BackendUrl
  URL publica do Railway (apos `railway domain`). Vira BACKEND_URL.

.PARAMETER FrontendUrl
  URL de producao do Vercel (apos `vercel --prod`). Vira FRONTEND_URL (CORS).
  Omita na 1a passada; rode de novo com este valor na Fase 3.

.PARAMETER Service
  Nome do servico Railway. Se omitido, usa o servico linkado ao diretorio atual.

.EXAMPLE
  cd backend
  ..\scripts\deploy_railway_env.ps1 -BackendUrl "https://xxx.up.railway.app"

.EXAMPLE
  ..\scripts\deploy_railway_env.ps1 -FrontendUrl "https://yyy.vercel.app"
#>
param(
    [string]$BackendUrl = "",
    [string]$FrontendUrl = "",
    [string]$Service = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $repoRoot "backend\.env"

if (-not (Test-Path $envFile)) {
    throw "Nao encontrei $envFile"
}

# Variaveis cujo valor de producao difere do .env local.
$overrides = [ordered]@{
    "APP_ENV"   = "production"
    "APP_DEBUG" = "false"
}
if ($BackendUrl)  { $overrides["BACKEND_URL"]  = $BackendUrl }
if ($FrontendUrl) { $overrides["FRONTEND_URL"] = $FrontendUrl }

# Essas nunca vem do arquivo — controladas so pelos overrides acima.
$skip = @("APP_ENV", "APP_DEBUG", "BACKEND_URL", "FRONTEND_URL")

$pairs = [System.Collections.Generic.List[string]]::new()

foreach ($raw in Get-Content -LiteralPath $envFile) {
    $line = $raw.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { continue }
    if ($line.StartsWith("export ")) { $line = $line.Substring(7).Trim() }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { continue }
    $key = $line.Substring(0, $idx).Trim()
    $val = $line.Substring($idx + 1).Trim()
    # remove aspas circundantes, se houver
    if ($val.Length -ge 2 -and (
            ($val.StartsWith('"') -and $val.EndsWith('"')) -or
            ($val.StartsWith("'") -and $val.EndsWith("'"))
        )) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    if ($skip -contains $key) { continue }
    $pairs.Add("$key=$val")
}

foreach ($k in $overrides.Keys) {
    $pairs.Add("$k=$($overrides[$k])")
}

if ($pairs.Count -eq 0) { throw "Nenhuma variavel lida de $envFile" }

# Monta os argumentos do railway. O splatting (@railwayArgs) passa cada
# valor como um token unico — sem reinterpretacao de $, aspas, etc.
$railwayArgs = [System.Collections.Generic.List[string]]::new()
$railwayArgs.Add("variables")
if ($Service) { $railwayArgs.Add("--service"); $railwayArgs.Add($Service) }
foreach ($p in $pairs) {
    $railwayArgs.Add("--set")
    $railwayArgs.Add($p)
}

$keys = $pairs | ForEach-Object { ($_ -split "=", 2)[0] }
Write-Host "Setando $($pairs.Count) variaveis no Railway:" -ForegroundColor Cyan
Write-Host ("  " + ($keys -join ", "))
Write-Host ""

& railway @railwayArgs
