#!/bin/bash
# Script to run database migration on Railway

echo "Running database migration..."
python migrate_db.py

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi
