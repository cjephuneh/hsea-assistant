"""
Email copy for task-related notifications. All return (subject, body) for plain-text emails.

Where mail is sent (all via send_email in email_service.py):
  • Task created        → service.send_task_created_emails          (assignee + creator)
  • Notes updated       → service.send_task_notes_updated_emails   (assignee + creator)
  • Task completed      → service.send_task_completed_emails       (assignee + creator)
  • Status changed      → service.send_task_status_changed_email  (assignee)
  • Assignee changed    → service.send_assignee_changed_emails    (new + old assignee + creator)
  • Due date changed    → service.send_due_date_changed_emails    (assignee + creator)
  • Comment added       → service.send_comment_added_emails       (assignee + creator, excl. commenter)
  • Mention in comment  → service.send_mention_email              (mentioned user)
  • Meeting scheduled   → service.send_meeting_scheduled_email     (attendee)
  • User composes mail → app/mail/routes.py, app/files/routes.py  (no templates)
"""


def task_created_assignee(task):
    due = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
    subject = f"New task assigned: {task.title}"
    body = (
        f"Hi {task.assignee.name},\n\n"
        f"You have been assigned a new task by {task.creator.name}.\n\n"
        f"Task: {task.title}\n"
        f"Description: {task.description or '(none)'}\n"
        f"Priority: {task.priority.value}\n"
        f"Due: {due}\n\n"
        f"View it in your HSEA Assistant dashboard."
    )
    return subject, body


def task_created_creator(task):
    due = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
    subject = f"Task created: {task.title}"
    body = (
        f"Hi {task.creator.name},\n\n"
        f"You created a task and assigned it to {task.assignee.name}.\n\n"
        f"Task: {task.title}\n"
        f"Description: {task.description or '(none)'}\n"
        f"Assignee: {task.assignee.name}\n"
        f"Due: {due}\n\n"
        f"It will appear on your dashboard."
    )
    return subject, body


def notes_updated_assignee(task, updated_by_name, new_notes):
    subject = f"Notes updated on: {task.title}"
    body = (
        f"Hi {task.assignee.name},\n\n"
        f"{updated_by_name} updated the notes on this task.\n\n"
        f"Task: {task.title}\n\n"
        f"Updated notes:\n{new_notes or '(cleared)'}\n\n"
        f"Check the task in HSEA Assistant for full details."
    )
    return subject, body


def notes_updated_creator(task, updated_by_name, new_notes):
    subject = f"Notes updated on: {task.title}"
    body = (
        f"Hi {task.creator.name},\n\n"
        f"{updated_by_name} updated the notes on a task you created.\n\n"
        f"Task: {task.title}\n"
        f"Assignee: {task.assignee.name}\n\n"
        f"Updated notes:\n{new_notes or '(cleared)'}\n\n"
        f"View it in your dashboard."
    )
    return subject, body


def task_completed_assignee(task):
    subject = f"Done! You completed: {task.title}"
    body = (
        f"Hi {task.assignee.name},\n\n"
        f"  You did it.\n\n"
        f"Task \"{task.title}\" is marked complete. Nice work.\n\n"
        f"Keep the momentum going in your HSEA Assistant dashboard."
    )
    return subject, body


def task_completed_creator(task):
    subject = f"Task completed: {task.title}"
    body = (
        f"Hi {task.creator.name},\n\n"
        f"  {task.assignee.name} just completed this task:\n\n"
        f"  \"{task.title}\"\n\n"
        f"One less thing on the list. View your dashboard for more."
    )
    return subject, body


# ---- Status changed (e.g. in progress, pending) ----
def task_status_changed_assignee(task, old_status: str, new_status: str, updated_by_name: str):
    subject = f"Status updated: {task.title}"
    body = (
        f"Hi {task.assignee.name},\n\n"
        f"{updated_by_name} updated the status of this task.\n\n"
        f"Task: {task.title}\n"
        f"Previous status: {old_status}\n"
        f"New status: {new_status}\n\n"
        f"View it in your HSEA Assistant dashboard."
    )
    return subject, body


