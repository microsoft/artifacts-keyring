#!/usr/bin/env pwsh
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
#
# End-to-end tests for artifacts-keyring against a live Azure Artifacts feed.
# A user already authenticated to Azure DevOps (e.g. via az login or browser) should
# be able to run this against a private feed and all scenarios should succeed.
#
# Usage:
#   .\test.ps1 -TestFeed <feed-simple-url> [-TestPackage <package-name>] [-WhlPath <path-to-whl>]
#
# Example:
#   .\test.ps1 -TestFeed https://pkgs.dev.azure.com/<org>/_packaging/<feed>/pypi/simple/ -TestPackage numpy

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$TestFeed,

    [Parameter(Mandatory = $false)]
    [string]$TestPackage = "pip",

    [Parameter(Mandatory = $false)]
    [string]$WhlPath = ""
)

$PassCount = 0
$FailCount = 0
$TestResults = @()

function Clear-AllCaches {
    Write-Host "`nClearing all credential and pip caches..." -ForegroundColor Yellow

    # Session Token Cache
    $sessionCache = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) "MicrosoftCredentialProvider" "SessionTokenCache.dat"
    if (Test-Path $sessionCache) {
        Remove-Item $sessionCache -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed session token cache: $sessionCache" -ForegroundColor DarkYellow
    }

    # MSAL Token Cache
    $msalCache = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) ".IdentityService"
    if (Test-Path $msalCache) {
        Remove-Item $msalCache -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed MSAL token cache: $msalCache" -ForegroundColor DarkYellow
    }

    # pip HTTP cache
    & pip cache purge 2>&1 | Out-Null
    Write-Host "  Cleared pip cache" -ForegroundColor DarkYellow
}

function Invoke-Test {
    param(
        [string]$Name,
        [string[]]$PipArgs
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan

    # Run pip directly to the console with no pipeline so that
    # credential provider stderr (device flow / browser prompts) is
    # never buffered and appears immediately.
    & pip @PipArgs
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "[PASS] $Name" -ForegroundColor Green
        $script:PassCount++
        $script:TestResults += [PSCustomObject]@{ Test = $Name; Result = "PASS" }
    }
    else {
        Write-Host "[FAIL] $Name (exit code: $exitCode)" -ForegroundColor Red
        $script:FailCount++
        $script:TestResults += [PSCustomObject]@{ Test = $Name; Result = "FAIL" }
    }

    return $exitCode
}

# ---------------------------------------------------------------------------
# Install the wheel under test if provided, otherwise use whatever is installed
# ---------------------------------------------------------------------------
if (-not [string]::IsNullOrEmpty($WhlPath)) {
    Write-Host "`nInstalling artifacts-keyring from: $WhlPath" -ForegroundColor Cyan
    & pip install $WhlPath --force-reinstall
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install artifacts-keyring wheel." -ForegroundColor Red
        exit 1
    }
}

# Confirm artifacts-keyring is registered as a keyring backend
Write-Host "`nRegistered keyring backends:" -ForegroundColor Cyan
& python -c "import keyring.backend; backends = keyring.backend.get_all_keyring(); [print(' -', type(b).__name__, b.priority) for b in sorted(backends, key=lambda b: b.priority, reverse=True)]"

# ---------------------------------------------------------------------------
# Test 1: pip install (interactive, fresh auth)
# ---------------------------------------------------------------------------
Clear-AllCaches
$result = Invoke-Test -Name "pip_install_interactive" -PipArgs @(
    "install", $TestPackage,
    "--index-url", $TestFeed,
    "--force-reinstall",
    "--no-cache-dir",
    "-v"
)

# Tests 2 and 3 depend on a valid cached token from Test 1 — skip if it failed
if ($result -ne 0) {
    Write-Host "`nSkipping Tests 2 and 3: require Test 1 to pass first." -ForegroundColor Yellow
}
else {
    # ---------------------------------------------------------------------------
    # Test 2: pip install (cached session token — should succeed silently)
    # ---------------------------------------------------------------------------
    $result = Invoke-Test -Name "pip_install_cached_token" -PipArgs @(
        "install", $TestPackage,
        "--index-url", $TestFeed,
        "--force-reinstall",
        "--no-cache-dir",
        "-v"
    )

    # ---------------------------------------------------------------------------
    # Test 3: pip install with non-interactive mode (requires valid cached token)
    # ---------------------------------------------------------------------------
    if ($result -ne 0) {
        Write-Host "`nSkipping Test 3: requires Test 2 to pass first." -ForegroundColor Yellow
    }
    else {
        $env:ARTIFACTS_KEYRING_NONINTERACTIVE_MODE = "true"
        Invoke-Test -Name "pip_install_noninteractive" -PipArgs @(
            "install", $TestPackage,
            "--index-url", $TestFeed,
            "--force-reinstall",
            "--no-cache-dir",
            "-v"
        )
        Remove-Item Env:\ARTIFACTS_KEYRING_NONINTERACTIVE_MODE -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------------------
# Test 4: pip install with credential provider logging enabled
# ---------------------------------------------------------------------------
Clear-AllCaches
$logPath = Join-Path $PSScriptRoot "credprovider_test4.log"
$env:ARTIFACTS_CREDENTIALPROVIDER_LOG_PATH = $logPath
Invoke-Test -Name "pip_install_with_credprovider_log" -PipArgs @(
    "install", $TestPackage,
    "--index-url", $TestFeed,
    "--force-reinstall",
    "--no-cache-dir",
    "-v"
)
Remove-Item Env:\ARTIFACTS_CREDENTIALPROVIDER_LOG_PATH -ErrorAction SilentlyContinue
if (Test-Path $logPath) {
    Write-Host "  Credential provider log written to: $logPath" -ForegroundColor DarkCyan
}
else {
    Write-Host "  Warning: Credential provider log was not created at $logPath" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Test 5: pip install after clearing only session token cache (forces cred provider re-auth via MSAL)
# ---------------------------------------------------------------------------
$sessionCache = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) "MicrosoftCredentialProvider" "SessionTokenCache.dat"
if (Test-Path $sessionCache) {
    Remove-Item $sessionCache -Force -ErrorAction SilentlyContinue
    Write-Host "`nCleared session token cache only (MSAL still warm)" -ForegroundColor Yellow
}
Invoke-Test -Name "pip_install_after_session_cache_clear" -PipArgs @(
    "install", $TestPackage,
    "--index-url", $TestFeed,
    "--force-reinstall",
    "--no-cache-dir",
    "-v"
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Test Results" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$TestResults | Format-Table Test, Result -AutoSize
Write-Host "PASSED: $PassCount  FAILED: $FailCount" -ForegroundColor $(if ($FailCount -eq 0) { "Green" } else { "Red" })

if ($FailCount -gt 0) {
    exit 1
}
exit 0
