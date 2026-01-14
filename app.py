from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import boto3
import json
import os
import logging
import requests 

app = Flask(__name__)

logging.basicConfig(
    filename = 'app.log',
    level=logging.INFO)

# Configure the database URI. Using SQLite file-based DB here
basedir = os.path.abspath(os.path.dirname(__file__))
print("The base dir is ", basedir)
db_name = 'tasks.db'

LAMBDA_API = 'https://7adeci92yh.execute-api.us-east-1.amazonaws.com/default/logTaskLambda'

def get_db_secret(secret_name, region_name = 'us-east-1'):
    client = boto3.client('secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except Exception as e:
        logging.error(f"Error retrieving secret {secret_name}: {e}")
        return None

# Fetch credentials from Secrets Manager
secret = get_db_secret('prod/rds/mydb')

app.config['SQLALCHEMY_DATABASE_URI']= f'mysql+pymysql://{secret['username']}:{secret['password']}@{secret['host']}/{secret['dbname']}'
db = SQLAlchemy(app)

BUCKET_NAME = 'flask-dec-todo-s3'

def upload_file_to_s3(file_path, file_name):
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, BUCKET_NAME, file_name)
        logging.info(f"File {file_name} uploaded to S3 bucket {BUCKET_NAME}")
    except Exception as e:
        logging.error(f"Error uploading file to S3: {e}")
        return None

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    s3_url = db.Column(db.String(500), nullable=True)


#Create tables within application context
with app.app_context():
    print("Creating database tables if they do not exist...")
    db.create_all()

# Define routes
@app.route('/')
def home():
    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

# Add task with optional file upload
@app.route('/add', methods= ['POST'])
def add_task():
    task = request.form.get('task')
    new_task = Task(title=task)
    file = request.files['file']
    if file:
        logging.info(f"Received file: {file.filename}")
        file_path = os.path.join(basedir, file.filename)
        file.save(file_path)
        upload_file_to_s3(file_path, file.filename)
        os.remove(file_path)
        new_task.s3_url = f"s3://{BUCKET_NAME}/{file.filename}"

    db.session.add(new_task)
    db.session.commit()
    
    # Log the task addition to the Lambda function
    try:
        response = requests.post(LAMBDA_API, json={"task": task})
        logging.info(f"Logged task addition to Lambda: {response.status_code}")
    except Exception as e:
        logging.error(f"Error logging to Lambda: {e}")

    return redirect('/')

# Delete task
@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task=Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect('/')

# Edit task
@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task = Task.query.get(task_id)
    if request.method == 'POST':
        task.title = request.form.get('task')
        db.session.commit()
        return redirect('/')
    return render_template('edit.html', task=task)

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)