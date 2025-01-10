from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import session
from flask_session import Session
from flask import Flask, send_file, Response
import subprocess
from io import BytesIO
from openai import OpenAI
import uuid
import sys
import logging
import re
import base64
import requests
import io
import json

from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import NoCredentialsError

import tempfile
import numpy as np
import faiss

from pymongo import MongoClient

import os

from langchain_community.vectorstores import FAISS

from langchain_chroma import Chroma

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from langchain_community.document_loaders import TextLoader


from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# import pytesseract
from PIL import Image
import io

from prompt_inputs import custom_prompts
from keys import keys
from scenarios import scenarios


import os
from google.cloud import vision
from sympy import sympify, simplify

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from datetime import datetime

import redis
import pickle  # To serialize/deserialize Python objects
from typing import Dict

user_id = "admin"



# Fetch links from google search
def fetch_links(context):
    search_query = f"{context} site:edu OR site:gov"
    api_key = keys.google_search['API_KEY']
    cse_id = keys.google_search['CSE_ID']
    url = f"https://www.googleapis.com/customsearch/v1?q={search_query}&key={api_key}&cx={cse_id}"
    response = requests.get(url)
    results = response.json()
    links = [
        f"[{item['title']}]({item['link']})"
        for item in results.get('items', [])[:3]
    ]
    return links

# Chat history to be saved in session
class RedisBackedChatMessageHistory:
    def __init__(self, session_id):
        self.session_id = session_id
        self.messages = []

    def add_messages(self, message):
        self.messages.append(message)
        if len(self.messages)>3:
            self.messages = self.messages[-3:]
        # print("redit messages----------", self.messages,file = sys.stderr)

    def to_redis(self):
        return pickle.dumps(self)

    @classmethod
    def from_redis(cls, data):
        return pickle.loads(data)

# Initialize Redis client
redis_client = redis.StrictRedis(host="redis", port=6379, decode_responses=False)

def get_session_history(session_id: str) -> RedisBackedChatMessageHistory:
    
    redis_key = f"session:{session_id}"
    history_data = redis_client.get(redis_key)
    if history_data:
        return RedisBackedChatMessageHistory.from_redis(history_data)
    else:
        return RedisBackedChatMessageHistory(session_id)
        

def save_session_history(session_id: str, history: RedisBackedChatMessageHistory):
    redis_key = f"session:{session_id}"
    redis_client.set(redis_key, history.to_redis())



# Replace these values with your MongoDB details
USERNAME = keys.document_db['USERNAME']
PASSWORD = keys.document_db['PASSWORD']
CLUSTER_ENDPOINT = keys.document_db['CLUSTER_ENDPOINT']
PORT = keys.document_db['PORT']  # Default DocumentDB port
DATABASE_NAME = "chat_history"
COLLECTION_NAME = "collection_1"

# connect to mongodb
def connect_to_documentdb(USERNAME = USERNAME,PASSWORD = PASSWORD,CLUSTER_ENDPOINT = CLUSTER_ENDPOINT,PORT = PORT):
    """Establishes a connection to Amazon DocumentDB."""
    try:
        # Connect to the DocumentDB cluster
        client_db = MongoClient(
            
            f"mongodb+srv://{USERNAME}:{PASSWORD}@{CLUSTER_ENDPOINT}/",
            
        )
        print("Connected to MongoDB successfully!",file=sys.stderr)
        return client_db
    except ConnectionFailure as e:
        print(f"Connection to  Mongodb failed: {e}",file=sys.stderr)
        return None

