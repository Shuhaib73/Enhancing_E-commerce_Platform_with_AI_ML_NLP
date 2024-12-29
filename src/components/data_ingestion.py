
import os 
import sys
import time 
import logging
from from_root import from_root
from datetime import datetime

import pandas as pd 
from dotenv import load_dotenv

import pinecone
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from langchain_community.document_loaders import DataFrameLoader
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

from src.configuration.mongo_db_connection import product_db
from src.logger import configure_logger

from src.exception import MyException

load_dotenv()

logger = configure_logger('data_ingestion')

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=pinecone_api_key)




class DataIngestion:
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path

    def ingest_data_to_mongo(self):
        '''
        Ingest data from csv file to mongodb with logging.
        '''
        try:

            logger.info(f"Data ingestion started for file: {self.csv_file_path} ")

            # Read CSV file into DataFrame
            df = pd.read_csv(self.csv_file_path, index_col=0)

            # Convert DataFrame into a list of dictionaries (records)
            df_records = df.to_dict('records')

            if not df_records:
                logger.warning("No records found in CSV.")
                
            # Insert the records into a MongoDB Collection
            product_db.products.insert_many(df_records)

            logger.info(f"Successfully ingested {len(df_records)} records into MongoDB.")

        except pd.errors.EmptyDataError as e:
            # Handle empty csv file specifically 
            error_message = 'CSV File is empty.'
            logger.error(error_message)
            raise MyException(error_message, sys) from e
        
        except Exception as e:
            # General exception handling with custom error class
            logger.error(f"An error occurred during data ingestion.{e}")
            raise MyException(e, sys) from e
    

    def create_index(self, index_name):

        if index_name in pc.list_indexes().names():
            logger.info(f"Index already exists: {index_name} - Pinecone\n")

            index = pc.Index(index_name)
            logger.info(f"here is the index description: {index.describe_index_stats()}")

        else:
            pc.create_index(
                name=index_name,
                dimension=768,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
                
            )

            while not pc.describe_index(index_name).status["ready"]:
                time.sleep(1)
            index= pc.Index(index_name)
            
            logger.info(f"Index Created Successfully: {index_name}\n")
            logger.info(f"here is the index description: {index.describe_index_stats()}")


    def upsert_data_pinecone(self):
        '''
        upsert data from csv file to pinecone with logging.
        '''
        try:

            logger.info(f"Data ingestion started for file: {self.csv_file_path} - Pinecone")
            index_name = "product-index1"

            self.create_index(index_name)

            # Read CSV file into DataFrame
            df = pd.read_csv(self.csv_file_path, index_col=0)

            df['tag'] = df['productDisplayName'] +' '+ df['usage']

            tags = pd.DataFrame(df[['id', 'tag']])

            loader = DataFrameLoader(tags, page_content_column="tag")

            docs = loader.load()

            embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

            PineconeVectorStore.from_documents(
                docs, 
                embedding=embeddings, 
                index_name=index_name
            )

            logger.info(f"Successfully ingested documents into Pinecone.")

        except pd.errors.EmptyDataError as e:
            # Handle empty csv file specifically 
            error_message = 'CSV File is empty - Pinecone.'
            logger.error(error_message)
            raise MyException(error_message, sys) from e
        
        except Exception as e:
            # General exception handling with custom error class
            logger.error(f"An error occurred during data ingestion - Pinecone.{e}")
            raise MyException(e, sys) from e
        




if __name__ == '__main__':

    csv_file_path = os.path.join(from_root(), 'notebooks', 'final_data.csv')
    ingestion = DataIngestion(csv_file_path=csv_file_path)
    # ingestion.ingest_data_to_mongo()
    # ingestion.upsert_data_pinecone()