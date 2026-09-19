<#
.SYNOPSIS
    Creates and edits the .env file consumed by migrate_android_studio.py.

.DESCRIPTION
    PowerShell equivalent of scripts/manage_env.py. Comments and unrelated
    lines in an existing .env are preserved; only the known SOURCE_*/DEST_*/
    LOG_FILE keys are added or updated.

.PARAMETER Command
    One of: init, set, get, list, edit

.PARAMETER Key
    Environment variable name (required for 'set' and 'get')

.PARAMETER Value
    Environment variable value (required for 'set')

.PARAMETER Force
    Overwrite an existing .env file (used with 'init')

.EXAMPLE
    .\Manage-Env.ps1 init
    .\Manage-Env.ps1 set SOURCE_AVD_DIR "C:\Users\YourName\.android\avd"
    .\Manage-Env.ps1 get SOURCE_AVD_DIR
    .\Manage-Env.ps1 list
    .\Manage-Env.ps1 edit
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("init", "set", "get", "list", "edit")]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Key,

    [Parameter(Position = 2)]
    [string]$Value,

    [switch]$Force
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$EnvFile = Join-Path $RepoRoot ".env"
$TemplateFile = Join-Path $RepoRoot ".env.example"

$KnownKeys = @(
    "SOURCE_AVD_DIR",
    "DEST_AVD_DIR",
    "SOURCE_PROJECTS_DIR",
    "DEST_PROJECTS_DIR",
    "LOG_FILE"
)

$KeyPrompts = @{
    SOURCE_AVD_DIR      = "Source AVD directory (e.g. C:\Users\YourName\.android\avd)"
    DEST_AVD_DIR        = "Destination AVD directory (e.g. D:\YourName\.android\avd)"
    SOURCE_PROJECTS_DIR = "Source AndroidStudioProjects directory"
    DEST_PROJECTS_DIR   = "Destination AndroidStudioProjects directory"
    LOG_FILE            = "Log file path (optional, leave blank for default)"
}

function Read-EnvLines {
    param([string]$Path)
    if (Test-Path -Path $Path) {
        return @(Get-Content -Path $Path -Encoding UTF8)
    }
    return @()
}

function Get-EnvValues {
    param([string[]]$Lines)
    $values = @{}
    foreach ($line in $Lines) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $values
}

function Set-EnvLineValue {
    param(
        [string[]]$Lines,
        [string]$Key,
        [string]$Value
    )
    $updated = New-Object System.Collections.Generic.List[string]
    $found = $false
    foreach ($line in $Lines) {
        $trimmed = $line.Trim()
        if (-not $found -and $trimmed.Contains("=") -and -not $trimmed.StartsWith("#")) {
            $existingKey = $trimmed.Split("=", 2)[0].Trim()
            if ($existingKey -eq $Key) {
                $updated.Add("$Key=$Value")
                $found = $true
                continue
            }
        }
        $updated.Add($line)
    }
    if (-not $found) {
        if ($updated.Count -gt 0 -and $updated[$updated.Count - 1].Trim()) {
            $updated.Add("")
        }
        $updated.Add("$Key=$Value")
    }
    return $updated
}

function Invoke-EnvInit {
    if ((Test-Path -Path $EnvFile) -and -not $Force) {
        Write-Error "ERROR: $EnvFile already exists. Use -Force to overwrite."
        exit 1
    }
    if (-not (Test-Path -Path $TemplateFile)) {
        Write-Error "ERROR: Template file not found: $TemplateFile"
        exit 1
    }
    Copy-Item -Path $TemplateFile -Destination $EnvFile -Force
    Write-Host "Created $EnvFile from $(Split-Path -Leaf $TemplateFile)."
}

function Invoke-EnvSet {
    if (-not $Key -or -not $Value) {
        Write-Error "ERROR: 'set' requires both a Key and a Value."
        exit 1
    }
    if ($KnownKeys -notcontains $Key) {
        Write-Warning "'$Key' is not a recognized key ($($KnownKeys -join ', '))."
    }
    $lines = Set-EnvLineValue -Lines (Read-EnvLines -Path $EnvFile) -Key $Key -Value $Value
    Set-Content -Path $EnvFile -Value $lines -Encoding UTF8
    Write-Host "Set $Key in $EnvFile."
}

function Invoke-EnvGet {
    if (-not $Key) {
        Write-Error "ERROR: 'get' requires a Key."
        exit 1
    }
    $values = Get-EnvValues -Lines (Read-EnvLines -Path $EnvFile)
    if (-not $values.ContainsKey($Key)) {
        Write-Error "ERROR: '$Key' is not set in $EnvFile."
        exit 1
    }
    Write-Output $values[$Key]
}

function Invoke-EnvList {
    $values = Get-EnvValues -Lines (Read-EnvLines -Path $EnvFile)
    if ($values.Count -eq 0) {
        Write-Host "No values set in $EnvFile."
        return
    }
    foreach ($key in $values.Keys) {
        Write-Output "$key=$($values[$key])"
    }
}

function Invoke-EnvEdit {
    if (-not (Test-Path -Path $EnvFile)) {
        if (Test-Path -Path $TemplateFile) {
            Copy-Item -Path $TemplateFile -Destination $EnvFile
            Write-Host "Created $EnvFile from $(Split-Path -Leaf $TemplateFile)."
        }
        else {
            New-Item -Path $EnvFile -ItemType File | Out-Null
        }
    }

    $lines = Read-EnvLines -Path $EnvFile
    $values = Get-EnvValues -Lines $lines

    foreach ($k in $KnownKeys) {
        $current = $values[$k]
        $promptLabel = $KeyPrompts[$k]
        if (-not $promptLabel) { $promptLabel = $k }
        $suffix = if ($current) { " [$current]" } else { "" }
        $response = Read-Host "$promptLabel$suffix"
        if ($response) {
            $lines = Set-EnvLineValue -Lines $lines -Key $k -Value $response
        }
        elseif ($current) {
            $lines = Set-EnvLineValue -Lines $lines -Key $k -Value $current
        }
    }

    Set-Content -Path $EnvFile -Value $lines -Encoding UTF8
    Write-Host "`nSaved $EnvFile."
}

switch ($Command) {
    "init" { Invoke-EnvInit }
    "set" { Invoke-EnvSet }
    "get" { Invoke-EnvGet }
    "list" { Invoke-EnvList }
    "edit" { Invoke-EnvEdit }
}
