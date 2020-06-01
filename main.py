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
from storage import Storage
from vision import Vision


app = Flask(__name__)
app.config['SECRET_KEY'] = 'Secret'
DOCUMENT_FOLDER = 'document'
MAX_CONTENT_LENGHT = 20 * 1024 * 1024 #20 MB max image dimension
ALLOWED_EXTENSIONS = ['jpg', 'png', 'jpeg', 'pdf']
storage_util = Storage()
vision_util = Vision()



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

@app.route('/single', methods=['GET', 'POST'])
def upload_single():
    imageform = ImageForm()
    filename = ''
    if imageform.validate_on_submit():
        img = imageform.img.data
        _, extension = os.path.splitext(img.filename)

        filename = str(uuid4()) + secure_filename(img.filename)
        path = f'{DOCUMENT_FOLDER}/{filename}/original'
        content = img.read()
        
        if sys.getsizeof(content) < MAX_CONTENT_LENGHT:
            if extension == '.pdf':
                page = pdf2image.convert_from_bytes(content)
                f = io.BytesIO()
                page[0].save(f, 'JPEG')
                storage_util.upload_document(f.getvalue(), path)
            else:
                storage_util.upload_document(content, path)
            return redirect(url_for('review_single', filename=filename))
        else:
            imageform.img.errors = ["File too big (max 20MB)"]

    return render_template('upload.html', imageform=imageform)

@app.route('/single/<filename>', methods=['GET'])
def review_single(filename):
    path = f'{DOCUMENT_FOLDER}/{filename}/original'
    edit = f'{DOCUMENT_FOLDER}/{filename}/edited'
    photo = f'{DOCUMENT_FOLDER}/{filename}/photo'
    messages = ['Label not found, probaly not a passport']

    if storage_util.check_document(path) and not storage_util.check_document(edit):

        faces, labels = vision_util.detect_document(path, edit)
        if faces == 0:
            storage_util.delete_document(f'{DOCUMENT_FOLDER}/{filename}')
            return 'No faces found, probably not a passport'

        for label in labels:
            if label.description == 'Identity document':
                messages.clear()
                messages.append(f'Found correct label with score: {label.score}')
                break

            messages.append(f'Found label {label.description} with score: {label.score}')

        content = storage_util.get_document(edit)
        person = vision_util.detect_person(content, photo)
        if person == 0:
            face = vision_util.crop_face(content, photo)
            print(face)

        fields = vision_util.detect_text(edit)
        
    return render_template('results.html', filename=filename, original = 'original', edited = 'edited', photo = 'photo', fields=fields, messages=messages)

@app.route('/multiple', methods=['GET', 'POST'])
def upload_multiple():
    multipleimageform = MultipleImageForm()
    filenames = []
    if multipleimageform.validate_on_submit():
        for image in multipleimageform.files.data:
            filenames.append(str(uuid4()) + secure_filename(image.filename))

        return f'Upload complete\n{filenames}'

    return render_template('upload_multiple.html', multipleimageform=multipleimageform)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# @app.route('/photo', methods=['GET', 'POST'])
# def upload_pic():
#     imageform = ImageForm()
#     filename = ''
#     if imageform.validate_on_submit():
#         img = imageform.img.data
#         filename = secure_filename(str(uuid4()) + '-' + img.filename)
#         path = f'{TEMPORANY_FOLDER}/{filename}'
#         content = img.read()
#         if sys.getsizeof(content) > MAX_CONTENT_LENGHT:
#             imageform.img.errors = ["File too big (max 20MB)"]
#         else:
#             storage_util.upload_document(storage_bucket, content, path)

#     return render_template('upload.html', imageform=imageform, target='profile pic', filename=filename, folder=TEMPORANY_FOLDER)

# @app.route('/photo/<filename>', methods=['GET'])
# def review_pic(filename):
#     accepted_face_option = ['Is your face expression neutral or smiling?', 'Is your headwear not covering your face?']
#     face = ''
#     safe = ''
#     fullmatch = ''
#     partialmatch = ''
#     path = f'{TEMPORANY_FOLDER}/{filename}'
#     dest = f'{PROFILE_FOLDER}/{filename}'
#     if storage_util.check_document(storage_bucket, path):
#         print('Siamo entrati')
#         content = storage_util.get_document(storage_bucket, path)

#         face = vision_util.check_faces(content, path, dest)
#         safe = vision_util.check_safe(content)
#         fullmatch, partialmatch = vision_util.check_web(content)
        
