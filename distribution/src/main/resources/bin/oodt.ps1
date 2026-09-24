# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0.

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('start', 'stop', 'restart', 'status')]
    [string] $Command,

    [string] $OodtHome = (Split-Path -Parent $PSScriptRoot),
    [int] $FileManagerPort = 9000,
    [int] $WorkflowPort = 9001,
    [int] $ResourceManagerPort = 9002,
    [int] $TomcatPort = 8080,
    [int] $SolrPort = 8983,
    [int] $ImageSpacePort = 8090
)

$ErrorActionPreference = 'Stop'
$OodtHome = [IO.Path]::GetFullPath($OodtHome)
$RunHome = Join-Path $OodtHome 'run'
$LogHome = Join-Path $OodtHome 'logs'
$StateFile = Join-Path $RunHome 'oodt-windows.json'

New-Item -ItemType Directory -Force -Path $RunHome, $LogHome | Out-Null

function Resolve-Java {
    foreach ($javaHome in @(
        $env:JAVA_HOME,
        [Environment]::GetEnvironmentVariable('JAVA_HOME', 'User'),
        [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine'))) {
        if (-not $javaHome) { continue }
        $candidate = Join-Path $javaHome 'bin\java.exe'
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    $command = Get-Command java.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'Java was not found. Set JAVA_HOME to a JDK installation.'
}

function Set-JavaEnvironment {
    $java = Resolve-Java
    $env:JAVA_HOME = Split-Path -Parent (Split-Path -Parent $java)
    return $java
}

function Test-Port([int] $Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.ConnectAsync('127.0.0.1', $Port)
        return $pending.Wait(500) -and $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Wait-Port([int] $Port, [bool] $Open, [int] $Seconds = 45) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        if ((Test-Port $Port) -eq $Open) { return $true }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    return $false
}

function Quote-Argument([string] $Value) {
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

function Start-ManagedProcess(
    [string] $Name,
    [string] $FilePath,
    [string[]] $Arguments,
    [string] $WorkingDirectory
) {
    $stdout = Join-Path $LogHome "$Name.out.log"
    $stderr = Join-Path $LogHome "$Name.err.log"
    $argumentLine = ($Arguments | ForEach-Object { Quote-Argument $_ }) -join ' '
    $process = Start-Process -FilePath $FilePath -ArgumentList $argumentLine `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    return $process.Id
}

function Get-State {
    if (-not (Test-Path -LiteralPath $StateFile)) { return @{} }
    try {
        $state = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
        $result = @{}
        $state.psobject.Properties | ForEach-Object { $result[$_.Name] = [int]$_.Value }
        return $result
    } catch {
        Write-Warning "Ignoring invalid state file: $StateFile"
        return @{}
    }
}

function Save-State([hashtable] $State) {
    $State | ConvertTo-Json | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Stop-ManagedProcess([string] $Name, [hashtable] $State) {
    if (-not $State.ContainsKey($Name)) { return }
    $process = Get-Process -Id $State[$Name] -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id
        try { Wait-Process -Id $process.Id -Timeout 10 -ErrorAction Stop } catch {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    $State.Remove($Name)
}

function Set-DeploymentEnvironment {
    # Long-running hosts may not yet have inherited recently installed tools.
    # Rebuild PATH from its persistent scopes and expose Git's POSIX shell when
    # present, since OODT PGE configurations may legitimately request `sh`.
    $persistentPath = @(
        [Environment]::GetEnvironmentVariable('Path', 'Machine'),
        [Environment]::GetEnvironmentVariable('Path', 'User'),
        $env:Path) -join ';'
    $gitShell = Join-Path $env:ProgramFiles 'Git\bin'
    $env:Path = if (Test-Path -LiteralPath (Join-Path $gitShell 'sh.exe')) {
        "$gitShell;$persistentPath"
    } else { $persistentPath }

    # Java accepts forward slashes on Windows. Keeping deployment paths in
    # that form also prevents downstream metadata/property parsers from
    # interpreting backslashes as escapes.
    $portableHome = $OodtHome -replace '\\', '/'
    $env:OODT_HOME = $portableHome
    $env:OODT_BASE = $portableHome
    $env:IMAGECAT_HOME = $portableHome
    $env:FILEMGR_HOME = "$portableHome/filemgr"
    $env:WORKFLOW_HOME = "$portableHome/workflow"
    # Resource Manager's properties append this value to file://. A leading
    # slash and URI separators produce a valid file:///C:/... URI on Windows.
    $env:RESMGR_HOME = "/$portableHome/resmgr"
    $env:PCS_HOME = "$portableHome/pcs"
    $env:CRAWLER_HOME = "$portableHome/crawler"
    $env:PGE_HOME = "$portableHome/pge"
    $env:PGE_ROOT = "$portableHome/pge"
    $env:FILEMGR_URL = "http://localhost:$FileManagerPort"
    $env:WORKFLOW_URL = "http://localhost:$WorkflowPort"
    $env:RESMGR_URL = "http://localhost:$ResourceManagerPort"
    $env:OPSUI_URL = "http://localhost:$TomcatPort/opsui"
    $env:SOLR_BASE_URL = "http://localhost:$SolrPort/solr"
    $env:SOLR_URL = "$($env:SOLR_BASE_URL)/imagecat"
    $env:SOLR_FM_URL = "$($env:SOLR_BASE_URL)/oodt-fm"
    $env:IMAGE_SPACE_HOME = "$portableHome/imagespace"
    $env:IMAGE_SPACE_DATA = "$portableHome/data/imagespace"
    $env:IMAGE_SPACE_SOLR = $env:SOLR_URL
    $env:KERAS_BACKEND = 'torch'
    $python = Join-Path $OodtHome '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        throw "ImageCat Python environment is missing. Run bin\imagecat.ps1 setup first."
    }
    $env:PYTHON_EXECUTABLE = $python -replace '\\', '/'
    $env:IMAGE_SPACE_PYTHON = $env:PYTHON_EXECUTABLE
    $env:Path = "$(Split-Path -Parent $python);$($env:Path)"
}

function Expand-PropertyFile([string] $Source) {
    # OODT distributions intentionally keep deployment paths as tokens such
    # as [OODT_HOME] and [DRAT_HOME]. The POSIX launch environment expands
    # those values; materialize an equivalent runtime-only copy on Windows.
    $content = Get-Content -LiteralPath $Source -Raw
    foreach ($name in @(
        'OODT_HOME', 'OODT_BASE', 'IMAGECAT_HOME', 'FILEMGR_HOME',
        'WORKFLOW_HOME', 'RESMGR_HOME', 'PCS_HOME', 'CRAWLER_HOME',
        'PGE_HOME', 'PGE_ROOT', 'FILEMGR_URL', 'WORKFLOW_URL',
        'RESMGR_URL', 'OPSUI_URL', 'SOLR_BASE_URL', 'SOLR_URL',
        'SOLR_FM_URL', 'IMAGE_SPACE_HOME', 'IMAGE_SPACE_DATA',
        'IMAGE_SPACE_SOLR', 'PYTHON_EXECUTABLE', 'IMAGE_SPACE_PYTHON')) {
        $value = [Environment]::GetEnvironmentVariable($name)
        # Backslashes are escape characters in Java .properties files.
        if ($null -ne $value) {
            $content = $content.Replace("[$name]", ($value -replace '\\', '/'))
        }
    }
    # A Windows drive in a file URI needs an empty authority component:
    # file:///C:/path, not file://C:/path (where C: is parsed as a host).
    $content = $content -replace 'file://([A-Za-z]:/)', 'file:///$1'
    $content = $content -replace 'file:([A-Za-z]:/)', 'file:///$1'
    $target = Join-Path $RunHome ((Split-Path -Leaf $Source) + '.windows')
    Set-Content -LiteralPath $target -Value $content -Encoding UTF8
    return $target
}

function Start-Oodt {
    Set-DeploymentEnvironment
    $java = Set-JavaEnvironment
    $state = Get-State

    # File Manager uses Solr as its catalog. Starting it first leaves the
    # server listening but only half initialized (repositoryManager is null),
    # and every workflow condition then retries forever.
    $solr = Join-Path $OodtHome 'solr-server\bin\solr.cmd'
    if (Test-Path -LiteralPath $solr) {
        if (Test-Port $SolrPort) { throw "Port $SolrPort is already in use." }
        & $solr start -p $SolrPort --solr-home (Join-Path $OodtHome 'solr') --user-managed
        # solr.cmd performs its own HTTP health probe and can return nonzero
        # even after Jetty has bound successfully. The service contract here
        # is the listening port; verify that directly.
        if (-not (Wait-Port $SolrPort $true 90)) {
            Save-State $state
            throw "Solr did not open port $SolrPort."
        }
        Write-Host "solr started on port $SolrPort."
    }

    $fileManagerProperties = Expand-PropertyFile (Join-Path $OodtHome 'filemgr\etc\filemgr.properties')
    $workflowProperties = Expand-PropertyFile (Join-Path $OodtHome 'workflow\etc\workflow.properties')
    $resourceProperties = Expand-PropertyFile (Join-Path $OodtHome 'resmgr\etc\resource.properties')
    $schemaArgs = @(
        '-cp', (Join-Path $OodtHome 'workflow\lib\*'),
        'org.apache.oodt.cas.workflow.instrepo.WorkflowInstanceSchema',
        $workflowProperties)
    & $java @schemaArgs *>&1 | Set-Content -LiteralPath (Join-Path $LogHome 'workflow-schema.log')
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to initialize the workflow database. See $LogHome\workflow-schema.log."
    }
    $services = @(
        @{
            Name = 'filemgr'; Port = $FileManagerPort; Home = Join-Path $OodtHome 'filemgr'
            Args = @('-cp', (Join-Path $OodtHome 'filemgr\lib\*'),
                "-Dlog4j.configurationFile=$(Join-Path $OodtHome 'filemgr\etc\log4j2.xml')",
                "-Djava.util.logging.config.file=$(Join-Path $OodtHome 'filemgr\etc\logging.properties')",
                "-Dorg.apache.oodt.cas.filemgr.properties=$fileManagerProperties",
                'org.apache.oodt.cas.filemgr.system.FileManagerServerMain', '--portNum', "$FileManagerPort")
        },
        @{
            Name = 'workflow'; Port = $WorkflowPort; Home = Join-Path $OodtHome 'workflow'
            Args = @('-cp', (Join-Path $OodtHome 'workflow\lib\*'),
                "-Dlog4j.configurationFile=$(Join-Path $OodtHome 'workflow\etc\log4j2.xml')",
                "-Djava.util.logging.config.file=$(Join-Path $OodtHome 'workflow\etc\logging.properties')",
                "-Dorg.apache.oodt.cas.workflow.properties=$workflowProperties",
                '-Dorg.apache.oodt.cas.pge.task.metkeys.legacyMode=true',
                '-Dorg.apache.oodt.cas.pge.task.status.legacyMode=true',
                'org.apache.oodt.cas.workflow.system.WorkflowManagerStarter', '--portNum', "$WorkflowPort")
        },
        @{
            Name = 'resmgr'; Port = $ResourceManagerPort; Home = Join-Path $OodtHome 'resmgr'
            Args = @('-cp', (Join-Path $OodtHome 'resmgr\lib\*'),
                "-Djava.util.logging.config.file=$(Join-Path $OodtHome 'resmgr\etc\logging.properties')",
                "-Dlog4j.configurationFile=$(Join-Path $OodtHome 'resmgr\etc\log4j2.xml')",
                "-Dorg.apache.oodt.cas.resource.properties=$resourceProperties",
                'org.apache.oodt.cas.resource.system.ResourceManagerMain', '--portNum', "$ResourceManagerPort")
        }
    )

    foreach ($service in $services) {
        if (Test-Port $service.Port) { throw "Port $($service.Port) is already in use." }
        $state[$service.Name] = Start-ManagedProcess $service.Name $java $service.Args $service.Home
        Save-State $state
        if (-not (Wait-Port $service.Port $true)) {
            Save-State $state
            throw "$($service.Name) did not open port $($service.Port). See $LogHome."
        }
        Write-Host "$($service.Name) started on port $($service.Port)."
    }

    $tomcat = Join-Path $OodtHome 'tomcat'
    if (Test-Path -LiteralPath $tomcat) {
        if (Test-Port $TomcatPort) { throw "Port $TomcatPort is already in use." }
        $tomcatArgs = @(
            "-Djava.util.logging.config.file=$(Join-Path $tomcat 'conf\logging.properties')",
            '-Djava.util.logging.manager=org.apache.juli.ClassLoaderLogManager',
            "-Dcatalina.base=$tomcat", "-Dcatalina.home=$tomcat",
            "-Djava.io.tmpdir=$(Join-Path $tomcat 'temp')",
            "-Ddrat.base.url=http://localhost:$TomcatPort",
            "-Ddrat.solr.base.url=http://localhost:$SolrPort",
            '-cp', ((Join-Path $tomcat 'bin\bootstrap.jar') + ';' + (Join-Path $tomcat 'bin\tomcat-juli.jar')),
            'org.apache.catalina.startup.Bootstrap', 'start')
        $state['tomcat'] = Start-ManagedProcess 'tomcat' $java $tomcatArgs $tomcat
        Save-State $state
        if (-not (Wait-Port $TomcatPort $true 90)) {
            Save-State $state
            throw "Tomcat did not open port $TomcatPort. See $LogHome."
        }
        Write-Host "tomcat started on port $TomcatPort."
    }

    $imageSpace = Join-Path $OodtHome 'imagespace'
    $python = Join-Path $OodtHome '.venv\Scripts\python.exe'
    if ((Test-Path -LiteralPath $imageSpace) -and
        (Test-Path -LiteralPath $python)) {
        if (Test-Port $ImageSpacePort) {
            throw "Port $ImageSpacePort is already in use."
        }
        $state['imagespace'] = Start-ManagedProcess 'imagespace' $python @(
            '-m', 'uvicorn', 'server.main:app', '--host', '127.0.0.1',
            '--port', "$ImageSpacePort") $imageSpace
        Save-State $state
        if (-not (Wait-Port $ImageSpacePort $true 90)) {
            throw "ImageSpace did not open port $ImageSpacePort. See $LogHome."
        }
        Write-Host "imagespace started on port $ImageSpacePort."
    }
    Save-State $state
}

function Stop-Oodt {
    Set-JavaEnvironment | Out-Null
    Set-DeploymentEnvironment
    $state = Get-State
    Stop-ManagedProcess 'imagespace' $state
    $solr = Join-Path $OodtHome 'solr-server\bin\solr.cmd'
    if ((Test-Path -LiteralPath $solr) -and (Test-Port $SolrPort)) {
        & $solr stop -p $SolrPort
    }
    foreach ($name in @('tomcat', 'resmgr', 'workflow', 'filemgr')) {
        Stop-ManagedProcess $name $state
    }
    Save-State $state
    Write-Host 'OODT services stopped.'
}

function Show-Status {
    $checks = [ordered]@{
        filemgr = $FileManagerPort
        workflow = $WorkflowPort
        resmgr = $ResourceManagerPort
        tomcat = $TomcatPort
    }
    if (Test-Path -LiteralPath (Join-Path $OodtHome 'solr-server')) { $checks.solr = $SolrPort }
    if (Test-Path -LiteralPath (Join-Path $OodtHome 'imagespace')) { $checks.imagespace = $ImageSpacePort }
    foreach ($entry in $checks.GetEnumerator()) {
        $status = if (Test-Port $entry.Value) { 'running' } else { 'stopped' }
        Write-Host "$($entry.Key): $status (port $($entry.Value))"
    }
}

switch ($Command) {
    'start' { Start-Oodt }
    'stop' { Stop-Oodt }
    'restart' { Stop-Oodt; Start-Oodt }
    'status' { Show-Status }
}
