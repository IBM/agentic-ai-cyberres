//
// Copyright contributors to the agentic-ai-cyberres project
//

// MongoDB validation script for mongosh
const mongoDBname = process.env.MONGODB_NAME;
const mongoDBcollection = process.env.MONGODB_COLLECTION_NAME;

// Use the database specified in environment
use(mongoDBname);

// Validate the collection
print("Validating database " + mongoDBname + " and collection " + mongoDBcollection);
const result = db.getCollection(mongoDBcollection).validate();
printjson(result);

