# Fire Emblem: Three Houses - PlayStation Prompts installer
# Installs one style into an emulator's mod folder, switches styles, or removes the mod.
# It only ever creates or deletes folders named "PS Prompts - ..." inside the mod folder you pick.
#
# Window:        double-click "PS Prompts Installer.bat"
# Command line:  powershell -File "PS Prompts Installer.ps1" -Action list|install|remove
#                    [-Emulator yuzu] [-Target <mod folder>] [-Style "DS4 Dark, Pill"] [-Confirm Circle|Cross]

param(
    [ValidateSet('', 'list', 'install', 'remove')] [string]$Action = '',
    [string]$Emulator = '',
    [string]$Target = '',
    [string]$Style = '',
    [ValidateSet('', 'Circle', 'Cross')] [string]$Confirm = ''
)

$ErrorActionPreference = 'Stop'
$TitleId = '010055D009F78000'
$Prefix = 'PS Prompts - '
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---------------------------------------------------------------- mod versions shipped next to this script
function Get-Variants {
    Get-ChildItem -LiteralPath $Here -Directory -Recurse -Depth 1 |
        Where-Object { $_.Name.StartsWith($Prefix) -and (Test-Path -LiteralPath (Join-Path $_.FullName 'romfs')) } |
        ForEach-Object {
            if ($_.Name -match '^PS Prompts - (.+) \[(Circle|Cross)\]$') {
                [pscustomobject]@{ Style = $Matches[1]; Confirm = $Matches[2]; Name = $_.Name; Path = $_.FullName }
            }
        }
}