# Insert data into mongoDB
def insert_data(client_db, data, DATABASE_NAME = DATABASE_NAME,COLLECTION_NAME = COLLECTION_NAME):
    """Inserts data into the specified collection."""
    try:
        db = client_db[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        print(db,file=sys.stderr)
        print(collection,file=sys.stderr)
        # Insert a single document
        if isinstance(data, dict):
            print("identified data as dict",file=sys.stderr)
            result = collection.insert_one(data)
            print(f"Inserted document ID: {result.inserted_id}",file=sys.stderr)
        # Insert multiple documents
        elif isinstance(data, list):
            result = collection.insert_many(data)
            print(f"Inserted document IDs: {result.inserted_ids}",file=sys.stderr)
        else:
            print("Invalid data format. Please provide a dictionary or list of dictionaries.",file=sys.stderr)
    except Exception as e:
        print(f"An error occurred while inserting data: {e}",file=sys.stderr)

# Update feedback that is provided to us by user
def update_feedback(client_db, u_id, feedback, DATABASE_NAME = DATABASE_NAME, COLLECTION_NAME = COLLECTION_NAME):
    """Updates the feedback of an existing document identified by u_id."""
    try:
        db = client_db[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        print(db, file=sys.stderr)
        print(collection, file=sys.stderr)
        
        # Update the feedback field of the document with the matching u_id
        result = collection.update_one(
            {'u_id': u_id},  # Filter to find the document based on u_id
            {'$set': {'feedback': feedback}}  # Update the feedback field
        )

        if result.matched_count > 0:
            print(f"Updated document with u_id: {u_id} to feedback: {feedback}", file=sys.stderr)
        else:
            print(f"No document found with u_id: {u_id}. No update performed.", file=sys.stderr)

    except Exception as e:
        print(f"An error occurred while updating data: {e}", file=sys.stderr)


UPLOAD_FOLDER = './vector_DB'
ALLOWED_EXTENSIONS = {'pdf','jpg','jpeg','png','txt'}

# Utility: Check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Utility: Perform OCR on an image and extract text
def perform_ocr(image_path):
    # image = Image.open(image_path)
    # text = pytesseract.image_to_string(image)
    # content = image_path.read()
    with open(image_path, "rb") as image_file:
        content = image_file.read()  # Read the image as bytes

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)


    # Extract text
    ocr_text = response.full_text_annotation.text

    # simplified_expr = simplify(sympify(ocr_text))
    # print("OCR data ------", ocr_text, file=sys.stderr)
    return ocr_text

# Utility: Extract images from a PDF and perform OCR
def extract_text_from_input(input_paths):
    # print("path_in_extract text from input",input_paths, file=sys.stderr)

    if input_paths.endswith(".pdf"):
    
        pdf_reader = PdfReader(input_paths)
        tot_pages = len(pdf_reader.pages)
        print("Total pages:", len(pdf_reader.pages), file=sys.stderr)
        if tot_pages > 30:
            document_text = []
        else:
            document_text = ""

        for page_num, page in enumerate(pdf_reader.pages):
            # Extract text
            try:
                text = page.extract_text()
            except:
                text = None

            if not text:  # Perform OCR if no text found
                print("OCR for page", page_num + 1, file=sys.stderr)
                images = convert_from_path(input_paths, first_page=page_num + 1, last_page=page_num + 1)
                ocr_text = ""
                for image_index, image in enumerate(images):
                    image_filename = f"{input_paths}_page_{page_num}_img_{image_index}.png"
                    image.save(image_filename)  # Save image for OCR processing
                    try:
                        ocr_text += perform_ocr(image_filename)
                    finally:
                        os.remove(image_filename)  # Clean up temp files
                text = ocr_text

            if tot_pages > 30:
                document_text.append({'file_name':input_paths, 'page_number': page_num + 1, 'text': text})
            else:
                document_text += str(page_num + 1)+ "\n" + text
    elif input_paths.endswith(".jpg") or input_paths.endswith(".jpeg") or input_paths.endswith(".png"):
        # print("input_paths--------",input_paths, file=sys.stderr)
        if len(input_paths) > 300:
            document_text = []
        else:
            document_text = ""
        ocr_text = ""
        path = input_paths
        # for path in input_paths:
        ocr_text += perform_ocr(path)
        text = ocr_text
        if len(input_paths) > 300:
            document_text.append({'file_name':input_paths, 'page_number': page_num + 1, 'text': text})
        else:
            document_text +=  "\n" + text
    elif input_paths.endswith(".txt"):
        if len(input_paths) > 300:
            document_text = []
        else:
            document_text = ""
        path = input_paths
        # for path in input_paths:
        with open(input_paths, 'r') as file:
            text = file.read()
        if len(input_paths) > 300:
            document_text.append({'file_name':input_paths, 'page_number': page_num + 1, 'text': text})
        else:
            document_text +=  "\n" + text
        
            

    return document_text

# Utility: Segment content by chapters
def segment_into_chapters(document_text):
    chapters = {}
    current_chapter = None
    current_content = []

    for page in document_text:
        page_text = page['text']
        if "Chapter" in page_text or "Lesson" in page_text:  # Detect chapter/lesson start
            if current_chapter:
                chapters[current_chapter] = "\n".join(current_content)
                current_content = []
            chapter_header = page_text.split("\n")[0].strip()  # Assume first line is header
            current_chapter = chapter_header
        current_content.append(page_text)

    if current_chapter:
        chapters[current_chapter] = "\n".join(current_content)
    return chapters

# Utility: Store chapters in mongoDB
def store_chapters_in_mongodb(chapters,s3_url):
    # Initialize OpenAI embeddings (make sure you have a valid API key or environment variable set)
    embeddings = OpenAIEmbeddings()

    client_upload = connect_to_documentdb()

    db = client_upload['vector_db']
    collection = db['my_uploads']
    u_id = str(uuid.uuid4())

    # Prepare the list of texts, metadata, and IDs to add to the vector store
    # texts = []
    
    if isinstance(chapters, list):
        texts = chapters
        
    else:
        texts = [chapters]
    # print("extracted text example",texts[1],file = sys.stderr)
    # metadatas = []
    # ids = [str(chapter['page_number']) for chapter in chapters]

    for i in range(len(texts)):
        
        if isinstance(chapters, list):
            page = texts[i]['page_number']
            
            text_final = texts[i]['text']

            
            
            
        else:
            page = "all"
            text_final = texts[i]
        
        
        
        embedding = embeddings.embed_query(text_final)

        document_to_store = {
                            "u_id": u_id,
                            "s3_url" : s3_url,
                            "page" : page,
                            "text": text_final,
                            "embedding": embedding
                            }
        collection.replace_one({"s3_url" : s3_url, "page" : page}, document_to_store, upsert=True)  # Upsert ensures no duplication

    



# Automatically uses GOOGLE_APPLICATION_CREDENTIALS
client = vision.ImageAnnotatorClient()

os.environ["OPENAI_API_KEY"] = keys.open_ai_keys["key_1"]

os.environ["AWS_ACCESS_KEY_ID"] = keys.aws_keys["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = keys.aws_keys["AWS_SECRET_ACCESS_KEY"]
os.environ["AWS_DEFAULT_REGION"] = keys.aws_keys["AWS_DEFAULT_REGION"]


# app = Flask(__name__, static_folder='../frontend', static_url_path='/')
app = Flask(__name__)
# Redis configuration for Flask-Session
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_REDIS"] = redis.StrictRedis(host='redis', port=6379, db=0)
# app.config['SESSION_COOKIE_SAMESITE'] = 'None'
# app.config['SESSION_COOKIE_SECURE'] = True
Session(app)

CORS(app,supports_credentials=True, origins="*")
# CORS(app,supports_credentials=True, origins="http://localhost:3001")

app.secret_key='901ae29d4392f060c6ff633325a2598c'

# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# # Ensure the upload directory exists
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# AWS S3 Configuration
S3_BUCKET= "formulations-myuploads"
S3_BUCKET_1 = 'formulations-commons'

S3_REGION = "ap-south-1"

s3_client = boto3.client('s3',region_name=S3_REGION)

# Helper function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




@app.route('/ocr-image', methods=['POST'])
def ocr_image():
    image_file = request.files['file']
    # image = Image.open(image_file)

    # # Perform OCR
    # ocr_text = pytesseract.image_to_string(image)
    # print("OCR data ------",ocr_text, file = sys.stderr)

    
    content = image_file.read()

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)


    # Extract text
    ocr_text = response.full_text_annotation.text
    session["input_context"] = ocr_text

    # simplified_expr = simplify(sympify(ocr_text))
    # print("OCR data ------", ocr_text, file=sys.stderr)

    return jsonify({'ocr_text': ocr_text})



@app.route('/list-folders', methods=['GET'])
def list_folders():
    user_name = session.get('user_name')
    # print("user_name",user_name,file = sys.stderr)
    prefix = request.args.get('prefix', '')  # optional, default to root
    session['prefix'] = prefix
    if prefix == '':
        prefix_my = f"{user_name}/"
    else:
        prefix_my = prefix
    # print("prefix",prefix,file = sys.stderr)
    
    # Root folder based on username
    user_root = f"{user_name}/"
    my_uploads_folder = f"{user_name}/my_uploads/"
    # print("user_root",user_root,file = sys.stderr)

    def ensure_root_folder(bucket_name, user_root):
        # Check if the user's root folder exists
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=user_root, Delimiter='/')
        if not response.get('Contents') and not response.get('CommonPrefixes'):
            # Root folder does not exist; create it
            s3_client.put_object(Bucket=bucket_name, Key=f"{user_root}placeholder.txt", Body="")
            print(f"Created root folder for user: {user_name} in bucket: {bucket_name}")
    
    def get_folders_and_files(bucket_name, prefix):
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
        folders = [item.get('Prefix') for item in response.get('CommonPrefixes', [])]
        files = [item.get('Key') for item in response.get('Contents', []) if item.get('Key') != prefix]
        return folders, files
    

    # Ensure user root folder exists in both buckets
    ensure_root_folder(S3_BUCKET, my_uploads_folder)
    # Adjust prefix to start with user's root folder
    full_prefix = f"{user_root}{prefix}" if prefix else user_root
    
    # Fetch from both buckets
    folders1, files1 = get_folders_and_files(S3_BUCKET, prefix_my)
    folders2, files2 = get_folders_and_files(S3_BUCKET_1, prefix)

    # print("folders1",folders1,file = sys.stderr)
    # print("files1",files1,file = sys.stderr)

    return jsonify({
        'folders': folders1 + folders2,  # Combine folder results
        'files': files1 + files2        # Combine file results
    })

