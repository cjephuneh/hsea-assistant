from app import db
from app.models import Notification, NotificationType, Task, Meeting
from app.notifications.sms_service import send_sms
from app.notifications.push_service import send_push_notification

class NotificationService:
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
    def create_task_completed_notification(task: Task):
        """Create notification when task is completed"""
        notification = Notification(
            user_id=task.created_by_id,
            type=NotificationType.TASK_COMPLETED,
            title='Task Completed',
            message=f'Task "{task.title}" has been completed by {task.assignee.name}'
        )
        db.session.add(notification)
        db.session.commit()
        
        creator = task.creator
        if creator.fcm_token:
            send_push_notification(
                creator.fcm_token,
                'Task Completed',
                f'{task.assignee.name} completed: {task.title}'
            )
    
    @staticmethod
    def create_meeting_scheduled_notification(meeting: Meeting, user_id: int):
        """Create notification when meeting is scheduled"""
        notification = Notification(
            user_id=user_id,
            type=NotificationType.MEETING_SCHEDULED,
            title='Meeting Scheduled',
            message=f'Meeting "{meeting.topic}" scheduled for {meeting.start_time.strftime("%Y-%m-%d %H:%M")}'
        )
        db.session.add(notification)
        db.session.commit()
        
        user = meeting.user if meeting.user_id == user_id else None
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
