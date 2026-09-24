# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0.

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('setup', 'start', 'stop', 'restart', 'status', 'index',
        'reset', 'check', 'help')]
    [string] $Command,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]] $Arguments,

    [string] $ImageCatHome = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$ImageCatHome = [IO.Path]::GetFullPath($ImageCatHome)
$portableHome = $ImageCatHome -replace '\\', '/'

function Resolve-Uv {
    $uv = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($uv) { return $uv.Source }
    $winget = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages') `
        -Filter uv.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($winget) { return $winget.FullName }
    throw 'uv was not found. Install it with: winget install astral-sh.uv'
}

function Invoke-Setup {
    $uv = Resolve-Uv
    $env:Path = @(
        [Environment]::GetEnvironmentVariable('Path', 'Machine'),
        [Environment]::GetEnvironmentVariable('Path', 'User'),
        $env:Path) -join ';'
    $venv = Join-Path $ImageCatHome '.venv'
    if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
        & $uv venv $venv --python 3.11
        if ($LASTEXITCODE -ne 0) { throw 'Unable to create the ImageCat virtual environment.' }
    }
    & $uv pip install --python (Join-Path $venv 'Scripts\python.exe') `
        -r (Join-Path $ImageCatHome 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install ImageCat Python dependencies.' }

    # Keep parity with bin/imagecat-setup: foreground/background indexing is
    # optional, but install its segmenter when the platform has a compatible
    # wheel. The top-level requirements already supplies onnxruntime.
    & $uv pip install --python (Join-Path $venv 'Scripts\python.exe') rembg
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'rembg was not installed; foreground/background indexing will be unavailable.'
    }

    $web = Join-Path $ImageCatHome 'imagespace\web'
    if (Test-Path -LiteralPath (Join-Path $web 'package.json')) {
        Push-Location $web
        try {
            & npm.cmd ci
            if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'ImageSpace UI build failed.' }
        } finally {
            Pop-Location
        }
    }
    Write-Host "ImageCat setup complete: $venv"
}

function Invoke-PosixCommand {
    $gitBin = Join-Path $env:ProgramFiles 'Git\bin'
    $sh = Join-Path $gitBin 'sh.exe'
    if (-not (Test-Path -LiteralPath $sh)) {
        throw 'Git Bash is required for ImageCat pipeline commands.'
    }
    $env:Path = "$gitBin;$(Join-Path $env:ProgramFiles 'Git\usr\bin');$env:Path"
    foreach ($javaHome in @(
        $env:JAVA_HOME,
        [Environment]::GetEnvironmentVariable('JAVA_HOME', 'User'),
        [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine'))) {
        if ($javaHome -and (Test-Path -LiteralPath (Join-Path $javaHome 'bin\java.exe'))) {
            $env:JAVA_HOME = $javaHome
            $env:JRE_HOME = $javaHome
            $env:Path = "$(Join-Path $javaHome 'bin');$($env:Path)"
            break
        }
    }
    if (-not $env:JAVA_HOME) {
        throw 'Java was not found. Set JAVA_HOME to a JDK installation.'
    }
    $env:IMAGECAT_HOME = $portableHome
    $env:OODT_HOME = $portableHome
    $env:OODT_BASE = $portableHome
    $env:PYTHON = "$portableHome/.venv/Scripts/python.exe"
    $env:IMAGE_SPACE_PYTHON = $env:PYTHON
    $env:PYTHON_EXECUTABLE = $env:PYTHON
    $script = "$portableHome/bin/imagecat"
    & $sh $script $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "ImageCat $Command failed with exit code $LASTEXITCODE." }
}

$oodt = Join-Path $PSScriptRoot 'oodt.ps1'
switch ($Command) {
    'setup' { Invoke-Setup }
    'start' { & $oodt start -OodtHome $ImageCatHome }
    'stop' { & $oodt stop -OodtHome $ImageCatHome }
    'restart' { & $oodt restart -OodtHome $ImageCatHome }
    'status' { Invoke-PosixCommand }
    'help' { & $oodt status -OodtHome $ImageCatHome; Write-Host 'Use: imagecat.ps1 setup|start|stop|status|index|reset|check' }
    default { Invoke-PosixCommand }
}
