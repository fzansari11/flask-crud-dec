from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy

import os

app = Flask(__name__)

# Configure the database URI. Using SQLite file-based DB here
basedir = os.path.abspath(os.path.dirname(__file__))
print("The base dir is ", basedir)
db_name = 'tasks.db'

final_db_path = os.path.join(basedir, db_name)

print ("The final database path is ", final_db_path)

#app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///tasks.db'
app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///' + final_db_path

db = SQLAlchemy(app)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)

#Create tables within application context
with app.app_context():
    print("Creating database tables if they do not exist...")
    db.create_all()

@app.route('/')
def home():
    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

@app.route('/add', methods= ['POST'])
def add_task():
    task = request.form.get('task')
    new_task = Task(title=task)
    db.session.add(new_task)
    db.session.commit()
    return redirect('/')

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task=Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect('/')

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task = Task.query.get(task_id)
    if request.method == 'POST':
        task.title = request.form.get('task')
        db.session.commit()
        return redirect('/')
    return render_template('edit.html', task=task)

if __name__ == '__main__':
    app.run(debug=True)