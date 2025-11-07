# Deployment script for EC2 updates
# Run this to deploy the latest changes from GitHub to your EC2 server

Write-Host "🚀 Deploying updates to EC2..." -ForegroundColor Cyan

# EC2 connection details
$EC2_IP = "3.135.232.123"
$EC2_USER = "ubuntu"

# Commands to run on EC2
$commands = @"
cd ~/webapp-deploy
echo '📥 Pulling latest code from GitHub...'
git pull origin main
echo '🔄 Restarting PM2 process...'
pm2 restart webapp-backend
echo '✅ Deployment complete!'
pm2 status
"@

Write-Host "Connecting to EC2 at $EC2_IP..." -ForegroundColor Yellow
ssh ${EC2_USER}@${EC2_IP} $commands

Write-Host "`n✨ Done! Your website should be updated at http://$EC2_IP:8000" -ForegroundColor Green