@app.route('/create-folder', methods=['POST'])
def create_folder():
    folder_name = request.json.get('folder_name')
    # print("folder_name",folder_name,file = sys.stderr)
    if not folder_name.endswith('/'):
        folder_name += '/'
    # print("session in create folder", session, file = sys.stderr)
    user_name = session.get('user_name')
    # print("user_name in create-folder------",user_name,file = sys.stderr)
    # folder_name = f"{user_name}/{folder_name}"
    # print("folder_name",folder_name,file = sys.stderr)
    if user_name not in ['admin', 'charan'] and folder_name.startswith("commons"):
        return jsonify({'message': f'Cannot create folder here. Only changes in your personal folder is allowed'})
    if folder_name.startswith("commons"):
        s3_buck = S3_BUCKET_1
    else:
        s3_buck = S3_BUCKET
    s3_client.put_object(Bucket=s3_buck, Key=folder_name)
    return jsonify({'message': f'Folder {folder_name} created successfully!'})


@app.route('/select-file', methods=['POST'])
def select_file():
    # Get file keys from the request args (assuming it is a comma-separated list)
    file_keys = request.json.get('file_keys')
    
    # Ensure file_keys is not empty
    if not file_keys:
        return jsonify({'error': 'No file keys provided'}), 400
    
    file_keys = file_keys.split(',')  # Convert the comma-separated string to a list
    # print("file_keys",file_keys, file=sys.stderr)

    urls = []
    
    try:
        for file_key in file_keys:
            if file_key.startswith("commons"):
                s3_buck = S3_BUCKET_1
            else:
                s3_buck = S3_BUCKET
            
            # Generate pre-signed URL for the file_key
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': s3_buck, 'Key': file_key},
                ExpiresIn=3600
            )
            urls.append(url)  # Add the URL to the list

        # Generate a new session ID and store it in the session
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        session['urls'] = urls  # Store the URLs list in the session

        return jsonify({'urls': urls})  # Return the list of URLs as a response
    
    except NoCredentialsError:
        return jsonify({'error': 'Credentials not available'}), 403

