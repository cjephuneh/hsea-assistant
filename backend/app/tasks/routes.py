from flask import Blueprint, request, jsonify
from app import db
from app.models import Task, User, Comment, TaskStatus, TaskPriority, TaskActivity, TaskDependency, TaskShareType, TaskAttachment, TaskCollaborator, StoredFile
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import or_, func
import secrets
import json

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('', methods=['GET'])
@jwt_required()
def get_tasks():
    user_id = int(get_jwt_identity())
    status_filter = request.args.get('status')
    assignee_filter = request.args.get('assignee_id')
    created_by_filter = request.args.get('created_by_id')
    workspace_filter = request.args.get('workspace_id')
    search = request.args.get('search')
    due_today = request.args.get('due_today', 'false').lower() == 'true'
    
    query = Task.query
    
    # Filter by workspace if specified
    if workspace_filter:
        query = query.filter(Task.workspace_id == workspace_filter)
    else:
        # Get user's current workspace
        user = User.query.get(user_id)
        if user and user.current_workspace_id:
            query = query.filter(Task.workspace_id == user.current_workspace_id)
    
    # Filter by assignee
    if assignee_filter:
        query = query.filter(Task.assignee_id == assignee_filter)
    else:
        # Default: show tasks assigned to current user or created by current user
        query = query.filter(or_(Task.assignee_id == user_id, Task.created_by_id == user_id))
    
    if created_by_filter:
        query = query.filter(Task.created_by_id == created_by_filter)
    
    if status_filter:
        try:
            status = TaskStatus[status_filter.upper()]
            query = query.filter(Task.status == status)
        except KeyError:
            pass
    
    if due_today:
        today = datetime.utcnow().date()
        query = query.filter(func.date(Task.due_date) == today)
    
    if search:
        query = query.filter(or_(
            Task.title.ilike(f'%{search}%'),
            Task.description.ilike(f'%{search}%')
        ))
    
    # Exclude subtasks from main list (show only top-level tasks)
    query = query.filter(Task.parent_task_id.is_(None))
    
    tasks = query.order_by(Task.created_at.desc()).all()
    
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'assignee': {
            'id': task.assignee.id,
            'name': task.assignee.name,
            'email': task.assignee.email
        },
        'created_by': {
            'id': task.creator.id,
            'name': task.creator.name,
            'email': task.creator.email
        },
        'status': task.status.value,
        'priority': task.priority.value,
        'category': task.category,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
        'comments_count': task.comments.count(),
        'subtasks_count': len(task.subtasks) if task.subtasks else 0,
    } for task in tasks]), 200

@tasks_bp.route('', methods=['POST'])
@jwt_required()
def create_task():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('assignee_id'):
        return jsonify({'error': 'Missing required fields: title, assignee_id'}), 400
    
    assignee = User.query.get(data['assignee_id'])
    if not assignee:
        return jsonify({'error': 'Assignee not found'}), 404
    
    try:
        priority = TaskPriority[data.get('priority', 'MEDIUM').upper()]
    except KeyError:
        priority = TaskPriority.MEDIUM
    
    # Get user's current workspace
    user = User.query.get(user_id)
    workspace_id = data.get('workspace_id') or (user.current_workspace_id if user else None)
    parent_task_id = data.get('parent_task_id')
    
    # For subtasks, inherit workspace from parent if not provided
    if parent_task_id and not workspace_id:
        parent = Task.query.get(parent_task_id)
        if parent:
            workspace_id = parent.workspace_id
    
    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        assignee_id=data['assignee_id'],
        created_by_id=user_id,
        workspace_id=workspace_id,
        template_id=data.get('template_id'),
        parent_task_id=parent_task_id,
        priority=priority,
        category=data.get('category'),
        due_date=datetime.fromisoformat(str(data['due_date']).replace('Z', '+00:00')) if data.get('due_date') else None,
        is_recurring=data.get('is_recurring', False),
        recurrence_type=data.get('recurrence_type'),
        recurrence_config=json.dumps(data.get('recurrence_config', {})) if data.get('recurrence_config') else None,
        estimated_hours=data.get('estimated_hours'),
        notes=data.get('notes'),
    )
    
    db.session.add(task)
    db.session.flush()
    
    # Create activity log
    activity = TaskActivity(
        task_id=task.id,
        user_id=user_id,
        activity_type='created',
        description=f'Task "{task.title}" was created'
    )
    db.session.add(activity)
    
    # Add collaborators (additional people on the task)
    collaborator_ids = data.get('collaborator_ids') or []
    for uid in collaborator_ids:
        if uid != data['assignee_id'] and User.query.get(uid):
            db.session.add(TaskCollaborator(task_id=task.id, user_id=uid))
    
    db.session.commit()
    
    # Create notification for assignee
    from app.notifications.service import NotificationService
    NotificationService.create_task_assigned_notification(task)
    
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'assignee': {
            'id': task.assignee.id,
            'name': task.assignee.name,
            'email': task.assignee.email
        },
        'created_by': {
            'id': task.creator.id,
            'name': task.creator.name,
            'email': task.creator.email
        },
        'status': task.status.value,
        'priority': task.priority.value,
        'category': task.category,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'created_at': task.created_at.isoformat()
    }), 201

