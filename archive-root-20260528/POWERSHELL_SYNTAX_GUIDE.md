# PowerShell Syntax Reference Guide

This guide helps prevent common PowerShell syntax errors, especially when transitioning from Bash/Linux commands.

## 🚨 Common Bash vs PowerShell Differences

### Command Chaining
| Bash | PowerShell | Description |
|------|------------|-------------|
| `cmd1 && cmd2` | `cmd1; cmd2` | Run commands sequentially |
| `cmd1 \|\| cmd2` | `cmd1; if (!$?) { cmd2 }` | Run cmd2 if cmd1 fails |
| `cmd1 && cmd2 && cmd3` | `cmd1; cmd2; cmd3` | Chain multiple commands |

**❌ WRONG:**
```powershell
cd backend && npm install && npm start
```

**✅ CORRECT:**
```powershell
cd backend; npm install; npm start
```

### Logical Operators in Conditionals
```powershell
# Use -and, -or, -not instead of &&, ||, !
if ($condition1 -and $condition2) { }
if ($condition1 -or $condition2) { }
if (-not $condition) { }
```

## 📁 Path Handling

### Path Separators
- **PowerShell accepts both:** `\` and `/`
- **Recommendation:** Use `/` for cross-platform compatibility

```powershell
# Both work in PowerShell
cd C:\Users\Documents
cd C:/Users/Documents

# Forward slashes are safer for scripts
$path = "C:/Users/Documents/file.txt"
```

### Special Path Variables
```powershell
$HOME           # User home directory
$PWD            # Current directory
$env:USERPROFILE # Windows user profile
$PSScriptRoot   # Directory of current script
```

## 🔧 Common Command Equivalents

| Bash | PowerShell | Alias Available |
|------|------------|-----------------|
| `ls` | `Get-ChildItem` | `ls`, `dir`, `gci` |
| `cat` | `Get-Content` | `cat`, `type`, `gc` |
| `grep` | `Select-String` | `sls` |
| `cp` | `Copy-Item` | `cp`, `copy`, `cpi` |
| `mv` | `Move-Item` | `mv`, `move`, `mi` |
| `rm` | `Remove-Item` | `rm`, `del`, `ri` |
| `mkdir` | `New-Item -ItemType Directory` | `mkdir`, `md` |
| `touch` | `New-Item -ItemType File` | - |
| `pwd` | `Get-Location` | `pwd`, `gl` |
| `cd` | `Set-Location` | `cd`, `sl` |
| `echo` | `Write-Output` | `echo`, `write` |
| `curl` | `Invoke-WebRequest` | `curl`, `wget`, `iwr` |
| `ps` | `Get-Process` | `ps`, `gps` |
| `kill` | `Stop-Process` | `kill`, `spps` |
| `env` | `Get-ChildItem Env:` | `ls env:` |

### Examples
```powershell
# List files recursively
Get-ChildItem -Recurse
ls -Recurse

# Search in files
Select-String -Path "*.txt" -Pattern "error"
sls -Path "*.txt" -Pattern "error"

# Read file content
Get-Content file.txt
cat file.txt

# Create directory
New-Item -ItemType Directory -Path "newfolder"
mkdir newfolder
```

## 🔄 Piping and Output

### Pipeline Differences
```powershell
# PowerShell passes objects, not text
Get-Process | Where-Object { $_.CPU -gt 100 }

# Bash-style text processing still works
Get-Content file.txt | Select-String "pattern"

# Format output
Get-Process | Format-Table Name, CPU, Memory
Get-Process | Format-List *
```

### Output Redirection
```powershell
# Same as Bash
command > output.txt          # Overwrite
command >> output.txt         # Append
command 2> error.txt          # Redirect errors
command 2>&1                  # Redirect errors to stdout
command > output.txt 2>&1     # Redirect both
```

## ⚠️ Error Handling

### Try-Catch Blocks
```powershell
try {
    # Commands that might fail
    Get-Content "nonexistent.txt" -ErrorAction Stop
} catch {
    Write-Host "Error: $_"
    # Handle error
}
```

### Error Action Preference
```powershell
# Stop on error (like bash set -e)
$ErrorActionPreference = "Stop"

# Continue on error (default)
$ErrorActionPreference = "Continue"

