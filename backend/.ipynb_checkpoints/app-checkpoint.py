from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import session
# from flask_session import Session
from flask import Flask, send_file, Response
import subprocess
from io import BytesIO
from openai import OpenAI
import uuid
import sys
import logging
import re
import base64
import mermaid
import requests
import io
import json
# import streamlit as st

import os
# import bs4
# from langchain.vectorstores import FAISS
# from langchain import hub
from langchain_chroma import Chroma
# from langchain_community.document_loaders import WebBaseLoader
# from langchain_community.document_loaders import PyPDFLoader
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# import pytesseract
from PIL import Image
import io

from prompt_inputs import custom_prompts
from lesson_mapping import lesson_mapping
from keys import keys
# from output_formats.flow_chart_image_test import mermaid_to_image_kroki

import os
from google.cloud import vision
from sympy import sympify, simplify

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from datetime import datetime

user_id = "admin"
# conv_num = 1


# Replace these values with your DocumentDB details
USERNAME = keys.document_db['USERNAME']
PASSWORD = keys.document_db['PASSWORD']
CLUSTER_ENDPOINT = keys.document_db['CLUSTER_ENDPOINT']
PORT = keys.document_db['PORT']  # Default DocumentDB port
DATABASE_NAME = "chat_history"
COLLECTION_NAME = "collection_1"

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



# Automatically uses GOOGLE_APPLICATION_CREDENTIALS
client = vision.ImageAnnotatorClient()

os.environ["OPENAI_API_KEY"] = keys.open_ai_keys["key_1"]


# app = Flask(__name__, static_folder='../frontend', static_url_path='/')
app = Flask(__name__)
CORS(app,supports_credentials=True, origins="*")
# CORS(app,supports_credentials=True, origins="http://localhost:3001")
mbue_maps_api_base_url = os.getenv("MBUE_MAPS_API_BASE_URL", "http://localhost:5001")  # Default to local testing

app.secret_key='901ae29d4392f060c6ff633325a2598c'

# app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem-based session storage
# app.config['SESSION_PERMANENT'] = False    # Session does not expire after browser close
# Session(app)


@app.route('/submit-name', methods=['POST'])
def submit_name():
    data = request.get_json()

    print(f"Received data: {data}",file=sys.stderr)

    print("session in submit name", session, file = sys.stderr)
    
    
    name = data.get('name')
    if name:
        session['user_name'] = name
        print("session in submit name", session, file = sys.stderr)
        print(f"Received name: {name}",file=sys.stderr)
        return jsonify({'message': 'Name received successfully!'}), 200
    return jsonify({'error': 'Name is required!'}), 400


