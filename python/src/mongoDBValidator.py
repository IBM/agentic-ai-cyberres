#
# Copyright contributors to the agentic-ai-cyberres project
#
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

def validate_mongodb():
    load_dotenv()
    
    mongodb_name = os.getenv("MONGODB_NAME")
    mongodb_collection = os.getenv("MONGODB_COLLECTION_NAME")
    
    if not mongodb_name or not mongodb_collection:
        print("Error: MongoDB environment variables not set")
        return
    
    connection_string = f"mongodb://localhost/{mongodb_name}"
    
    try:
        client = MongoClient(connection_string)
        db = client[mongodb_name]
        collection = db[mongodb_collection]
        
        print(f"Validating database {mongodb_name} and collection {mongodb_collection}")
        
        # MongoDB validation command
        validation_result = db.command("validate", mongodb_collection)
        print(json.dumps(validation_result, indent=2))
        return validation_result
        
    except Exception as e:
        print(f"Error validating MongoDB: {e}")
        raise e

if __name__ == "__main__":
    validate_mongodb()