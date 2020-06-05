from PIL import Image, ImageDraw
from google.cloud import vision
import io
import os
from storage import Storage
from detection import FieldDetection
import cv2
import numpy as np

storage_util = Storage()
detection_util = FieldDetection()
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
        
        return labels

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

        if abs(roll) > 6:
            if abs(roll-90) < 5:
                out = out.rotate(90, expand=True, fillcolor='white')
            elif abs(roll+90) < 5:
                out = out.rotate(-90, expand=True, fillcolor='white')
            elif abs(roll-180) < 5 or abs(roll+180) < 5:
                out = out.rotate(180, expand=True, fillcolor='white')
            else:
                out = out.rotate(roll, expand=True, fillcolor='white')

        f = io.BytesIO()
        out.save(f, format=form)
        storage_util.upload_document(f.getvalue(), dest)

    def detect_person(self, content, dest):
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
    
    def detect_text(self, path):
        content = storage_util.get_document(path)
        image = vision.types.Image(content=content)
        response = client.document_text_detection(image=image)
        document = response.full_text_annotation

        return detection_util.retrieve_fields(document)
