import os

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import requests
import tarfile
import zipfile
import datetime
from flask import *
import urllib.request

from classes.User import User
from classes.Post import Post
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
from flask_socketio import SocketIO
from classes.forms import RegistrationForm, LoginForm, PostForm
from flask_bcrypt import Bcrypt
from docproduct.predictor import RetreiveQADoc, GenerateQADoc

from classes.Message import Message

app = Flask("__app__")
app.config['SECRET_KEY'] = 'a551d32359baf371b9095f28d45347c8b8621830'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
socketio = SocketIO(app)

doc = None
messages = None


@login_manager.user_loader
def load_user(user_id):
    return User.fetch_userid(int(user_id))


@app.route("/login", methods=['GET', 'POST'])
@app.route("/", methods=['GET', 'POST'])
def login():
    global messages
    form = LoginForm()
    if form.validate_on_submit():
        user = User.fetch(form.email.data)

        if user:
            validate = bcrypt.check_password_hash(user.password, form.password.data)
            if validate:
                login_user(user)
                messages = Message.fetch(current_user.username)
                return redirect(url_for('profile'))
            else:
                flash(f'Password incorrect. Login unsuccessful', 'danger')
                return redirect(url_for('login'))

        else:
            flash(f'User does not exist', 'danger')
            return redirect(url_for('register'))
    else:
        return render_template("login.html", title='Login', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user1 = User(request.form['username'], hashed, request.form['email'], 'default.jpg')
        user1.upload()
        flash(f'Account created for {form.username.data}! Now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registration', form=form)


@app.route("/about", methods=['GET', 'POST'])
def about():
    return render_template('about.html', title='About')


@app.route("/profile", methods=['GET', 'POST'])
def profile():
    form = PostForm()
    if form.validate_on_submit():
        url = ''
        now = datetime.datetime.now().strftime("%H:%M %d-%m-%y")
        post = Post(current_user.username, form.title.data, form.content.data, now, url, current_user.profile_pic)
        post.upload()
        socketio.emit("newPost", include_self=True)
        return redirect(url_for('home'))

    return render_template('post.html', title='Post', form=form, messages=messages)


@app.route('/message_user', methods=['GET', 'POST'])
def message_user():
    content = request.get_json()
    msg = Message(current_user.username, 'user', content['content'])
    msg.upload()
    socketio.emit('message_user', json.dumps({
        'user': 'user',
        'content': msg.content,
        'time': msg.time,
    }))
    ans = doc.predict(msg.content, search_by='answer', topk=1, answer_only=True)[0]
    ans_msg = Message(current_user.username, 'bot', ans)
    socketio.emit('message_bot', json.dumps({
        'user': 'bot',
        'content': ans_msg.content,
        'time': ans_msg.time,
    }))
    ans_msg.upload()
    return '', 200


@app.route('/message_model', methods=['GET', 'POST'])
def message_model():
    ans = "Test"
    msg = Message(current_user.username, 'bot', ans)
    msg.upload()
    socketio.emit('message', json.dumps({
        'user': 'bot',
        'content': ans,
        'time': msg.time,
    }))
    return '', 200


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


def download_file_from_google_drive(id, destination):
    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params={'id': id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {'id': id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)


def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None


def save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)


def use_once_func():
    urllib.request.urlretrieve(
        'https://github.com/naver/biobert-pretrained/releases/download/v1.0-pubmed-pmc/biobert_v1.0_pubmed_pmc.tar.gz',
        'BioBert.tar.gz')

    if not os.path.exists('BioBertFolder'):
        os.makedirs('BioBertFolder')

    tar = tarfile.open("BioBert.tar.gz")
    tar.extractall(path='BioBertFolder/')
    tar.close()

    file_id = '1uCXv6mQkFfpw5txGnVCsl93Db7t5Z2mp'

    download_file_from_google_drive(file_id, 'Float16EmbeddingsExpanded5-27-19.pkl')

    file_id = 'https://onedrive.live.com/download?cid=9DEDF3C1E2D7E77F&resid=9DEDF3C1E2D7E77F%2132792&authkey=AEQ8GtkcDbe3K98'

    urllib.request.urlretrieve(file_id, 'DataAndCheckpoint.zip')

    if not os.path.exists('newFolder'):
        os.makedirs('newFolder')

    zip_ref = zipfile.ZipFile('DataAndCheckpoint.zip', 'r')
    zip_ref.extractall('newFolder')
    zip_ref.close()


def load_weights():
    global doc
    pretrained_path = 'BioBertFolder/biobert_v1.0_pubmed_pmc/'
    bert_ffn_weight_file = 'newFolder/models/bertffn_crossentropy/bertffn'
    embedding_file = 'Float16EmbeddingsExpanded5-27-19.pkl'

    doc = RetreiveQADoc(pretrained_path=pretrained_path,
                        ffn_weight_file=None,
                        bert_ffn_weight_file=bert_ffn_weight_file,
                        embedding_file=embedding_file)


load_weights()
socketio.run(app, debug=True, host='0.0.0.0')
