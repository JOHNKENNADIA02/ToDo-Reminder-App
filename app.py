from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_this'

# Database configuration
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'john8667'  # Change if you set a password
DB_NAME = 'task_management'

def get_db_connection():
    """Create and return a database connection"""
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

@app.route('/')
def index():
    """Redirect to login if not logged in, else to dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters')
        
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # Check if user exists
                cursor.execute('SELECT * FROM users WHERE email = %s OR username = %s', (email, username))
                if cursor.fetchone():
                    return render_template('register.html', error='Email or username already exists')
                
                # Create new user
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                    (username, email, hashed_password)
                )
                connection.commit()
                return redirect(url_for('login'))
        except Exception as e:
            return render_template('register.html', error=f'Error: {str(e)}')
        finally:
            connection.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', error='Invalid email or password')
        except Exception as e:
            return render_template('login.html', error=f'Error: {str(e)}')
        finally:
            connection.close()
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Show user's tasks with filtering"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    filter_option = request.args.get('filter', 'all')  # default = all

    query = "SELECT * FROM tasks WHERE user_id = %s"
    params = [session['user_id']]

    if filter_option == 'completed':
        query += " AND is_completed = 1"
    elif filter_option == 'pending':
        query += " AND is_completed = 0"

    query += " ORDER BY created_at DESC"

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            tasks = cursor.fetchall()

        return render_template(
            'dashboard.html',
            tasks=tasks,
            username=session['username'],
            filter_option=filter_option
        )
    except Exception as e:
        return render_template(
            'dashboard.html',
            error=f'Error: {str(e)}',
            tasks=[]
        )
    finally:
        connection.close()


@app.route('/add_task', methods=['POST'])
def add_task():
    """Add a new task"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    description = request.form.get('description')
    reminder_date = request.form.get('reminder_date')
    
    if not title:
        return redirect(url_for('dashboard'))
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO tasks (user_id, title, description, reminder_date, created_at) VALUES (%s, %s, %s, %s, NOW())',
                (session['user_id'], title, description, reminder_date if reminder_date else None)
            )
            connection.commit()
    except Exception as e:
        print(f"Error adding task: {str(e)}")
    finally:
        connection.close()
    
    return redirect(url_for('dashboard'))

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    """Edit a task"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM tasks WHERE id = %s AND user_id = %s', (task_id, session['user_id']))
            task = cursor.fetchone()
            
            if not task:
                return redirect(url_for('dashboard'))
            
            if request.method == 'POST':
                title = request.form.get('title')
                description = request.form.get('description')
                reminder_date = request.form.get('reminder_date')
                
                cursor.execute(
                    'UPDATE tasks SET title = %s, description = %s, reminder_date = %s WHERE id = %s',
                    (title, description, reminder_date if reminder_date else None, task_id)
                )
                connection.commit()
                return redirect(url_for('dashboard'))
            
            return render_template('edit_task.html', task=task)
    finally:
        connection.close()

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    """Mark task as complete"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE tasks SET is_completed = 1 WHERE id = %s AND user_id = %s',
                (task_id, session['user_id'])
            )
            connection.commit()
    finally:
        connection.close()
    
    return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    """Delete a task"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', (task_id, session['user_id']))
            connection.commit()
    finally:
        connection.close()
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