@app.route('/submit-data', methods=['POST'])
def submit_data():
    # global clss, sub, topic
    data = request.get_json()  # Get the data from the POST request
    # clss = data.get('grades')
    # sub = data.get('subject')
    # topic = data.get('topic')
    
    
    session['clss'] = data.get('grades')
    session['sub'] = data.get('subject')
    session['topic'] = data.get('topic')
    session['chapter'] = data.get('chapter')
    


    # You can process the data here (e.g., save to a database)
    # print(f"Received class: {clss}, subject: {sub}, topic:{topic}")
    print(f"Received class: {session['clss']}, subject: {session['sub']}, topic:{session['topic']}, chapter: {session['chapter']}")
    # Logic to fetch or generate the PDF
    pdf_path = f"ncert/{session['clss']}/{session['sub']}/{lesson_mapping.details[session['clss']][session['sub']][session['chapter']]}"
    print("pdf path extracted -----------",pdf_path,file = sys.stderr)
    if not os.path.exists(pdf_path):
        # Generate PDF if it doesn't exist (placeholder logic)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(b"Sample PDF Content")
    # Send a response back to the React frontend
    # return jsonify({'message': 'Data received successfully', 'class': session['clss'], 
    #                 'subject': session['sub'], 'topic': session['topic'],
    #                 'chapter' : session['chapter']})
    # Serve the PDF file
    return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{session['chapter']}.pdf")
    # return jsonify({'message': 'Data received successfully', 'class': clss, 'subject': sub, 'topic': topic})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    # OCR
    if 'image' in request.files:
        # return jsonify({'error': 'No image file provided'}), 400
        print("reched image page ------", file = sys.stderr)
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
        print("OCR data ------", ocr_text, file=sys.stderr)

        return jsonify({'ocr_text': ocr_text})
    data = request.json
    user_message = data.get('message')
    dropdown_option = data.get('dropdownOption', 'general Query')
    print("dropdown_option ------------------",dropdown_option,file = sys.stderr)

    client_db = connect_to_documentdb()
    
    
    # Simple bot response logic
    if user_message:
        # Initialize embeddings
        embeddings = OpenAIEmbeddings()
        clss = session.get('clss')
        sub = session.get('sub')
        topic = session.get('topic')
        chapter = session.get('chapter')
        user_name = session.get('user_name')
        
        print("user_name-------", user_name, file = sys.stderr)
        
        # print(clss,sub,topic,file=sys.stderr)

        # load from ChromaDB
        db3 = Chroma(persist_directory="vector_DB/ncert_cw/"+clss+"/"+sub+"/"+topic+"/"+chapter+"/", embedding_function=embeddings)
        db3.get() 

        # print("length:",len(db3.get()['ids']))
        llm_model = "gpt-4o"
        temperature = 0.3
        # llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5)
        llm = ChatOpenAI(model=llm_model, temperature=temperature)
        
        # loader=TextLoader("C:/personal/ncert/class_9/maths\\iemh101.txt",encoding = 'UTF-8')
        # docs = loader.aload()
        
        # retriever = docs
        retriever = db3.as_retriever()

        from langchain.chains import create_history_aware_retriever
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


        prompt_for_db_extraction = custom_prompts.db_extract_prompt['chapter_details']

        if "easy explanation" in dropdown_option:
            prompt_for_db_extraction = custom_prompts.db_extract_prompt['chapter_details']
        elif "answer the question" in dropdown_option:
            prompt_for_db_extraction = custom_prompts.db_extract_prompt['chapter_details']
        elif "I did not understand" in dropdown_option:
            prompt_for_db_extraction = custom_prompts.db_extract_prompt['chapter_details']

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
        
        # Log or print the retrieved documents
        # app.logger.info('Retrieved Documents from History Aware Retriever: %s', relevant_documents)
        # print('Retrieved Documents from History Aware Retriever: ', relevant_documents,file=sys.stderr)

        # Write relevant documents to a text file
        with open("relevant_documents.txt", "w", encoding='utf-8') as file:
            if isinstance(relevant_documents, list):  # Check if it's a list of documents
                for doc in relevant_documents:
                    file.write(f"{doc}\n")  # Write each document on a new line
            else:
                file.write(f"{relevant_documents}\n")  # Handle the case where it's not a list


        from langchain.chains import create_retrieval_chain
        from langchain.chains.combine_documents import create_stuff_documents_chain

        system_prompt = custom_prompts.llm_system_prompt['question_answer_from_chapter']
        
        if "Rewrite in simple words" in dropdown_option:
            print("I am in easy explanation ---------",file=sys.stderr)
            system_prompt = custom_prompts.llm_system_prompt['rewrite_in_simple_words']
        elif "answer the question" in dropdown_option and "maths" in sub :
            print("I am in solve the question ---------",file=sys.stderr)
            system_prompt = custom_prompts.llm_system_prompt['answer_question_maths']
        elif "answer the question" in dropdown_option :
            print("I am in answer the question ---------",file=sys.stderr)
            system_prompt = custom_prompts.llm_system_prompt['answer_question']
        elif "I did not understand" in dropdown_option:
            print("I am in I did not understand the question ---------",file=sys.stderr)
            system_prompt = custom_prompts.llm_system_prompt['did_not_understand']
        elif "Analyze text" in dropdown_option:
            print("I am in Analyze text -----------------",file=sys.stderr)
            system_prompt = custom_prompts.llm_system_prompt['analyze_the_text']
        elif "Correct the answer" in dropdown_option:
            print("I am in Correct the answer ---------",file=sys.stderr)
            system_prompt = custom_prompts.llm_system_prompt['correct_the_answer']
        elif "Help me remember" in dropdown_option:
            print("I am in Help me remember ---------",file=sys.stderr)
            system_prompt = custom_prompts.llm_system_prompt['help_me_remember']


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


        from langchain_core.chat_history import BaseChatMessageHistory
        from langchain_core.runnables.history import RunnableWithMessageHistory
        from langchain_community.chat_message_histories import ChatMessageHistory
        store = {}


        def get_session_history(session_id: str) -> BaseChatMessageHistory:
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]
        


        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id  # Store in Flask session
        app.logger.info('Session ID: ')
        app.logger.info(session_id)
        print("session_id------------------------", session_id, file = sys.stderr)

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
        # print("The session ID is: ",session_id, file=sys.stderr)
        
        current_time = datetime.now()
        document_upload = {
                            'user_id' : user_name,
                            'session_id' : session_id,
                            'datetime' : current_time,
                            'class' : clss,
                            'subject' : sub,
                            'topic' : topic,
                            'chapter' : chapter,
                            'llm_model' : llm_model,
                            'temperature' : temperature,
                            "context_filter" : dropdown_option,
                            'user_input' : user_message,
                            'llm_response' : response
                        }
        
        if client_db:
            insert_data(client_db, document_upload)  # Insert one document
            # conv_num += 1
            client_db.close() 
            
            
        if "flow chart" in user_message:
            response = response.replace("```json","")
            response = response.replace("```","")
            print("response",response,file = sys.stderr)
            print("response type",type(response),file = sys.stderr)
            # print("response",response,file = sys.stderr)
            # response = response.replace("'", '"')
            response = json.loads(response)
            
            # Create the mindmap
            mindmap_creation_url = f"{mbue_maps_api_base_url}/mindmaps"
            # print("mindmap_creation_url -------------------------",file = sys.stderr)
            # print(mindmap_creation_url,file = sys.stderr)
            create_response = requests.post(mindmap_creation_url, json=response)
            # print("create_response -------------------------",file = sys.stderr)
            # print(create_response,file = sys.stderr)
            mindmap_id = create_response.json().get("id")
            # mindmap_id = session_id
            # print("mindmap_id -------------------------",file = sys.stderr)
            # print(mindmap_id,file = sys.stderr)
            graphviz_api_url = f"{mbue_maps_api_base_url}/mindmaps/{mindmap_id}/render"
            print("graphviz_api_url",graphviz_api_url, file = sys.stderr)
            api_response = requests.get(graphviz_api_url, stream=True)
            # print(api_response,file = sys.stderr)
            image = api_response.json().get("img")
            image_data = base64.b64decode(image)
            image_io = BytesIO(image_data)
            image_io.seek(0)
            
            return send_file(image_io, mimetype='image/png')
            
        else:
            # response = convert_mixed_expression(response)
            return jsonify({'response': response})
        
                 
            

            


    else:
        response = "I didn't catch that."
    
    # return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
