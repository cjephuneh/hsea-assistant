#!/usr/bin/env python3
"""
Script to create test users for HSEA Assistant
Run this after setting up the database
"""

from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

def create_test_users():
    with app.app_context():
        # Create test users
        test_users = [
            {"name": "Caleb", "email": "caleb@example.com", "password": "password123", "phone": "+1234567890"},
            {"name": "Scott", "email": "scott@example.com", "password": "password123"},
            {"name": "Admin User", "email": "admin@example.com", "password": "admin123"},
            {"name": "Test User", "email": "test@example.com", "password": "test123"},
        ]
        
        created_count = 0
        for user_data in test_users:
            existing_user = User.query.filter_by(email=user_data["email"]).first()
            if not existing_user:
                user = User(
                    name=user_data["name"],
                    email=user_data["email"],
                    password_hash=generate_password_hash(user_data["password"]),
                    phone=user_data.get("phone")
                )
                db.session.add(user)
                created_count += 1
                print(f"✅ Created user: {user_data['email']} (Password: {user_data['password']})")
            else:
                print(f"⚠️  User already exists: {user_data['email']}")
        
        db.session.commit()
        
        if created_count > 0:
            print(f"\n🎉 Successfully created {created_count} test user(s)!")
            print("\nYou can now login with:")
            for user_data in test_users:
                print(f"  Email: {user_data['email']}")
                print(f"  Password: {user_data['password']}\n")
        else:
            print("\nAll test users already exist.")

if __name__ == "__main__":
    create_test_users()