# Per-command error handling
Get-Content "file.txt" -ErrorAction SilentlyContinue
```

### Check Last Command Status
```powershell
# $? contains success/failure of last command
command
if ($?) {
    Write-Host "Success"
} else {
    Write-Host "Failed"
}

# $LASTEXITCODE contains exit code
command
if ($LASTEXITCODE -eq 0) {
    Write-Host "Success"
}
```

## 🎯 Variables and Strings

### Variable Declaration
```powershell
# No need for 'export' or 'declare'
$myVar = "value"
$number = 42

# Environment variables
$env:PATH = "C:/new/path;$env:PATH"

# Constants
Set-Variable -Name "API_KEY" -Value "secret" -Option Constant
```

### String Interpolation
```powershell
# Double quotes for interpolation
$name = "World"
Write-Host "Hello, $name"
Write-Host "Path: $($env:PATH)"

# Single quotes for literal strings
Write-Host 'Hello, $name'  # Outputs: Hello, $name
```

## 🔍 Conditional Operators

| Operation | PowerShell | Bash |
|-----------|------------|------|
| Equal | `-eq` | `==` or `-eq` |
| Not equal | `-ne` | `!=` or `-ne` |
| Greater than | `-gt` | `>` or `-gt` |
| Less than | `-lt` | `<` or `-lt` |
| Greater or equal | `-ge` | `>=` or `-ge` |
| Less or equal | `-le` | `<=` or `-le` |
| String match | `-like`, `-match` | `=~` |
| Contains | `-contains` | - |
| File exists | `Test-Path` | `-f` |

### Examples
```powershell
# Numeric comparison
if ($count -gt 10) { }

# String comparison
if ($status -eq "ready") { }

# Pattern matching
if ($text -like "*error*") { }
if ($text -match "^\d+$") { }  # Regex

# File/directory checks
if (Test-Path "file.txt") { }
if (Test-Path "folder" -PathType Container) { }
```

## 🚀 Quick Reference: Common Tasks

### Running Multiple Commands
```powershell
# Sequential execution (use semicolon)
cd project; npm install; npm start

# Conditional execution
command; if ($?) { Write-Host "Success" }

# Background jobs
Start-Job -ScriptBlock { long-running-command }
```

### Working with JSON
```powershell
# Parse JSON
$data = Get-Content "config.json" | ConvertFrom-Json

# Create JSON
$object | ConvertTo-Json | Out-File "output.json"
```

### HTTP Requests
```powershell
# GET request
$response = Invoke-RestMethod -Uri "https://api.example.com/data"

# POST request
$body = @{ key = "value" } | ConvertTo-Json
Invoke-RestMethod -Uri "https://api.example.com" -Method Post -Body $body -ContentType "application/json"
```

### Process Management
```powershell
# List processes
Get-Process | Where-Object { $_.Name -like "*node*" }

# Kill process
Stop-Process -Name "node" -Force

# Start process
Start-Process "notepad.exe"
```

## 📝 Script Best Practices

### Script Header
```powershell
#!/usr/bin/env pwsh
# Enable strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
```

### Parameter Declaration
```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [int]$Timeout = 30
)
```

### Functions
```powershell
function Get-ServerStatus {
    param(
        [string]$ServerName
    )
    
    # Function body
    return $result
}
```

## 🎓 Key Takeaways

1. **Use `;` not `&&`** for command chaining
2. **Use `-and`, `-or`, `-not`** for logical operations
3. **Use `-eq`, `-ne`, `-gt`, `-lt`** for comparisons
4. **Forward slashes `/` work** in paths and are cross-platform
5. **`$?` checks** if last command succeeded
6. **`$LASTEXITCODE`** contains the exit code
7. **PowerShell is object-based**, not text-based
8. **Use `Try-Catch`** for error handling
9. **Cmdlets follow** `Verb-Noun` naming convention
10. **Tab completion** is your friend - use it!

## 🔗 Additional Resources

- [PowerShell Documentation](https://docs.microsoft.com/powershell/)
- [PowerShell Gallery](https://www.powershellgallery.com/)
- [About Comparison Operators](https://docs.microsoft.com/powershell/module/microsoft.powershell.core/about/about_comparison_operators)

---

**Remember:** When in doubt, use `;` instead of `&&` and `-eq` instead of `==`!