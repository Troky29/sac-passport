from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

basePath = '/api/v1'

class Passport(Resource):
    def get(self, filename):
        pass

    def post(self, filename):
        pass

app.add_resource(Passport, f'{basePath}/passport/<string:filename>')

if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=true)