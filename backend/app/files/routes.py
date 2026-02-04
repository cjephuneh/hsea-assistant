from flask import Blueprint, request, jsonify, send_file, current_app
from app import db
from app.models import StoredFile, User
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid
from werkzeug.utils import secure_filename
from app.notifications.email_service import send_email

files_bp = Blueprint('files', __name__)


def get_upload_folder():
    folder = current_app.config.get('UPLOAD_FOLDER')
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    return folder


@files_bp.route('', methods=['GET'])
@jwt_required()
def list_files():
    user_id = int(get_jwt_identity())
    files = StoredFile.query.filter_by(user_id=user_id).order_by(StoredFile.created_at.desc()).all()
    return jsonify([{
        'id': f.id,
        'original_filename': f.original_filename,
        'content_type': f.content_type,
        'file_size': f.file_size,
        'created_at': f.created_at.isoformat(),
    } for f in files]), 200


@files_bp.route('', methods=['POST'])
@jwt_required()
def upload_file():
    user_id = int(get_jwt_identity())
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    original = secure_filename(file.filename) or 'unnamed'
    ext = os.path.splitext(original)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    folder = get_upload_folder()
    path = os.path.join(folder, stored_name)
    file.save(path)
    size = os.path.getsize(path)
    stored = StoredFile(
        user_id=user_id,
        original_filename=original,
        stored_filename=stored_name,
        content_type=file.content_type,
        file_size=size,
    )
    db.session.add(stored)
    db.session.commit()
    return jsonify({
        'id': stored.id,
        'original_filename': stored.original_filename,
        'content_type': stored.content_type,
        'file_size': stored.file_size,
        'created_at': stored.created_at.isoformat(),
    }), 201


@files_bp.route('/<int:file_id>', methods=['GET'])
@jwt_required()
def download_file(file_id):
    user_id = int(get_jwt_identity())
    f = StoredFile.query.filter_by(id=file_id, user_id=user_id).first_or_404()
    folder = get_upload_folder()
    path = os.path.join(folder, f.stored_filename)
    if not os.path.isfile(path):
        return jsonify({'error': 'File not found on disk'}), 404
    return send_file(path, as_attachment=True, download_name=f.original_filename)


@files_bp.route('/<int:file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    user_id = int(get_jwt_identity())
    f = StoredFile.query.filter_by(id=file_id, user_id=user_id).first_or_404()
    folder = get_upload_folder()
    path = os.path.join(folder, f.stored_filename)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
    db.session.delete(f)
    db.session.commit()
    return jsonify({'message': 'File deleted'}), 200


@files_bp.route('/<int:file_id>/send-email', methods=['POST'])
@jwt_required()
def send_file_by_email(file_id):
    user_id = int(get_jwt_identity())
    sender = User.query.get(user_id)
    f = StoredFile.query.filter_by(id=file_id, user_id=user_id).first_or_404()
    data = request.get_json() or {}
    to_user_id = data.get('to_user_id')
    to_email = data.get('to_email')
    message = data.get('message', 'Please find the attached file.')
    subject = data.get('subject', f'File: {f.original_filename}')
    if to_user_id:
        recipient = User.query.get(to_user_id)
        if not recipient:
            return jsonify({'error': 'User not found'}), 404
        to_email = recipient.email
    if not to_email:
        return jsonify({'error': 'Provide to_user_id or to_email'}), 400
    folder = get_upload_folder()
    path = os.path.join(folder, f.stored_filename)
    if not os.path.isfile(path):
        return jsonify({'error': 'File not found on disk'}), 404
    with open(path, 'rb') as fp:
        file_bytes = fp.read()
    body = message
    if sender:
        body = f"{message}\n\n— Sent from HSEA Assistant by {sender.name}"
    ok, err = send_email(
        to_email,
        subject,
        body,
        attachments=[(f.original_filename, file_bytes, f.content_type or 'application/octet-stream')],
    )
    if not ok:
        return jsonify({'error': err or 'Failed to send email'}), 500
    return jsonify({'message': f'Email sent to {to_email}'}), 200
