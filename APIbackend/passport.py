from storage import Storage
from vision import Vision
from firestore import Firestore
import os
import io
import pdf2image

DOCUMENT_FOLDER = 'document'
storage_util = Storage()
vision_util = Vision()
firestore_util = Firestore()


class Passport(object):
    def post_passport(self, filename, content):
        path = f'{DOCUMENT_FOLDER}/{filename}/original'

        _, extension = os.path.splitext(filename)

        if extension == '.pdf':
            page = pdf2image.convert_from_bytes(content)
            f = io.BytesIO()
            page[0].save(f, 'JPEG')
            content = f.getvalue()

        if not storage_util.check_document(path):
            storage_util.upload_document(content, path)

        else:
            return 409
    
    def get_passport_fields(self, filename):
        path = f'{DOCUMENT_FOLDER}/{filename}/original'
        edit = f'{DOCUMENT_FOLDER}/{filename}/edited'
        photo = f'{DOCUMENT_FOLDER}/{filename}/photo'

        labels_found = {}

        if storage_util.check_document(path):
            if not storage_util.check_document(edit):
                faces, labels = vision_util.detect_document(path, edit)

                if faces == 0:
                    storage_util.delete_document(f'{DOCUMENT_FOLDER}/{filename}')
                    return 400

                for label in labels:
                    labels_found[label.description] = label.score
    
                content = storage_util.get_document(edit)
                person = vision_util.detect_person(content, photo)
                if person == 0:
                    if vision_util.crop_face(content, photo) == 0:
                        storage_util.delete_document(f'{DOCUMENT_FOLDER}/{filename}')
                        return 400

            if not firestore_util.check_info(filename):
                fields = vision_util.detect_text(edit)
                firestore_util.save_info(filename, fields, labels_found)
            else:
                fields = firestore_util.get_info(filename)
                labels_found = fields.pop('labels', None)
        else:
            return 404

        return {'fields':fields, 'labels':labels_found}

    def get_passport(self, filename, document):
        path = f'{DOCUMENT_FOLDER}/{filename}/{document}'

        return storage_util.get_document(path)

    def delete_passport(self, filename):
        path = f'{DOCUMENT_FOLDER}/{filename}'
        images = ['/original', '/edited', '/photo', '']
        for image in images: storage_util.delete_document(path + image)
        firestore_util.del_info(filename)

    def get_status(self):
        status = firestore_util.all_status()
        ret = []
        for name, status in status.items():
            ret.append({'name':name, 'status':status})
        return ret

    def del_status(self):
        firestore_util.del_status()
        return 'Success'