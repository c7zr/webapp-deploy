# Quick Deploy Script - Restart PM2 with Latest Code
Write-Host "🚀 Deploying updates to EC2..." -ForegroundColor Cyan

# Use SSH without key (password auth or existing session)
$commands = @"
cd ~/webapp-deploy
git pull origin main
pm2 restart webapp
pm2 logs webapp --lines 50
"@

Write-Host "Running deployment commands..." -ForegroundColor Yellow
ssh ubuntu@3.135.232.123 $commands

Write-Host "`n✅ Deployment complete! Server restarted with latest code." -ForegroundColor Green
Write-Host "🌐 Access at: http://3.135.232.123:8000" -ForegroundColor Cyan
