from PIL import Image, ImageDraw
from google.cloud import vision
import io
import os
import re
from storage import Storage
import cv2
import numpy as np

storage_util = Storage()
client = vision.ImageAnnotatorClient()

class Vision(object):

    def detect_document(self, path, dest):
        content = storage_util.get_document(path)
        image = vision.types.Image(content=content)
        response = client.face_detection(image=image)
        faces = response.face_annotations
        face_num = sum(1 for face in faces)
        labels = None

        if face_num > 0:
            best = faces[0]
            for face in faces:
                if face.detection_confidence > best.detection_confidence:
                    best = face
            self.crop_document(content, best.roll_angle, dest)

        labels = self.check_label(dest)

        return face_num, labels

    def check_label(self, path):
        content = storage_util.get_document(path)
        image = vision.types.Image(content=content)
        response = client.label_detection(image=image)
        labels = response.label_annotations
        
        for label in labels:
            if label.description == 'Identity document':
                return label.score
        return None

    def crop_document(self, content, roll, dest):
        source = np.asarray(bytearray(content), np.uint8)
        image = cv2.imdecode(source, cv2.IMREAD_UNCHANGED)
        h, w = image.shape[:2]
        image = image[25:h-0, 25:w-25]
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        kernel = np.ones((5, 5), np.uint8)
        ker_er = np.ones((2, 2), np.uint8)

        thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 5)
        thr = cv2.erode(thr, ker_er, iterations=1)
        thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=3)
        thr = cv2.dilate(thr, kernel, iterations=3)

        hull = []
        contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for i in range(len(contours)):
            hull.append(cv2.convexHull(contours[i]))

        best = sorted(hull, key = cv2.contourArea, reverse=True)[0]
        x1 = np.min(best[:, 0, 0])
        y1 = np.min(best[:, 0, 1])
        x2 = np.max(best[:, 0, 0])
        y2 = np.max(best[:, 0, 1])
        
        cropped = image[y1:y2, x1:x2]
        cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        out = Image.fromarray(cropped)
        form = Image.open(io.BytesIO(content)).format

        if abs(roll) > 5:
            out = out.rotate(roll, expand=True, fillcolor='white')

        f = io.BytesIO()
        out.save(f, format=form)
        storage_util.upload_document(f.getvalue(), dest)

    def detect_person(self, content, dest):
        # content = storage_util.get_document(path)
        image = vision.types.Image(content=content)
        objects = client.object_localization(image=image, max_results=5).localized_object_annotations

        person_num = sum(1 for obj in objects if obj.name == 'Person')

        if person_num > 0:
            score = 0
            best = None
            for obj in objects:
                if obj.name == 'Person' and obj.score > score:
                    score = obj.score
                    best = obj
            self.crop_person(best, content, dest)

        return person_num

    def crop_person(self, box, content ,dest):
        # image = io.BytesIO(storage_util.get_document(path))
        image = io.BytesIO(content)
        img = Image.open(image)

        vert = box.bounding_poly.normalized_vertices
        width, height = img.size
        x1 = vert[0].x * width
        y1 = vert[0].y * height
        x2 = vert[2].x * width
        y2 = vert[2].y * height

        cropped = img.crop([x1, y1, x2, y2])
        
        f = io.BytesIO()
        cropped.save(f, format=img.format)

        storage_util.upload_document(f.getvalue(), dest)

    def crop_face(self, content, dest):
        # content = storage_util.get_document(path)
        image = vision.types.Image(content=content)
        response = client.face_detection(image=image)
        faces = response.face_annotations
        face_num = sum(1 for face in faces)

        if face_num > 0:
            best = faces[0]
            for face in faces:
                if face.detection_confidence > best.detection_confidence:
                    best = face

        image = io.BytesIO(content)
        img = Image.open(image)
        width, height = img.size

        vert = best.fd_bounding_poly.vertices
        x1 = max(vert[0].x - 30, 0)
        y1 = max(vert[0].y - 30, 0)
        x2 = min(vert[2].x + 30, width)
        y2 = min(vert[2].y + 30, height)

        
        out = img.crop([x1, y1, x2, y2])

        f = io.BytesIO()
        out.save(f, format=img.format)
        storage_util.upload_document(f.getvalue(), dest)

        return face_num
    
    def detect_text(self, content):
        image = vision.types.Image(content=content)
        response = client.document_text_detection(image=image)
        document = response.full_text_annotation

        fields = ['type',
            'code of issuing state',
            'passport no',
            'surname',
            'given names',
            'nationality',
            'date of birth',
            'sex',
            'place of birth',
            'date of issue',
            'authority',
            'date of expiry',
            'country code',
            'personal no']

        doc_words = []
        doc_lines = []
        doc_fields = []
        
        response = []

        lenght = 0
        for page in document.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        string = ''
                        start = word.symbols[0].bounding_box.vertices[0]
                        end = word.symbols[-1].bounding_box.vertices[1]

                        if doc_words:
                            if cv2.norm((start.x, start.y), (doc_words[-1]['end'].x, doc_words[-1]['end'].y)) > lenght: 
                                doc_words[-1]['word'] += '\n'
                        lenght = 4*cv2.norm((end.x, end.y), (start.x, start.y))/len(word.symbols)

                        for symbol in word.symbols:
                            string += symbol.text
                            break_type = symbol.property.detected_break.type
                            if break_type == 1: string += ' '
                            if break_type == 2 or break_type == 3 or break_type == 5: string +='\n'

                        doc_words.append({'word':string, 'start':start, 'end':end})
                        
        line_text = ''
        start = 0
        line_start = doc_words[start]['start']
        for i in range(len(doc_words)):
            line_text += doc_words[i]['word']

            if '\n' in line_text:
                for field in fields:
                    if field in line_text.lower():
                        line_text = ''
                        if all(cur['field'] != field for cur in doc_fields):
                            doc_fields.append({'field':field, 'start':line_start, 'end':doc_words[i]['end']})
                        elif all(line_start.y > cur['start'].y for cur in doc_fields):
                            for cur in doc_fields: 
                                        if cur['field'] == field: cur['start'] = line_start
                
                if line_text != '':
                    doc_lines.append({'text':line_text.strip(), 'words':doc_words[start:i+1]})

                if i < (len(doc_words)-1):

                    line_text = ''
                    start = i+1
                    line_start = doc_words[start]['start']

        for i in range(len(doc_fields)):
            x1 = doc_fields[i]['start'].x
            y1 = doc_fields[i]['start'].y
            best = 300
            result = ''
            dist = 0
            for line in doc_lines:
                x2 = line['words'][0]['start'].x
                y2 = line['words'][0]['start'].y
                x3 = line['words'][-1]['end'].x
                dist = cv2.norm((x1, y1), (x2, y2))
                if dist < best and 0< y2 - y1 < 100 and x3 > x1:
                    
                    if i < len(doc_fields) - 1:

                        field_vertical_distance = abs(doc_fields[i]['end'].y - doc_fields[i+1]['start'].y)

                        if field_vertical_distance < 50 and x3 > doc_fields[i+1]['start'].x:
                            for k in range(1, len(line['words'])):
                                if line['words'][-k]['end'].x > doc_fields[i+1]['start'].x:
                                    doc_lines.append({'text':''.join(line['text'].split()[-k:]), 'words':line['words'][-k:]})
                                    line['words'] = line['words'][:-k]
                                    line['text'] = ' '.join(line['text'].split()[:-k])

                    result = line['text']
                    best = dist

            response.append({'field':doc_fields[i]['field'], 'value':result})
        
        #TODO: Mettere un bel controllo, in modo tale da utilizzare la coordinata verticale della parola già presente nella linea più vicina...
        lines = []
        for line in doc_lines:
            y = line['words'][0]['start'].y
            if any(abs(y - cur['start']) < 20 for cur in lines):
                for cur in lines:
                    if abs(y - cur['start']) < 20: cur['words'] += line['words']
            else:
                lines.append({'start':y, 'words':line['words']})
        
        barcode = ''
        sorted_lines = sorted(lines, key=lambda k: k['start'])
        for line in sorted_lines[-2:]:
            line['words'] = sorted(line['words'], key=lambda k: k['start'].x)
            for word in line['words']: barcode += word['word'].strip()
            print(barcode, '\n')
        
        response.append({'field':'barcode', 'value':re.sub("[^0-9A-Z]", "<", barcode)})

        return response

