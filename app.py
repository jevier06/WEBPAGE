from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import openai
import os
import uuid
from datetime import timedelta
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # Set to True if using HTTPS
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Simulated database with a dictionary
users_db = {}


# OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')


@app.route('/')
def home():
    return render_template('index.html', username=session.get('username'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_db.get(username)


        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session.permanent = True
            flash('Login successful!', 'success')
            return redirect(url_for('chatbot'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))


    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']


        if not username or not password or not email:
            flash('All fields are required', 'danger')
            return redirect(url_for('signup'))


        if username in users_db:
            flash('Username already taken', 'danger')
            return redirect(url_for('signup'))


        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        users_db[username] = {'username': username, 'password': hashed_password, 'email': email}


        flash('Signup successful! You can now login.', 'success')
        return redirect(url_for('login'))


    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))


@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'username' not in session:
        flash('You need to be logged in to access the chatbot.', 'warning')
        return redirect(url_for('login'))


    bot_response = None
    image_url = None


    if request.method == 'POST':
        user_input = request.form.get('question')
        image = request.files.get('file')


        if image and allowed_file(image.filename):
            unique_filename = str(uuid.uuid4()) + "_" + secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image.save(image_path)
            image_url = url_for('uploaded_file', filename=unique_filename)
        elif image:
            flash('Invalid file type. Please upload a valid image.', 'danger')


        if user_input:
            try:
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=user_input,
                    max_tokens=150
                )
                bot_response = response.choices[0].text.strip()
            except openai.error.OpenAIError as e:
                flash(f'OpenAI API Error: {str(e)}', 'danger')
                bot_response = 'Sorry, there was an error with the AI service.'
            except Exception as e:
                flash(f'Error: {str(e)}', 'danger')
                bot_response = 'Sorry, there was an error processing your request.'


        return jsonify({
            'bot_response': bot_response,
            'image_url': image_url
        })


    return render_template('chatbot.html', username=session.get('username'), bot_response=bot_response, image_url=image_url)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename='uploads/' + filename))


def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


if __name__ == '__main__':
    app.run(debug=True, port=8000)