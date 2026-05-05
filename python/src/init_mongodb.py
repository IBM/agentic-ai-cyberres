"""
Initialize MongoDB database with indexes and test data.

Run with: python init_mongodb.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()


async def initialize_mongodb():
    """Initialize MongoDB database."""
    
    # Connect to MongoDB
    connection_string = os.getenv("MONGODB_URL", "mongodb://admin:beeai2024@localhost:27017/beeai?authSource=admin")
    database_name = os.getenv("MONGODB_DATABASE", "beeai")
    
    print(f"Connecting to MongoDB: {database_name}")
    client = AsyncIOMotorClient(connection_string)
    db = client[database_name]
    
    try:
        # Test connection
        await db.command("ping")
        print("✅ MongoDB connection successful!")
        
        # Create collections
        collections = ["validation_runs", "user_sessions", "audit_log"]
        existing = await db.list_collection_names()
        
        for collection in collections:
            if collection not in existing:
                await db.create_collection(collection)
                print(f"✅ Created collection: {collection}")
            else:
                print(f"ℹ️  Collection already exists: {collection}")
        
        # Create indexes
        print("\nCreating indexes...")
        
        # validation_runs indexes
        await db.validation_runs.create_index([("user_id", 1), ("created_at", -1)])
        await db.validation_runs.create_index([("target_host", 1)])
        await db.validation_runs.create_index([("status", 1)])
        await db.validation_runs.create_index([("score", 1)])
        await db.validation_runs.create_index([("session_id", 1)])
        await db.validation_runs.create_index([("created_at", -1)])
        print("✅ Created indexes for validation_runs")
        
        # user_sessions indexes
        await db.user_sessions.create_index([("user_id", 1)])
        await db.user_sessions.create_index([("session_id", 1)], unique=True)
        await db.user_sessions.create_index([("last_activity", -1)])
        print("✅ Created indexes for user_sessions")
        
        # audit_log indexes
        await db.audit_log.create_index([("user_id", 1)])
        await db.audit_log.create_index([("action", 1)])
        await db.audit_log.create_index([("created_at", -1)])
        print("✅ Created indexes for audit_log")
        
        # Show database stats
        stats = await db.command("dbStats")
        print(f"\n📊 Database Stats:")
        print(f"   Collections: {stats['collections']}")
        print(f"   Indexes: {stats['indexes']}")
        print(f"   Data Size: {stats['dataSize']} bytes")
        
        print("\n✅ MongoDB initialization complete!")
        print("\nNext steps:")
        print("1. Run: chainlit run chainlit_app_mongodb.py -w")
        print("2. Open: http://localhost:8000")
        print("3. Type: test")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if MongoDB is running: docker ps | grep mongodb")
        print("2. Verify connection string in .env file")
        print("3. Check MongoDB logs: docker logs beeai-mongodb")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(initialize_mongodb())

# Made with Bob
