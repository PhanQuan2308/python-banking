from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from models import Account, Transaction, User  # Đảm bảo đã import User
from service.utils import send_email

transaction_bp = Blueprint("transaction", __name__)

@transaction_bp.route("/api/v1/history", methods=["GET"])
@jwt_required() 
def transaction_history():
    user_id = get_jwt_identity() 

    account_id = Account.get_account_id_by_user(user_id)
    if not account_id:
        return jsonify({"message": "Account not found"}), 404

    history = Transaction.get_transaction_history(account_id)
    return jsonify({"history": history}), 200


@transaction_bp.route("/api/v1/deposit", methods=["POST"])
@jwt_required()
def deposit():
    user_id = get_jwt_identity()
    data = request.get_json()
    amount = data.get("amount")

    account_id = Account.get_account_id_by_user(user_id)
    if not account_id:
        return jsonify({"message": "Account not found"}), 404

    Account.update_balance(account_id, amount, "deposit")
    Transaction.create_transaction(account_id, "deposit", amount)

    user = User.get_user_by_id(user_id)
    subject = "Deposit Confirmation"
    body = f"Dear {user['name']},\n\nYou have successfully deposited {amount} into your account."
    send_email(subject, user["email"], body) 

    return jsonify({"message": "Deposit successful!"}), 201


@transaction_bp.route("/api/v1/withdraw", methods=["POST"])
@jwt_required()
def withdraw():
    user_id = get_jwt_identity()
    data = request.get_json()
    amount = data.get("amount")

    account_id = Account.get_account_id_by_user(user_id)
    if not account_id:
        return jsonify({"message": "Account not found"}), 404

    balance = Account.get_balance(account_id)
    if balance < amount:
        return jsonify({"message": "Insufficient funds"}), 400

    Account.update_balance(account_id, amount, "withdraw")
    Transaction.create_transaction(account_id, "withdraw", amount)

    user = User.get_user_by_id(user_id)
    subject = "Withdrawal Confirmation"
    body = f"Dear {user['name']},\n\nYou have successfully withdrawn {amount} from your account."
    send_email(subject, user["email"], body) 

    return jsonify({"message": "Withdrawal successful!"}), 201


@transaction_bp.route("/api/v1/check-recipient", methods=["POST"])
@jwt_required()
def check_recipient():
    data = request.get_json()
    recipient_email = data.get("email")
    
    recipient = User.verify_user_email(recipient_email) 
    if recipient:
        return jsonify({"message": "Recipient found", "recipient_id": recipient["id"]}), 200
    return jsonify({"message": "Recipient not found"}), 404


@transaction_bp.route("/api/v1/transfer", methods=["POST"])
@jwt_required()
def transfer():
    user_id = get_jwt_identity()
    data = request.get_json()
    recipient_email = data.get("recipient_email")
    amount = data.get("amount")

    sender_account_id = Account.get_account_id_by_user(user_id)
    if not sender_account_id:
        return jsonify({"message": "Sender account not found"}), 404

    recipient = User.verify_user_email(recipient_email)
    if not recipient:
        return jsonify({"message": "Recipient not found"}), 404
    
    recipient_account_id = Account.get_account_id_by_user(recipient["id"])
    
    balance = Account.get_balance(sender_account_id)
    if balance < amount:
        return jsonify({"message": "Insufficient funds"}), 400

    Account.update_balance(sender_account_id, amount, "withdraw")  # Trừ tiền người gửi
    Account.update_balance(recipient_account_id, amount, "deposit")  # Cộng tiền người nhận

    Transaction.create_transaction(sender_account_id, "transfer", -amount)
    Transaction.create_transaction(recipient_account_id, "transfer", amount)

    sender = User.get_user_by_id(user_id)
    subject = "Transfer Confirmation"
    body = f"Dear {sender['name']},\n\nYou have successfully transferred {amount} to {recipient_email}."
    send_email(subject, sender["email"], body)

    body_recipient = f"Dear {recipient['name']},\n\nYou have received {amount} from {sender['email']}."
    send_email(subject, recipient["email"], body_recipient)

    return jsonify({"message": "Transfer successful!"}), 200
