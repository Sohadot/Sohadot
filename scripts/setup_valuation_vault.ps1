# Create a private valuation vault outside every Git working tree.
# Pass the destination. This script has no machine-specific default path.
# It does not initialise Git, enable BitLocker, or change machine-wide policy.
param(
    [Parameter(Mandatory = $true)]
    [string]$VaultPath
)

$ErrorActionPreference = "Stop"
$Vault = [System.IO.Path]::GetFullPath($VaultPath)

function Test-GitAtOrAbove([string]$Start) {
    $currentPath = $Start
    if (-not (Test-Path -LiteralPath $currentPath)) {
        $currentPath = Split-Path -Parent $currentPath
    }
    while ($currentPath) {
        if (Test-Path -LiteralPath (Join-Path $currentPath ".git")) {
            return $currentPath
        }
        $parent = Split-Path -Parent $currentPath
        if (-not $parent -or $parent -eq $currentPath) {
            break
        }
        $currentPath = $parent
    }
    return $null
}

# Reject a repository root, or any path inside one, before creating directories.
$git = Test-GitAtOrAbove $Vault
if ($git) {
    throw "Refusing to create a vault inside a Git working tree: $git"
}
if (Test-Path -LiteralPath $Vault) {
    $existing = Get-Item -LiteralPath $Vault -Force
    if ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing reparse point: $Vault"
    }
}

$stages = @(
    "sources", "licences", "raw-sales", "verified-sales", "calibration",
    "holdout", "evaluation", "export", "audit", "config"
)
New-Item -ItemType Directory -Force -Path $Vault | Out-Null
foreach ($stage in $stages) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Vault $stage) | Out-Null
}
New-Item -ItemType Directory -Force -Path (Join-Path $Vault "export\approved") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Vault "evaluation\rejected") | Out-Null

if (Test-Path -LiteralPath (Join-Path $Vault ".git")) {
    throw "Git metadata is present in the vault. Do not commit or push this directory."
}

[Environment]::SetEnvironmentVariable("SOHADOT_PRIVATE_ROOT", $Vault, "User")
$env:SOHADOT_PRIVATE_ROOT = $Vault

$acl = & icacls $Vault /inheritance:d
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not adjust inheritance on $Vault. Existing permissions were left unchanged."
} else {
    $acl | Out-Host
    & icacls $Vault /grant:r "${env:USERNAME}:(OI)(CI)F" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not grant the current user an explicit full-control entry."
    }
    & icacls $Vault /remove "BUILTIN\Users" "NT AUTHORITY\Authenticated Users" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not remove broad inherited user entries. Review icacls output before importing real records."
    }
}

Write-Host ""
Write-Host "Vault directory: $Vault"
Write-Host "SOHADOT_PRIVATE_ROOT set for the current user."
Write-Host "This script did not enable BitLocker and did not create a backup."
Write-Host "Do not put this folder in a cloud-sync directory, and do not run git init here."
Write-Host ""
Write-Host "Synthetic demo, in an empty directory that is not this vault:"
Write-Host "  python scripts\valuation_vault.py demo --root <empty-disposable-directory>"
