import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import razorpay

# Load the hidden secrets
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# --- 1. CONFIGURATIONS ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL')

app.config['RAZORPAY_KEY_ID'] = os.getenv('RAZORPAY_KEY_ID')
app.config['RAZORPAY_KEY_SECRET'] = os.getenv('RAZORPAY_KEY_SECRET')

razorpay_client = razorpay.Client(auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_KEY_SECRET']))
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- 2. DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)

class Jersey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General')
    image_file = db.Column(db.String(200), nullable=False, default='default.jpg')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    date_ordered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    customer = db.relationship('User', backref='orders', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    jersey_id = db.Column(db.Integer, db.ForeignKey('jersey.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)

class StoreSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 3. DYNAMIC CMS CONTEXT ---
@app.context_processor
def inject_store_settings():
    try:
        settings = {row.key: row.value for row in StoreSetting.query.all()}
    except:
        settings = {}
        
    defaults = {
        'store_name': 'Headerr Store',
        'announcement_text': '🔥 Free Shipping on Orders Above Rs. 1499! 🔥',
        'hero_title': 'Premium Football Kits',
        'theme_color': 'black', 
        'show_retro': 'True'
    }
    
    for key, val in defaults.items():
        if key not in settings: settings[key] = val
    return dict(store=settings)

# --- 4. AUTHENTICATION ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('catalog'))
    if request.method == 'POST':
        email, name, password = request.form.get('email'), request.form.get('name'), request.form.get('password')
        if User.query.filter_by(email=email).first(): return redirect(url_for('register'))
        new_user = User(email=email, name=name, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('catalog'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('catalog'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('catalog'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('catalog'))

# --- 5. CART & RAZORPAY CHECKOUT ---
def get_cart_details():
    cart_items, total = [], 0
    if 'cart' in session:
        for j_id, qty in session['cart'].items():
            jersey = Jersey.query.get(int(j_id))
            if jersey:
                total += jersey.price * qty
                cart_items.append({'jersey': jersey, 'quantity': qty, 'subtotal': jersey.price * qty})
    return cart_items, total

@app.route('/add-to-cart/<int:jersey_id>', methods=['POST'])
def add_to_cart(jersey_id):
    cart = session.setdefault('cart', {})
    cart[str(jersey_id)] = cart.get(str(jersey_id), 0) + 1
    session.modified = True
    return redirect(request.referrer or url_for('catalog'))

@app.route('/cart')
def cart():
    items, total = get_cart_details()
    return render_template('cart.html', cart_items=items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items, total_price = get_cart_details()
    if not cart_items: return redirect(url_for('catalog'))

    if request.method == 'POST':
        amount_in_paise = int(total_price * 100)
        razorpay_order = razorpay_client.order.create({"amount": amount_in_paise, "currency": "INR", "payment_capture": "1"})
        session['checkout_address'] = request.form.get('address')
        
        return render_template('razorpay_checkout.html', order_id=razorpay_order['id'], amount=amount_in_paise, 
                               key_id=app.config['RAZORPAY_KEY_ID'], total=total_price, user=current_user)
    return render_template('checkout.html', cart_items=cart_items, total=total_price)

@app.route('/verify-payment', methods=['POST'])
@login_required
def verify_payment():
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': request.form.get('razorpay_order_id'),
            'razorpay_payment_id': request.form.get('razorpay_payment_id'),
            'razorpay_signature': request.form.get('razorpay_signature')
        })
        cart_items, total_price = get_cart_details()
        new_order = Order(user_id=current_user.id, total_price=total_price, address=session.get('checkout_address', ''), status='Pending')
        db.session.add(new_order)
        db.session.commit()
        
        for item in cart_items:
            db.session.add(OrderItem(order_id=new_order.id, jersey_id=item['jersey'].id, quantity=item['quantity'], price_at_purchase=item['jersey'].price))
            
        db.session.commit()
        session.pop('cart', None)
        return redirect(url_for('success', order_id=new_order.id))
    except:
        return redirect(url_for('cart'))

@app.route('/success/<int:order_id>')
@login_required
def success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('success.html', order=order)

# --- 6. ADMIN CMS & DASHBOARD ---
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.email != app.config['ADMIN_EMAIL']: return redirect(url_for('catalog'))

    if request.method == 'POST':
        image = request.files.get('image')
        filename = 'default.jpg'
        if image and image.filename:
            filename = secure_filename(image.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        db.session.add(Jersey(name=request.form.get('name'), price=float(request.form.get('price')), category=request.form.get('category'), image_file=filename))
        db.session.commit()
        return redirect(url_for('admin'))

    return render_template('admin.html', jerseys=Jersey.query.order_by(Jersey.id.desc()).all(), orders=Order.query.order_by(Order.date_ordered.desc()).all())

@app.route('/admin/update_settings', methods=['POST'])
@login_required
def update_settings():
    if current_user.email != app.config['ADMIN_EMAIL']: return redirect(url_for('catalog'))
    
    # Update text settings
    for key in ['store_name', 'announcement_text', 'hero_title', 'theme_color']:
        val = request.form.get(key)
        if val:
            setting = StoreSetting.query.filter_by(key=key).first()
            if setting: setting.value = val
            else: db.session.add(StoreSetting(key=key, value=val))
            
    # Update checkbox
    show_retro = 'True' if 'show_retro' in request.form else 'False'
    retro_setting = StoreSetting.query.filter_by(key='show_retro').first()
    if retro_setting: retro_setting.value = show_retro
    else: db.session.add(StoreSetting(key='show_retro', value=show_retro))

    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
@login_required
def update_order(order_id):
    if current_user.email == app.config['ADMIN_EMAIL']:
        Order.query.get_or_404(order_id).status = request.form.get('status')
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete_jersey/<int:jersey_id>', methods=['POST'])
@login_required
def delete_jersey(jersey_id):
    if current_user.email == app.config['ADMIN_EMAIL']:
        try:
            db.session.delete(Jersey.query.get_or_404(jersey_id))
            db.session.commit()
        except: db.session.rollback()
    return redirect(url_for('admin'))

# --- 7. PUBLIC STOREFRONT ---
@app.route('/')
def catalog():
    cat = request.args.get('category')
    jerseys = Jersey.query.filter_by(category=cat).all() if cat else Jersey.query.order_by(Jersey.id.desc()).all()
    return render_template('catalog.html', jerseys=jerseys, active_category=cat)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)