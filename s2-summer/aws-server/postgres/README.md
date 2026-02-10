# PostgreSQL with JSONB Docker Compose Setup
## Environment Variables
```bash
    cp .env.example .env
```
---  
## Quick Start


1. Start the database:
```bash
docker-compose up -d
```

2. Stop the database:
```bash
docker-compose down
```

3. Connect to database:
```bash
docker-compose exec postgres psql -U minimart_user -d minimart_db
```