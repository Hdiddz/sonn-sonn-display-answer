param([switch]$Stop)
$ErrorActionPreference = 'Stop'
$monitorScript = Join-Path $PSScriptRoot 'monitor.py'
$pidPath = Join-Path $PSScriptRoot 'monitor.pid'
$settingsPath = Join-Path $PSScriptRoot '.monitor-settings'
$stopPath = Join-Path $PSScriptRoot 'monitor.stop'
$envPath = Join-Path $PSScriptRoot '.env'

# ---- console look -----------------------------------------------------------
# Box drawing is built from code points so this script stays plain ASCII and
# Windows PowerShell 5.1 cannot mis-read it.
$boxH = [string][char]0x2550
$boxV = [string][char]0x2551
$boxTL = [string][char]0x2554
$boxTR = [string][char]0x2557
$boxBL = [string][char]0x255A
$boxBR = [string][char]0x255D
$boxL = [string][char]0x2500

try { $Host.UI.RawUI.WindowTitle = 'sonnsonn' } catch { }
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    chcp 65001 > $null
} catch { }

function Clear-Screen {
    try { Clear-Host } catch { }
}

function Write-Banner([string]$subtitle) {
    $title = 'sonnsonn'
    $rest = '   ' + $subtitle
    $available = 54 - $title.Length
    if ($rest.Length -gt $available) { $rest = $rest.Substring(0, $available) }
    $pad = ' ' * [Math]::Max(0, 54 - $title.Length - $rest.Length)
    Write-Host ''
    Write-Host ('  ' + $boxTL + ($boxH * 56) + $boxTR) -ForegroundColor DarkCyan
    Write-Host ('  ' + $boxV + '  ') -NoNewline -ForegroundColor DarkCyan
    Write-Host $title -NoNewline -ForegroundColor Cyan
    Write-Host $rest -NoNewline -ForegroundColor DarkGray
    Write-Host ($pad + $boxV) -ForegroundColor DarkCyan
    Write-Host ('  ' + $boxBL + ($boxH * 56) + $boxBR) -ForegroundColor DarkCyan
}

function Write-Pair([string]$k1, [string]$v1, [string]$k2 = '', [string]$v2 = '') {
    Write-Host ('     ' + $k1.PadRight(10)) -NoNewline -ForegroundColor DarkGray
    if ($k2) {
        if ($v1.Length -gt 22) { $v1 = $v1.Substring(0, 21) + '>' }
        if ($v2.Length -gt 24) { $v2 = $v2.Substring(0, 24) }
        Write-Host $v1.PadRight(22) -NoNewline -ForegroundColor White
        Write-Host $k2.PadRight(10) -NoNewline -ForegroundColor DarkGray
        Write-Host $v2 -ForegroundColor Cyan
    } else {
        Write-Host $v1 -ForegroundColor White
    }
}

function Write-Section([string]$title) {
    $label = '    ' + $boxL + $boxL + ' ' + $title.ToUpper() + ' '
    $fill = [Math]::Max(0, 60 - $label.Length)
    Write-Host ''
    Write-Host ($label + ($boxL * $fill)) -ForegroundColor DarkCyan
}

function Write-Item([string]$key, [string]$text) {
    Write-Host ('     [' + $key + ']  ') -NoNewline -ForegroundColor Yellow
    Write-Host $text -ForegroundColor White
}

function Write-Item2([string]$k1, [string]$t1, [string]$k2, [string]$t2) {
    Write-Host ('     [' + $k1 + ']  ') -NoNewline -ForegroundColor Yellow
    Write-Host $t1.PadRight(25) -NoNewline -ForegroundColor White
    Write-Host ('[' + $k2 + ']  ') -NoNewline -ForegroundColor Yellow
    Write-Host $t2 -ForegroundColor White
}

function Read-Choice([string]$range) {
    Write-Host ''
    Write-Host ('     ' + $range + '  ') -NoNewline -ForegroundColor DarkGray
    Write-Host '>' -NoNewline -ForegroundColor Yellow
    Write-Host ' ' -NoNewline
    return (Read-Host)
}

function Write-Ok([string]$message) {
    Write-Host '     ' -NoNewline
    Write-Host 'ok ' -NoNewline -ForegroundColor Green
    Write-Host $message -ForegroundColor Gray
}

function Write-Warn([string]$message) {
    Write-Host '     ' -NoNewline
    Write-Host '!  ' -NoNewline -ForegroundColor DarkYellow
    Write-Host $message -ForegroundColor Gray
}

# ---- settings ---------------------------------------------------------------

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

$settings = @{ popup = 'on'; position = 'bottom-left'; scale = '100'; thinking = 'high'; duration = '2' }
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
    $lines += ('duration=' + $settings.duration)
    Set-Content -LiteralPath $settingsPath -Value $lines
}