@tasks_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    comments = [{
        'id': comment.id,
        'content': comment.content,
        'user': {
            'id': comment.user.id,
            'name': comment.user.name,
            'email': comment.user.email
        },
        'created_at': comment.created_at.isoformat()
    } for comment in task.comments.order_by(Comment.created_at.desc()).all()]
    
    # Subtasks (tasks with this task as parent)
    subtasks = Task.query.filter(Task.parent_task_id == task_id).order_by(Task.created_at.asc()).all()
    subtask_list = [{
        'id': st.id,
        'title': st.title,
        'description': st.description,
        'status': st.status.value,
        'priority': st.priority.value,
        'due_date': st.due_date.isoformat() if st.due_date else None,
        'assignee': {'id': st.assignee.id, 'name': st.assignee.name, 'email': st.assignee.email},
        'created_at': st.created_at.isoformat(),
    } for st in subtasks]
    
    # Attachments
    attachments = []
    for att in task.attachments.all():
        sf = att.stored_file
        attachments.append({
            'id': att.id,
            'file_id': sf.id,
            'original_filename': sf.original_filename,
            'content_type': sf.content_type,
            'file_size': sf.file_size,
            'uploaded_by': {'id': att.uploaded_by.id, 'name': att.uploaded_by.name},
            'created_at': att.created_at.isoformat(),
        })
    
    # Collaborators (additional people on the task, excluding primary assignee)
    collaborators = []
    for collab in task.collaborators.all():
        u = collab.user
        collaborators.append({'id': u.id, 'name': u.name, 'email': u.email})
    
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'notes': task.notes,
        'assignee': {
            'id': task.assignee.id,
            'name': task.assignee.name,
            'email': task.assignee.email
        },
        'created_by': {
            'id': task.creator.id,
            'name': task.creator.name,
            'email': task.creator.email
        },
        'status': task.status.value,
        'priority': task.priority.value,
        'category': task.category,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
        'comments': comments,
        'subtasks': subtask_list,
        'attachments': attachments,
        'collaborators': collaborators,
    }), 200

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    
    old_status = task.status.value
    
    if data.get('title'):
        task.title = data['title']
    if data.get('description') is not None:
        task.description = data['description']
    if data.get('assignee_id'):
        assignee = User.query.get(data['assignee_id'])
        if not assignee:
            return jsonify({'error': 'Assignee not found'}), 404
        task.assignee_id = data['assignee_id']
    if data.get('status'):
        try:
            new_status = TaskStatus[data['status'].upper()]
            task.status = new_status
            if old_status != new_status.value:
                # Log status change
                activity = TaskActivity(
                    task_id=task_id,
                    user_id=user_id,
                    activity_type='status_changed',
                    description=f'Status changed from {old_status} to {new_status.value}',
                    activity_metadata=json.dumps({'old_status': old_status, 'new_status': new_status.value})
                )
                db.session.add(activity)
        except KeyError:
            return jsonify({'error': 'Invalid status'}), 400
    if data.get('priority'):
        try:
            task.priority = TaskPriority[data['priority'].upper()]
        except KeyError:
            return jsonify({'error': 'Invalid priority'}), 400
    if data.get('category') is not None:
        task.category = data['category']
    if data.get('due_date') is not None:
        if data['due_date']:
            task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
        else:
            task.due_date = None
    if data.get('actual_hours') is not None:
        task.actual_hours = data['actual_hours']
    if data.get('notes') is not None:
        task.notes = data['notes']
    
    task.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Create notification for status change
    from app.notifications.service import NotificationService
    NotificationService.create_task_updated_notification(task)
    
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status.value,
        'priority': task.priority.value,
        'updated_at': task.updated_at.isoformat()
    }), 200

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted successfully'}), 200

