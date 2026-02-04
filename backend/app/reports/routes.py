from flask import Blueprint, request, jsonify, make_response
from app import db
from app.models import Task, User, TaskStatus, Notification
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import io
import csv

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/task-completion', methods=['GET'])
@jwt_required()
def task_completion_report():
    user_id = int(get_jwt_identity())
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Task.query
    if start_date:
        query = query.filter(Task.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Task.created_at <= datetime.fromisoformat(end_date))
    
    # Get tasks for current user (assigned or created)
    tasks = query.filter(
        (Task.assignee_id == user_id) | (Task.created_by_id == user_id)
    ).all()
    
    total_tasks = len(tasks)
    completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
    in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
    pending = len([t for t in tasks if t.status == TaskStatus.PENDING])
    
    return jsonify({
        'total_tasks': total_tasks,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'completion_rate': (completed / total_tasks * 100) if total_tasks > 0 else 0,
        'tasks': [{
            'id': t.id,
            'title': t.title,
            'status': t.status.value,
            'priority': t.priority.value,
            'created_at': t.created_at.isoformat()
        } for t in tasks]
    }), 200

@reports_bp.route('/user-activity', methods=['GET'])
@jwt_required()
def user_activity_report():
    user_id = int(get_jwt_identity())
    days = int(request.args.get('days', 30))
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Tasks created
    tasks_created = Task.query.filter(
        Task.created_by_id == user_id,
        Task.created_at >= start_date
    ).count()
    
    # Tasks completed
    tasks_completed = Task.query.filter(
        Task.assignee_id == user_id,
        Task.status == TaskStatus.COMPLETED,
        Task.updated_at >= start_date
    ).count()
    
    # Notifications received
    notifications_received = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.created_at >= start_date
    ).count()
    
    return jsonify({
        'period_days': days,
        'tasks_created': tasks_created,
        'tasks_completed': tasks_completed,
        'notifications_received': notifications_received,
        'start_date': start_date.isoformat()
    }), 200

@reports_bp.route('/task-assignment', methods=['GET'])
@jwt_required()
def task_assignment_report():
    """Report on task assignments by user"""
    user_id = int(get_jwt_identity())
    
    # Get all users
    users = User.query.all()
    
    report_data = []
    for user in users:
        assigned_count = Task.query.filter_by(assignee_id=user.id).count()
        completed_count = Task.query.filter_by(
            assignee_id=user.id,
            status=TaskStatus.COMPLETED
        ).count()
        
        report_data.append({
            'user_id': user.id,
            'user_name': user.name,
            'user_email': user.email,
            'tasks_assigned': assigned_count,
            'tasks_completed': completed_count,
            'completion_rate': (completed_count / assigned_count * 100) if assigned_count > 0 else 0
        })
    
    return jsonify({
        'users': report_data
    }), 200

@reports_bp.route('/export/csv', methods=['GET'])
@jwt_required()
def export_tasks_csv():
    user_id = int(get_jwt_identity())
    
    tasks = Task.query.filter(
        (Task.assignee_id == user_id) | (Task.created_by_id == user_id)
    ).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID', 'Title', 'Description', 'Assignee', 'Created By', 'Status', 'Priority', 'Due Date', 'Created At'])
    
    # Data
    for task in tasks:
        writer.writerow([
            task.id,
            task.title,
            task.description or '',
            task.assignee.name,
            task.creator.name,
            task.status.value,
            task.priority.value,
            task.due_date.isoformat() if task.due_date else '',
            task.created_at.isoformat()
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=tasks_export.csv'
    
    return response

@reports_bp.route('/export/pdf', methods=['GET'])
@jwt_required()
def export_tasks_pdf():
    user_id = int(get_jwt_identity())
    
    tasks = Task.query.filter(
        (Task.assignee_id == user_id) | (Task.created_by_id == user_id)
    ).all()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph("Task Report", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Table data
    data = [['ID', 'Title', 'Assignee', 'Status', 'Priority', 'Due Date']]
    
    for task in tasks:
        data.append([
            str(task.id),
            task.title[:30],
            task.assignee.name,
            task.status.value,
            task.priority.value,
            task.due_date.strftime('%Y-%m-%d') if task.due_date else 'N/A'
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    doc.build(story)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=tasks_export.pdf'
    
    return response
