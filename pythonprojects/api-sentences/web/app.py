from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import spacy

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.similarityDB
users = db["Users"]

def UserExists(username):
    if users.count_documents({"Username":username}) == 0:
        return False
    else:
        return True
class Register(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        if UserExists(username):
            retJson = {
                "status": 301,
                "message": "Invalid username"
            }
            return jsonify(retJson)
        hashed_pw = bcrypt.hashpw((password.encode('utf8')), bcrypt.gensalt())         
        users.insert_one({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 10
        })
        retJson = {
            "status": 200,
            "message": "Your account has been created!"
        }
        return jsonify(retJson)

def verifyPW(username, password):
    if not UserExists(username):
        return False
    hashed_pw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def countTokens(username):
    tokens = users.find({
        "Username": username
    })[0]["Tokens"]
    return tokens

class Detect(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        text1 = postedData["text1"]
        text2 = postedData["text2"]

        if not UserExists(username):
            retJson = {
                "status": 301,
                "message": "Invalid username"
            }
            return jsonify(retJson)

        correct_pw = verifyPW(username, password)

        if not correct_pw:
            retJson = {
                "status": 302,
                "message": "Invalid password"
            }
            return jsonify(retJson)

        num_tokens = countTokens(username)

        if num_tokens <= 0:
            retJson = {
                "status": 303,
                "message": "You are out of tokens"
            }
            return jsonify(retJson)
        nlp = spacy.load('en_core_web_sm')
        text1 = nlp(text1)
        text2 = nlp(text2)
        # ratio, number b/w 0 and 1, if closer to one then the texts are similar 
        ratio = text1.similarity(text2)
        retJson = {
            "status": 200,
            "similarity": ratio,
            "message": "The similarity score has been successfully calculated"
        }
        current_tokens = countTokens(username)
        users.update_one({
            "Username": username
        },{
            "$set":{
                "Tokens": current_tokens - 1
            }
        })
        return jsonify(retJson)

class Refill(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["admin_pw"]
        refill_amount = postedData["refill"]

        if not UserExists(username):
            retJson = {
                "status": 301,
                "message": "Invalid username"
            }
            return jsonify(retJson)
        
        correct_pw = "FPdzd*bes4G9RfPyGktR" #homework

        if not password == correct_pw:
            retJson = {
                "status": 304,
                "message": "Invalid password"
            }
            return jsonify(retJson)
        
        current_tokens = countTokens(username)

        users.update_one({
            "Username": username
        },{
            "$set":{
                "Tokens": refill_amount + current_tokens
            }
        })

        retJson = {
            "status": 200,
            "message": "Your tokens have been replenished"
        }
        return jsonify(retJson)
 
api.add_resource(Register, "/register")
api.add_resource(Detect, "/detect")
api.add_resource(Refill, "/refill")

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)