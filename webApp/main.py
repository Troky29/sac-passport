from flask import Flask, render_template, send_from_directory, redirect, url_for, request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import MultipleFileField
from wtforms.validators import DataRequired, ValidationError
from werkzeug.utils import secure_filename
from uuid import uuid4
import os
import io
import json
import pdf2image
from requests import get, post, delete
from base64 import b64decode
from google.cloud import pubsub_v1

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Secret'
app.config['PUBSUB_VERIFICATION_TOKEN'] = os.environ['PUBSUB_VERIFICATION_TOKEN']

DOCUMENT_FOLDER = 'document'
MAX_CONTENT_LENGHT = 20 * 1024 * 1024 #20 MB max image dimension
ALLOWED_EXTENSIONS = ['jpg', 'png', 'jpeg', 'pdf']
# basePath = 'https://api-dot-sac-passport-205890.nw.r.appspot.com/api/v1'
basePath = 'http://127.0.0.1:8080/api/v1'
MESSAGES = []

project_id = 'sac-passport-205890'
topic_name = 'start-operations'

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

class ImageForm(FlaskForm):
    img = FileField('image', validators=[FileRequired(), FileAllowed(ALLOWED_EXTENSIONS, 'Images or PDF only!')])

def validate_extension(form, field):
        for image in field.data:
            filename = image.filename
            extension = os.path.splitext(filename)[1].strip('.')
            if extension.lower() not in ALLOWED_EXTENSIONS:
                raise ValidationError("Images or PDF only!")

class MultipleImageForm(FlaskForm):
    files = MultipleFileField('files', render_kw={'multiple':True}, validators=[DataRequired(), validate_extension])

def read_image(img):
    _, extension = os.path.splitext(img.filename)

    filename = str(uuid4()) + secure_filename(img.filename)
    content = img.read()
    
    return filename, content

@app.route('/single', methods=['GET', 'POST'])
def upload_single():
    imageform = ImageForm()
    filename = ''
    if imageform.validate_on_submit():
        img = imageform.img.data
        filename, content = read_image(img)
        
        if len(content) < MAX_CONTENT_LENGHT:
            ret = post(f'{basePath}/passport/{filename}', data=content)
            result = ret.json()
            code = ret.status_code

            if code != 201:
                return f'ERROR:\ncode: {code}\nmessage: {result}'

            return redirect(url_for('review_single', filename=filename))
        else:
            imageform.img.errors = ["File too big (max 20MB)"]

    return render_template('upload.html', imageform=imageform)

@app.route('/single/<filename>', methods=['GET'])
def review_single(filename):
    messages = ['Label not found, probaly not a passport']

    ret = get(f'{basePath}/passport/{filename}')
    result = ret.json()
    code = ret.status_code

    if code != 200:
        return f'ERROR:\ncode: {code}\nmessage: {result}'

    fields = result['fields']
    labels = result['labels']

    if 'Identity document' in labels:
            messages.clear()
            messages.append('Found correct label with score: {}'.format(labels['Identity document']))
    else:
        for label, confidence in labels.items(): messages.append(f'Found {label} with confidence: {confidence}')
        
    return render_template('results.html', filename=filename, original='original', edited='edited', photo='photo', fields=fields, messages=messages)

@app.route('/multiple', methods=['GET', 'POST'])
def upload_multiple():
    multipleimageform = MultipleImageForm()
    filenames = []
    errors = []

    if multipleimageform.validate_on_submit():
        images = multipleimageform.files.data
        for image in images:
            filename, content = read_image(image)

            if len(content) < MAX_CONTENT_LENGHT:
                ret = post(f'{basePath}/passport/{filename}', data=content)
                result = ret.json()
                
                code = ret.status_code
                if code != 201:
                    return f'ERROR:\ncode: {code}\nmessage: {result}'
                filenames.append(filename)
            else:
                errors.append(f"{image.filename} skipped: file too big (max 20MB)")

        if filenames:
            attribute = ' '.join(filenames).encode('ascii')
            future = publisher.publish(topic_path, b'Start batch operation', filenames=attribute)
            print(future.result())
    return render_template('upload_multiple.html', multipleimageform=multipleimageform, filenames=filenames, errors=errors)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', messages=MESSAGES)

@app.route('/render/<filename>/<document>')
def send_image(filename, document):
    ret = get(f'{basePath}/passport/read/{filename}/{document}')
    code = ret.status_code
    result = ret.json()
    if code != 200:
        return f'ERROR:\ncode: {code}\nmessage: {result}'

    image = b64decode(result['image'])
    return image

@app.route('/clean/<filename>')
def clear_image(filename):
    ret = delete(f'{basePath}/passport/{filename}')
    code = ret.status_code
    result = ret.json()
    if code != 200:
        return f'ERROR:\ncode: {code}\nmessage: {result}'

    return redirect(url_for('upload_single'))

@app.route('/pubsub/push', methods=['POST'])
def pubsub_push():
    print('Messaggio arrivato')
    if request.args.get(('token', '')) != app.config['PUBSUB_VERIFICATION_TOKEN']:
        return 'Invalid request', 400
    
    envelope = json.load(request.data.decode('utf-8'))
    payload = b64decode(envelope['message']['data'])
    MESSAGES.append(payload)

    return 'OK', 200

if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)