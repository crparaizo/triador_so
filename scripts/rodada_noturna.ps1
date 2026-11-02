# Rodada noturna de execuções da monografia (Etapa 4 e variante sem raciocínio).
#
# Uso, na raiz do projeto:
#   powershell -ExecutionPolicy Bypass -File scripts\rodada_noturna.ps1
#
# Etapas, em sequência (registro em results\rodada_noturna.log):
#   1. Alarmes simulados — três abordagens, configuração padrão (referência)
#   2. 100 casos — LLM puro e híbrida sem o modo de raciocínio (OLLAMA_REASONING=false)
#   3. Alarmes simulados — LLM puro e híbrida sem o modo de raciocínio
#   4. Experimento CPU x GPU com 10 relatos
#
# O script pede ao Windows que não entre em suspensão enquanto roda e inicia o
# Ollama se ele não estiver respondendo. Nada aqui altera configurações do sistema.

$ErrorActionPreference = "Continue"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)
$py = ".\.venv\Scripts\python.exe"
$log = "results\rodada_noturna.log"
$env:PYTHONIOENCODING = "utf-8"

function Log([string]$m) {
    $linha = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m"
    Write-Host $linha
    $linha | Out-File -FilePath $log -Append -Encoding utf8
}

function Etapa([string]$nome, [string]$raciocinio, [string[]]$argumentos) {
    if ($raciocinio) { $env:OLLAMA_REASONING = $raciocinio } else { Remove-Item Env:OLLAMA_REASONING -ErrorAction SilentlyContinue }
    Log "INICIO  $nome"
    & $py @argumentos 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath $log -Append -Encoding utf8
    Log "FIM     $nome (codigo de saida $LASTEXITCODE)"
}

# Evita a suspensão do Windows durante a rodada (vale só enquanto este processo roda)
Add-Type -Namespace Rodada -Name Energia -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
[void][Rodada.Energia]::SetThreadExecutionState([uint32]"0x80000001")   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

Log "=== Rodada noturna iniciada ==="
try { Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 5 | Out-Null }
catch {
    Log "Ollama nao respondeu; iniciando"
    Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 15
}
try { $v = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 5; Log "Ollama $($v.version) respondendo" }
catch { Log "ERRO: Ollama indisponivel. Rodada interrompida."; exit 1 }

Etapa "1/4 Alarmes - tres abordagens (padrao)" "" @("-m", "src.evaluation", "--dataset", "datasets/alarm_cases.json")
Etapa "2/4 100 casos - LLM puro e hibrida sem raciocinio" "false" @("-m", "src.evaluation", "--approaches", "llm", "hibrido")
Etapa "3/4 Alarmes - LLM puro e hibrida sem raciocinio" "false" @("-m", "src.evaluation", "--approaches", "llm", "hibrido", "--dataset", "datasets/alarm_cases.json")
Etapa "4/4 CPU x GPU com 10 relatos" "" @("-m", "scripts.experimento_cpu_gpu", "--casos", "10")

Remove-Item Env:OLLAMA_REASONING -ErrorAction SilentlyContinue
[void][Rodada.Energia]::SetThreadExecutionState([uint32]"0x80000000")    # libera a suspensão
Log "=== Rodada noturna concluida ==="