function Read-Thinking {
    Write-Host ''
    Write-Host '     off / low / high / max' -ForegroundColor DarkGray
    $pick = Read-Choice ('choose 1-4, Enter = ' + $settings.thinking)
    switch ($pick) {
        '1' { $settings.thinking = 'off' }
        '2' { $settings.thinking = 'low' }
        '3' { $settings.thinking = 'high' }
        '4' { $settings.thinking = 'max' }
    }
    Save-Settings
    Write-Ok ('thinking = ' + $settings.thinking)
}

function Read-Position {
    Write-Host ''
    Write-Host ('     ' + '[1] bottom-left   [2] bottom-right   [3] top-left   [4] top-right   [5] center') -ForegroundColor DarkGray
    $pick = Read-Choice ('choose 1-5, Enter = ' + $settings.position)
    switch ($pick) {
        '1' { $settings.position = 'bottom-left' }
        '2' { $settings.position = 'bottom-right' }
        '3' { $settings.position = 'top-left' }
        '4' { $settings.position = 'top-right' }
        '5' { $settings.position = 'center' }
    }
    Save-Settings
    Write-Ok ('position = ' + $settings.position)
}

function Read-Scale {
    $pick = Read-Choice ('size 50-200, Enter = ' + $settings.scale)
    if ($pick -match '^\d+$') {
        $value = [int]$pick
        if ($value -ge 50 -and $value -le 200) {
            $settings.scale = [string]$value
            Save-Settings
            Write-Ok ('scale = ' + $settings.scale + '%')
        } else {
            Write-Warn 'keep it between 50 and 200 percent; nothing changed'
        }
    } elseif ([string]::IsNullOrWhiteSpace($pick)) {
        Write-Ok ('scale stays at ' + $settings.scale + '%')
    } else {
        Write-Warn 'not a number; nothing changed'
    }
}

function Read-Duration {
    $pick = Read-Choice ('seconds 1-30, Enter = ' + $settings.duration)
    if ($pick -match '^\d+(\.\d+)?$') {
        $value = [double]$pick
        if ($value -ge 1 -and $value -le 30) {
            $settings.duration = $value.ToString([System.Globalization.CultureInfo]::InvariantCulture)
            Save-Settings
            Write-Ok ('box stays ' + $settings.duration + 's on screen')
        } else {
            Write-Warn 'keep it between 1 and 30 seconds; nothing changed'
        }
    } elseif ([string]::IsNullOrWhiteSpace($pick)) {
        Write-Ok ('box stays ' + $settings.duration + 's')
    } else {
        Write-Warn 'not a number; nothing changed'
    }
}

# ---- is it running? ---------------------------------------------------------

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
    # Every setting here is read per answer, so changes apply without a restart.
    while ($true) {
        Clear-Screen
        Write-Banner ('monitor active  -  PID ' + $running.ProcessId)
        Write-Host ''
        Write-Pair 'popup' $settings.popup 'thinking' $settings.thinking
        Write-Pair 'position' $settings.position 'scale' ($settings.scale + '%')
        Write-Pair 'duration' ($settings.duration + 's')
        Write-Section 'monitor'
        Write-Item '1' 'Stop the monitor'
        Write-Section 'answer box'
        Write-Item2 '2' 'Hide the box' '3' 'Show the box'
        Write-Item2 '4' 'Move the box' '5' 'Resize the box'
        Write-Section 'display & brain'
        Write-Item2 '6' 'Box duration' '7' 'Thinking effort'
        Write-Host ''
        Write-Item '8' 'Close this window'
        $action = Read-Choice 'choose 1-8, Enter = 8'
        if ([string]::IsNullOrWhiteSpace($action)) { $action = '8' }
        switch ($action) {
            '1' {
                Set-Content -LiteralPath $stopPath -Value 'stop'
                Write-Ok 'stop requested - the monitor exits after the current request'
                Start-Sleep -Seconds 1
                exit 0
            }
            '2' {
                $settings.popup = 'off'
                Save-Settings
                Write-Ok 'answer box hidden - CapsLock flashes stay on'
                Start-Sleep -Seconds 1
            }
            '3' {
                $settings.popup = 'on'
                Save-Settings
                Write-Ok 'answer box enabled again'
                Start-Sleep -Seconds 1
            }
            '4' { Read-Position; Start-Sleep -Seconds 1 }
            '5' { Read-Scale; Start-Sleep -Seconds 1 }
            '6' { Read-Duration; Start-Sleep -Seconds 1 }
            '7' { Read-Thinking; Start-Sleep -Seconds 1 }
            default { exit 0 }
        }
    }
}

