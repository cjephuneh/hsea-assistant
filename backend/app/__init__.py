from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
from app.config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    socketio.init_app(app)

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.tasks.routes import tasks_bp
    from app.voice.routes import voice_bp
    from app.meetings.routes import meetings_bp
    from app.notifications.routes import notifications_bp
    from app.reports.routes import reports_bp
    from app.workspaces.routes import workspaces_bp
    from app.templates.routes import templates_bp
    from app.calendar.routes import calendar_bp
    from app.files.routes import files_bp
    from app.mail.routes import mail_bp
    from app.gmail.routes import gmail_bp
    from app.whiteboards.routes import whiteboards_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(voice_bp, url_prefix='/api/voice')
    app.register_blueprint(meetings_bp, url_prefix='/api/meetings')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(workspaces_bp, url_prefix='/api/workspaces')
    app.register_blueprint(templates_bp, url_prefix='/api/templates')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(mail_bp, url_prefix='/api/mail')
    app.register_blueprint(gmail_bp, url_prefix='/api/gmail')
    app.register_blueprint(whiteboards_bp, url_prefix='/api/whiteboards')

    # Create tables
    with app.app_context():
        db.create_all()
        # Add tasks.notes column if missing (e.g. existing SQLite DB)
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                conn.execute(text("SELECT notes FROM tasks LIMIT 1"))
                conn.commit()
        except Exception:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN notes TEXT"))
                    conn.commit()
            except Exception:
                pass
        # Add meetings.workspace_id and meetings.source if missing
        for col, sql_type in [('workspace_id', 'INTEGER'), ('source', 'VARCHAR(50)')]:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(f"SELECT {col} FROM meetings LIMIT 1"))
                    conn.commit()
            except Exception:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE meetings ADD COLUMN {col} {sql_type}"))
                        conn.commit()
                except Exception:
                    pass

    return app
