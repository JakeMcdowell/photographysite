import mimetypes
import os
import urllib.parse
import uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from watermark import apply_watermark  # your watermark function
from firebase_admin import credentials, initialize_app, storage


app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///photos.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "sqlite:////var/data/photos.db"  # 4 slashes for absolute path
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images/originals'
app.config['WATERMARKED_FOLDER'] = 'static/images/watermarked'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


app.config['FIREBASE_STORAGE_BUCKET'] = "profileuploads-3de42.firebasestorage.app"

cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json"))
initialize_app(cred, {"storageBucket": app.config['FIREBASE_STORAGE_BUCKET']})

db = SQLAlchemy(app)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    is_featured = db.Column(db.Boolean, default=False)
    price = db.Column(db.Float, default=0.0)

    # New field: where the file lives in Firebase
    storage_url = db.Column(db.Text, nullable=False)  # Firebase public URL

class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(50))  # e.g., "service" or "print"
    label = db.Column(db.String(100))     # e.g., "Corporate Head Shot"
    amount = db.Column(db.Float)          # e.g., 25.00


# --- Firebase init ---

def upload_to_firebase(local_path: str, dest_path: str) -> str:
    """
    Uploads a file to Firebase Storage at dest_path and returns a durable download URL
    using a firebaseStorageDownloadTokens token.
    """
    bucket = storage.bucket()
    blob = bucket.blob(dest_path)

    # Guess content type
    ctype, _ = mimetypes.guess_type(local_path)
    if not ctype:
        ctype = "application/octet-stream"

    # Generate a token to allow direct download
    token = uuid.uuid4().hex
    blob.metadata = {"firebaseStorageDownloadTokens": token}

    # Upload file
    blob.upload_from_filename(local_path, content_type=ctype)

    # Construct public download URL (token-based)
    quoted_name = urllib.parse.quote(blob.name, safe="")
    url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{quoted_name}?alt=media&token={token}"
    return url



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def home():
    featured_photos = Photo.query.filter_by(is_featured=True).all()
    return render_template('index.html', photos=featured_photos)



@app.route('/gallery')
def gallery():
    category_filter = request.args.get('category', 'all')
    if category_filter == 'all':
        photos = Photo.query.all()
    else:
        photos = Photo.query.filter_by(category=category_filter).all()
    categories = ['all', 'animals', 'people', 'landscape']  # add more as needed
    return render_template('gallery.html', photos=photos, selected_category=category_filter, categories=categories)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    categories = ['animals', 'people', 'landscape']  # keep in sync with gallery categories
    if request.method == 'POST':
        if 'photo' not in request.files:
            return "No file part", 400
        file = request.files['photo']
        category = request.form.get('category')

        if not category or category not in categories:
            return "Invalid or missing category", 400
        if file.filename == '':
            return "No selected file", 400
        if file and allowed_file(file.filename):
            # Make a unique, safe filename (preserve extension)
            ext = Path(file.filename).suffix.lower()
            filename = f"{uuid.uuid4().hex}{ext}"  # unique
            safe_filename = secure_filename(filename)

            original_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            watermarked_path = os.path.join(app.config['WATERMARKED_FOLDER'], safe_filename)

            # Save original locally
            file.save(original_path)

            # Apply watermark to watermarked_path
            apply_watermark(original_path, watermarked_path)

            # Destination path in Firebase (organize by category/date if you like)
            dest_path = f"{category}/{safe_filename}"

            # Upload the watermarked image to Firebase Storage
            try:
                public_url = upload_to_firebase(watermarked_path, dest_path)
            except Exception as e:
                # Clean up and report
                return (f"Upload to Firebase failed: {e}", 500)

            # Save info in DB (store cloud URL)
            photo = Photo(filename=safe_filename, category=category, storage_url=public_url)
            db.session.add(photo)
            db.session.commit()

            # Optional: clean up local files
            try:
                os.remove(original_path)
                os.remove(watermarked_path)
            except OSError:
                pass

            return redirect(url_for('gallery'))

    return render_template('upload.html', categories=categories)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/pricing')
def pricing():
    services = Price.query.filter_by(item_type='Service').all()
    prints = Price.query.filter_by(item_type='Print').all()
    return render_template('pricing.html', services=services, prints=prints)

@app.route("/admin/seed-prices")
def seed_prices():
    prices = [
        Price(item_type="Service", label="Corporate Head Shot", amount=25.00),
        Price(item_type="Service", label="20min Mini Session Indoor or Out", amount=60.00),
        Price(item_type="Service", label="1hr Session 2-Locations", amount=150.00),
        Price(item_type="Service", label="2hr Multiple Locations", amount=250.00),
        Price(item_type="Print", label="Digital Copy E-mail", amount=10.00),
        Price(item_type="Print", label="5x7 Print", amount=15.00),
        Price(item_type="Print", label="8x10 Print", amount=25.00),
        Price(item_type="Print", label="11x14 Print", amount=30.00),
        Price(item_type="Print", label="13x19 Print", amount=35.00),
    ]

    db.session.bulk_save_objects(prices)
    db.session.commit()

    return "Seeded prices successfully!"



@app.route('/admin/prices', methods=['POST'])
def update_price():
    price_id = request.form.get('price_id')
    label = request.form.get('label')
    amount = float(request.form.get('amount', 0))

    price = Price.query.get(price_id)
    if price:
        price.label = label
        price.amount = amount
        db.session.commit()
    return redirect('/admin')



@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        photo_id = request.form.get('photo_id')
        is_featured = request.form.get('is_featured') == '1'
        price = float(request.form.get('price', 0))
        category = request.form.get('category')

        photo = Photo.query.get(photo_id)
        if photo:
            photo.is_featured = is_featured
            photo.price = price
            if category:
                photo.category = category
            db.session.commit()

    photos = Photo.query.all()
    prices = Price.query.all()  # ← add this line
    return render_template('admin.html', photos=photos, prices=prices)  # ← include prices


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['WATERMARKED_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
        # seed_prices() only need to do once
    app.run(debug=True)