@tasks_bp.route('/<int:task_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'error': 'Comment content is required'}), 400
    
    # Extract mentions from content (@username)
    import re
    mentions = []
    mention_pattern = r'@(\w+)'
    matches = re.findall(mention_pattern, data['content'])
    for username in matches:
        user = User.query.filter(User.name.ilike(f'%{username}%')).first()
        if user:
            mentions.append(user.id)
    
    comment = Comment(
        task_id=task_id,
        user_id=user_id,
        parent_comment_id=data.get('parent_comment_id'),
        content=data['content'],
        mentions=json.dumps(mentions) if mentions else None
    )
    
    db.session.add(comment)
    
    # Create activity
    activity = TaskActivity(
        task_id=task_id,
        user_id=user_id,
        activity_type='commented',
        description=f'Added a comment'
    )
    db.session.add(activity)
    db.session.commit()
    
    # Notify mentioned users
    if mentions:
        from app.notifications.service import NotificationService
        for mentioned_id in mentions:
            NotificationService.create_mention_notification(mentioned_id, task_id, comment.id)
    
    return jsonify({
        'id': comment.id,
        'content': comment.content,
        'parent_comment_id': comment.parent_comment_id,
        'mentions': mentions,
        'user': {
            'id': comment.user.id,
            'name': comment.user.name,
            'email': comment.user.email
        },
        'created_at': comment.created_at.isoformat()
    }), 201

@tasks_bp.route('/<int:task_id>/share', methods=['POST'])
@jwt_required()
def share_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    
    share_type = data.get('share_type', 'private')
    try:
        task.share_type = TaskShareType[share_type.upper()]
    except KeyError:
        return jsonify({'error': 'Invalid share type'}), 400
    
    if task.share_type == TaskShareType.PUBLIC:
        # Generate share token
        task.share_token = secrets.token_urlsafe(32)
    
    db.session.commit()
    
    return jsonify({
        'share_type': task.share_type.value,
        'share_token': task.share_token,
        'share_url': f'/tasks/shared/{task.share_token}' if task.share_token else None
    }), 200

@tasks_bp.route('/shared/<token>', methods=['GET'])
def get_shared_task(token):
    task = Task.query.filter_by(share_token=token, share_type=TaskShareType.PUBLIC).first_or_404()
    
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status.value,
        'priority': task.priority.value,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'created_at': task.created_at.isoformat()
    }), 200

@tasks_bp.route('/<int:task_id>/dependencies', methods=['POST'])
@jwt_required()
def add_dependency(task_id):
    data = request.get_json()
    depends_on_id = data.get('depends_on_id')
    
    if not depends_on_id:
        return jsonify({'error': 'depends_on_id is required'}), 400
    
    if task_id == depends_on_id:
        return jsonify({'error': 'Task cannot depend on itself'}), 400
    
    # Check for circular dependencies
    # (simplified check - in production, do a full graph traversal)
    
    dependency = TaskDependency(
        task_id=task_id,
        depends_on_id=depends_on_id
    )
    
    db.session.add(dependency)
    db.session.commit()
    
    return jsonify({
        'id': dependency.id,
        'task_id': dependency.task_id,
        'depends_on_id': dependency.depends_on_id
    }), 201

@tasks_bp.route('/<int:task_id>/activities', methods=['GET'])
@jwt_required()
def get_task_activities(task_id):
    task = Task.query.get_or_404(task_id)
    activities = task.activities.limit(50).all()
    
    return jsonify([{
        'id': act.id,
        'activity_type': act.activity_type,
        'description': act.description,
        'user': {
            'id': act.user.id,
            'name': act.user.name,
            'email': act.user.email
        },
        'metadata': json.loads(act.activity_metadata) if act.activity_metadata else None,
        'created_at': act.created_at.isoformat()
    } for act in activities]), 200

@tasks_bp.route('/due-today', methods=['GET'])
@jwt_required()
def get_tasks_due_today():
    user_id = int(get_jwt_identity())
    today = datetime.utcnow().date()
    
    tasks = Task.query.filter(
        Task.assignee_id == user_id,
        func.date(Task.due_date) == today
    ).all()
    
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'status': task.status.value,
        'priority': task.priority.value,
        'due_date': task.due_date.isoformat()
    } for task in tasks]), 200

@tasks_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'phone': user.phone
    } for user in users]), 200


