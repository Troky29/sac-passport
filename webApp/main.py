from flask import Flask, render_template, send_from_directory, redirect, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import MultipleFileField
from wtforms.validators import DataRequired, ValidationError
from werkzeug.utils import secure_filename
from uuid import uuid4
import sys
import os
import io
import pdf2image
from requests import get, post, delete
from base64 import b64decode
from google.cloud import pubsub_v1

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Secret'
DOCUMENT_FOLDER = 'document'
MAX_CONTENT_LENGHT = 20 * 1024 * 1024 #20 MB max image dimension
ALLOWED_EXTENSIONS = ['jpg', 'png', 'jpeg', 'pdf']
basePath = 'http://127.0.0.1:5000/api/v1'

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

    if extension == '.pdf':
        page = pdf2image.convert_from_bytes(content)
        f = io.BytesIO()
        page[0].save(f, 'JPEG')
        filename += '.jpeg'
        content = f.getvalue()
    
    return filename, content

@app.route('/single', methods=['GET', 'POST'])
def upload_single():
    imageform = ImageForm()
    filename = ''
    if imageform.validate_on_submit():
        img = imageform.img.data
        filename, content = read_image(img)
        
        if sys.getsizeof(content) < MAX_CONTENT_LENGHT:
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

    for label in labels:
        if label['label'] == 'Identity document':
                messages.clear()
                messages.append('Found correct label with score: {}'.format(label['confidence']))
                break
        messages.append('Found {} with confidence: {}'.format(label['label'], label['confidence']))
        
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

            if sys.getsizeof(content) < MAX_CONTENT_LENGHT:
                ret = post(f'{basePath}/passport/{filename}', data=content)
                result = ret.json()
                
                code = ret.status_code
                if code != 201:
                    return f'ERROR:\ncode: {code}\nmessage: {result}'
                filenames.append(filename)
            else:
                errors.append(f"{image.filename} skipped: file too big (max 20MB)")

        attribute = ' '.join(filenames).encode('ascii')
        print(attribute)
        future = publisher.publish(topic_path, b'Start batch operation', filename=attribute)
        print(future.result())
    return render_template('upload_multiple.html', multipleimageform=multipleimageform, filenames=filenames, errors=errors)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

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

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)