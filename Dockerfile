#1. Set the base image to python 3.11
FROM python:3.11 

#2. Set the working directory inside a container
WORKDIR /app

#3. Copy the req. txt to the working directory (container)
COPY ./requirements.txt .   

#4. Install the python dependencies
RUN pip install --no-cache-dir -r requirements.txt

#5. Copy the application code into the container
COPY . . 

#6. Expose the port that the application will use
EXPOSE 8000

#7. Define the dafault command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
