from keys import keys
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


import pymongo
import sys

ssl_cert_path = "rds-combined-ca-bundle.pem"
##Create a MongoDB client, open a connection to Amazon DocumentDB as a replica set and specify the read preference as secondary preferred
client = pymongo.MongoClient(
    'mongodb+srv://mbue-user:ssrtssmk@cluster-mbue.xo4a2.mongodb.net/',      
                             ) 
print(client.server_info())
print(client.list_database_names())
##Specify the database to be used
db = client.test

##Specify the collection to be used
col = db.collection_1

print(db,col)

##Insert a single document
col.insert_one({'hello':'Amazon DocumentDB'})


##Find the document that was previously written
x = col.find_one({'hello':'Amazon DocumentDB'})

##Print the result to the screen
print(x)

##Close the connection
client.close()

# user_id = "admin"


# # Replace these values with your DocumentDB details
# USERNAME = keys.document_db['USERNAME']
# PASSWORD = keys.document_db['PASSWORD']
# CLUSTER_ENDPOINT = keys.document_db['CLUSTER_ENDPOINT']
# PORT = keys.document_db['PORT']  # Default DocumentDB port
# DATABASE_NAME = "test"
# COLLECTION_NAME = "collection_1"

# def connect_to_documentdb(USERNAME = USERNAME,PASSWORD = PASSWORD,CLUSTER_ENDPOINT = CLUSTER_ENDPOINT,PORT = PORT):
#     """Establishes a connection to Amazon DocumentDB."""
#     try:
#         # Connect to the DocumentDB cluster
#         client_db = MongoClient(
#             f"mongodb://{USERNAME}:{PASSWORD}@{CLUSTER_ENDPOINT}:{PORT}/?ssl=true&replicaSet=rs0&readPreference=primary&retryWrites=false",
#             tlsAllowInvalidCertificates=True,  # DocumentDB uses self-signed certs
#             socketTimeoutMS=120000,
#             connectTimeoutMS=120000
#         )
#         print("Connected to Amazon DocumentDB successfully!",file=sys.stderr)
#         return client_db
#     except ConnectionFailure as e:
#         print(f"Connection to Amazon DocumentDB failed: {e}",file=sys.stderr)
#         return None

# def insert_data(client_db, data, DATABASE_NAME = DATABASE_NAME,COLLECTION_NAME = COLLECTION_NAME):
#     """Inserts data into the specified collection."""
#     try:
#         db = client_db[DATABASE_NAME]
#         collection = db[COLLECTION_NAME]
#         print(db,file=sys.stderr)
#         print(collection,file=sys.stderr)
#         # Insert a single document
#         if isinstance(data, dict):
#             print("identified data as dict",file=sys.stderr)
#             result = collection.insert_one(data)
#             print(f"Inserted document ID: {result.inserted_id}",file=sys.stderr)
#         # Insert multiple documents
#         elif isinstance(data, list):
#             result = collection.insert_many(data)
#             print(f"Inserted document IDs: {result.inserted_ids}",file=sys.stderr)
#         else:
#             print("Invalid data format. Please provide a dictionary or list of dictionaries.",file=sys.stderr)
#     except Exception as e:
#         print(f"An error occurred while inserting data: {e}",file=sys.stderr)

# client_db = connect_to_documentdb()

# document_upload = {
#                     'user_id' : "user_test",
#                     'session_id' : "123",
#                     'class' : "test_class",
#                     'subject' : "maths",
#                     'topic' : "math",
#                     'chapter' : "numbers",
#                     'llm_model' : "turbo",
#                     'temperature' : 0.4,
#                     'user_input' : "what is a test message",
#                     'llm_response' : "It can be anything"
#                 }
        
# if client_db:
#     insert_data(client_db, document_upload)  # Insert one document
#     client_db.close() 