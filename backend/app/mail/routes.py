from flask import Blueprint, request, jsonify, current_app
from app.models import User, StoredFile
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from app.notifications.email_service import send_email

mail_bp = Blueprint('mail', __name__)


def get_upload_folder():
    folder = current_app.config.get('UPLOAD_FOLDER')
    return folder if folder and os.path.isdir(folder) else None


@mail_bp.route('/send', methods=['POST'])
@jwt_required()
def send_mail():
    user_id = int(get_jwt_identity())
    sender = User.query.get(user_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    to_user_id = data.get('to_user_id')
    to_email = data.get('to_email')
    subject = data.get('subject', '').strip()
    body = data.get('body', '').strip()
    file_ids = data.get('file_ids') or []
    if not subject:
        return jsonify({'error': 'Subject is required'}), 400
    if to_user_id:
        recipient = User.query.get(to_user_id)
        if not recipient:
            return jsonify({'error': 'User not found'}), 404
        to_email = recipient.email
    if not to_email:
        return jsonify({'error': 'Provide to_user_id or to_email'}), 400
    attachments = []
    folder = get_upload_folder()
    for fid in file_ids:
        f = StoredFile.query.filter_by(id=fid, user_id=user_id).first()
        if not f or not folder:
            continue
        path = os.path.join(folder, f.stored_filename)
        if os.path.isfile(path):
            with open(path, 'rb') as fp:
                attachments.append((f.original_filename, fp.read(), f.content_type or 'application/octet-stream'))
    if sender:
        body = f"{body}\n\n— Sent from HSEA Assistant by {sender.name}"
    ok, err = send_email(to_email, subject, body, attachments=attachments if attachments else None)
    if not ok:
        return jsonify({'error': err or 'Failed to send email'}), 500
    return jsonify({'message': f'Email sent to {to_email}'}), 200