@app.route('/submit-name', methods=['POST'])
def submit_name():
    data = request.get_json()

    # print(f"Received data: {data}",file=sys.stderr)

    # print("session in submit name", session, file = sys.stderr)
    
    
    name = data.get('name')
    if name:
        session['user_name'] = name
        session['state'] = 'ready'
        # print("session in submit name", session, file = sys.stderr)
        # print(f"Received name: {name}",file=sys.stderr)
        return jsonify({'message': 'Name received successfully!'}), 200
    return jsonify({'error': 'Name is required!'}), 400

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()

    print(f"Received data: {data}",file=sys.stderr)

    # print("session in submit feedback", session, file = sys.stderr)
    
    
    u_id = data.get('u_id')
    feedback = data.get('feedback')

    client_db = connect_to_documentdb()
    if client_db:
        update_feedback(client_db, u_id, feedback)
        client_db.close()
    
    session['u_id'] = u_id
    session['feedback'] = feedback
    # print("session in submit feedback", session, file = sys.stderr)
    # print(f"Received u_id: {u_id}",file=sys.stderr)
    # print(f"Received feedback: {feedback}",file=sys.stderr)
    return jsonify({'message': 'u_id received successfully!'}), 200
    # return jsonify({'error': 'Name is required!'}), 400

@app.route('/upload-file', methods=['POST'])
def upload_file():
    # Check if the post request has a file
    # print("request_files in upload-file",request.files, file = sys.stderr)
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400
    # Get the custom filename from the request, if provided (default to original filename if not)
    new_filename = request.form.get('filename', file.filename)  
    if file and allowed_file(file.filename):
        filename = secure_filename(new_filename)  # Use the new filename
        # filename = secure_filename(file.filename)
        # print(session.get('prefix'), file = sys.stderr)
        user_name = session.get('user_name')
        user_folder = session.get('prefix', user_name)  # Get the folder prefix
        
        # Define folder structure (e.g., user-submitted path in form)
        # user_folder = request.form.get('folder', 'default-folder')
        s3_key = f"{user_folder}{filename}"  # Define S3 path
        # print("s3_key--------------",s3_key, file = sys.stderr)

        try:
            if s3_key.startswith("commons"):
                s3_buck = S3_BUCKET_1
            else:
                s3_buck = S3_BUCKET
            # Upload file to S3
            # print("s3_buck--------------",s3_buck, file = sys.stderr)
            s3_client.upload_fileobj(
                file,
                s3_buck,
                s3_key,
                ExtraArgs={"ContentType": file.content_type}
            )
            # Construct S3 URL
            # s3_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
            s3_url = f"https://{s3_buck}.s3.amazonaws.com/{s3_key}"
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
        # Download file back using the S3 URL
        response = requests.get(s3_url, stream=True)
        response.raise_for_status()
        upload_file_name = file.filename
        # print("upload_file_name--------------",upload_file_name, file = sys.stderr)
        file_extension = os.path.splitext(upload_file_name)[1]
        
        # Temporarily save the file locally to perform OCR
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        # Extract text and perform OCR
        document_text = extract_text_from_input(temp_file_path)
        # print("document text extracted -----------",document_text,file = sys.stderr)

        # Segment into chapters or lessons
        # chapters = segment_into_chapters(document_text)

        # Store chapters in ChromaDB
        try:
            # store_chapters_in_chromadb(document_text)
            store_chapters_in_mongodb(document_text, s3_url)
            os.remove(temp_file_path)  # Cleanup uploaded file
            return jsonify({"message": "File uploaded and processed successfully!","folder":user_folder}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to store data in mongoDB: {str(e)}"}), 500

    return jsonify({"error": "Invalid file format"}), 400

@app.route('/chatbot', methods=['POST'])
def chatbot():
    # OCR
    if 'image' in request.files:
        # return jsonify({'error': 'No image file provided'}), 400
        # print("reched image page ------", file = sys.stderr)
        # print("session in chatbot 1", session, file = sys.stderr)
        image_file = request.files['image']
        # image = Image.open(image_file)

        # # Perform OCR
        # ocr_text = pytesseract.image_to_string(image)
        # print("OCR data ------",ocr_text, file = sys.stderr)

        
        content = image_file.read()

        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)


        # Extract text
        ocr_text = response.full_text_annotation.text

        # simplified_expr = simplify(sympify(ocr_text))
        # print("OCR data ------", ocr_text, file=sys.stderr)

        return jsonify({'ocr_text': ocr_text})
    data = request.json
    user_message = data.get('message')
    dropdown_option = data.get('dropdownOption', 'general Query')
    u_id = data.get('u_id')
    temperature =  data.get('temperature')
    print("temperature ------------------",temperature,file = sys.stderr)
    
    

    client_db = connect_to_documentdb()
    
    
    # Simple bot response logic
    if user_message:
        # Initialize embeddings
        embeddings = OpenAIEmbeddings()
        
        user_name = session.get('user_name')
        pdf_url = session.get('urls')
        

        pdf_urls = []
        for url_key in pdf_url:
            url_key = url_key.split('?')[0]
            pdf_urls.append(url_key)

        pdf_url = pdf_url[0].split('?')[0]

        print("pdf_url",pdf_url, file = sys.stderr)
        
        
        # llm_model = "gpt-4o"
        # llm_model = "gpt-3.5-turbo"
        llm_model = "gpt-4o-mini"
        if 'gpt-4o' in dropdown_option:
            llm_model = "gpt-4o"
        # temperature = 0.3
        api_key = keys.open_ai_keys["key_1"]


        # This is to have option to categorize the type of question asked and then decide prompt based on it
        # category = scenarios.categorize_text(api_key, user_message, "gpt-4")
        

        # load from ChromaDB
        # db3 = Chroma(persist_directory="vector_DB/ncert_cw/"+clss+"/"+sub+"/"+topic+"/"+chapter+"/", embedding_function=embeddings)
        # db3.get() 

        # load from MongoDB
        client_db = MongoClient(
            
            f"mongodb+srv://{USERNAME}:{PASSWORD}@{CLUSTER_ENDPOINT}/",
            
        )

        db = client_db["vector_db"]
        collection = db["my_uploads"]

        
        documents = []
        all_embeddings = []
        print("important pdf urls--------",pdf_urls,file=sys.stderr)

        filter_query = {
                            's3_url': {'$in': pdf_urls}
                        }
        for document in collection.find(filter_query):
            # Assumes the documents have a text field, but adjust based on your structure
            # print("Inside collection",document, file = sys.stderr)
            text_content = document['text']
            embedds = document['embedding']
            # documents += "\n" + text_content
            documents.append(text_content)
            all_embeddings.append(embedds)

        text_embeddings = list(zip(documents, all_embeddings))
        

        db3 = FAISS.from_embeddings(text_embeddings=text_embeddings, embedding = embeddings)

        # llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5)
        llm = ChatOpenAI(model=llm_model, temperature=temperature)
        retriever = db3.as_retriever()

        from langchain.chains import create_history_aware_retriever
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


        prompt_for_db_extraction = custom_prompts.db_extract_prompt['generate_standalone_question']
        
        

        contextualize_q_system_prompt=prompt_for_db_extraction
        
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )

        # Get the relevant documents based on the user's message and chat history
        relevant_documents = history_aware_retriever.invoke({"input": user_message}) 
        

        # Write relevant documents to a text file
        with open("relevant_documents.txt", "w", encoding='utf-8') as file:
            if isinstance(relevant_documents, list):  # Check if it's a list of documents
                for doc in relevant_documents:
                    file.write(f"{doc}\n")  # Write each document on a new line
            else:
                file.write(f"{relevant_documents}\n")  # Handle the case where it's not a list


        from langchain.chains import create_retrieval_chain
        from langchain.chains.combine_documents import create_stuff_documents_chain

        

        input_context = session.get('input_context')

        print("input_context in chatbot 4", input_context, file = sys.stderr)
        

        
        system_prompt = custom_prompts.llm_system_prompt['research_assistant'] + custom_prompts.llm_system_prompt['response_beautification']

        if input_context is not None :
            system_prompt = system_prompt + custom_prompts.llm_system_prompt['response_format'] + " " + input_context
        qa_system_prompt = system_prompt+"""{context}"""
        
        # print("The qa_system_prompt is: ",qa_system_prompt, file=sys.stderr)

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )


        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        # print("session in chatbot 4 after create retrieval chain", session, file = sys.stderr)

        from langchain_core.chat_history import BaseChatMessageHistory
        from langchain_core.runnables.history import RunnableWithMessageHistory
        from langchain_community.chat_message_histories import ChatMessageHistory


        session_id = session.get('session_id')
        if not session_id:
            # session_id = str(uuid.uuid4())
            session['session_id'] = session_id  # Store in Flask session
        app.logger.info('Session ID: ')
        app.logger.info(session_id)

        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )


        def chat_with_bot(user_input):
            output = conversational_rag_chain.invoke(
                {"input": user_input},
                config={
                    "configurable": {"session_id": session_id}
                },  # constructs a key "abc123" in `store`.
            )
            answer= output["answer"]
            # doc = output["context"]
            
            return answer,output
        
        

        response,output = chat_with_bot(user_message)


        response = re.sub(r"\\\[([\s\S]*?)\\\]", lambda match: "\[" + " ".join(match.group(1).split()) + "\]", response, flags=re.DOTALL)
        response = re.sub(r"$([\s\S]*?)$", lambda match: "$" + " ".join(match.group(1).split()) + "$", response, flags=re.DOTALL)
        response = re.sub(r"$$([\s\S]*?)$$", lambda match: "$$" + " ".join(match.group(1).split()) + "$$", response, flags=re.DOTALL)
        response = re.sub(r"\\\(([\s\S]*?)\\\)", lambda match: "\(" + " ".join(match.group(1).split()) + "\)", response, flags=re.DOTALL)
        response = response.replace("$$$$$$","")

        external_links = fetch_links(user_message)
        links_text = "\n\n".join(external_links)
        

        # Combine response and links
        response = f"{response}\n\n### Additional Resources:\n\n{links_text}"

        history = get_session_history(session_id)
        history.add_messages({"role": "user", "content": user_message})
        history.add_messages({"role": "ai", "content":response})
        save_session_history(session_id, history)
        

        

        
        current_time = datetime.now()
        document_upload = {
                            'user_id' : user_name,
                            'session_id' : session_id,
                            'datetime' : current_time,
                            'llm_model' : llm_model,
                            'temperature' : temperature,
                            "context_filter" : dropdown_option,
                            'user_input' : user_message,
                            'llm_response' : response,
                            'u_id' : u_id,
                            "feedback" : "Neutral"
                        }
        
        if client_db:
            insert_data(client_db, document_upload)  # Insert one document
            # conv_num += 1
            client_db.close() 
            
        return jsonify({'response': response})
        

    else:
        response = "I didn't catch that."
    
    # return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
