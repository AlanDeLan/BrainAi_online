"""
Database migration script for multi-user system.
Run this to update existing database to new schema.
"""
from sqlalchemy import create_engine, text
from core.logger import logger
from core.settings import settings


def migrate_database():
    """Migrate database to multi-user schema."""
    
    engine = create_engine(settings.database_url)
    
    migrations = [
        # 1. Create users table
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        """,
        
        # 2. Create archetypes table
        """
        CREATE TABLE IF NOT EXISTS archetypes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            system_prompt TEXT NOT NULL,
            model_name VARCHAR(100) DEFAULT 'gemini-1.5-flash',
            temperature INTEGER DEFAULT 70,
            max_tokens INTEGER DEFAULT 2048,
            is_public BOOLEAN DEFAULT FALSE,
            uses_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        );
        CREATE INDEX IF NOT EXISTS idx_archetypes_user ON archetypes(user_id);
        CREATE INDEX IF NOT EXISTS idx_archetypes_public ON archetypes(is_public);
        """,
        
        # 3. Update chat_messages table
        """
        -- Add user_id column if doesn't exist
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='chat_messages' AND column_name='user_id_int'
            ) THEN
                ALTER TABLE chat_messages ADD COLUMN user_id_int INTEGER REFERENCES users(id) ON DELETE CASCADE;
            END IF;
        END $$;
        
        -- Add archetype_id column if doesn't exist
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='chat_messages' AND column_name='archetype_id'
            ) THEN
                ALTER TABLE chat_messages ADD COLUMN archetype_id INTEGER REFERENCES archetypes(id) ON DELETE SET NULL;
            END IF;
        END $$;
        
        CREATE INDEX IF NOT EXISTS idx_chat_user_chat ON chat_messages(user_id_int, chat_id);
        CREATE INDEX IF NOT EXISTS idx_chat_user_created ON chat_messages(user_id_int, created_at);
        """,
        
        # 4. Create user_sessions table
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            ip_address VARCHAR(50),
            user_agent VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
        """,
        
        # 5. Create function to limit archetypes per user
        """
        CREATE OR REPLACE FUNCTION check_archetype_limit()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (SELECT COUNT(*) FROM archetypes WHERE user_id = NEW.user_id) >= 2 THEN
                RAISE EXCEPTION 'User cannot have more than 2 archetypes';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS archetype_limit_trigger ON archetypes;
        CREATE TRIGGER archetype_limit_trigger
        BEFORE INSERT ON archetypes
        FOR EACH ROW EXECUTE FUNCTION check_archetype_limit();
        """,
        
        # 6. Create function to cleanup old messages (keep last 100 per user)
        """
        CREATE OR REPLACE FUNCTION cleanup_old_messages()
        RETURNS TRIGGER AS $$
        BEGIN
            DELETE FROM chat_messages
            WHERE id IN (
                SELECT id FROM chat_messages
                WHERE user_id_int = NEW.user_id_int
                ORDER BY created_at DESC
                OFFSET 100
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS cleanup_messages_trigger ON chat_messages;
        CREATE TRIGGER cleanup_messages_trigger
        AFTER INSERT ON chat_messages
        FOR EACH ROW EXECUTE FUNCTION cleanup_old_messages();
        """
    ]
    
    try:
        with engine.connect() as conn:
            for i, migration in enumerate(migrations, 1):
                logger.info(f"Running migration {i}/{len(migrations)}...")
                conn.execute(text(migration))
                conn.commit()
                logger.info(f"✅ Migration {i} completed")
        
        logger.info("🎉 All migrations completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Starting database migration...")
    success = migrate_database()
    if success:
        print("✅ Migration completed!")
    else:
        print("❌ Migration failed! Check logs for details.")
