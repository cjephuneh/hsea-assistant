from flask import Blueprint, request, jsonify
from app import db
from app.models import TaskTemplate, Workspace, User, Task, TaskPriority
from flask_jwt_extended import jwt_required, get_jwt_identity

templates_bp = Blueprint('templates', __name__)

@templates_bp.route('', methods=['GET'])
@jwt_required()
def get_templates():
    user_id = int(get_jwt_identity())
    workspace_id = request.args.get('workspace_id', type=int)
    
    query = TaskTemplate.query.filter_by(created_by_id=user_id)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)
    
    templates = query.all()
    
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'title_template': t.title_template,
        'description_template': t.description_template,
        'default_priority': t.default_priority.value,
        'default_category': t.default_category,
        'estimated_hours': t.estimated_hours,
        'workspace_id': t.workspace_id,
        'created_at': t.created_at.isoformat()
    } for t in templates]), 200

@templates_bp.route('', methods=['POST'])
@jwt_required()
def create_template():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('title_template'):
        return jsonify({'error': 'Name and title template are required'}), 400
    
    try:
        priority = TaskPriority[data.get('default_priority', 'MEDIUM').upper()]
    except KeyError:
        priority = TaskPriority.MEDIUM
    
    template = TaskTemplate(
        name=data['name'],
        description=data.get('description', ''),
        workspace_id=data.get('workspace_id'),
        created_by_id=user_id,
        title_template=data['title_template'],
        description_template=data.get('description_template', ''),
        default_priority=priority,
        default_category=data.get('default_category'),
        estimated_hours=data.get('estimated_hours')
    )
    
    db.session.add(template)
    db.session.commit()
    
    return jsonify({
        'id': template.id,
        'name': template.name,
        'title_template': template.title_template,
        'description_template': template.description_template,
        'default_priority': template.default_priority.value,
        'default_category': template.default_category,
        'estimated_hours': template.estimated_hours
    }), 201

@templates_bp.route('/<int:template_id>/create-task', methods=['POST'])
@jwt_required()
def create_task_from_template(template_id):
    user_id = int(get_jwt_identity())
    template = TaskTemplate.query.get_or_404(template_id)
    data = request.get_json()
    
    # Get assignee
    assignee_id = data.get('assignee_id')
    if not assignee_id:
        return jsonify({'error': 'Assignee ID is required'}), 400
    
    # Create task from template
    task = Task(
        title=template.title_template,
        description=template.description_template or '',
        assignee_id=assignee_id,
        created_by_id=user_id,
        workspace_id=template.workspace_id,
        template_id=template_id,
        priority=template.default_priority,
        category=template.default_category,
        estimated_hours=template.estimated_hours
    )
    
    db.session.add(task)
    db.session.commit()
    
    # Create notification
    from app.notifications.service import NotificationService
    NotificationService.create_task_assigned_notification(task)
    
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status.value,
        'priority': task.priority.value
    }), 201
