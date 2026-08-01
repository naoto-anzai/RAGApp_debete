# Debate RAG セットアップスクリプト (Windows / PowerShell)
# 使い方: プロジェクト直下(RAGApp)で  .\setup.ps1  を実行
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== Debate RAG セットアップ ==" -ForegroundColor Cyan

# 1) Python 確認(3.11 推奨)
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "python が見つかりません。Python 3.11 をインストールしてPATHを通してください。" }
python --version

# 2) venv 作成
if (-not (Test-Path ".venv")) {
    Write-Host "[1/4] .venv を作成します..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "[1/4] 既存の .venv を使用します" -ForegroundColor Yellow
}
$venvPy = ".\.venv\Scripts\python.exe"

# 3) 依存インストール(torch等で数GB・十数分かかる場合あり)
Write-Host "[2/4] 依存パッケージをインストールします(数GB・時間がかかります)..." -ForegroundColor Yellow
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt

# 4) .env 準備
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[3/4] .env を作成しました。エディタで開いて GROQ_API_KEY を設定してください!" -ForegroundColor Red
} else {
    Write-Host "[3/4] .env は既に存在します(GROQ_API_KEY が設定済みか確認してください)" -ForegroundColor Yellow
}

# 5) ベクトルDB構築
Write-Host "[4/4] ベクトルDB(debate_pro / debate_con)を構築します..." -ForegroundColor Yellow
$env:PYTHONUTF8 = "1"
& $venvPy -m debate_agent.make_vector_db

Write-Host ""
Write-Host "セットアップ完了! 次のコマンドでデモを実行できます:" -ForegroundColor Green
Write-Host '  $env:PYTHONUTF8 = "1"' -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m debate_agent.debate_main" -ForegroundColor Green
