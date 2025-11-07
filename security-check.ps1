# Security Check Script for Instagram Report Bot
# Run this before deploying to production

Write-Host "Instagram Report Bot - Security Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$issues = 0

# Check 1: Dependencies
Write-Host "[1/6] Checking dependencies..." -ForegroundColor Yellow
if (Get-Command pip -ErrorAction SilentlyContinue) {
    Write-Host "  - Installing security tools..." -ForegroundColor Gray
    pip install pip-audit safety --quiet
    
    Write-Host "  - Running pip-audit..." -ForegroundColor Gray
    $auditResult = pip-audit 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ VULNERABILITIES FOUND!" -ForegroundColor Red
        Write-Host $auditResult
        $issues++
    } else {
        Write-Host "  ✅ No known CVEs in dependencies" -ForegroundColor Green
    }
} else {
    Write-Host "  ❌ pip not found" -ForegroundColor Red
    $issues++
}

# Check 2: .env file
Write-Host ""
Write-Host "[2/6] Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path "backend\.env") {
    $envContent = Get-Content "backend\.env" -Raw
    
    if ($envContent -match "your-super-secret-jwt-key-change-this-in-production") {
        Write-Host "  ❌ DEFAULT SECRET_KEY DETECTED - CHANGE THIS!" -ForegroundColor Red
        $issues++
    } else {
        Write-Host "  ✅ Custom SECRET_KEY found" -ForegroundColor Green
    }
    
    if ($envContent -match "DATABASE_TYPE=sqlite") {
        Write-Host "  ⚠️  WARNING: Using SQLite (OK for dev, NOT for production)" -ForegroundColor Yellow
    }
    
    if ($envContent -match "DATABASE_HOST=localhost|DATABASE_HOST=127.0.0.1") {
        Write-Host "  ❌ DATABASE ON SAME HOST - MOVE TO SEPARATE SERVER!" -ForegroundColor Red
        $issues++
    } elseif ($envContent -match "DATABASE_HOST=") {
        Write-Host "  ✅ External database configured" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠️  No .env file found (using defaults)" -ForegroundColor Yellow
}

# Check 3: Debug mode
Write-Host ""
Write-Host "[3/6] Checking for debug code..." -ForegroundColor Yellow
$debugFiles = Get-ChildItem -Path "backend" -Filter "*.py" -Recurse | Select-String -Pattern "debug.*True|print\(" -CaseSensitive
if ($debugFiles) {
    Write-Host "  ⚠️  Found debug statements in code" -ForegroundColor Yellow
    $debugFiles | ForEach-Object { Write-Host "    - $($_.Filename):$($_.LineNumber)" -ForegroundColor Gray }
} else {
    Write-Host "  ✅ No obvious debug code found" -ForegroundColor Green
}

# Check 4: HTTPS
Write-Host ""
Write-Host "[4/6] Checking HTTPS configuration..." -ForegroundColor Yellow
Write-Host "  ⚠️  Manual check: Are you using HTTPS in production?" -ForegroundColor Yellow
Write-Host "  ⚠️  Manual check: Is HSTS enabled?" -ForegroundColor Yellow

# Check 5: Outdated packages
Write-Host ""
Write-Host "[5/6] Checking for outdated packages..." -ForegroundColor Yellow
Write-Host "  - Running pip list --outdated..." -ForegroundColor Gray
$outdated = pip list --outdated 2>&1
if ($outdated -match "Package|---") {
    Write-Host "  ⚠️  Outdated packages found:" -ForegroundColor Yellow
    Write-Host $outdated
} else {
    Write-Host "  ✅ All packages up to date" -ForegroundColor Green
}

# Check 6: File permissions
Write-Host ""
Write-Host "[6/6] Checking sensitive files..." -ForegroundColor Yellow
$sensitiveFiles = @(".env", "swatnfo.db", "*.key", "*.pem")
foreach ($pattern in $sensitiveFiles) {
    $files = Get-ChildItem -Path "backend" -Filter $pattern -Recurse -ErrorAction SilentlyContinue
    if ($files) {
        Write-Host "  ⚠️  Found: $($files.Name) - Ensure not in git!" -ForegroundColor Yellow
    }
}

# Check .gitignore
if (Test-Path ".gitignore") {
    $gitignore = Get-Content ".gitignore" -Raw
    if ($gitignore -match "\.env") {
        Write-Host "  ✅ .env is in .gitignore" -ForegroundColor Green
    } else {
        Write-Host "  ❌ .env NOT in .gitignore - ADD IT!" -ForegroundColor Red
        $issues++
    }
} else {
    Write-Host "  ❌ No .gitignore file found" -ForegroundColor Red
    $issues++
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($issues -eq 0) {
    Write-Host "Security Check: PASSED ✅" -ForegroundColor Green
    Write-Host "No critical issues found." -ForegroundColor Green
} else {
    Write-Host "Security Check: FAILED ❌" -ForegroundColor Red
    Write-Host "Found $issues critical issue(s) - FIX BEFORE DEPLOYING!" -ForegroundColor Red
}
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Fix all ❌ critical issues" -ForegroundColor White
Write-Host "  2. Review all ⚠️  warnings" -ForegroundColor White
Write-Host "  3. Run: pip install --upgrade -r requirements.txt" -ForegroundColor White
Write-Host "  4. Set up external database server" -ForegroundColor White
Write-Host "  5. Enable HTTPS with valid SSL certificate" -ForegroundColor White
Write-Host "  6. Read SECURITY.md for full checklist" -ForegroundColor White
Write-Host ""
