from flask import Flask, render_template, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
db_uri = os.environ.get('DATABASE_URL', 'sqlite:///headerr.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# INITIALIZE DB HERE BEFORE USING IT
db = SQLAlchemy(app)

# Now you can use db.Model
class Jersey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_file = db.Column(db.String(100), nullable=False)

# Force initialize database
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    jerseys = Jersey.query.all()
    return render_template('catalog.html', jerseys=jerseys)

@app.route('/cart')
def view_cart():
    return "Your Cart is Empty"

if __name__ == '__main__':
    app.run(debug=True)