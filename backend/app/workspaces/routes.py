from flask import Blueprint, request, jsonify
from app import db
from app.models import Workspace, WorkspaceMember, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

workspaces_bp = Blueprint('workspaces', __name__)

@workspaces_bp.route('', methods=['GET'])
@jwt_required()
def get_workspaces():
    user_id = int(get_jwt_identity())
    
    # Get workspaces where user is a member
    memberships = WorkspaceMember.query.filter_by(user_id=user_id).all()
    workspace_ids = [m.workspace_id for m in memberships]
    workspaces = Workspace.query.filter(Workspace.id.in_(workspace_ids)).all()
    
    return jsonify([{
        'id': ws.id,
        'name': ws.name,
        'description': ws.description,
        'owner_id': ws.owner_id,
        'member_count': ws.members.count(),
        'created_at': ws.created_at.isoformat()
    } for ws in workspaces]), 200

@workspaces_bp.route('', methods=['POST'])
@jwt_required()
def create_workspace():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Workspace name is required'}), 400
    
    workspace = Workspace(
        name=data['name'],
        description=data.get('description', ''),
        owner_id=user_id
    )
    
    db.session.add(workspace)
    db.session.flush()
    
    # Add creator as owner member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user_id,
        role='owner'
    )
    db.session.add(member)
    db.session.commit()
    
    return jsonify({
        'id': workspace.id,
        'name': workspace.name,
        'description': workspace.description,
        'owner_id': workspace.owner_id
    }), 201

@workspaces_bp.route('/<int:workspace_id>', methods=['GET'])
@jwt_required()
def get_workspace(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Check if user is member
    user_id = int(get_jwt_identity())
    member = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member:
        return jsonify({'error': 'Unauthorized'}), 403
    
    members = [{
        'id': m.user.id,
        'name': m.user.name,
        'email': m.user.email,
        'role': m.role
    } for m in workspace.members.all()]
    
    return jsonify({
        'id': workspace.id,
        'name': workspace.name,
        'description': workspace.description,
        'owner_id': workspace.owner_id,
        'members': members,
        'created_at': workspace.created_at.isoformat()
    }), 200

@workspaces_bp.route('/<int:workspace_id>/members', methods=['POST'])
@jwt_required()
def add_member(workspace_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Check if user is admin/owner
    member = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member or member.role not in ['owner', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if already a member
    existing = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user.id).first()
    if existing:
        return jsonify({'error': 'User is already a member'}), 400
    
    new_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user.id,
        role=data.get('role', 'member')
    )
    
    db.session.add(new_member)
    db.session.commit()
    
    return jsonify({
        'id': new_member.id,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email
        },
        'role': new_member.role
    }), 201

@workspaces_bp.route('/switch', methods=['POST'])
@jwt_required()
def switch_workspace():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    workspace_id = data.get('workspace_id')
    if not workspace_id:
        return jsonify({'error': 'Workspace ID is required'}), 400
    
    # Check if user is member
    member = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    user.current_workspace_id = workspace_id
    db.session.commit()
    
    return jsonify({'message': 'Workspace switched successfully'}), 200
