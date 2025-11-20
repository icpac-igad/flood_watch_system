# 🌊 FloodWatch - Early Warning System

> Real-time flood forecasting and monitoring for Eastern Africa

FloodWatch helps communities in Eastern Africa prepare for and respond to flood events by providing accurate, timely forecasts and actionable early warning information.

## 🚀 Get Started in 5 Minutes

### What You Need
- Docker installed on your computer
- At least 8GB RAM
- 20GB free disk space

### Install and Run

```bash
# 1. Get the code
git clone https://github.com/icpac-igad/flood_watch_system.git
cd flood_watch_system

# 2. Set up your environment
cp .env.example .env

# 3. Start the system
docker-compose up -d

# 4. Set up the database
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py init_db
```

### 🎯 Access the System

Open these in your browser:

- **📊 FloodWatch Dashboard**: http://localhost:8094
- **⚙️ Admin Panel**: http://localhost:8090/admin (admin / admin123)
- **📡 API Documentation**: http://localhost:9050/docs

> ⚠️ **Important**: Change the default password before deploying to production!

## 💡 What Does It Do?

FloodWatch combines multiple data sources to create accurate flood forecasts:

- **Deterministic Forecasts** - Day-to-day flood predictions
- **Ensemble Forecasts** - Probability-based long-term forecasts
- **Satellite Observations** - Real-time ground conditions
- **Interactive Maps** - Visualize risks and impacts

## 📚 Learn More

Need more details? Check out the documentation:

- [📖 Full API Reference](docs/API_DOCUMENTATION.md)
- [🚢 Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [🏗️ System Architecture](docs/SIMPLIFIED_FRONTEND_ARCHITECTURE.md)

## 🔧 Common Tasks

### Load Forecast Data
```bash
docker-compose exec backend python manage.py sync_floodproofs_to_db
```

### Load Ensemble Data
```bash
docker-compose exec backend python manage.py sync_ensemble_from_ftp
```

### View Logs
```bash
docker-compose logs -f
```

### Restart a Service
```bash
docker-compose restart backend
```

## 🆘 Need Help?

**Something not working?**

1. Check if all containers are running: `docker-compose ps`
2. View the logs: `docker-compose logs -f [service_name]`
3. Make sure your `.env` file is configured correctly
4. See the [troubleshooting guide](docs/DEPLOYMENT_GUIDE.md#troubleshooting)

**Still stuck?** Open an issue on GitHub!

## 🏗️ Technical Stack

The system runs 8 services in Docker containers:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | React + Leaflet | Interactive map interface |
| Backend | Django + PostGIS | API and data management |
| Database | PostgreSQL + PostGIS | Spatial data storage |
| Cache | Redis | Fast data access |
| Workers | Celery | Background tasks |
| API | FastAPI | High-speed forecast data |
| Tiles | TiPg | Vector map tiles |

## 🤝 Contributing

We welcome contributions! This system is developed by ICPAC to serve communities across Eastern Africa.

## 📄 License

[Add your license here]

---

**Built with ❤️ by ICPAC** - IGAD Climate Prediction and Applications Centre
