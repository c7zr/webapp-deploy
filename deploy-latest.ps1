# Deploy Latest Updates to EC2 Server
# Run this script to deploy all changes to 3.135.232.123

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  SWATNFO WebApp Deployment Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Server details
$SERVER = "ubuntu@3.135.232.123"
$KEY_PATH = "C:\Users\awzax\Downloads\swatnfo-key.pem"

Write-Host "🚀 Deploying to: $SERVER" -ForegroundColor Yellow
Write-Host ""

# SSH commands to execute on server
$DEPLOY_COMMANDS = @"
echo '📥 Pulling latest changes from GitHub...'
cd ~/webapp-deploy
git pull origin main

echo ''
echo '🔄 Restarting PM2 process...'
pm2 restart webapp

echo ''
echo '📊 PM2 Status:'
pm2 status

echo ''
echo '📝 Recent logs (last 20 lines):'
pm2 logs webapp --lines 20 --nostream

echo ''
echo '✅ Deployment complete!'
echo ''
echo '🌐 Backend: http://3.135.232.123:8000'
echo '📊 API Docs: http://3.135.232.123:8000/docs'
echo '💬 Chat: http://3.135.232.123:8000/chat.html'
echo ''
echo '📋 Recent Changes:'
echo '  ✅ Single report: 1-20 reports per target (1.5s delay)'
echo '  ✅ Mass reporting: Up to 200 reports with multi-threading (PREMIUM)'
echo '  ✅ Announcement modal: Shows twice then hides'
echo '  ✅ Hourly chat auto-clear'
echo '  ✅ Fixed navigation links'
"@

# Execute deployment
Write-Host "🔌 Connecting to server and deploying..." -ForegroundColor Green
ssh -i $KEY_PATH $SERVER $DEPLOY_COMMANDS

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Visit http://3.135.232.123:8000/dashboard.html" -ForegroundColor White
Write-Host "2. Login and test the announcement modal" -ForegroundColor White
Write-Host "3. Try mass reporting (Premium users only)" -ForegroundColor White
Write-Host "4. Check PM2 logs if any issues" -ForegroundColor White
Write-Host ""
