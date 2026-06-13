from app import app, db

with app.app_context():
    print("Dropping old database tables from Neon cloud...")
    db.drop_all()
    print("Creating updated database tables with status columns...")
    db.create_all()
    print("✅ Neon Cloud Database Synced Successfully!")
    