from flask import Flask, jsonify, request
import bcrypt
from pymongo import MongoClient
from flask_restful import Api, Resource

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankAPI
users = db["Users"]

def UserExists(username):
    if users.count_documents({"Username": username}) == 0:
        return False
    else:
        return True

def verifyPW(username,password):
    if not UserExists(username):
        return False
    hashed_pw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def verifyCredentials(username,password):
    if not UserExists(username):
        return generateReturnDictionary(301, "Invalid username"), True
    correct_pw = verifyPW(username,password)
    if not correct_pw:
        return generateReturnDictionary(302, "Invalid password"), True        

    return None, False

def cashWithUser(username):
    balance = users.find({
        "Username": username
    })[0]["Balance"]
    return balance

def debtWithUser(username):
    loan_balance = users.find({
        "Username": username
    })[0]["Loan balance"]
    return loan_balance

def updateAccount(username, balance):
    users.update_one({
        "Username": username
    },{"$set":{
            "Balance": balance
        }
    })

def updateBorrowed(username, loan_balance):
    users.update_one({
        "Username": username
    },{"$set":{
            "Loan balance": loan_balance
        }
    })

def generateReturnDictionary(status,message):
    retJson = {
        "status": status,
        "message": message
    }
    return retJson

class register(Resource):
    def post (self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        if UserExists(username):
            retJson = {
                "status": 301,
                "message": "invalid username"
            }
            return jsonify(retJson)
        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        users.insert_one({
            "Username": username,
            "Password": hashed_pw,
            "Balance": 0,
            "Loan balance": 0
        })

        return jsonify(generateReturnDictionary(200, "Your account has been successfully created"))

class deposit(Resource):
    def post (self):

        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        deposit = postedData["deposit"]
        
        retJson, error = verifyCredentials(username,password)
        
        if error:
            return jsonify(retJson)
        if deposit <= 0:
            return jsonify(generateReturnDictionary)(304, "The deposit amount must be greater than 0.")

        balance = cashWithUser(username)
        deposit -= 1
        bank_cash_reserve = cashWithUser("bank")
        updateAccount(username, balance + deposit)
        updateAccount("bank", bank_cash_reserve + 1)

        return jsonify(generateReturnDictionary(200, "Deposit completed successfully"))

class transfer(Resource):
    def post (self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        receiving_account = postedData["receiving_account"]
        transfer_amount = postedData["transfer_amount"]
        
        retJson, error = verifyCredentials(username,password)

        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)

        if cash <= 0:
            return jsonify(generateReturnDictionary(304, "Not enough funds to transfer. Please deposit funds to transfer"))

        if not UserExists(receiving_account):
            return jsonify(generateReturnDictionary(301, "User does not exist."))

        cash_sending_account = cashWithUser(username)
        cash_receiving_account = cashWithUser(receiving_account)
        bank_cash = cashWithUser("bank")

        updateAccount("bank", bank_cash + 1)
        updateAccount(receiving_account, cash_receiving_account - 1)
        updateAccount(username, cash_sending_account - transfer_amount)

        return jsonify(generateReturnDictionary(200, "Amount transferred successfully"))

class balance(Resource):
    def post (self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)
        
        retJson = users.find({
            "Username": username
        },{
            "Password": 0,
            "_id": 0
        })[0]

        return jsonify(retJson)

class takeloan(Resource):
    def post (self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        borrowed_amount = postedData["borrowed_amount"]

        retJson, error = verifyCredentials(username,password)
        
        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)
        loan_balance = debtWithUser(username)
        updateAccount(username, cash + borrowed_amount)
        updateBorrowed(username, borrowed_amount + loan_balance)

        return jsonify(generateReturnDictionary(200, f"You have borrowed {borrowed_amount}"))

class payloan(Resource):
    def post (self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        borrow_payment = postedData["borrow_payment"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)
        
        cash = cashWithUser(username)
        
        if cash < borrow_payment:
            return generateReturnDictionary(303, "Insufficient cash")

        loan_balance = debtWithUser(username)
        updateAccount(username, cash - borrow_payment)
        updateBorrowed(username, loan_balance - borrow_payment)

        return jsonify(generateReturnDictionary(200, "Payment made!"))

api.add_resource(register,  "/register")
api.add_resource(deposit,   "/deposit")
api.add_resource(transfer,  "/transfer")
api.add_resource(balance,   "/balance")
api.add_resource(takeloan,  "/takeloan")
api.add_resource(payloan,   "/payloan")

if __name__ == '__main__':
    app.run(host='0.0.0.0')