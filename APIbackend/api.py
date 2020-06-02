from flask import Flask, request
from flask_restful import Resource, Api
from uuid import UUID
from passport import Passport
from base64 import b64encode

app = Flask(__name__)
api = Api(app)

basePath = '/api/v1'

passport = Passport()

def checkFilename(filename):
    if len(filename) < 36: return False

    uuid = filename[:36]
    # f = filename[36:]
    try:
        UUID(uuid, version=4)
    except ValueError:
        return False
    
    return True

class CheckPassport(Resource):
    def get(self, filename):
        if not checkFilename(filename):
            return 'Invalid input data', 400

        ret = passport.get_passport_fields(filename)

        if ret == 404:
            return 'File not found', 404
        elif ret == 400:
            return 'No faces found, probably not a passport', 400
        
        return ret, 200

    def post(self, filename):
        if not checkFilename(filename):
            return 'Invalid input data', 400
        
        content = request.get_data()

        ret = passport.post_passport(filename, content)
        if ret == 409:
            return 'File already exist', 409
        
        return 'Success', 201

    def delete(self, filename):
        if not checkFilename(filename):
            return 'Invalid input data', 400

        passport.delete_passport(filename)

        return 'Success', 200

class PassportImage(Resource):
    def get(self, filename, document):
        if not checkFilename(filename):
            return 'Invalid input data', 400

        ret = passport.get_passport(filename, document)

        if ret is None:
            return 'File not found', 404

        image = b64encode(ret).decode('utf-8')
        return {'image':image}, 200


api.add_resource(CheckPassport, f'{basePath}/passport/<string:filename>')
api.add_resource(PassportImage, f'{basePath}/passport/read/<string:filename>/<string:document>')

if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)

