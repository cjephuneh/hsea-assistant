from flask import Blueprint, request, jsonify
from app import db
from app.models import Whiteboard, WhiteboardDocument, User, StoredFile
from flask_jwt_extended import jwt_required, get_jwt_identity

whiteboards_bp = Blueprint('whiteboards', __name__)


@whiteboards_bp.route('', methods=['GET'])
@jwt_required()
def list_whiteboards():
    user_id = int(get_jwt_identity())
    workspace_id = request.args.get('workspace_id', type=int)
    query = Whiteboard.query.filter(Whiteboard.user_id == user_id)
    if workspace_id:
        query = query.filter(Whiteboard.workspace_id == workspace_id)
    boards = query.order_by(Whiteboard.updated_at.desc()).all()
    return jsonify([{
        'id': w.id,
        'title': w.title,
        'workspace_id': w.workspace_id,
        'created_at': w.created_at.isoformat(),
        'updated_at': w.updated_at.isoformat(),
        'documents_count': w.documents.count(),
    } for w in boards]), 200


@whiteboards_bp.route('', methods=['POST'])
@jwt_required()
def create_whiteboard():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    user = User.query.get(user_id)
    workspace_id = data.get('workspace_id') or (user.current_workspace_id if user else None)
    title = data.get('title') or 'Untitled Whiteboard'
    w = Whiteboard(
        user_id=user_id,
        workspace_id=workspace_id,
        title=title,
        content=data.get('content'),
    )
    db.session.add(w)
    db.session.commit()
    return jsonify({
        'id': w.id,
        'title': w.title,
        'workspace_id': w.workspace_id,
        'content': w.content,
        'created_at': w.created_at.isoformat(),
        'updated_at': w.updated_at.isoformat(),
    }), 201


@whiteboards_bp.route('/<int:whiteboard_id>', methods=['GET'])
@jwt_required()
def get_whiteboard(whiteboard_id):
    user_id = int(get_jwt_identity())
    w = Whiteboard.query.get_or_404(whiteboard_id)
    if w.user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403
    documents = []
    for doc in w.documents.all():
        sf = doc.stored_file
        documents.append({
            'id': doc.id,
            'file_id': sf.id,
            'original_filename': sf.original_filename,
            'content_type': sf.content_type,
            'file_size': sf.file_size,
            'uploaded_by': {'id': doc.uploaded_by.id, 'name': doc.uploaded_by.name},
            'created_at': doc.created_at.isoformat(),
        })
    return jsonify({
        'id': w.id,
        'title': w.title,
        'workspace_id': w.workspace_id,
        'content': w.content,
        'created_at': w.created_at.isoformat(),
        'updated_at': w.updated_at.isoformat(),
        'documents': documents,
    }), 200


@whiteboards_bp.route('/<int:whiteboard_id>', methods=['PUT'])
@jwt_required()
def update_whiteboard(whiteboard_id):
    user_id = int(get_jwt_identity())
    w = Whiteboard.query.get_or_404(whiteboard_id)
    if w.user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403
    data = request.get_json() or {}
    if data.get('title') is not None:
        w.title = data['title']
    if data.get('content') is not None:
        w.content = data['content']
    if data.get('workspace_id') is not None:
        w.workspace_id = data['workspace_id']
    w.updated_at = __import__('datetime').datetime.utcnow()
    db.session.commit()
    return jsonify({
        'id': w.id,
        'title': w.title,
        'content': w.content,
        'updated_at': w.updated_at.isoformat(),
    }), 200


@whiteboards_bp.route('/<int:whiteboard_id>', methods=['DELETE'])
@jwt_required()
def delete_whiteboard(whiteboard_id):
    user_id = int(get_jwt_identity())
    w = Whiteboard.query.get_or_404(whiteboard_id)
    if w.user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403
    db.session.delete(w)
    db.session.commit()
    return jsonify({'message': 'Whiteboard deleted'}), 200


@whiteboards_bp.route('/<int:whiteboard_id>/documents', methods=['GET'])
@jwt_required()
def get_whiteboard_documents(whiteboard_id):
    user_id = int(get_jwt_identity())
    w = Whiteboard.query.get_or_404(whiteboard_id)
    if w.user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403
    documents = [{
        'id': doc.id,
        'file_id': doc.stored_file.id,
        'original_filename': doc.stored_file.original_filename,
        'content_type': doc.stored_file.content_type,
        'file_size': doc.stored_file.file_size,
        'uploaded_by': {'id': doc.uploaded_by.id, 'name': doc.uploaded_by.name},
        'created_at': doc.created_at.isoformat(),
    } for doc in w.documents.all()]
    return jsonify(documents), 200


@whiteboards_bp.route('/<int:whiteboard_id>/documents', methods=['POST'])
@jwt_required()
def add_whiteboard_document(whiteboard_id):
    user_id = int(get_jwt_identity())
    w = Whiteboard.query.get_or_404(whiteboard_id)
    if w.user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403
    data = request.get_json()
    file_id = data.get('file_id') if data else None
    if not file_id:
        return jsonify({'error': 'file_id is required'}), 400
    f = StoredFile.query.filter_by(id=file_id, user_id=user_id).first()
    if not f:
        return jsonify({'error': 'File not found or not owned by you'}), 404
    if w.documents.filter(WhiteboardDocument.stored_file_id == file_id).first():
        return jsonify({'error': 'File already added to this whiteboard'}), 400
    doc = WhiteboardDocument(whiteboard_id=whiteboard_id, stored_file_id=file_id, uploaded_by_id=user_id)
    db.session.add(doc)
    db.session.commit()
    return jsonify({
        'id': doc.id,
        'file_id': f.id,
        'original_filename': f.original_filename,
        'content_type': f.content_type,
        'file_size': f.file_size,
        'uploaded_by': {'id': doc.uploaded_by.id, 'name': doc.uploaded_by.name},
        'created_at': doc.created_at.isoformat(),
    }), 201


@whiteboards_bp.route('/<int:whiteboard_id>/documents/<int:doc_id>', methods=['DELETE'])
@jwt_required()
def remove_whiteboard_document(whiteboard_id, doc_id):
    user_id = int(get_jwt_identity())
    w = Whiteboard.query.get_or_404(whiteboard_id)
    if w.user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403
    doc = WhiteboardDocument.query.filter_by(id=doc_id, whiteboard_id=whiteboard_id).first_or_404()
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document removed from whiteboard'}), 200
