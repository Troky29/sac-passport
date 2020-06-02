from storage import Storage
from vision import Vision


DOCUMENT_FOLDER = 'document'
storage_util = Storage()
vision_util = Vision()

class Passport(object):
    def post_passport(self, filename, content):
        path = f'{DOCUMENT_FOLDER}/{filename}/original'
        edit = f'{DOCUMENT_FOLDER}/{filename}/edited'
        photo = f'{DOCUMENT_FOLDER}/{filename}/photo'
        labels_found = []

        if not storage_util.check_document(path):
            storage_util.upload_document(content, path)

            faces, labels = vision_util.detect_document(path, edit)
            if faces == 0:
                storage_util.delete_document(f'{DOCUMENT_FOLDER}/{filename}')
                return 400

            for label in labels:
                labels_found.append({'label':label.description, 'confidence':label.score})
                    
            content = storage_util.get_document(edit)
            person = vision_util.detect_person(content, photo)
            if person == 0:
                face = vision_util.crop_face(content, photo)
                print(face)

            return labels_found

        else:
            return 409
    
    def get_passport_fields(self, filename):
        edit = f'{DOCUMENT_FOLDER}/{filename}/edited'

        if not storage_util.check_document(edit):
            return 404

        fields = vision_util.detect_text(edit)

        return fields

    def get_passport(self, filename, document):
        path = f'{DOCUMENT_FOLDER}/{filename}/{document}'

        return storage_util.get_document(path)

    def delete_passport(self, filename):
        path = f'{DOCUMENT_FOLDER}/{filename}'
        images = ['/original', '/edited', '/photo', '']
        for image in images: storage_util.delete_document(path + image)
