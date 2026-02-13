# Quick Start - Danswer POC

## Launch in 3 Steps

### 1. Configure Environment
```powershell
cd danswer-poc
cp .env.example .env
notepad .env  # Add your OPENAI_API_KEY
```

### 2. Start Services
```powershell
docker-compose up -d
```

### 3. Access Danswer
Open http://localhost:3100

**First login:**
- Email: `admin@example.com`  
- Password: `admin`

**Note:** Using port 3100 to avoid conflicts with existing containers.

## Connect Your Google Drive

1. Go to **Admin > Connectors**
2. Click **Google Drive**
3. Authenticate or upload service account JSON
4. Specify folder ID from your current system
5. Click **Index Now**

## Test It

Ask questions like:
- "What are NerdsToGo's business hours?"
- "How do I submit a PTO request?"
- "Compare service plans"

Compare answers to your current NerdsIQ system.

## Evaluation

See [README.md](README.md) for complete evaluation checklist.

## Stop Services

```powershell
docker-compose down        # Stop, keep data
docker-compose down -v     # Stop, delete data
```

## Next Steps

After evaluation:
1. Review answer quality vs. current system
2. If approved, see [MIGRATION_PLAN.md](MIGRATION_PLAN.md)
3. Schedule migration timeline with stakeholders

## Troubleshooting

**Containers won't start:**
```powershell
docker-compose logs
docker ps -a
```

**Port conflicts:**
```powershell
netstat -ano | findstr "3000 8080 5432"
```

**Need help:** Check [README.md](README.md#troubleshooting) or Danswer docs: https://docs.danswer.dev