# ---------------------------------------------------------------- emulators
function Get-Emulators {
    $list = @()
    foreach ($name in 'yuzu', 'suyu', 'sudachi', 'citron', 'eden', 'torzu') {
        $base = Join-Path $env:APPDATA $name
        if (Test-Path -LiteralPath $base) {
            $list += [pscustomobject]@{ Name = $name; Path = (Join-Path $base "load\$TitleId") }
        }
    }
    $ryu = Join-Path $env:APPDATA 'Ryujinx'
    if (Test-Path -LiteralPath $ryu) {
        $list += [pscustomobject]@{ Name = 'Ryujinx'; Path = (Join-Path $ryu ("mods\contents\" + $TitleId.ToLower())) }
    }
    $list
}

function Get-Installed([string]$modDir) {
    if (-not $modDir -or -not (Test-Path -LiteralPath $modDir)) { return @() }
    @(Get-ChildItem -LiteralPath $modDir -Directory | Where-Object { $_.Name.StartsWith($Prefix) })
}

function Remove-PSPrompts([string]$modDir) {
    $removed = @()
    foreach ($d in Get-Installed $modDir) {
        # safety: only folders named "PS Prompts - ..." directly inside the chosen mod folder
        if ($d.Parent.FullName.TrimEnd('\') -ne (Resolve-Path -LiteralPath $modDir).Path.TrimEnd('\')) { continue }
        Remove-Item -LiteralPath $d.FullName -Recurse -Force
        $removed += $d.Name
    }
    $removed
}

function Install-PSPrompts($variant, [string]$modDir) {
    if (-not (Test-Path -LiteralPath $modDir)) { New-Item -ItemType Directory -Path $modDir -Force | Out-Null }
    $removed = Remove-PSPrompts $modDir
    $dest = Join-Path $modDir $variant.Name
    Copy-Item -LiteralPath $variant.Path -Destination $dest -Recurse -Force
    # check every file arrived with the right size
    $src = Get-ChildItem -LiteralPath $variant.Path -Recurse -File
    foreach ($f in $src) {
        $rel = $f.FullName.Substring($variant.Path.Length)
        $copy = Join-Path $dest $rel
        if (-not (Test-Path -LiteralPath $copy) -or (Get-Item -LiteralPath $copy).Length -ne $f.Length) {
            throw "Copy check failed for $rel"
        }
    }
    [pscustomobject]@{ Installed = $variant.Name; Removed = $removed; Files = $src.Count; Path = $dest }
}

function Resolve-Target {
    if ($Target) { return $Target }
    $emus = @(Get-Emulators)
    if ($Emulator) {
        $e = $emus | Where-Object { $_.Name -eq $Emulator } | Select-Object -First 1
        if (-not $e) { throw "Emulator '$Emulator' not found in $env:APPDATA. Use -Target with the mod folder." }
        return $e.Path
    }
    if ($emus.Count -eq 1) { return $emus[0].Path }
    throw 'Several or no emulators found. Use -Emulator <name> or -Target <mod folder>.'
}

# ---------------------------------------------------------------- command-line mode
if ($Action) {
    $variants = @(Get-Variants)
    switch ($Action) {
        'list' {
            'Versions in this folder:'
            $variants | ForEach-Object { '  ' + $_.Name }
            'Emulators found:'
            Get-Emulators | ForEach-Object { '  {0}  {1}' -f $_.Name, $_.Path }
            if ($Target -or $Emulator) {
                $t = Resolve-Target
                'Installed in ' + $t + ':'
                Get-Installed $t | ForEach-Object { '  ' + $_.Name }
            }
        }
        'install' {
            $v = $variants | Where-Object { $_.Style -eq $Style -and $_.Confirm -eq $Confirm } | Select-Object -First 1
            if (-not $v) { throw "No version '$Style' [$Confirm] next to the installer." }
            $r = Install-PSPrompts $v (Resolve-Target)
            'Installed {0} ({1} files) at {2}' -f $r.Installed, $r.Files, $r.Path
            if ($r.Removed) { 'Removed: ' + ($r.Removed -join ', ') }
        }
        'remove' {
            $r = @(Remove-PSPrompts (Resolve-Target))
            if ($r) { 'Removed: ' + ($r -join ', ') } else { 'Nothing to remove.' }
        }
    }
    return
}

# ---------------------------------------------------------------- window
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$variants = @(Get-Variants)
if (-not $variants) {
    [System.Windows.Forms.MessageBox]::Show("No 'PS Prompts - ...' folders were found next to the installer.`nExtract the whole archive first, then run the installer from the extracted folder.", 'PS Prompts Installer') | Out-Null
    return
}
$styles = @($variants | ForEach-Object { $_.Style } | Select-Object -Unique)
$order = 'DualSense', 'DS4 Light, Label', 'DS4 Light, Pill', 'DS4 Dark, Label', 'DS4 Dark, Pill'
$styles = @($order | Where-Object { $styles -contains $_ }) + @($styles | Where-Object { $order -notcontains $_ })

$font = New-Object System.Drawing.Font('Segoe UI', 9.5)
$bold = New-Object System.Drawing.Font('Segoe UI', 9.5, [System.Drawing.FontStyle]::Bold)
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Fire Emblem: Three Houses - PlayStation Prompts'
$form.Font = $font
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.StartPosition = 'CenterScreen'
$form.ClientSize = New-Object System.Drawing.Size(560, 430)

function Add-Label($text, $x, $y, $w = 520, $h = 20, $f = $font) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text; $l.Location = New-Object System.Drawing.Point($x, $y)
    $l.Size = New-Object System.Drawing.Size($w, $h); $l.Font = $f
    $form.Controls.Add($l); $l
}

# 1. emulator
Add-Label '1. Emulator' 20 15 520 20 $bold | Out-Null
$emuBox = New-Object System.Windows.Forms.ComboBox
$emuBox.DropDownStyle = 'DropDownList'
$emuBox.Location = New-Object System.Drawing.Point(20, 38); $emuBox.Size = New-Object System.Drawing.Size(410, 24)
$form.Controls.Add($emuBox)
$browse = New-Object System.Windows.Forms.Button
$browse.Text = 'Browse...'; $browse.Location = New-Object System.Drawing.Point(440, 37); $browse.Size = New-Object System.Drawing.Size(100, 26)
$form.Controls.Add($browse)
$pathLabel = Add-Label '' 20 66 520 34
$pathLabel.ForeColor = [System.Drawing.Color]::DimGray

$targets = New-Object System.Collections.ArrayList
foreach ($e in Get-Emulators) { [void]$targets.Add($e); [void]$emuBox.Items.Add($e.Name) }

# 2. style
Add-Label '2. Button style' 20 108 520 20 $bold | Out-Null
$styleBox = New-Object System.Windows.Forms.ComboBox
$styleBox.DropDownStyle = 'DropDownList'
$styleBox.Location = New-Object System.Drawing.Point(20, 131); $styleBox.Size = New-Object System.Drawing.Size(250, 24)
$styles | ForEach-Object { [void]$styleBox.Items.Add($_) }
$styleBox.SelectedIndex = 0
$form.Controls.Add($styleBox)
$styleHelp = Add-Label '' 280 128 260 40
$styleHelp.ForeColor = [System.Drawing.Color]::DimGray
$help = @{
    'DualSense'        = 'Pale buttons, symbol cut out. Options / Create.'
    'DS4 Light, Label' = 'Pale buttons, coloured symbols. Share / Options as word labels.'
    'DS4 Light, Pill'  = 'Pale buttons, coloured symbols. Share / Options as small pills.'
    'DS4 Dark, Label'  = 'Dark buttons, coloured symbols. Share / Options as word labels.'
    'DS4 Dark, Pill'   = 'Dark buttons, coloured symbols. Share / Options as small pills.'
}

# 3. confirm button
Add-Label '3. Which button confirms?' 20 176 520 20 $bold | Out-Null
$circle = New-Object System.Windows.Forms.RadioButton
$circle.Text = 'Circle  (emulator default: buttons mapped by position)'
$circle.Location = New-Object System.Drawing.Point(20, 199); $circle.Size = New-Object System.Drawing.Size(520, 22); $circle.Checked = $true
$cross = New-Object System.Windows.Forms.RadioButton
$cross.Text = 'Cross  (you swapped A and B: A = Cross, B = Circle)'
$cross.Location = New-Object System.Drawing.Point(20, 222); $cross.Size = New-Object System.Drawing.Size(520, 22)
$form.Controls.Add($circle); $form.Controls.Add($cross)
Add-Label 'Not sure? In a game menu press Cross: if it selects, choose Cross; if it backs out, choose Circle.' 20 246 520 34 | ForEach-Object { $_.ForeColor = [System.Drawing.Color]::DimGray }

# status and buttons
$status = Add-Label '' 20 290 520 60
$install = New-Object System.Windows.Forms.Button
$install.Text = 'Install'; $install.Location = New-Object System.Drawing.Point(20, 370); $install.Size = New-Object System.Drawing.Size(150, 34)
$remove = New-Object System.Windows.Forms.Button
$remove.Text = 'Remove'; $remove.Location = New-Object System.Drawing.Point(180, 370); $remove.Size = New-Object System.Drawing.Size(150, 34)
$close = New-Object System.Windows.Forms.Button
$close.Text = 'Close'; $close.Location = New-Object System.Drawing.Point(440, 370); $close.Size = New-Object System.Drawing.Size(100, 34)
$form.Controls.Add($install); $form.Controls.Add($remove); $form.Controls.Add($close)
$form.AcceptButton = $install; $form.CancelButton = $close

function Current-Target {
    if ($emuBox.SelectedIndex -lt 0) { return $null }
    $targets[$emuBox.SelectedIndex].Path
}

function Refresh-Status {
    $t = Current-Target
    $pathLabel.Text = if ($t) { "Mod folder: $t" } else { 'No emulator found. Use Browse to pick the folder your emulator opens with "Open Mod Data Location" for Three Houses.' }
    $styleHelp.Text = $help[[string]$styleBox.SelectedItem]
    $inst = @(Get-Installed $t)
    if (-not $t) {
        $status.Text = ''
    } elseif ($inst.Count -eq 0) {
        $status.Text = 'Installed now: none.'
    } else {
        $status.Text = 'Installed now: ' + (($inst | ForEach-Object { $_.Name.Substring($Prefix.Length) }) -join ', ')
        if ($inst.Count -gt 1) { $status.Text += "`nOnly one should be installed. Install keeps just the one you pick." }
    }
    $install.Enabled = [bool]$t
    $remove.Enabled = $inst.Count -gt 0
}

$browse.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = 'Pick the Three Houses mod folder (the one "Open Mod Data Location" opens in your emulator).'
    if ($dlg.ShowDialog() -eq 'OK') {
        [void]$targets.Add([pscustomobject]@{ Name = 'Custom'; Path = $dlg.SelectedPath })
        [void]$emuBox.Items.Add('Custom: ' + $dlg.SelectedPath)
        $emuBox.SelectedIndex = $emuBox.Items.Count - 1
    }
})
$emuBox.Add_SelectedIndexChanged({ Refresh-Status })
$styleBox.Add_SelectedIndexChanged({ Refresh-Status })

$install.Add_Click({
    $t = Current-Target
    $conf = if ($cross.Checked) { 'Cross' } else { 'Circle' }
    $v = $variants | Where-Object { $_.Style -eq [string]$styleBox.SelectedItem -and $_.Confirm -eq $conf } | Select-Object -First 1
    if (-not $v) { [System.Windows.Forms.MessageBox]::Show('That version is missing from the extracted folder.', 'PS Prompts Installer') | Out-Null; return }
    $form.UseWaitCursor = $true; $status.Text = 'Installing...'; $form.Refresh()
    try {
        $r = Install-PSPrompts $v $t
        $msg = "Installed $($r.Installed)."
        if ($r.Removed) { $msg += "`nRemoved: " + ($r.Removed -join ', ') }
        $msg += "`n`nClose the game if it is running, then make sure the mod is ticked in the game's Add-ons / Mods list and start the game."
        [System.Windows.Forms.MessageBox]::Show($msg, 'PS Prompts Installer') | Out-Null
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Install failed: $($_.Exception.Message)`n`nIs the game still running? Close it and try again.", 'PS Prompts Installer') | Out-Null
    } finally {
        $form.UseWaitCursor = $false; Refresh-Status
    }
})

$remove.Add_Click({
    $t = Current-Target
    $ok = [System.Windows.Forms.MessageBox]::Show("Remove PlayStation Prompts from`n$t ?", 'PS Prompts Installer', 'YesNo')
    if ($ok -ne 'Yes') { return }
    try {
        $r = @(Remove-PSPrompts $t)
        [System.Windows.Forms.MessageBox]::Show('Removed: ' + ($r -join ', '), 'PS Prompts Installer') | Out-Null
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Remove failed: $($_.Exception.Message)`n`nIs the game still running? Close it and try again.", 'PS Prompts Installer') | Out-Null
    } finally { Refresh-Status }
})
$close.Add_Click({ $form.Close() })

if ($emuBox.Items.Count -gt 0) { $emuBox.SelectedIndex = 0 } else { Refresh-Status }
# preselect the style and confirm set already installed, if any
$cur = @(Get-Installed (Current-Target)) | Select-Object -First 1
if ($cur -and $cur.Name -match '^PS Prompts - (.+) \[(Circle|Cross)\]$') {
    $i = $styleBox.Items.IndexOf($Matches[1]); if ($i -ge 0) { $styleBox.SelectedIndex = $i }
    if ($Matches[2] -eq 'Cross') { $cross.Checked = $true }
}
Refresh-Status
[void]$form.ShowDialog()