if __name__ == "__main__":
    path = f'document/93300e60-681c-4122-906b-57b846ee350a/original'
    edited = f'document/93300e60-681c-4122-906b-57b846ee350a/edited'
    content = storage_util.get_document(edited)
    ret = Vision().detect_text(content)
    print(ret)

    def process_document(self, path):
            name = path.split('.')[0]
            return self.detect_documents(f'gs://{storage_bucket}/{path}', f'gs://{storage_bucket}/{name}/')

    def detect_documents(self, source_uri, destination_uri):
        mime_type = 'application/pdf'
        batch_size = 2
        feature = vision.types.Feature(type=vision.enums.Feature.Type.DOCUMENT_TEXT_DETECTION)
        source = vision.types.GcsSource(uri=source_uri)
        input_config = vision.types.InputConfig(gcs_source=source, mime_type=mime_type)
        destination = vision.types.GcsDestination(uri=destination_uri)
        output_config = vision.types.OutputConfig(gcs_destination=destination, batch_size=batch_size)

        async_request = vision.types.AsyncAnnotateFileRequest(features=[feature], input_config=input_config, output_config=output_config)

        operation = client.async_batch_annotate_files(requests=[async_request])
        operation.result(timeout=60)

        match = re.match(r'gs://([^/]+)/(.+)', destination_uri)
        bucket_name = match.group(1)
        prefix = match.group(2)

        return storage_util.get_text(bucket_name, prefix, vision.types.AnnotateFileResponse())
