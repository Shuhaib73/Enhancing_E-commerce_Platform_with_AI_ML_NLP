import os
import sys 
from from_root import from_root
from src.exception import MyException

from src.components.data_ingestion import DataIngestion, logger


class TrainPipeline:
    def __init__(self):
        self.csv_file_path = os.path.join(from_root(), 'notebooks', 'final_data.csv')


    def run_data_ingestion(self):
        try:
            logger.info("Starting data ingestion pipeline.")
            ingestion = DataIngestion(self.csv_file_path)
            ingestion.ingest_data_to_mongo()
            logger.info("Data ingestion pipeline completed successfully.")

        except Exception as e:
            logger.error(f"Error occurred in TrainPipeline: {e}")
            raise MyException(e, sys) from e
        
    def run_data_ingestion_pinecone(self):
        try:
            logger.info("Starting data ingestion pipeline - Pinecone.")
            ingestion = DataIngestion(self.csv_file_path)
            ingestion.upsert_data_pinecone()
            logger.info("Data ingestion pipeline completed successfully - Pinecone.")

        except Exception as e:
            logger.error(f"Error occurred in TrainPipeline - Pinecone: {e}")
            raise MyException(e, sys) from e



if __name__ == "__main__":
    pipeline = TrainPipeline()
    # pipeline.run_data_ingestion()
    # pipeline.run_data_ingestion_pinecone()