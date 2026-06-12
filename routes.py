from flask import render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
from app import app, db
from models import Jersey

# 1. The Home Page
@app.route('/')
def index():
    jerseys = Jersey.query.all()
    return render_template('catalog.html', jerseys=jerseys)

# 2. The Order Ledger (Only one route for /admin)
@app.route('/admin')
def admin_orders():
    # Fetch your orders here
    return render_template('admin_orders.html')

# 3. The Upload Form (A separate route)
@app.route('/admin/upload', methods=['GET', 'POST'])
def admin_upload():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        file = request.files['image']
        
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            new_jersey = Jersey(name=name, price=price, image_file=filename)
            db.session.add(new_jersey)
            db.session.commit()
            return "Product uploaded successfully! <a href='/'>Back to Store</a>"
            
    return render_template('admin.html')