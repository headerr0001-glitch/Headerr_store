from app import app
from models import db, Jersey

with app.app_context():
    # First, we clear out the old test data so we have a clean slate
    db.drop_all()
    db.create_all()

    # Create your new real inventory
    kit_1 = Jersey(
        name="MBSG Home Kit",
        description="Authentic Maroon and Green",
        price=90.00,
        image_file="default.jpg" # We will link real images later
    )

    kit_2 = Jersey(
        name="Argentina 3-Star Home",
        description="Official Match Jersey",
        price=120.00,
        image_file="default.jpg"
    )
    
    kit_3 = Jersey(
        name="HEADERR Blackout Concept",
        description="Limited Edition Pre-season Drop",
        price=150.00,
        image_file="default.jpg"
    )

    # Add them to the database ledger and save
    db.session.add_all([kit_1, kit_2, kit_3])
    db.session.commit()
    
    print("Success! The MBSG and Argentina kits are now in the database.")