from flask import Flask, request
from flask_restful import Resource, Api
from uuid import UUID
from passport import Passport

app = Flask(__name__)
api = Api(app)

basePath = '/api/v1'

passport = Passport()

class CheckPassport(Resource):
    def get(self, filename):
        return 'Hello', 404

    def post(self, filename):
        if len(filename) < 36:
            return 'Invalid input data', 400
        uuid = filename[:36]
        f = filename[36:]

        try:
            UUID(uuid, version=4)
        except ValueError:
            return 'Invalid input data', 400

        res = passport.post_passport(filename)
        if res == 404:
            return 'File not found', 404
        elif res == 400:
            return 'No faces found, probably not a passport', 400
        
        return res, 201

        
        


api.add_resource(CheckPassport, f'{basePath}/passport/<string:filename>')

if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)

