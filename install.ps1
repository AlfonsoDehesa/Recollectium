$ErrorActionPreference = "Stop"

$Repo = "AlfonsoDehesa/recollectium"
$InstallDir = Join-Path $env:LOCALAPPDATA "uv"
$UvBin = Join-Path $InstallDir "uv.exe"
$ToolBin = Join-Path $HOME ".local\bin"
$OriginalPath = $env:Path
$ManagedPathEdits = @()
$ManagedCompletionEdits = @()

function Test-GuidanceColorSupported {
    return ((-not $env:NO_COLOR) -and (-not [Console]::IsOutputRedirected))
}

function Write-Guidance {
    param(
        [string]$Message,
        [string]$Color
    )
    if ((-not (Test-GuidanceColorSupported)) -or [string]::IsNullOrWhiteSpace($Color)) {
        Write-Host $Message
    }
    else {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Get-ExpectedRecollectiumPaths {
    @(
        (Join-Path $ToolBin "recollectium.exe"),
        (Join-Path $ToolBin "recollectium.cmd"),
        (Join-Path $ToolBin "recollectium")
    ) | ForEach-Object { [System.IO.Path]::GetFullPath($_) }
}

function Test-ExpectedRecollectiumSource {
    param([string]$Source)
    if ([string]::IsNullOrWhiteSpace($Source)) { return $false }
    $fullSource = [System.IO.Path]::GetFullPath($Source)
    foreach ($expected in Get-ExpectedRecollectiumPaths) {
        if ([string]::Equals($fullSource, $expected, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Test-InstalledRecollectium {
    foreach ($expected in Get-ExpectedRecollectiumPaths) {
        if (Test-Path $expected) { return $true }
    }
    return $false
}

function Test-CurrentRecollectiumPath {
    $savedPath = $env:Path
    try {
        $env:Path = $OriginalPath
        $command = Get-Command recollectium -ErrorAction SilentlyContinue | Select-Object -First 1
        return ($null -ne $command -and (Test-ExpectedRecollectiumSource $command.Source))
    }
    finally {
        $env:Path = $savedPath
    }
}

function Test-UserPathContainsToolBin {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { return $false }
    $parts = $userPath -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    foreach ($part in $parts) {
        try {
            if ([string]::Equals(
                [System.IO.Path]::GetFullPath($part),
                [System.IO.Path]::GetFullPath($ToolBin),
                [System.StringComparison]::OrdinalIgnoreCase
            )) { return $true }
        }
        catch {
        }
    }
    return $false
}

function Get-PersistedPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    return (@($machinePath, $userPath) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join ';'
}

function Test-FutureRecollectiumPath {
    $shells = @("powershell", "pwsh")
    foreach ($shell in $shells) {
        $shellCommand = Get-Command $shell -ErrorAction SilentlyContinue
        if (-not $shellCommand) { continue }
        $savedPath = $env:Path
        try {
            $env:Path = Get-PersistedPath
            $resolved = & $shellCommand.Source -NoProfile -Command "`$command = Get-Command recollectium -ErrorAction SilentlyContinue; if (`$command) { `$command.Source }" 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            $first = @($resolved | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1)
            if ($first.Count -gt 0 -and (Test-ExpectedRecollectiumSource $first[0])) { return $true }
        }
        catch {
        }
        finally {
            $env:Path = $savedPath
        }
    }
    return $false
}

function Write-FinalGuidance {
    $tempPathCommand = '  $env:Path = "{0};$env:Path"' -f $ToolBin
    if (Test-CurrentRecollectiumPath) {
        Write-Guidance "Recollectium installed." Green
        Write-Guidance "Verify with: recollectium --version" Green
        return
    }

    if (Test-FutureRecollectiumPath) {
        Write-Guidance "Recollectium installed." Green
        Write-Guidance "Open a new terminal window before using recollectium, or run this command in the current terminal:" Yellow
        Write-Guidance $tempPathCommand Yellow
        Write-Guidance "Then verify with: recollectium --version" Yellow
        return
    }

    if (Test-UserPathContainsToolBin) {
        Write-Guidance "Recollectium installed, but PATH setup could not be verified for a new terminal." Yellow
        Write-Guidance "Your User Path already includes this directory:" Yellow
        Write-Guidance "  $ToolBin" Yellow
        Write-Guidance "Restart your terminal, or run this command in the current terminal:" Yellow
        Write-Guidance $tempPathCommand Yellow
        Write-Guidance "Then verify with: recollectium --version" Yellow
        return
    }

    Write-Guidance "Recollectium installed, but PATH setup could not be verified." Yellow
    Write-Guidance "Add this directory to your User Path:" Yellow
    Write-Guidance "  $ToolBin" Yellow
    Write-Guidance "Then restart your terminal, or run this command in the current terminal:" Yellow
    Write-Guidance $tempPathCommand Yellow
    Write-Guidance "Then verify with: recollectium --version" Yellow
}

function Get-UvArchiveName {
    $arch = $env:PROCESSOR_ARCHITECTURE
    switch ($arch) {
        "AMD64" { return "uv-x86_64-pc-windows-msvc.zip" }
        "ARM64" { return "uv-aarch64-pc-windows-msvc.zip" }
        default { throw "unsupported Windows architecture: $arch" }
    }
}

function Install-Uv {
    $existing = Get-Command uv -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "uv already installed: $($existing.Source)"
        return $existing.Source
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $archive = Get-UvArchiveName
    $url = "https://github.com/astral-sh/uv/releases/latest/download/$archive"
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid())
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp $archive

    Write-Host "Downloading uv..."
    Invoke-WebRequest -Uri $url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $found = Get-ChildItem -Path $tmp -Filter uv.exe -Recurse | Select-Object -First 1
    if (-not $found) { throw "uv.exe not found in archive" }
    Copy-Item $found.FullName $UvBin -Force
    Remove-Item $tmp -Recurse -Force
    Write-Host "Installed uv: $UvBin"
    return $UvBin
}

function Normalize-VersionRef {
    param([string]$Value)
    $raw = $Value.Trim()
    if ($raw.StartsWith("v")) { $raw = $raw.Substring(1) }
    if ($raw -notmatch '^[0-9][0-9A-Za-z.+!-]*([.][0-9A-Za-z.+!-]+)*$') { throw "invalid install version: $Value" }
    return "v$raw"
}

function Get-RefKind {
    param([string]$Value)
    if ($Value -eq "main") { return "main" }
    if ($Value -match '^v?[0-9]+([.][0-9A-Za-z.+!-]+)*$') { return "release" }
    return "custom_ref"
}

function Get-LatestReleaseTag {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
    if ($release.tag_name) { return $release.tag_name }
    throw "latest GitHub release did not include tag_name"
}

$script:TrackingKind = "latest_release"
$script:TrackingSelector = "latest"
$script:TrackingVersion = $null

function Get-RecollectiumInstallRef {
    $selectors = @($env:RECOLLECTIUM_INSTALL_VERSION, $env:RECOLLECTIUM_INSTALL_MAIN, $env:RECOLLECTIUM_INSTALL_REF) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if ($selectors.Count -gt 1) { throw "set only one of RECOLLECTIUM_INSTALL_VERSION, RECOLLECTIUM_INSTALL_MAIN, or RECOLLECTIUM_INSTALL_REF" }

    if ($env:RECOLLECTIUM_INSTALL_MAIN -match '^(1|true|yes)$') {
        $script:TrackingKind = "main"
        $script:TrackingSelector = "main"
        if ($env:RECOLLECTIUM_INSTALL_RESOLVED_REF) { return $env:RECOLLECTIUM_INSTALL_RESOLVED_REF }
        return "main"
    }
    if ($env:RECOLLECTIUM_INSTALL_VERSION) {
        if ($env:RECOLLECTIUM_INSTALL_VERSION.ToLowerInvariant() -eq "latest") {
            $script:TrackingKind = "latest_release"
            $script:TrackingSelector = "latest"
            if ($env:RECOLLECTIUM_INSTALL_RESOLVED_REF) { return $env:RECOLLECTIUM_INSTALL_RESOLVED_REF }
        }
        else {
            $ref = Normalize-VersionRef $env:RECOLLECTIUM_INSTALL_VERSION
            $script:TrackingKind = "release"
            $script:TrackingSelector = $ref
            $script:TrackingVersion = $ref.Substring(1)
            return $ref
        }
    }
    elseif ($env:RECOLLECTIUM_INSTALL_REF) {
        $kind = Get-RefKind $env:RECOLLECTIUM_INSTALL_REF
        $script:TrackingKind = $kind
        $script:TrackingSelector = $env:RECOLLECTIUM_INSTALL_REF
        if ($kind -eq "release") { $script:TrackingVersion = $env:RECOLLECTIUM_INSTALL_REF.TrimStart("v") }
        return $env:RECOLLECTIUM_INSTALL_REF
    }

    try {
        return Get-LatestReleaseTag
    }
    catch {
        throw "failed to resolve latest GitHub release; set RECOLLECTIUM_INSTALL_MAIN=1 to install main"
    }
}

$uv = Install-Uv
$ref = Get-RecollectiumInstallRef
$package = "git+https://github.com/$Repo.git@$ref"
Write-Host "Installing Recollectium from $ref..."
& $uv tool install --python 3.12 --force $package
if ($LASTEXITCODE -ne 0) { throw "failed to install Recollectium package" }
if (-not (Test-InstalledRecollectium)) { throw "recollectium executable was not installed in uv tool bin directory: $ToolBin" }
Write-Host "Maintaining embeddings (config, database, model, stale memories)..."
& $uv tool run --from $package recollectium embedding-maintenance
if ($LASTEXITCODE -ne 0) { throw "embedding maintenance failed; retry with: recollectium embedding-maintenance" }
if ($env:Path -notlike "*$ToolBin*") {
    $env:Path = "$ToolBin;$env:Path"
}
if ($env:GITHUB_PATH) {
    Add-Content -Path $env:GITHUB_PATH -Value $ToolBin
}
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
if ($userPath -notlike "*$ToolBin*") {
    [Environment]::SetEnvironmentVariable("Path", "$ToolBin;$userPath", "User")
    $ManagedPathEdits += "User Path: $ToolBin"
}
$profilePath = $PROFILE.CurrentUserCurrentHost
$env:RECOLLECTIUM_POWERSHELL_PROFILE = $profilePath
try {
    & $uv tool run --from $package recollectium completion --install powershell --yes | Out-Null
    $ManagedCompletionEdits += [ordered]@{
        shell = "powershell"
        path = $profilePath
        source_command = "recollectium completion --source powershell"
    }
    Write-Host "PowerShell completion configured in $profilePath."
}
finally {
    Remove-Item Env:RECOLLECTIUM_POWERSHELL_PROFILE -ErrorAction SilentlyContinue
}
$stateDir = Join-Path $env:LOCALAPPDATA "recollectium"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$metadataPath = Join-Path $stateDir "install.json"
$resolvedRefKind = if ($script:TrackingKind -eq "latest_release") { "release" } else { $script:TrackingKind }
$trackingTarget = [ordered]@{
    kind = $script:TrackingKind
    selector = $script:TrackingSelector
    repo = $Repo
}
if ($script:TrackingVersion) {
    $trackingTarget.version = $script:TrackingVersion
    $trackingTarget.ref = $ref
}
elseif ($script:TrackingKind -eq "main") {
    $trackingTarget.ref = $script:TrackingSelector
}
elseif ($script:TrackingKind -ne "latest_release") {
    $trackingTarget.ref = $ref
}
$resolved = [ordered]@{
    ref = $ref
    resolved_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}
if ($script:TrackingVersion) { $resolved.version = $script:TrackingVersion }
$now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$metadata = [ordered]@{
    metadata_version = 2
    install_method = "bootstrap"
    source_ref = $ref
    source_ref_kind = $resolvedRefKind
    source_repo = $Repo
    installed_at = $now
    updated_at = $now
    tracking_target = $trackingTarget
    last_resolved = $resolved
    managed_path_edits = $ManagedPathEdits
    managed_completion_edits = $ManagedCompletionEdits
}
$metadata | ConvertTo-Json | Set-Content -Path $metadataPath -Encoding utf8
Write-FinalGuidance
