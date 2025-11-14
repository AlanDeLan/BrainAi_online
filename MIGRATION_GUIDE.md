# Database Migration Guide for Railway

## Prerequisites
- Railway CLI installed: `npm install -g @railway/cli`
- Logged into Railway: `railway login`
- Project linked: `railway link`

## Option 1: Run migration via Railway CLI (Recommended)

```bash
# Link to your project (if not linked)
railway link

# Run migration directly on Railway
railway run python migrate_db.py
```

## Option 2: Manual migration via Railway Dashboard

1. Go to Railway Dashboard: https://railway.app/dashboard
2. Open your project: BrainAi_online
3. Click on PostgreSQL service
4. Click "Connect" and copy connection string
5. Set DATABASE_URL locally and run:

```bash
export DATABASE_URL="postgresql://..." # paste connection string
python migrate_db.py
```

## Option 3: One-time deployment command

Add migration to Railway deployment:

1. In Railway Dashboard, go to Settings → Deploy
2. Add custom start command temporarily:
   ```
   python migrate_db.py && python railway_start.py
   ```
3. Re-deploy
4. After successful migration, revert to: `python railway_start.py`

## Verify Migration

After running migration, check tables exist:

```sql
-- Connect to Railway PostgreSQL via Railway Dashboard > Data tab
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Should see: users, archetypes, chat_messages, user_sessions
```

## Migration Steps Performed

The migration script creates:

1. **users** table with email, username, password_hash
2. **archetypes** table with user_id FK, system_prompt, is_public
3. **chat_messages** table with user_id and archetype_id FKs
4. **user_sessions** table for JWT session tracking
5. **Triggers**:
   - `enforce_archetype_limit`: Max 2 archetypes per user
   - `cleanup_old_messages`: Auto-delete messages beyond 100 per user
6. **Indexes** for performance on user_id, archetype_id, timestamps

## Troubleshooting

**Error: "relation already exists"**
- Tables already created, skip migration or drop tables first

**Error: "permission denied"**
- Check DATABASE_URL has correct credentials
- Verify PostgreSQL service is running on Railway

**Error: "could not connect"**
- Check Railway PostgreSQL is deployed and running
- Verify DATABASE_URL environment variable is set
