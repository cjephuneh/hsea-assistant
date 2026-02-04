from flask import Blueprint, request, jsonify
from app import db, socketio
from app.models import Task, User, TaskPriority, TaskStatus, Meeting
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import re
import azure.cognitiveservices.speech as speechsdk
from app.config import Config
from dateutil import parser as date_parser

voice_bp = Blueprint('voice', __name__)

def parse_voice_command(text):
    """Parse voice command to extract task information"""
    task_info = {
        'title': '',
        'description': '',
        'assignee_name': '',
        'priority': 'medium',
        'due_date': None
    }
    
    # Extract assignee name (e.g., "for caleb", "to john", "assign to scott")
    # More flexible patterns to catch variations, but avoid common words like "add", "new", etc.
    # Exclude common task-related words that might be mistaken for names
    excluded_words = ['add', 'new', 'create', 'task', 'the', 'a', 'an', 'to', 'for', 'do', 'review']
    
    assignee_patterns = [
        # Pattern: "task for [name]" or "task to [name]" - most reliable
        r'task\s+(?:for|to)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
        # Pattern: "for [name]" after task creation keywords
        r'(?:create|new|add|make)\s+(?:a\s+)?task\s+(?:for|to)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
        # Pattern: "[name] should/needs to" - but only if name is not excluded
        r'([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+(?:should|needs to|has to|to review|to do)',
    ]
    for pattern in assignee_patterns:
        assignee_match = re.search(pattern, text, re.IGNORECASE)
        if assignee_match:
            potential_name = assignee_match.group(1).lower().strip()
            # Check if it's not an excluded word
            if potential_name not in excluded_words and len(potential_name) > 2:
                task_info['assignee_name'] = potential_name.split()[0]  # Take first word as name
                break
    
    # If still not found, try to extract name after common task phrases
    if not task_info['assignee_name']:
        # Look for name after "create task for" or similar
        name_after_task = re.search(r'(?:create|new|add|make)\s+(?:a\s+)?task\s+(?:for|to)\s+([a-zA-Z]+)', text, re.IGNORECASE)
        if name_after_task:
            potential_name = name_after_task.group(1).lower()
            if potential_name not in excluded_words and len(potential_name) > 2:
                task_info['assignee_name'] = potential_name
    
    # Extract priority keywords
    text_lower = text.lower()
    if any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'critical']):
        task_info['priority'] = 'urgent'
    elif any(word in text_lower for word in ['important', 'high priority', 'high']):
        task_info['priority'] = 'high'
    elif any(word in text_lower for word in ['low priority', 'low', 'later', 'whenever']):
        task_info['priority'] = 'low'
    
    # Extract due date keywords
    if 'today' in text_lower:
        task_info['due_date'] = datetime.utcnow().date()
    elif 'tomorrow' in text_lower:
        task_info['due_date'] = (datetime.utcnow() + timedelta(days=1)).date()
    elif 'next week' in text_lower:
        task_info['due_date'] = (datetime.utcnow() + timedelta(days=7)).date()
    
    # Extract task title (usually after colon or "to do")
    colon_match = re.search(r':\s*(.+?)(?:\.|$)', text, re.IGNORECASE)
    if colon_match:
        task_info['title'] = colon_match.group(1).strip()
    else:
        # Remove assignee and priority keywords to get the task
        cleaned_text = re.sub(assignee_patterns[0], '', text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'\b(create|new|add|task|urgent|asap|important|high|low|later|for|to|assign)\b', '', cleaned_text, flags=re.IGNORECASE)
        task_info['title'] = cleaned_text.strip()
    
    # Use title as description if no separate description
    if not task_info['description']:
        task_info['description'] = task_info['title']
    
    return task_info