# ---- starting a new monitor -------------------------------------------------

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    Clear-Screen
    Write-Banner 'first run - installing'
    Write-Host ''
    Write-Host '     creating .venv and installing dependencies, about a minute...' -ForegroundColor Gray
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
    $keyLabel = 'not set'
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

    Clear-Screen
    Write-Banner 'screen answer reader'
    Write-Host ''
    Write-Pair 'popup' $settings.popup 'thinking' $settings.thinking
    Write-Pair 'position' $settings.position 'scale' ($settings.scale + '%')
    Write-Pair 'duration' ($settings.duration + 's') 'hotkey' 'F9'
    Write-Pair 'api key' $keyLabel 'model' $model
    Write-Pair 'endpoint' $baseUrl
    Write-Section 'start'
    Write-Item '1' 'Answer box + CapsLock flashes'
    Write-Item '2' 'CapsLock flashes only'
    Write-Section 'display & brain'
    Write-Item2 '3' 'Popup position' '4' 'Popup size'
    Write-Item2 '5' 'Box duration' '6' 'Thinking effort'
    Write-Section 'connection'
    Write-Item2 '7' 'API key' '8' 'Model / endpoint'
    Write-Item '0' 'Exit'
    Write-Host ''
    Write-Host '     settings save to .monitor-settings' -ForegroundColor DarkGray

    $choice = Read-Choice 'choose 0-8'
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '0' }

    $start = $false
    switch ($choice) {
        '1' { $settings.popup = 'on';  Save-Settings; $start = $true }
        '2' { $settings.popup = 'off'; Save-Settings; $start = $true }
        '3' { Read-Position; Start-Sleep -Seconds 1 }
        '4' { Read-Scale; Start-Sleep -Seconds 1 }
        '5' { Read-Duration; Start-Sleep -Seconds 1 }
        '6' { Read-Thinking; Start-Sleep -Seconds 1 }
        '7' {
            if ([Console]::IsInputRedirected) {
                # A hidden prompt reads the console directly and would block on
                # piped input, so accept a normal line when input is redirected.
                $plain = Read-Host '     paste the new API key (Enter keeps the current one)'
            } else {
                $secure = Read-Host '     paste the new API key (Enter keeps the current one)' -AsSecureString
                $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
                try {
                    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
                } finally {
                    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
                }
            }
            if ([string]::IsNullOrWhiteSpace($plain)) {
                Write-Ok 'API key unchanged'
            } else {
                Set-EnvValue 'DEEPSEEK_API_KEY' $plain.Trim()
                Write-Ok 'API key saved to .env'
            }
            Start-Sleep -Seconds 1
        }
        '8' {
            $newModel = Read-Host ('     model [Enter = ' + $model + ']')
            if (-not [string]::IsNullOrWhiteSpace($newModel)) {
                Set-EnvValue 'DEEPSEEK_MODEL' $newModel.Trim()
            }
            $newBase = Read-Host ('     API base URL [Enter = ' + $baseUrl + ']')
            if (-not [string]::IsNullOrWhiteSpace($newBase)) {
                Set-EnvValue 'DEEPSEEK_BASE_URL' ($newBase.Trim().TrimEnd('/'))
            }
            Write-Ok 'connection settings saved'
            Start-Sleep -Seconds 1
        }
        default { exit 0 }
    }
    if ($start) { break }
}

if (Test-Path -LiteralPath $stopPath) { Remove-Item -LiteralPath $stopPath }
Write-Host ''
Write-Host '     starting monitor...' -ForegroundColor DarkGray
$arguments = @('-u', ('"' + $monitorScript + '"'), '--key', 'f9', '--mute',
               '--stop-file', ('"' + $stopPath + '"'))
$process = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'monitor.log') -RedirectStandardError (Join-Path $PSScriptRoot 'monitor-error.log') -PassThru
Set-Content -LiteralPath $pidPath -Value $process.Id
Start-Sleep -Milliseconds 800
$process.Refresh()
if ($process.HasExited) {
    throw 'Monitor exited during startup. Check monitor.log and monitor-error.log.'
}
Clear-Screen
Write-Banner 'ready'
Write-Host ''
Write-Pair 'status' 'listening' 'hotkey' 'F9'
Write-Pair 'popup' $settings.popup 'thinking' $settings.thinking
Write-Pair 'position' $settings.position 'scale' ($settings.scale + '%')
Write-Pair 'pid' ([string]$process.Id) 'log' 'monitor.log'
Write-Host ''
Write-Host '     press F9 on any question' -ForegroundColor Cyan
Write-Host '     this window closes by itself - run stop.cmd to stop' -ForegroundColor DarkGray
Start-Sleep -Seconds 2
