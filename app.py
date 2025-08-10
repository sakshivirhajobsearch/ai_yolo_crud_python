import os
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename
import sqlite3
from yolo_model import detect_objects

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'supersecretkey'

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize SQLite DB
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS images
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT NOT NULL,
                  detections TEXT)''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, detections FROM images")
    images = c.fetchall()
    conn.close()
    # detections stored as str, convert to list of dict
    images_data = []
    import ast
    for img in images:
        det = ast.literal_eval(img[2]) if img[2] else []
        images_data.append({'id': img[0], 'filename': img[1], 'detections': det})
    return render_template('index.html', images=images_data)

@app.route('/upload', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Run detection
            detections = detect_objects(filepath)

            # Store info in DB
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("INSERT INTO images (filename, detections) VALUES (?, ?)", 
                      (filename, str(detections)))
            conn.commit()
            conn.close()
            flash('Image uploaded and analyzed successfully!')
            return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/delete/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT filename FROM images WHERE id=?", (image_id,))
    row = c.fetchone()
    if row:
        filename = row[0]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        c.execute("DELETE FROM images WHERE id=?", (image_id,))
        conn.commit()
    conn.close()
    flash('Image deleted successfully!')
    return redirect(url_for('index'))

@app.route('/edit/<int:image_id>', methods=['GET', 'POST'])
def edit_image(image_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT filename FROM images WHERE id=?", (image_id,))
    row = c.fetchone()
    if not row:
        flash('Image not found')
        return redirect(url_for('index'))
    filename = row[0]

    if request.method == 'POST':
        # Allow replacing image
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Remove old image
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(old_path):
                os.remove(old_path)

            # Save new image
            new_filename = secure_filename(file.filename)
            new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(new_path)

            # Run detection again
            detections = detect_objects(new_path)

            # Update DB
            c.execute("UPDATE images SET filename=?, detections=? WHERE id=?", 
                      (new_filename, str(detections), image_id))
            conn.commit()
            conn.close()
            flash('Image updated successfully!')
            return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', image_id=image_id, filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