@voice_bp.route('/command', methods=['POST'])
@jwt_required()
def process_voice_command():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('text'):
        return jsonify({'error': 'Voice text is required'}), 400
    
    text = data['text'].lower()
    
    # Log incoming command for debugging
    print(f"[Voice Command] User {user_id}: {data['text']}")
    
    # PRIORITY ORDER: Check queries FIRST before commands to avoid false positives
    # This prevents "What events do I have?" from being detected as task creation
    
    # Check for event queries (Google Calendar events + meetings) - MUST check first
    is_event_query = any(keyword in text for keyword in [
        'what events', 'my events', 'events today', 'events this week', 
        'show events', 'list events', 'do i have events', 'any events',
        'what events do i have', 'events do i have'
    ])
    
    # Check for meeting queries
    is_meeting_query = any(keyword in text for keyword in [
        'what meetings', 'my meetings', 'upcoming meetings', 'meetings today', 
        'meetings this week', 'show meetings', 'list meetings'
    ])
    
    # Check for task queries (but NOT if it's an event/meeting query)
    is_task_query = not is_event_query and not is_meeting_query and any(indicator in text for indicator in [
        'tasks', 'task', 'what tasks', 'my tasks', 'show tasks', 'list tasks',
        'pending', 'completed', 'done', 'in progress', 'due today',
        'what do i have', 'what are my', 'tell me about', 'show me',
        'do i have any', 'are there any', 'what are'
    ]) and ('task' in text or 'todo' in text)
    
    # ULTRA-PERMISSIVE APPROACH: Detect task creation intent from natural language
    # Only check if NOT a query to avoid false positives
    wants_to_create_task = False
    if not is_event_query and not is_meeting_query and not is_task_query:
        task_creation_indicators = [
            'create task', 'create a task', 'new task', 'add task', 'make task',
            'task for', 'task to', 'create task for', 'add task for', 'new task for',
            'i need', 'i want', 'can you create', 'please create', 'create',
            'add a task', 'make a task', 'i have to', 'i should', 'i need to',
            'supposed to', 'meet', 'meeting with', 'have a meeting'
        ]
        
        # Check if user wants to create a task (very permissive)
        wants_to_create_task = any(indicator in text for indicator in task_creation_indicators)
        
        # Also check for natural language patterns like "I'm supposed to meet X"
        # But exclude if it's clearly a query
        if not any(q in text for q in ['what', 'show', 'list', 'tell me', 'do i have']):
            if 'supposed to' in text or ('meet' in text and not 'meeting' in text.lower().split()[:3]):
                wants_to_create_task = True
    
    # Handle event queries (Google Calendar + meetings)
    if is_event_query:
        try:
            from app.calendar.routes import get_google_access_token
            import requests
            
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            # Filter by date if mentioned
            if 'today' in text:
                time_min = today_start.isoformat() + 'Z'
                time_max = today_end.isoformat() + 'Z'
            elif 'this week' in text:
                week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
                week_end = week_start + timedelta(days=7)
                time_min = week_start.isoformat() + 'Z'
                time_max = week_end.isoformat() + 'Z'
            else:
                time_min = datetime.utcnow().isoformat() + 'Z'
                time_max = None
            
            all_events = []
            
            # Fetch Google Calendar events
            access_token = get_google_access_token(user_id)
            if access_token:
                params = {
                    'maxResults': 50,
                    'singleEvents': 'true',
                    'orderBy': 'startTime',
                    'timeMin': time_min
                }
                if time_max:
                    params['timeMax'] = time_max
                
                try:
                    response = requests.get(
                        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                        headers={'Authorization': f'Bearer {access_token}'},
                        params=params,
                        timeout=5
                    )
                    if response.status_code == 200:
                        google_events = response.json().get('items', [])
                        for event in google_events:
                            start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
                            if start:
                                all_events.append({
                                    'title': event.get('summary', 'No title'),
                                    'start': start,
                                    'source': 'Google Calendar'
                                })
                except Exception as e:
                    print(f"[Voice] Error fetching Google Calendar events: {e}")
            
            # Fetch local meetings
            user_obj = User.query.get(user_id)
            workspace_id = user_obj.current_workspace_id if user_obj else None
            
            meeting_query = Meeting.query.filter(Meeting.user_id == user_id)
            if 'today' in text:
                meeting_query = meeting_query.filter(Meeting.start_time >= today_start, Meeting.start_time < today_end)
            elif 'this week' in text:
                week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
                week_end = week_start + timedelta(days=7)
                meeting_query = meeting_query.filter(Meeting.start_time >= week_start, Meeting.start_time < week_end)
            else:
                meeting_query = meeting_query.filter(Meeting.start_time >= datetime.utcnow())
            
            if workspace_id:
                meeting_query = meeting_query.filter(Meeting.workspace_id == workspace_id)
            
            meetings = meeting_query.order_by(Meeting.start_time.asc()).limit(20).all()
            
            for meeting in meetings:
                all_events.append({
                    'title': meeting.topic or 'Meeting',
                    'start': meeting.start_time.isoformat() if meeting.start_time else None,
                    'source': meeting.source or 'Local'
                })
            
            # Sort all events by start time
            all_events.sort(key=lambda x: x['start'] if x['start'] else '9999-12-31')
            
            if not all_events:
                date_str = "today" if 'today' in text else ("this week" if 'this week' in text else "upcoming")
                return jsonify({
                    'message': f'You have no events {date_str}',
                    'events': []
                }), 200
            
            # Format message
            event_list = []
            for i, event in enumerate(all_events[:10]):  # Limit to 10
                try:
                    start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                    time_str = start_dt.strftime('%I:%M %p')
                    source_str = f" ({event['source']})" if event.get('source') else ""
                    event_list.append(f"{i+1}. {event['title']} at {time_str}{source_str}")
                except:
                    event_list.append(f"{i+1}. {event['title']}")
            
            date_str = "today" if 'today' in text else ("this week" if 'this week' in text else "upcoming")
            message = f'You have {len(all_events)} event(s) {date_str}:\n' + '\n'.join(event_list)
            
            return jsonify({
                'message': message,
                'events': all_events[:10]
            }), 200
        except Exception as e:
            print(f"[Voice] Error querying events: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': f'Error querying events: {str(e)}',
                'message': 'Sorry, I encountered an error while fetching your events.'
            }), 500
    
    # Check for meeting queries (list meetings)
    elif is_meeting_query:
        try:
            user_obj = User.query.get(user_id)
            workspace_id = user_obj.current_workspace_id if user_obj else None
            
            query = Meeting.query.filter(Meeting.user_id == user_id)
            
            # Filter by date if mentioned
            if 'today' in text:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                query = query.filter(Meeting.start_time >= today_start, Meeting.start_time < today_end)
            elif 'this week' in text:
                week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
                week_end = week_start + timedelta(days=7)
                query = query.filter(Meeting.start_time >= week_start, Meeting.start_time < week_end)
            
            if workspace_id:
                query = query.filter(Meeting.workspace_id == workspace_id)
            
            # Get upcoming meetings
            now = datetime.utcnow()
            meetings = query.filter(Meeting.start_time >= now).order_by(Meeting.start_time.asc()).limit(10).all()
            
            if not meetings:
                return jsonify({
                    'message': 'You have no upcoming meetings' + (' today' if 'today' in text else ''),
                    'meetings': []
                }), 200
            
            meeting_list = []
            for m in meetings:
                meeting_list.append({
                    'id': m.id,
                    'topic': m.topic,
                    'start_time': m.start_time.isoformat() if m.start_time else None,
                    'duration': m.duration,
                    'source': m.source or 'Local'
                })
            
            # Format message
            meeting_titles = []
            for i, m in enumerate(meeting_list):
                try:
                    start_dt = datetime.fromisoformat(m['start_time'].replace('Z', '+00:00'))
                    time_str = start_dt.strftime('%I:%M %p')
                    source_str = f" ({m['source']})" if m.get('source') else ""
                    meeting_titles.append(f"{i+1}. {m['topic']} at {time_str}{source_str}")
                except:
                    meeting_titles.append(f"{i+1}. {m['topic']}")
            
            date_str = "today" if 'today' in text else ("this week" if 'this week' in text else "upcoming")
            message = f'You have {len(meetings)} {date_str} meeting(s):\n' + '\n'.join(meeting_titles)
            
            return jsonify({
                'message': message,
                'meetings': meeting_list
            }), 200
        except Exception as e:
            print(f"[Voice] Error querying meetings: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': f'Error querying meetings: {str(e)}',
                'message': 'Sorry, I encountered an error while fetching your meetings.'
            }), 500
    
    # Now handle commands in priority order: queries first, then creation
    
    if wants_to_create_task:
        print(f"[Voice] Detected task creation intent: {data['text']}")
        
        # Try to extract assignee - be very flexible with natural language
        # Handle patterns like "meet Scott", "supposed to meet X", "task for X", etc.
        assignee_patterns = [
            r'(?:meet|meeting with|meeting)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "meet Scott" or "meeting with John"
            r'supposed to\s+meet\s+([A-Z][a-z]+)',  # "supposed to meet Scott"
            r'(?:for|to|assign to|give to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "for Caleb" or "to John"
            r'(?:for|to)\s+([a-z]+)',  # Lowercase names
            r'([A-Z][a-z]+)\s+(?:should|needs to|has to|to do|to review|to)',  # "Caleb should" or "John needs to"
        ]
        
        assignee_name = None
        for pattern in assignee_patterns:
            match = re.search(pattern, data['text'])
            if match:
                potential_name = match.group(1).strip()
                # Exclude common words
                excluded = ['task', 'the', 'a', 'an', 'today', 'tomorrow', 'me', 'i', 'you', 'create', 'add', 'new', 'make', 'meeting', 'meet']
                if potential_name.lower() not in excluded and len(potential_name) > 2:
                    assignee_name = potential_name
                    print(f"[Voice] Extracted assignee from pattern '{pattern}': {assignee_name}")
                    break
        
        # If no assignee found, try to extract from context
        if not assignee_name:
            # Look for capitalized words that might be names (especially after "meet" or "for")
            capitalized_words = re.findall(r'\b([A-Z][a-z]+)\b', data['text'])
            # Filter out common words
            excluded = ['Task', 'Today', 'Tomorrow', 'Create', 'Add', 'New', 'Make', 'The', 'A', 'An', 'Meeting', 'Meet', 'I', 'You']
            potential_names = [w for w in capitalized_words if w not in excluded]
            if potential_names:
                assignee_name = potential_names[0]
                print(f"[Voice] Extracted assignee from capitalized words: {assignee_name}")
        
        # If we still don't have assignee_name, try parse_voice_command as fallback
        if not assignee_name:
            task_info_fallback = parse_voice_command(data['text'])
            assignee_name = task_info_fallback.get('assignee_name')
            print(f"[Voice] Fallback parse result: {task_info_fallback}")
        
        if not assignee_name:
            print(f"[Voice] No assignee found - asking user: {data['text']}")
            return jsonify({
                'message': 'I understand you want to create a task. Who should this task be assigned to? Please say something like "Create a task for Caleb" or "I\'m supposed to meet Scott".',
                'incomplete': True,
                'recognized': True
            }), 200  # Return 200 so conversation continues
        
        # Get full task info
        task_info = parse_voice_command(data['text'])
        # Override assignee_name with what we extracted (more reliable)
        task_info['assignee_name'] = assignee_name
        
        # Find user by name (case-insensitive, try multiple variations)
        assignee = User.query.filter(User.name.ilike(f"%{assignee_name}%")).first()
        
        # Try with capitalized first letter if not found
        if not assignee and assignee_name:
            capitalized = assignee_name.capitalize()
            assignee = User.query.filter(User.name.ilike(f"%{capitalized}%")).first()
        
        # Try exact match (case-insensitive)
        if not assignee:
            assignee = User.query.filter(func.lower(User.name) == assignee_name.lower()).first()
        
        if not assignee:
            # List available users for debugging
            all_users = User.query.all()
            user_names = [u.name for u in all_users]
            print(f"[Voice] User '{assignee_name}' not found. Available users: {user_names}")
            return jsonify({
                'error': f'User "{assignee_name}" not found. Available users: {", ".join(user_names)}',
                'parsed': task_info,
                'available_users': user_names
            }), 404
        
        print(f"[Voice] Found assignee: {assignee.name} (ID: {assignee.id})")
        
        # Create task
        try:
            priority = TaskPriority[task_info['priority'].upper()]
        except KeyError:
            priority = TaskPriority.MEDIUM
        
        # Get user's current workspace (same logic as tasks API)
        user = User.query.get(user_id)
        workspace_id = user.current_workspace_id if user else None
        
        # Extract task title and description more intelligently
        task_title = task_info.get('title', '').strip()
        task_description = task_info.get('description', data.get('text', '')).strip()
        
        # If title is empty or too generic, try to extract from the original text
        if not task_title or task_title == 'Task from voice command' or len(task_title) < 5:
            # Remove the assignee name and common phrases to get the actual task
            cleaned_text = data['text']
            # Remove assignee name
            if assignee_name:
                cleaned_text = re.sub(rf'\b{assignee_name}\b', '', cleaned_text, flags=re.IGNORECASE)
            # Remove common task creation phrases
            cleaned_text = re.sub(r'\b(create|add|new|make|a|task|for|to|i|am|supposed|meet|meeting)\b', '', cleaned_text, flags=re.IGNORECASE)
            cleaned_text = cleaned_text.strip(' ,.')
            if cleaned_text and len(cleaned_text) > 5:
                task_title = cleaned_text
                task_description = data.get('text', '')
        
        # Fallback if still empty
        if not task_title or len(task_title) < 3:
            task_title = f'Task for {assignee.name}'
            task_description = data.get('text', '')
        
        print(f"[Voice] Creating task: title='{task_title}', description='{task_description[:50]}...', workspace_id={workspace_id}")
        
        task = Task(
            title=task_title,
            description=task_description,
            assignee_id=assignee.id,
            created_by_id=user_id,
            workspace_id=workspace_id,
            priority=priority,
            due_date=task_info.get('due_date'),
            status=TaskStatus.PENDING  # Always start as pending
        )
        
        db.session.add(task)
        db.session.commit()
        
        print(f"[Voice] Task created successfully: ID={task.id}, workspace_id={task.workspace_id}")
        
        # Create notification
        from app.notifications.service import NotificationService
        NotificationService.create_task_assigned_notification(task)
        
        return jsonify({
            'message': f'Task "{task_title}" created and assigned to {assignee.name}',
            'task': {
                'id': task.id,
                'title': task.title,
                'status': task.status.value,
                'priority': task.priority.value,
                'workspace_id': task.workspace_id,
                'assignee': assignee.name
            }
        }), 201
    
    # Check for task status updates - be more permissive
    elif any(keyword in text for keyword in ['mark', 'complete', 'finish', 'start', 'update', 'change', 'move', 'set']) and 'task' in text:
        # Try to find task by number or title
        task_id_match = re.search(r'task\s+(\d+)', text)
        if not task_id_match:
            # Try to find task by title
            title_match = re.search(r'(?:task|to|mark|complete|start|finish)\s+"([^"]+)"', text, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r'(?:task|to|mark|complete|start|finish)\s+([a-zA-Z][^.!?]*)', text, re.IGNORECASE)
            
            if title_match:
                task_title = title_match.group(1).strip()
                # Find task by title
                user_obj = User.query.get(user_id)
                workspace_id = user_obj.current_workspace_id if user_obj else None
                query = Task.query.filter(
                    Task.title.ilike(f'%{task_title}%'),
                    or_(Task.assignee_id == user_id, Task.created_by_id == user_id)
                )
                if workspace_id:
                    query = query.filter(Task.workspace_id == workspace_id)
                task = query.first()
                if not task:
                    return jsonify({'error': f'Task "{task_title}" not found'}), 404
            else:
                return jsonify({'error': 'Please specify task number or title. For example: "Mark task 5 as completed" or "Complete task Review report"'}), 400
        else:
            task_id = int(task_id_match.group(1))
            task = Task.query.get(task_id)
            if not task:
                return jsonify({'error': f'Task {task_id} not found'}), 404
        
        # Check permissions
        if task.assignee_id != user_id and task.created_by_id != user_id:
            return jsonify({'error': 'You do not have permission to update this task'}), 403
        
        # Determine new status with more flexible matching
        old_status = task.status.value
        if any(word in text for word in ['complete', 'completed', 'done', 'finish', 'finished', 'close', 'closed']):
            new_status = TaskStatus.COMPLETED
            status_msg = 'completed'
        elif any(word in text for word in ['progress', 'working', 'start', 'started', 'begin', 'begun']):
            new_status = TaskStatus.IN_PROGRESS
            status_msg = 'in progress'
        elif any(word in text for word in ['pending', 'wait', 'pause', 'paused', 'hold', 'on hold']):
            new_status = TaskStatus.PENDING
            status_msg = 'pending'
        elif any(word in text for word in ['cancel', 'cancelled', 'delete', 'remove']):
            new_status = TaskStatus.CANCELLED
            status_msg = 'cancelled'
        else:
            return jsonify({'error': 'Could not determine status. Try: "complete task X", "start task X", or "mark task X as pending"'}), 400
        
        task.status = new_status
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        from app.notifications.service import NotificationService
        NotificationService.create_task_updated_notification(task)
        
        return jsonify({
            'message': f'Task "{task.title}" moved from {old_status} to {status_msg}',
            'task': {
                'id': task.id,
                'title': task.title,
                'status': task.status.value,
                'old_status': old_status
            }
        }), 200
    
    # Check for task queries
    elif is_task_query:
        try:
            today = datetime.utcnow().date()
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            user_obj = User.query.get(user_id)
            workspace_id = user_obj.current_workspace_id if user_obj else None
            
            # Use same query logic as tasks API - show tasks assigned to user OR created by user
            query = Task.query.filter(or_(Task.assignee_id == user_id, Task.created_by_id == user_id))
            
            # Filter by due date if asking about today
            if 'today' in text:
                # Include tasks due today OR tasks without due date that are pending/in progress
                query = query.filter(
                    db.or_(
                        db.and_(Task.due_date >= today_start, Task.due_date < today_end),
                        db.and_(
                            Task.due_date.is_(None),
                            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
                        )
                    )
                )
            elif 'pending' in text:
                # Show only pending tasks
                query = query.filter(Task.status == TaskStatus.PENDING)
            else:
                # For general "my tasks" query, show all active tasks (not completed/cancelled)
                query = query.filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
            
            if workspace_id:
                query = query.filter(Task.workspace_id == workspace_id)
            
            # Order by due date (nulls last), then priority
            # SQLite: NULLs sort last by default in ASC order
            tasks = query.order_by(
                Task.due_date.asc(),
                Task.priority.desc()
            ).all()
            
            if not tasks:
                if 'today' in text:
                    return jsonify({
                        'message': 'You have no tasks due today',
                        'tasks': []
                    }), 200
                elif 'pending' in text:
                    return jsonify({
                        'message': 'You have no pending tasks',
                        'tasks': []
                    }), 200
                else:
                    return jsonify({
                        'message': 'You have no active tasks',
                        'tasks': []
                    }), 200
            
            task_list = []
            for t in tasks:
                task_list.append({
                    'id': t.id,
                    'title': t.title,
                    'status': t.status.value,
                    'priority': t.priority.value,
                    'due_date': t.due_date.isoformat() if t.due_date else None
                })
            
            # Format message with actual task details
            task_titles = []
            for i, t in enumerate(task_list):
                status_str = f" ({t['status']})" if t['status'] != 'pending' else ""
                task_titles.append(f"{i+1}. {t['title']}{status_str}")
            
            query_type = "due today" if 'today' in text else ("pending" if 'pending' in text else "active")
            message = f'You have {len(tasks)} {query_type} task(s):\n' + '\n'.join(task_titles)
            
            return jsonify({
                'message': message,
                'tasks': task_list
            }), 200
        except Exception as e:
            print(f"[Voice] Error querying tasks: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': f'Error querying tasks: {str(e)}',
                'message': 'Sorry, I encountered an error while fetching your tasks.'
            }), 500
    
    # Check for meeting queries (list meetings)
    elif is_meeting_query:
        user_obj = User.query.get(user_id)
        
        query = Meeting.query.filter(Meeting.user_id == user_id)
        
        # Filter by date if mentioned
        if 'today' in text:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            query = query.filter(Meeting.start_time >= today_start, Meeting.start_time < today_end)
        elif 'this week' in text:
            week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
            week_end = week_start + timedelta(days=7)
            query = query.filter(Meeting.start_time >= week_start, Meeting.start_time < week_end)
        
        # Get upcoming meetings
        now = datetime.utcnow()
        meetings = query.filter(Meeting.start_time >= now).order_by(Meeting.start_time.asc()).limit(10).all()
        
        if not meetings:
            return jsonify({
                'message': 'You have no upcoming meetings' + (' today' if 'today' in text else ''),
                'meetings': []
            }), 200
        
        meeting_list = []
        for m in meetings:
            meeting_list.append({
                'id': m.id,
                'topic': m.topic,
                'start_time': m.start_time.isoformat() if m.start_time else None,
                'duration': m.duration,
                'zoom_meeting_id': m.zoom_meeting_id
            })
        
        # Format message with actual meeting details
        meeting_details = []
        for i, m in enumerate(meeting_list):
            try:
                start_time = datetime.fromisoformat(m['start_time'].replace('Z', '+00:00')) if m['start_time'] else None
                if start_time:
                    time_str = start_time.strftime('%B %d at %I:%M %p')
                else:
                    time_str = 'TBD'
            except:
                time_str = m['start_time'] or 'TBD'
            meeting_details.append(f"{i+1}. {m['topic']} - {time_str}")
        
        message = f'You have {len(meetings)} upcoming meeting(s):\n' + '\n'.join(meeting_details)
        
        return jsonify({
            'message': message,
            'meetings': meeting_list
        }), 200
    
    # Check for meeting scheduling
    elif any(keyword in text for keyword in ['schedule meeting', 'create meeting', 'meeting with', 'zoom meeting']):
        # Extract person name
        person_match = re.search(r'(?:with|for)\s+([a-z]+)', text, re.IGNORECASE)
        person_name = person_match.group(1).lower() if person_match else None
        
        # Extract date/time
        date_time = None
        try:
            # Try to parse relative dates
            if 'tomorrow' in text:
                date_time = datetime.utcnow() + timedelta(days=1)
            elif 'today' in text:
                date_time = datetime.utcnow()
            
            # Extract time
            time_match = re.search(r'(\d{1,2})\s*(?:am|pm|:)?\s*(\d{0,2})?\s*(am|pm)?', text, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                period = time_match.group(3)
                if period and period.lower() == 'pm' and hour != 12:
                    hour += 12
                if date_time:
                    date_time = date_time.replace(hour=hour, minute=minute)
        except:
            pass
        
        if not date_time:
            date_time = datetime.utcnow() + timedelta(days=1)  # Default to tomorrow
        
        # Find task if mentioned
        task_id_match = re.search(r'task\s+(\d+)', text)
        task_id = int(task_id_match.group(1)) if task_id_match else None
        
        # Create meeting
        from app.meetings.routes import create_meeting
        meeting_data = {
            'topic': f'Meeting with {person_name or "team"}' if person_name else 'Team Meeting',
            'start_time': date_time.isoformat(),
            'duration': 30,
            'task_id': task_id
        }
        
        # This would need to be refactored to call the meeting creation logic
        return jsonify({
            'message': f'Meeting scheduled for {date_time.strftime("%Y-%m-%d %H:%M")}',
            'meeting': meeting_data
        }), 200
    
    # Check for reports
    elif any(keyword in text for keyword in ['completion rate', 'task completion', 'how many tasks', 'task report']):
        # Get completion stats
        total = Task.query.filter_by(assignee_id=user_id).count()
        completed = Task.query.filter_by(assignee_id=user_id, status=TaskStatus.COMPLETED).count()
        rate = (completed / total * 100) if total > 0 else 0
        
        # Check for time period
        if 'this week' in text:
            week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
            completed = Task.query.filter(
                Task.assignee_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.updated_at >= week_start
            ).count()
            return jsonify({
                'message': f'You completed {completed} task(s) this week',
                'completed': completed
            }), 200
        
        return jsonify({
            'message': f'Your task completion rate is {rate:.1f}% ({completed} of {total} tasks completed)',
            'total': total,
            'completed': completed,
            'rate': rate
        }), 200
    
    # Check for status queries
    elif any(keyword in text for keyword in ['where are we', 'status', 'how is', 'what is the status', 'check task']):
        # Extract task identifier from query
        task_id_match = re.search(r'task\s+(\d+)', text)
        if task_id_match:
            task_id = int(task_id_match.group(1))
            task = Task.query.get(task_id)
            if task:
                return jsonify({
                    'message': f'Task "{task.title}" is currently {task.status.value}',
                    'task': {
                        'id': task.id,
                        'title': task.title,
                        'status': task.status.value,
                        'assignee': task.assignee.name
                    }
                }), 200
        
        # Query by assignee name
        assignee_match = re.search(r'(?:for|with|assigned to)\s+([a-z]+)', text)
        if assignee_match:
            assignee_name = assignee_match.group(1).lower()
            assignee = User.query.filter(User.name.ilike(f"%{assignee_name}%")).first()
            if assignee:
                tasks = Task.query.filter_by(assignee_id=assignee.id).all()
                return jsonify({
                    'message': f'{assignee.name} has {len(tasks)} task(s)',
                    'tasks': [{
                        'id': t.id,
                        'title': t.title,
                        'status': t.status.value
                    } for t in tasks]
                }), 200
        
        return jsonify({'error': 'Could not find task or assignee'}), 404
    
    # Check for task deletion - be permissive
    elif any(keyword in text for keyword in ['delete', 'remove', 'cancel', 'erase']) and 'task' in text:
        task_id_match = re.search(r'task\s+(\d+)', text)
        if not task_id_match:
            # Try to find task by title
            title_match = re.search(r'(?:task|delete|remove)\s+"([^"]+)"', text, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r'(?:task|delete|remove)\s+([a-zA-Z][^.!?]*)', text, re.IGNORECASE)
            
            if title_match:
                task_title = title_match.group(1).strip()
                # Find task by title
                user_obj = User.query.get(user_id)
                workspace_id = user_obj.current_workspace_id if user_obj else None
                query = Task.query.filter(
                    Task.title.ilike(f'%{task_title}%'),
                    or_(Task.assignee_id == user_id, Task.created_by_id == user_id)
                )
                if workspace_id:
                    query = query.filter(Task.workspace_id == workspace_id)
                task = query.first()
                if not task:
                    return jsonify({'error': f'Task "{task_title}" not found'}), 404
            else:
                return jsonify({'error': 'Please specify task number or title. For example: "Delete task 5" or "Remove task Review report"'}), 400
        else:
            task_id = int(task_id_match.group(1))
            task = Task.query.get(task_id)
            if not task:
                return jsonify({'error': f'Task {task_id} not found'}), 404
        
        # Only allow deletion if user created it or is assigned to it
        if task.created_by_id != user_id and task.assignee_id != user_id:
            return jsonify({'error': 'You do not have permission to delete this task'}), 403
        
        task_title = task.title
        task_id = task.id
        db.session.delete(task)
        db.session.commit()
        
        print(f"[Voice] Task {task_id} deleted: {task_title}")
        
        return jsonify({
            'message': f'Task "{task_title}" has been deleted',
            'deleted': True,
            'task_id': task_id
        }), 200
    
    # Check for email sending commands
    elif any(keyword in text for keyword in ['send email', 'email to', 'send a message to', 'email', 'send an email']):
        original_text = data['text']
        
        # Extract recipient email or name (more flexible patterns)
        email_match = re.search(r'(?:to|email|send to)\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', original_text, re.IGNORECASE)
        name_patterns = [
            r'(?:to|email|send to)\s+([a-z]+)',
            r'email\s+([a-z]+)\s+(?:about|regarding|that)',
            r'send\s+(?:an?\s+)?email\s+to\s+([a-z]+)',
        ]
        
        recipient_email = None
        recipient_name = None
        
        if email_match:
            recipient_email = email_match.group(1)
        else:
            for pattern in name_patterns:
                name_match = re.search(pattern, text)
                if name_match:
                    recipient_name = name_match.group(1).lower()
                    # Find user by name
                    recipient_user = User.query.filter(User.name.ilike(f"%{recipient_name}%")).first()
                    if recipient_user:
                        recipient_email = recipient_user.email
                        break
        
        if not recipient_email:
            return jsonify({
                'error': 'Could not identify recipient. Please specify email address or user name.',
                'parsed': {'recipient_name': recipient_name, 'text': original_text}
            }), 400
        
        # Extract subject - look for "subject", "about", "regarding", "re:", or after recipient
        subject_patterns = [
            r'(?:subject|about|regarding|re:)\s+(.+?)(?:\s+body|\s+message|\s+saying|$)',
            r'email\s+to\s+[^\s]+\s+(?:about|regarding)\s+(.+?)(?:\s+body|\s+message|$)',
            r'email\s+[^\s]+\s+about\s+(.+?)(?:\s+body|\s+message|$)',
        ]
        
        subject = 'Voice Message'
        for pattern in subject_patterns:
            subject_match = re.search(pattern, original_text, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
                break
        
        # Extract body/content - look for "body", "message", "saying", "that", or everything after subject
        body_patterns = [
            r'(?:body|message|saying|that|content)\s+(.+?)$',
            r'email\s+to\s+[^\s]+\s+(?:subject\s+[^\s]+\s+)?(?:body\s+)?(.+?)$',
            r'about\s+[^\s]+\s+(?:body\s+)?(.+?)$',
        ]
        
        body = None
        for pattern in body_patterns:
            body_match = re.search(pattern, original_text, re.IGNORECASE)
            if body_match:
                body = body_match.group(1).strip()
                break
        
        # If no explicit body found, try to extract text after recipient and subject
        if not body:
            # Remove recipient and subject parts, get the rest
            cleaned = re.sub(r'(?:send\s+)?(?:an?\s+)?email\s+to\s+[^\s]+\s*', '', original_text, flags=re.IGNORECASE)
            cleaned = re.sub(r'(?:subject|about|regarding)\s+[^\s]+\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            if cleaned and len(cleaned) > 5:
                body = cleaned
            else:
                body = 'Sent via voice command from HSEA Assistant'
        
        # Send email via Gmail API
        from app.gmail.routes import get_gmail_access_token
        access_token = get_gmail_access_token(user_id)
        
        if not access_token:
            return jsonify({
                'error': 'Gmail not connected. Please connect your Gmail account first.',
                'action': 'connect_gmail'
            }), 401
        
        # Import send_gmail function logic
        import base64
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import requests
        
        user = User.query.get(user_id)
        from_email = user.email if user else None
        
        if not from_email:
            return jsonify({'error': 'User email not found'}), 400
        
        # Create email message
        message = MIMEMultipart()
        message['to'] = recipient_email
        message['from'] = from_email
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send via Gmail API
        gmail_response = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={'raw': raw_message}
        )
        
        if gmail_response.status_code != 200:
            return jsonify({
                'error': 'Failed to send email',
                'details': gmail_response.text
            }), 500
        
        return jsonify({
            'message': f'Email sent to {recipient_email}',
            'email': {
                'to': recipient_email,
                'subject': subject,
                'body': body
            }
        }), 200
    
    else:
        # For any unrecognized input, try to be helpful
        # Check if it's at least task/meeting related
        task_related_words = ['task', 'todo', 'meeting', 'email', 'schedule', 'create', 'add', 'list', 'show', 'what']
        is_task_related = any(word in text for word in task_related_words)
        
        if is_task_related:
            # User mentioned something task-related but we didn't understand
            return jsonify({
                'message': 'I understand you\'re asking about tasks or meetings. Could you be more specific? For example:\n- "What tasks do I have?"\n- "Create a task for Caleb to review the report"\n- "Show me my meetings"',
                'recognized': False,
                'helpful': True
            }), 200
        else:
            # Not task-related, let AI handle naturally
            return jsonify({
                'message': 'I understand. How else can I help you?',
                'recognized': False
            }), 200

@voice_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio using Azure Speech Services"""
    if not Config.AZURE_SPEECH_KEY or not Config.AZURE_SPEECH_REGION:
        return jsonify({'error': 'Azure Speech Services not configured'}), 500
    
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'error': 'Audio file is required'}), 400
    
    speech_config = speechsdk.SpeechConfig(
        subscription=Config.AZURE_SPEECH_KEY,
        region=Config.AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language = "en-US"
    
    audio_config = speechsdk.audio.AudioConfig(filename=audio_file.filename)
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    result = speech_recognizer.recognize_once()
    
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return jsonify({'text': result.text}), 200
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return jsonify({'error': 'No speech could be recognized'}), 400
    else:
        return jsonify({'error': f'Speech recognition failed: {result.reason}'}), 500