@tasks_bp.route('/<int:task_id>/attachments', methods=['GET'])
@jwt_required()
def get_task_attachments(task_id):
    task = Task.query.get_or_404(task_id)
    user_id = int(get_jwt_identity())
    if task.assignee_id != user_id and task.created_by_id != user_id:
        if not any(c.user_id == user_id for c in task.collaborators.all()):
            return jsonify({'error': 'Not authorized'}), 403
    attachments = []
    for att in task.attachments.all():
        sf = att.stored_file
        attachments.append({
            'id': att.id,
            'file_id': sf.id,
            'original_filename': sf.original_filename,
            'content_type': sf.content_type,
            'file_size': sf.file_size,
            'uploaded_by': {'id': att.uploaded_by.id, 'name': att.uploaded_by.name},
            'created_at': att.created_at.isoformat(),
        })
    return jsonify(attachments), 200


@tasks_bp.route('/<int:task_id>/attachments', methods=['POST'])
@jwt_required()
def add_task_attachment(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    if task.assignee_id != user_id and task.created_by_id != user_id:
        if not any(c.user_id == user_id for c in task.collaborators.all()):
            return jsonify({'error': 'Not authorized'}), 403
    data = request.get_json()
    file_id = data.get('file_id')
    if not file_id:
        return jsonify({'error': 'file_id is required'}), 400
    f = StoredFile.query.filter_by(id=file_id, user_id=user_id).first()
    if not f:
        return jsonify({'error': 'File not found or not owned by you'}), 404
    if task.attachments.filter(TaskAttachment.stored_file_id == file_id).first():
        return jsonify({'error': 'File already attached to this task'}), 400
    att = TaskAttachment(task_id=task_id, stored_file_id=file_id, uploaded_by_id=user_id)
    db.session.add(att)
    db.session.commit()
    return jsonify({
        'id': att.id,
        'file_id': f.id,
        'original_filename': f.original_filename,
        'content_type': f.content_type,
        'file_size': f.file_size,
        'uploaded_by': {'id': att.uploaded_by.id, 'name': att.uploaded_by.name},
        'created_at': att.created_at.isoformat(),
    }), 201


@tasks_bp.route('/<int:task_id>/attachments/<int:att_id>', methods=['DELETE'])
@jwt_required()
def delete_task_attachment(task_id, att_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    if task.assignee_id != user_id and task.created_by_id != user_id:
        if not any(c.user_id == user_id for c in task.collaborators.all()):
            return jsonify({'error': 'Not authorized'}), 403
    att = TaskAttachment.query.filter_by(id=att_id, task_id=task_id).first_or_404()
    db.session.delete(att)
    db.session.commit()
    return jsonify({'message': 'Attachment removed'}), 200


@tasks_bp.route('/<int:task_id>/collaborators', methods=['GET'])
@jwt_required()
def get_task_collaborators(task_id):
    task = Task.query.get_or_404(task_id)
    user_id = int(get_jwt_identity())
    if task.assignee_id != user_id and task.created_by_id != user_id:
        if not any(c.user_id == user_id for c in task.collaborators.all()):
            return jsonify({'error': 'Not authorized'}), 403
    collaborators = [{'id': c.user.id, 'name': c.user.name, 'email': c.user.email} for c in task.collaborators.all()]
    return jsonify(collaborators), 200


@tasks_bp.route('/<int:task_id>/collaborators', methods=['POST'])
@jwt_required()
def add_task_collaborator(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    if task.assignee_id != user_id and task.created_by_id != user_id:
        return jsonify({'error': 'Only assignee or creator can add collaborators'}), 403
    data = request.get_json()
    collaborator_user_id = data.get('user_id')
    if not collaborator_user_id:
        return jsonify({'error': 'user_id is required'}), 400
    if collaborator_user_id == task.assignee_id:
        return jsonify({'error': 'User is already the assignee'}), 400
    if not User.query.get(collaborator_user_id):
        return jsonify({'error': 'User not found'}), 404
    if task.collaborators.filter(TaskCollaborator.user_id == collaborator_user_id).first():
        return jsonify({'error': 'User is already a collaborator'}), 400
    db.session.add(TaskCollaborator(task_id=task_id, user_id=collaborator_user_id))
    db.session.commit()
    u = User.query.get(collaborator_user_id)
    return jsonify({'id': u.id, 'name': u.name, 'email': u.email}), 201


@tasks_bp.route('/<int:task_id>/collaborators/<int:collab_user_id>', methods=['DELETE'])
@jwt_required()
def remove_task_collaborator(task_id, collab_user_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    if task.assignee_id != user_id and task.created_by_id != user_id:
        return jsonify({'error': 'Only assignee or creator can remove collaborators'}), 403
    collab = TaskCollaborator.query.filter_by(task_id=task_id, user_id=collab_user_id).first_or_404()
    db.session.delete(collab)
    db.session.commit()
    return jsonify({'message': 'Collaborator removed'}), 200