#         if not face or any(items in face for items in accepted_face_option):
#             vision_util.crop_profile(content, path, dest)
#         storage_util.delete_document(storage_bucket, path)

#     return render_template('results.html', filename=filename, folder=PROFILE_FOLDER, face=face, safe=safe, fullmatch=fullmatch, partialmatch=partialmatch)

# @app.route('/identity/<photo>', methods=['GET', 'POST'])
# def upload_id(photo):
#     imageform = ImageForm()
#     filename = ''
#     if imageform.validate_on_submit():
#         img = imageform.img.data
#         filename = secure_filename(str(uuid4()) + '-' + img.filename)
#         dest = f'{IDENTITY_FOLDER}/{filename}'
#         content = img.read()

#         if sys.getsizeof(content) > MAX_CONTENT_LENGHT:
#             imageform.img.errors = ["File too big (max 20MB)"]
#         else:
#             storage_util.upload_document(storage_bucket, content, dest)

#     return render_template('upload.html', imageform=imageform, target='identification document', filename=filename, folder=IDENTITY_FOLDER, photo=photo)

# @app.route('/identity/<photo>/<filename>', methods=['GET', 'POST'])
# def review_id(photo, filename):
#     message = ''
#     identityform = IdentityForm()
#     path = f'{IDENTITY_FOLDER}/{filename}'

#     if identityform.validate_on_submit():
#         return redirect(url_for('index'))

#     if storage_util.check_document(storage_bucket, path):
#         content = storage_util.get_document(storage_bucket, path)

#         if vision_util.check_label(content):
#             message = 'This is probably an identifying document'
#         else:
#             message = 'Are you shure you submitted an identifying document?'
#         text = vision_util.detect_text(content)
#         update_fields(identityform, text)

#     return render_template('identify.html', message=message, text=text, folder=IDENTITY_FOLDER, filename=filename, photo=photo, identityform=identityform)

# @app.route('/document', methods=['GET', 'POST'])
# def upload_doc():
#     documentform = DocumentForm()
#     filename = ''
#     if documentform.validate_on_submit():
#         doc = documentform.doc.data
#         filename = secure_filename(doc.filename)
#         dest = f'{DOCUMENT_FOLDER}/{filename}'
#         content = doc.read()

#         if sys.getsizeof(content) > MAX_CONTENT_LENGHT:
#             documentform.img.errors = ["File too big (max 20MB)"]
#         else:
#             storage_util.upload_document(storage_bucket, content, dest)

#     return render_template('docselect.html', documentform=documentform, filename=filename)

# @app.route('/document/<filename>', methods=['GET'])
# def review_doc(filename):
#     message = 'No document selected'
#     text = ''
#     path = f'{DOCUMENT_FOLDER}/{filename}'
#     if storage_util.check_document(storage_bucket, path):
#         print('start')
#         text = vision_util.process_document(path)
#         message = ''
#         print('end')
#     return render_template('docresults.html', message=message, text=text)

@app.route('/render/<filename>/<document>')
def send_image(filename, document):
    path = path = f'{DOCUMENT_FOLDER}/{filename}/{document}'
    return storage_util.get_document(path)

@app.route('/clean/<filename>')
def clear_image(filename):
    path = f'{DOCUMENT_FOLDER}/{filename}'
    images = ['/original', '/edited', '/photo', '']
    for image in images: storage_util.delete_document(path+image)
    return redirect(url_for('upload_single'))

# @app.route('/clean/<folder>/<filename>/<photo>')
# def clear_id(folder, filename, photo):
#     path = f'{folder}/{filename}'
#     storage_util.delete_document(storage_bucket, path)
#     return redirect(url_for('upload_id', photo=photo))

# def update_fields(form, text):
#     form.municipality.data = text['municipality']
#     form.surname.data = text['surname']
#     form.name.data = text['name']
#     form.place_of_birth.data = text['place of birth']
#     form.province_of_birth.data = text['province of birth']
#     form.date_of_birth.data = '.'.join(list(text['date of birth'].values()))
#     form.sex.data = text['sex']
#     form.height.data = text['height']
#     form.nationality.data = text['nationality']
#     form.issuing.data = '.'.join(list(text['issuing'].values()))
#     form.expiry.data = '.'.join(list(text['expiry'].values()))

# def get_fields(form, text):
#     pass

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)