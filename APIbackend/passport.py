from storage import Storage
from vision import Vision


DOCUMENT_FOLDER = 'document'
storage_util = Storage()
vision_util = Vision()

class Passport(object):
    def post_passport(self, filename):
        path = f'{DOCUMENT_FOLDER}/{filename}/original'
        edit = f'{DOCUMENT_FOLDER}/{filename}/edited'
        photo = f'{DOCUMENT_FOLDER}/{filename}/photo'
        labels_found = []

        if storage_util.check_document(path):

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

            fields = vision_util.detect_text(edit)

            return {'labels':labels_found, 'fields':fields}

        else:
            return 404
    
    def get_passport(self, filename):
        pass