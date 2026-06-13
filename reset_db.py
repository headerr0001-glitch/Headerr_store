from app import app, db

with app.app_context():
    print("Dropping old cloud tables...")
    db.drop_all()
    print("Creating new upgraded tables...")
    db.create_all()
    print("✅ Cloud Database Reset Complete!")