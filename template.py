import os
from pathlib import Path

# Define project name and folder structure
project_name = "src"

# List of files with full paths (adjusted for clarity)
list_of_files = [
    # Core project files
    f"{project_name}/__init__.py",
    f"{project_name}/components/__init__.py",
    f"{project_name}/components/data_ingestion.py",  
    
    # Configuration files
    f"{project_name}/configuration/__init__.py",
    f"{project_name}/configuration/mongo_db_connection.py",
    # f"{project_name}/configuration/aws_connection.py",
    
    # Data access files
    f"{project_name}/data_access/__init__.py",
    f"{project_name}/data_access/proj1_data.py",
    
    # Exception handling and logging
    f"{project_name}/exception/__init__.py",
    f"{project_name}/logger/__init__.py",
    
    # Pipeline files
    f"{project_name}/pipeline/__init__.py",
    f"{project_name}/pipeline/training_pipeline.py",
 
    
    # Other important files
    "app.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yaml",
]

# Function to create necessary directories and files
def create_project_structure(files: list):
    for filepath in files:
        filepath = Path(filepath)
        filedir, filename = os.path.split(filepath)

        # Create directories if they don't exist
        if filedir != "":
            os.makedirs(filedir, exist_ok=True)

        # Check if the file exists or is empty, create or skip accordingly
        if not filepath.exists() or filepath.stat().st_size == 0:
            with open(filepath, "w") as f:
                pass  # Create an empty file
        else:
            print(f"File is already present: {filepath}")

# Run the function to create project structure
create_project_structure(list_of_files)

print("Project structure has been successfully created/validated.")
