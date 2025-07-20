#!/usr/bin/env pwsh

Write-Host "🚀 Starting VoiceFlow Pro servers..." -ForegroundColor Green
Write-Host ""

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Change to project directory
Set-Location "C:\Users\sreen\Desktop\freelance\VoiceFlow-Pro"

Write-Host "📦 Starting Docker services..." -ForegroundColor Blue
docker-compose up -d

Write-Host ""
Write-Host "📊 Checking service status..." -ForegroundColor Blue
docker-compose ps

Write-Host ""
Write-Host "🌐 Services should be available at:" -ForegroundColor Yellow
Write-Host "   Frontend:    http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "   LiveKit:     ws://localhost:7880" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Useful commands:" -ForegroundColor Yellow
Write-Host "   View logs:    docker-compose logs -f" -ForegroundColor Gray
Write-Host "   Stop services: docker-compose down" -ForegroundColor Gray
Write-Host ""

# Wait for services to start
Write-Host "⏳ Waiting for services to start..." -ForegroundColor Blue
Start-Sleep -Seconds 10

# Check health endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Backend API is healthy!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Backend API not ready yet. Check logs with: docker-compose logs backend" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 VoiceFlow Pro is starting up!" -ForegroundColor Green
Write-Host "📖 Remember to add your API keys to the .env file for full functionality" -ForegroundColor Yellow