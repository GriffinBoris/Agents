param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('source', 'opencode', 'claude', 'copilot', 'codex', 'gemini')]
    [string]$Target,

    [string]$Dest = '.',
    [string]$Ref = 'main',
    [switch]$Force,
    [string]$Repo = 'GriffinBoris/Agents'
)

$ErrorActionPreference = 'Stop'

function Resolve-AbsolutePath {
    param([string]$PathValue)

    return [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PathValue -ErrorAction SilentlyContinue)?.Path ?? (Join-Path (Get-Location) $PathValue))
}

function Normalize-RepoSlug {
    param([string]$RepoValue)

    if ($RepoValue -match '^https://github\.com/([^/]+/[^/]+?)(\.git)?/?$') {
        return $Matches[1]
    }

    return $RepoValue
}

function Get-SourceRoot {
    param(
        [string]$RepoValue,
        [string]$RefValue,
        [string]$TempRoot
    )

    if (Test-Path -LiteralPath $RepoValue -PathType Container) {
        return Resolve-AbsolutePath -PathValue $RepoValue
    }

    $repoSlug = Normalize-RepoSlug -RepoValue $RepoValue
    $archivePath = Join-Path $TempRoot 'repo.zip'
    $extractRoot = Join-Path $TempRoot 'extract'
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null

    Invoke-WebRequest -Uri "https://github.com/$repoSlug/archive/$RefValue.zip" -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractRoot -Force

    $sourceRoot = Get-ChildItem -LiteralPath $extractRoot | Where-Object { $_.PSIsContainer } | Select-Object -First 1
    if (-not $sourceRoot) {
        throw 'Unable to locate extracted repository contents.'
    }

    return $sourceRoot.FullName
}

function Get-InstallFiles {
    param(
        [string]$InstallRoot,
        [string]$DestinationRoot
    )

    $prefixLength = $InstallRoot.Length + 1
    $files = @()
    foreach ($sourceFile in Get-ChildItem -LiteralPath $InstallRoot -File -Recurse) {
        if ($sourceFile.Name -eq 'README.md') {
            continue
        }

        $relativePath = $sourceFile.FullName.Substring($prefixLength)
        $destinationFile = Join-Path $DestinationRoot $relativePath
        $files += [PSCustomObject]@{
            Source = $sourceFile.FullName
            Destination = $destinationFile
        }
    }

    return $files
}

function Copy-InstallFiles {
    param([array]$InstallFiles)

    foreach ($file in $InstallFiles) {
        $destinationDirectory = Split-Path -Path $file.Destination -Parent
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
        Copy-Item -LiteralPath $file.Source -Destination $file.Destination -Force
        Write-Host "OK: installed $($file.Destination)"
    }
}

$absoluteDest = Resolve-AbsolutePath -PathValue $Dest
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    $sourceRoot = Get-SourceRoot -RepoValue $Repo -RefValue $Ref -TempRoot $tempRoot

    if ($Target -eq 'source') {
        $installRoot = $sourceRoot
        $destinationRoot = $absoluteDest
    } else {
        $installRoot = Join-Path $sourceRoot (Join-Path 'dist' $Target)
        $destinationRoot = $absoluteDest
    }

    if (-not (Test-Path -LiteralPath $installRoot -PathType Container)) {
        throw "Install source does not exist: $installRoot"
    }

    if ($Target -eq 'source') {
        $sourcePaths = @('agents') |
            ForEach-Object { Join-Path $installRoot $_ } |
            Where-Object { Test-Path -LiteralPath $_ }

        if ($sourcePaths.Count -eq 0) {
            throw "Install source does not exist: $installRoot"
        }

        $plannedCopies = @()
        foreach ($sourcePath in $sourcePaths) {
            $rootRelativePath = $sourcePath.Substring($installRoot.Length + 1)
            $item = Get-Item -LiteralPath $sourcePath
            if ($item.PSIsContainer) {
                foreach ($child in Get-ChildItem -LiteralPath $sourcePath -File -Recurse | Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and $_.Extension -ne '.pyc' }) {
                    if ($child.Name -eq 'README.md') {
                        continue
                    }

                    $relativePath = $child.FullName.Substring($sourcePath.Length + 1)
                    $destinationPath = Join-Path (Join-Path $destinationRoot $rootRelativePath) $relativePath
                    $plannedCopies += [PSCustomObject]@{ Source = $child.FullName; Destination = $destinationPath }
                }
            } else {
                $destinationPath = Join-Path $destinationRoot $rootRelativePath
                $plannedCopies += [PSCustomObject]@{ Source = $item.FullName; Destination = $destinationPath }
            }
        }

        foreach ($copy in $plannedCopies) {
            $destinationDirectory = Split-Path -Path $copy.Destination -Parent
            New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
            Copy-Item -LiteralPath $copy.Source -Destination $copy.Destination -Force
            Write-Host "OK: installed $($copy.Destination)"
        }

        exit 0
    }

    New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
    $installFiles = Get-InstallFiles -InstallRoot $installRoot -DestinationRoot $destinationRoot

    Copy-InstallFiles -InstallFiles $installFiles
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
