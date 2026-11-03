#requires -Version 5.1
$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/OAMaestro/video-vision-mcp.git"
$PinnedCommit = "cb854278518c46943a5b9e89643f2e29c7aca839"
$InstallRoot = Join-Path $env:LOCALAPPDATA "VanitasStudio\ClipForge\video-vision-mcp"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. Install Git and Node.js 18+ first."
    }
}

Require-Command "git"
Require-Command "node"
Require-Command "npm"

$NodeVersion = (node -p "process.versions.node").Trim()
$NodeSemver = [version]$NodeVersion
if ($NodeSemver -lt [version]"20.9.0") { throw "Node.js 20.9 or newer is required by the audited sharp build. Found $NodeVersion." }

New-Item -ItemType Directory -Force -Path (Split-Path $InstallRoot -Parent) | Out-Null
if (-not (Test-Path (Join-Path $InstallRoot ".git"))) {
    if (Test-Path $InstallRoot) {
        throw "Install folder exists but is not a Git checkout: $InstallRoot. Move it aside before installing."
    }
    git clone --no-checkout $RepoUrl $InstallRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not clone Video Vision MCP." }
} else {
    $ExistingOrigin = (git -C $InstallRoot remote get-url origin).Trim()
    if ($ExistingOrigin -ne $RepoUrl) { throw "Existing install has an unexpected Git remote: $ExistingOrigin" }
    git -C $InstallRoot fetch --depth 1 origin $PinnedCommit
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch the pinned Video Vision MCP revision." }
}

git -C $InstallRoot checkout --detach $PinnedCommit
if ($LASTEXITCODE -ne 0) { throw "Could not select pinned revision $PinnedCommit." }

Push-Location $InstallRoot
try {
    # The repository's published package name currently returns npm registry 404.
    # Build from the audited Git revision and apply safe dependency overrides.
    npm pkg set "dependencies.sharp=^0.35.5" "dependencies.uuid=^11.1.1" "overrides.sharp=^0.35.5" "overrides.qs=6.17.1"
    if ($LASTEXITCODE -ne 0) { throw "Could not apply audited dependency versions." }

    npm install
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

    npm audit fix
    if ($LASTEXITCODE -ne 0) { throw "Could not update vulnerable transitive dependencies without breaking changes." }

    npm audit --omit=dev --audit-level=moderate
    if ($LASTEXITCODE -ne 0) { throw "Dependency audit did not pass. Video Vision MCP was not built." }

    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Video Vision MCP TypeScript build failed." }

    $Manifest = @{
        repository = $RepoUrl
        commit = $PinnedCommit
        packageVersion = "0.1.0"
        license = "MIT"
        installedAt = (Get-Date).ToUniversalTime().ToString("o")
        securityOverrides = @{
            sharp = "^0.35.5"
            uuid = "^11.1.1"
            qs = "6.17.1"
        }
    }
    $Manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $InstallRoot "clipforge-install.json")
} finally {
    Pop-Location
}

$Entry = Join-Path $InstallRoot "dist\index.js"
if (-not (Test-Path $Entry)) { throw "Build completed but dist/index.js is missing." }
Write-Host "Video Vision MCP installed and audited." -ForegroundColor Green
Write-Host "Location: $InstallRoot"
Write-Host "Pinned revision: $PinnedCommit"
Write-Host "ClipForge setting: set CLIPFORGE_VIDEO_VISION_ENABLED=1 to enable it."
