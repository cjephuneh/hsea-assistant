from app import db
from app.models import Notification, NotificationType, Task, Meeting, User
from app.notifications.sms_service import send_sms
from app.notifications.push_service import send_push_notification
from app.notifications.email_service import send_email
from app.notifications import email_templates

class NotificationService:
    @staticmethod
    def send_task_created_emails(task: Task):
        """Send email to assignee and creator when a task is created."""
        subj, body = email_templates.task_created_assignee(task)
        send_email(task.assignee.email, subj, body)
        if task.created_by_id != task.assignee_id:
            subj, body = email_templates.task_created_creator(task)
            send_email(task.creator.email, subj, body)

    @staticmethod
    def create_task_assigned_notification(task: Task):
        """Create notification when task is assigned"""
        notification = Notification(
            user_id=task.assignee_id,
            type=NotificationType.TASK_ASSIGNED,
            title='New Task Assigned',
            message=f'You have been assigned a new task: {task.title}'
        )
        db.session.add(notification)
        db.session.commit()
        
        # Send email to assignee and creator
        NotificationService.send_task_created_emails(task)
        
        # Send push notification
        if task.assignee.fcm_token:
            send_push_notification(
                task.assignee.fcm_token,
                'New Task Assigned',
                f'You have been assigned: {task.title}'
            )
        
        # Send SMS if phone number exists
        if task.assignee.phone:
            send_sms(
                task.assignee.phone,
                f'New task assigned: {task.title}. Check your HSEA Assistant app for details.'
            )
    
    @staticmethod
    def create_task_updated_notification(task: Task):
        """Create notification when task is updated"""
        notification = Notification(
            user_id=task.assignee_id,
            type=NotificationType.TASK_UPDATED,
            title='Task Updated',
            message=f'Task "{task.title}" has been updated. Status: {task.status.value}'
        )
        db.session.add(notification)
        db.session.commit()
        
        if task.assignee.fcm_token:
            send_push_notification(
                task.assignee.fcm_token,
                'Task Updated',
                f'{task.title} - Status: {task.status.value}'
            )

    @staticmethod
    def send_task_status_changed_email(task: Task, old_status: str, new_status: str, updated_by_name: str):
        subj, body = email_templates.task_status_changed_assignee(task, old_status, new_status, updated_by_name)
        send_email(task.assignee.email, subj, body)

    @staticmethod
    def send_assignee_changed_emails(task: Task, old_assignee, new_assignee_name: str):
        """old_assignee is the User who was previously assigned (before commit)."""
        subj, body = email_templates.assignee_changed_new_assignee(task, old_assignee.name)
        send_email(task.assignee.email, subj, body)
        subj, body = email_templates.assignee_changed_previous_assignee(task, new_assignee_name)
        send_email(old_assignee.email, subj, body)
        if task.created_by_id != task.assignee_id and task.created_by_id != old_assignee.id:
            subj, body = email_templates.assignee_changed_creator(task, old_assignee.name, new_assignee_name)
            send_email(task.creator.email, subj, body)

    @staticmethod
    def send_due_date_changed_emails(task: Task, old_due_str: str, new_due_str: str, updated_by_name: str):
        subj, body = email_templates.due_date_changed_assignee(task, old_due_str, new_due_str, updated_by_name)
        send_email(task.assignee.email, subj, body)
        if task.created_by_id != task.assignee_id:
            subj, body = email_templates.due_date_changed_creator(task, old_due_str, new_due_str)
            send_email(task.creator.email, subj, body)

    @staticmethod
    def send_comment_added_emails(task: Task, comment_author_name: str, comment_snippet: str, exclude_user_ids=None):
        """Notify assignee and creator when someone adds a comment. exclude_user_ids = don't email these (e.g. commenter)."""
        exclude_user_ids = set(exclude_user_ids or [])
        snippet = (comment_snippet or "")[:500]
        if task.assignee_id not in exclude_user_ids:
            subj, body = email_templates.comment_added_assignee(task, comment_author_name, snippet)
            send_email(task.assignee.email, subj, body)
        if task.created_by_id != task.assignee_id and task.created_by_id not in exclude_user_ids:
            subj, body = email_templates.comment_added_creator(task, comment_author_name, snippet)
            send_email(task.creator.email, subj, body)

    @staticmethod
    def send_mention_email(mentioned_user, task: Task, comment_author_name: str, comment_snippet: str):
        subj, body = email_templates.mention_in_comment(mentioned_user.name, task, comment_author_name, (comment_snippet or "")[:500])
        send_email(mentioned_user.email, subj, body)

    @staticmethod
    def send_meeting_scheduled_email(attendee_email: str, attendee_name: str, meeting: Meeting):
        start_str = meeting.start_time.strftime("%Y-%m-%d %H:%M") if meeting.start_time else ""
        join_url = getattr(meeting, "join_url", None) or ""
        subj, body = email_templates.meeting_scheduled(attendee_name, meeting.topic or "Meeting", start_str, join_url)
        send_email(attendee_email, subj, body)
    
    @staticmethod
    def send_task_notes_updated_emails(task: Task, updated_by_name: str, new_notes: str):
        """Send email to assignee and creator when task notes are updated."""
        subj, body = email_templates.notes_updated_assignee(task, updated_by_name, new_notes)
        send_email(task.assignee.email, subj, body)
        if task.created_by_id != task.assignee_id:
            subj, body = email_templates.notes_updated_creator(task, updated_by_name, new_notes)
            send_email(task.creator.email, subj, body)

    @staticmethod
    def send_task_completed_emails(task: Task):
        """Send creative completion emails to assignee and creator."""
        subj, body = email_templates.task_completed_assignee(task)
        send_email(task.assignee.email, subj, body)
        if task.created_by_id != task.assignee_id:
            subj, body = email_templates.task_completed_creator(task)
            send_email(task.creator.email, subj, body)

    @staticmethod
    def create_task_completed_notification(task: Task):
        """Create notification and send emails when task is completed."""
        notification = Notification(
            user_id=task.created_by_id,
            type=NotificationType.TASK_COMPLETED,
            title='Task Completed',
            message=f'Task "{task.title}" has been completed by {task.assignee.name}'
        )
        db.session.add(notification)
        db.session.commit()
        NotificationService.send_task_completed_emails(task)
        creator = task.creator
        if creator.fcm_token:
            send_push_notification(
                creator.fcm_token,
                'Task Completed',
                f'{task.assignee.name} completed: {task.title}'
            )
    
    @staticmethod
    def create_meeting_scheduled_notification(meeting: Meeting, user_id: int):
        """Create notification and email when meeting is scheduled"""
        notification = Notification(
            user_id=user_id,
            type=NotificationType.MEETING_SCHEDULED,
            title='Meeting Scheduled',
            message=f'Meeting "{meeting.topic}" scheduled for {meeting.start_time.strftime("%Y-%m-%d %H:%M")}'
        )
        db.session.add(notification)
        db.session.commit()
        
        user = User.query.get(user_id)
        if user:
            NotificationService.send_meeting_scheduled_email(user.email, user.name, meeting)
        if user and user.fcm_token:
            send_push_notification(
                user.fcm_token,
                'Meeting Scheduled',
                f'{meeting.topic} at {meeting.start_time.strftime("%Y-%m-%d %H:%M")}'
            )
        
        if user and user.phone:
            send_sms(
                user.phone,
                f'Meeting scheduled: {meeting.topic} at {meeting.start_time.strftime("%Y-%m-%d %H:%M")}. Join: {meeting.join_url}'
            )
    
    @staticmethod
    def create_mention_notification(user_id: int, task_id: int, comment_id: int):
        """Create notification when user is mentioned in a comment"""
        from app.models import User, Task, Comment
        user = User.query.get(user_id)
        task = Task.query.get(task_id)
        comment = Comment.query.get(comment_id)
        
        if not user or not task or not comment:
            return
        
        notification = Notification(
            user_id=user_id,
            type=NotificationType.MENTION,
            title='You were mentioned',
            message=f'{comment.user.name} mentioned you in a comment on task "{task.title}"'
        )
        db.session.add(notification)
        db.session.commit()
        
        if user.fcm_token:
            send_push_notification(
                user.fcm_token,
                'You were mentioned',
                f'{comment.user.name} mentioned you in task "{task.title}"'
            )