# ---- Assignee reassigned ----
def assignee_changed_new_assignee(task, previous_assignee_name: str):
    subject = f"New task assigned to you: {task.title}"
    body = (
        f"Hi {task.assignee.name},\n\n"
        f"This task was reassigned to you (previously: {previous_assignee_name}).\n\n"
        f"Task: {task.title}\n"
        f"Description: {task.description or '(none)'}\n"
        f"Due: {task.due_date.strftime('%Y-%m-%d') if task.due_date else 'No due date'}\n\n"
        f"View it in your HSEA Assistant dashboard."
    )
    return subject, body


def assignee_changed_previous_assignee(task, new_assignee_name: str):
    subject = f"Task reassigned: {task.title}"
    body = (
        f"Hi,\n\n"
        f"Task \"{task.title}\" is no longer assigned to you. It was reassigned to {new_assignee_name}.\n\n"
        f"Check your dashboard for other tasks."
    )
    return subject, body


def assignee_changed_creator(task, old_assignee_name: str, new_assignee_name: str):
    subject = f"Assignee changed: {task.title}"
    body = (
        f"Hi {task.creator.name},\n\n"
        f"The assignee for this task was updated.\n\n"
        f"Task: {task.title}\n"
        f"Previous assignee: {old_assignee_name}\n"
        f"New assignee: {new_assignee_name}\n\n"
        f"View it in your dashboard."
    )
    return subject, body


# ---- Due date changed ----
def due_date_changed_assignee(task, old_due_str: str, new_due_str: str, updated_by_name: str):
    subject = f"Due date updated: {task.title}"
    body = (
        f"Hi {task.assignee.name},\n\n"
        f"{updated_by_name} updated the due date for this task.\n\n"
        f"Task: {task.title}\n"
        f"Previous due: {old_due_str}\n"
        f"New due: {new_due_str}\n\n"
        f"View it in your HSEA Assistant dashboard."
    )
    return subject, body


def due_date_changed_creator(task, old_due_str: str, new_due_str: str):
    subject = f"Due date updated: {task.title}"
    body = (
        f"Hi {task.creator.name},\n\n"
        f"The due date for a task you created was updated.\n\n"
        f"Task: {task.title}\n"
        f"Assignee: {task.assignee.name}\n"
        f"Previous due: {old_due_str}\n"
        f"New due: {new_due_str}\n\n"
        f"View it in your dashboard."
    )
    return subject, body


# ---- Comment added on task ----
def comment_added_assignee(task, comment_author_name: str, comment_snippet: str):
    subject = f"New comment on: {task.title}"
    body = (
        f"Hi {task.assignee.name},\n\n"
        f"{comment_author_name} left a comment on this task.\n\n"
        f"Task: {task.title}\n\n"
        f"Comment:\n{comment_snippet}\n\n"
        f"View the full thread in HSEA Assistant."
    )
    return subject, body


def comment_added_creator(task, comment_author_name: str, comment_snippet: str):
    subject = f"New comment on: {task.title}"
    body = (
        f"Hi {task.creator.name},\n\n"
        f"{comment_author_name} commented on a task you created.\n\n"
        f"Task: {task.title}\n"
        f"Assignee: {task.assignee.name}\n\n"
        f"Comment:\n{comment_snippet}\n\n"
        f"View the full thread in HSEA Assistant."
    )
    return subject, body


# ---- Mention in comment ----
def mention_in_comment(mentioned_name: str, task, comment_author_name: str, comment_snippet: str):
    subject = f"You were mentioned: {task.title}"
    body = (
        f"Hi {mentioned_name},\n\n"
        f"{comment_author_name} mentioned you in a comment on this task.\n\n"
        f"Task: {task.title}\n\n"
        f"Comment:\n{comment_snippet}\n\n"
        f"View and reply in HSEA Assistant."
    )
    return subject, body


# ---- Meeting scheduled ----
def meeting_scheduled(attendee_name: str, meeting_topic: str, start_time_str: str, join_url: str = ""):
    subject = f"Meeting scheduled: {meeting_topic}"
    body = (
        f"Hi {attendee_name},\n\n"
        f"A meeting has been scheduled.\n\n"
        f"Topic: {meeting_topic}\n"
        f"Time: {start_time_str}\n"
    )
    if join_url:
        body += f"\nJoin: {join_url}\n"
    body += "\nAdd it to your calendar in HSEA Assistant."
    return subject, body
