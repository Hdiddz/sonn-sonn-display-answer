param([switch]$Stop)
$ErrorActionPreference = 'Stop'
$monitorScript = Join-Path $PSScriptRoot 'monitor.py'
$pidPath = Join-Path $PSScriptRoot 'monitor.pid'
$settingsPath = Join-Path $PSScriptRoot '.monitor-settings'
$stopPath = Join-Path $PSScriptRoot 'monitor.stop'
$envPath = Join-Path $PSScriptRoot '.env'

function Get-EnvValue([string]$name) {
    if (-not (Test-Path -LiteralPath $envPath)) { return '' }
    $pattern = '^\s*' + [regex]::Escape($name) + '\s*=\s*(.*)$'
    foreach ($line in Get-Content -LiteralPath $envPath) {
        if ($line -match $pattern) {
            return $matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ''
}

function Set-EnvValue([string]$name, [string]$value) {
    $output = @()
    $replaced = $false
    if (Test-Path -LiteralPath $envPath) {
        $pattern = '^\s*' + [regex]::Escape($name) + '\s*='
        foreach ($line in Get-Content -LiteralPath $envPath) {
            if ($line -match $pattern) {
                $output += ($name + '=' + $value)
                $replaced = $true
            } else {
                $output += $line
            }
        }
    }
    if (-not $replaced) { $output += ($name + '=' + $value) }
    Set-Content -LiteralPath $envPath -Value $output -Encoding UTF8
}

$settings = @{ popup = 'on'; position = 'bottom-left'; scale = '100'; thinking = 'high' }
if (Test-Path -LiteralPath $settingsPath) {
    $raw = (Get-Content -LiteralPath $settingsPath -Raw).Trim()
    if ($raw -eq '1' -or $raw -eq '2') {
        # settings written by an older version: a single on/off value
        if ($raw -eq '2') { $settings.popup = 'off' }
    } else {
        foreach ($line in ($raw -split "`r?`n")) {
            if ($line -match '^\s*([A-Za-z_]+)\s*=\s*(.+?)\s*$') {
                $key = $matches[1].ToLower()
                if ($settings.ContainsKey($key)) { $settings[$key] = $matches[2] }
            }
        }
    }
}

function Save-Settings {
    $lines = @()
    $lines += ('popup=' + $settings.popup)
    $lines += ('position=' + $settings.position)
    $lines += ('scale=' + $settings.scale)
    $lines += ('thinking=' + $settings.thinking)
    Set-Content -LiteralPath $settingsPath -Value $lines
}

function Read-Thinking {
    Write-Host '    [1] off    [2] low    [3] high    [4] max'
    $pick = Read-Host ("  Thinking effort 1-4 [Enter = " + $settings.thinking + ']')
    switch ($pick) {
        '1' { $settings.thinking = 'off' }
        '2' { $settings.thinking = 'low' }
        '3' { $settings.thinking = 'high' }
        '4' { $settings.thinking = 'max' }
    }
    Save-Settings
    Write-Host ("  Thinking effort: " + $settings.thinking)
}

function Read-Position {
    Write-Host '    [1] bottom-left   [2] bottom-right   [3] top-left'
    Write-Host '    [4] top-right     [5] center'
    $pick = Read-Host ("  Position 1-5 [Enter = " + $settings.position + ']')
    switch ($pick) {
        '1' { $settings.position = 'bottom-left' }
        '2' { $settings.position = 'bottom-right' }
        '3' { $settings.position = 'top-left' }
        '4' { $settings.position = 'top-right' }
        '5' { $settings.position = 'center' }
    }
    Save-Settings
    Write-Host ("  Popup position: " + $settings.position)
}

function Read-Scale {
    $pick = Read-Host ("  Popup size in percent 50-200 [Enter = " + $settings.scale + ']')
    if ($pick -match '^\d+$') {
        $value = [int]$pick
        if ($value -ge 50 -and $value -le 200) {
            $settings.scale = [string]$value
            Save-Settings
            Write-Host ("  Popup size: " + $settings.scale + '%')
        } else {
            Write-Host '  Keep it between 50 and 200 percent; nothing changed.'
        }
    } elseif ([string]::IsNullOrWhiteSpace($pick)) {
        Write-Host ("  Popup size stays at " + $settings.scale + '%')
    } else {
        Write-Host '  Not a number; nothing changed.'
    }
}

$running = $null
if (Test-Path -LiteralPath $pidPath) {
    $monitorProcessId = 0
    if ([int]::TryParse((Get-Content -LiteralPath $pidPath -Raw).Trim(), [ref]$monitorProcessId)) {
        $candidate = Get-CimInstance Win32_Process -Filter "ProcessId = $monitorProcessId"
        if ($candidate -and $candidate.Name -match '^python(w)?\.exe$' -and
            $candidate.CommandLine.Contains($monitorScript)) {
            $running = $candidate
        }
    }
}
if ($Stop) {
    if ($running) {
        Set-Content -LiteralPath $stopPath -Value 'stop'
        Write-Host 'Stop requested. The monitor will finish its current request and exit.'
    } else {
        Write-Host 'Monitor is already stopped.'
    }
    exit 0
}

if ($running) {
    # A running monitor still needs a console, so this window controls it.
    # Position and size are read per answer, so they apply without a restart.
    while ($true) {
        Write-Host ''
        Write-Host ("  Monitor is running (PID $($running.ProcessId)).")
        Write-Host ("    popup: " + $settings.popup + "   position: " + $settings.position +
                    "   scale: " + $settings.scale + '%   thinking: ' + $settings.thinking)
        Write-Host '    [1] Stop the monitor'
        Write-Host '    [2] Hide the answer box (CapsLock flashes only)'
        Write-Host '    [3] Show the answer box again'
        Write-Host '    [4] Move the answer box'
        Write-Host '    [5] Resize the answer box'
        Write-Host '    [6] Thinking effort (off/low/high/max)'
        Write-Host '    [7] Nothing, just close'
        $action = Read-Host '  Choose 1-7 [Enter = 7]'
        if ([string]::IsNullOrWhiteSpace($action)) { $action = '7' }
        switch ($action) {
            '1' {
                Set-Content -LiteralPath $stopPath -Value 'stop'
                Write-Host '  Stop requested. The monitor exits after the current request.'
                exit 0
            }
            '2' {
                $settings.popup = 'off'
                Save-Settings
                Write-Host '  Answer box hidden. CapsLock flashes stay on.'
            }
            '3' {
                $settings.popup = 'on'
                Save-Settings
                Write-Host '  Answer box enabled again.'
            }
            '4' { Read-Position }
            '5' { Read-Scale }
            '6' { Read-Thinking }
            default { exit 0 }
        }
    }
}

# ---- starting a new monitor ------------------------------------------------

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & py -3 -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment. Install Python 3.10 or newer.' }
    & $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}

# A python.exe that lives inside this folder can start at low integrity here,
# and Windows then blocks keyboard reads: the F9 hotkey never fires and the
# monitor exits with "low integrity". Prefer the base interpreter outside the
# folder and expose the venv packages through PYTHONPATH instead.
$pythonPath = $venvPython
$sitePackages = Join-Path $PSScriptRoot '.venv\Lib\site-packages'
$venvConfig = Join-Path $PSScriptRoot '.venv\pyvenv.cfg'
if ((Test-Path -LiteralPath $venvConfig) -and (Test-Path -LiteralPath $sitePackages)) {
    $homeLine = Get-Content -LiteralPath $venvConfig |
        Where-Object { $_ -match '^\s*home\s*=' } | Select-Object -First 1
    if ($homeLine) {
        $homeDir = ($homeLine -replace '^\s*home\s*=\s*', '').Trim()
        $basePython = Join-Path $homeDir 'python.exe'
        if (Test-Path -LiteralPath $basePython) {
            $pythonPath = $basePython
            $env:PYTHONPATH = $sitePackages
        }
    }
}

while ($true) {
    $apiKey = Get-EnvValue 'DEEPSEEK_API_KEY'
    $keyLabel = 'not set - choose [6]'
    if ($apiKey -and $apiKey -ne 'your_key_here') {
        if ($apiKey.Length -gt 8) {
            $keyLabel = $apiKey.Substring(0, 4) + '...' + $apiKey.Substring($apiKey.Length - 4)
        } else {
            $keyLabel = 'set'
        }
    }
    $model = Get-EnvValue 'DEEPSEEK_MODEL'
    if (-not $model) { $model = 'deepseek-flash' }
    $baseUrl = Get-EnvValue 'DEEPSEEK_BASE_URL'
    if (-not $baseUrl) { $baseUrl = 'https://api.deepseek.com' }

    Write-Host ''
    Write-Host '  CapsLock Monitor'
    Write-Host ("    popup    : " + $settings.popup)
    Write-Host ("    position : " + $settings.position + "    scale: " + $settings.scale + '%')
    Write-Host ("    thinking : " + $settings.thinking)
    Write-Host ("    api key  : " + $keyLabel)
    Write-Host ("    model    : " + $model + "  (" + $baseUrl + ')')
    Write-Host ''
    Write-Host '    [1] Start - answer box + CapsLock flashes'
    Write-Host '    [2] Start - CapsLock flashes only'
    Write-Host '    [3] Popup position'
    Write-Host '    [4] Popup size'
    Write-Host '    [5] Thinking effort (off/low/high/max)'
    Write-Host '    [6] API key'
    Write-Host '    [7] Model / API base URL'
    Write-Host '    [8] Exit'
    $choice = Read-Host '  Choose 1-8'
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '8' }

    $start = $false
    switch ($choice) {
        '1' { $settings.popup = 'on';  Save-Settings; $start = $true }
        '2' { $settings.popup = 'off'; Save-Settings; $start = $true }
        '3' { Read-Position }
        '4' { Read-Scale }
        '5' { Read-Thinking }
        '6' {
            if ([Console]::IsInputRedirected) {
                # A hidden prompt reads the console directly and would block on
                # piped input, so accept a normal line when input is redirected.
                $plain = Read-Host '  Paste the new API key (Enter keeps the current one)'
            } else {
                $secure = Read-Host '  Paste the new API key (Enter keeps the current one)' -AsSecureString
                $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
                try {
                    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
                } finally {
                    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
                }
            }
            if ([string]::IsNullOrWhiteSpace($plain)) {
                Write-Host '  API key unchanged.'
            } else {
                Set-EnvValue 'DEEPSEEK_API_KEY' $plain.Trim()
                Write-Host '  API key saved to .env.'
            }
        }
        '7' {
            $newModel = Read-Host ("  Model [Enter = " + $model + ']')
            if (-not [string]::IsNullOrWhiteSpace($newModel)) {
                Set-EnvValue 'DEEPSEEK_MODEL' $newModel.Trim()
            }
            $newBase = Read-Host ("  API base URL [Enter = " + $baseUrl + ']')
            if (-not [string]::IsNullOrWhiteSpace($newBase)) {
                Set-EnvValue 'DEEPSEEK_BASE_URL' ($newBase.Trim().TrimEnd('/'))
            }
        }
        default { exit 0 }
    }
    if ($start) { break }
}

if (Test-Path -LiteralPath $stopPath) { Remove-Item -LiteralPath $stopPath }
$arguments = @('-u', ('"' + $monitorScript + '"'), '--key', 'f9', '--mute',
               '--stop-file', ('"' + $stopPath + '"'))
$process = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'monitor.log') -RedirectStandardError (Join-Path $PSScriptRoot 'monitor-error.log') -PassThru
Set-Content -LiteralPath $pidPath -Value $process.Id
Start-Sleep -Milliseconds 800
$process.Refresh()
if ($process.HasExited) {
    throw 'Monitor exited during startup. Check monitor.log and monitor-error.log.'
}
Write-Host "Monitor started (PID $($process.Id)). Press F9 to capture. Run stop.cmd to stop."
