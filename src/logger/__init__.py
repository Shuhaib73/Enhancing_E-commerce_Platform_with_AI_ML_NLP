
import logging
import os 
from datetime import datetime
from from_root import from_root



def configure_logger(logf_name):
    # Create logger 
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a file handler to save the log file 
    log_folder = 'logs'
    log_dir_path = os.path.join(from_root(), log_folder)

    os.makedirs(log_dir_path, exist_ok=True)

    # Log file path
    log_file_name = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}_{logf_name}.log"
    log_file = os.path.join(log_dir_path, log_file_name)

    # file handler for logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Create a formatter for the logs 
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    return logger


# Initialize and Configure the logger 
# logger = configure_logger('testing_demo')