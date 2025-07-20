@echo off
echo Starting VoiceFlow Pro servers...
echo.

echo Setting up environment...
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your API keys before running docker-compose
    pause
)

echo Starting Docker services...
docker-compose up -d

echo.
echo Checking service status...
docker-compose ps

echo.
echo Services should be available at:
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo LiveKit: ws://localhost:7880
echo.
echo To view logs: docker-compose logs -f
echo To stop services: docker-compose down
echo.
pause