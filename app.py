import os
import sqlite3
from flask import Flask, render_template, request, jsonify, g, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# SQLite 檔案與上傳圖片資料夾都放在 data/ 下
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = os.path.join(DATA_DIR, 'markers.db')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g._database = conn
    return g._database

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with open(os.path.join(BASE_DIR, 'schema.sql'), 'r', encoding='utf-8') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.route('/initdb')
def initdb_route():
    init_db()
    return "DB initialized"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # 回傳圖片檔案
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/markers', methods=['GET'])
def get_markers():
    db = get_db()
    cur = db.execute("SELECT id, lat, lng, text, image_path, created_at FROM markers")
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "lat": r["lat"],
            "lng": r["lng"],
            "text": r["text"],
            "image_url": ("/uploads/" + r["image_path"]) if r["image_path"] else None,
            "created_at": r["created_at"]
        })
    return jsonify(out)

@app.route('/markers', methods=['POST'])
def post_marker():
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    text = request.form.get('text', "")
    file = request.files.get('image')

    if lat is None or lng is None:
        return jsonify({"error": "lat/lng missing"}), 400

    image_path = None
    if file and allowed_file(file.filename):
        fn = secure_filename(file.filename)
        name, ext = os.path.splitext(fn)
        # 為避免衝突，用 timestamp 或隨機字串
        fn = f"{name}_{int(sqlite3.time.time())}{ext}"
        save_to = os.path.join(UPLOAD_FOLDER, fn)
        file.save(save_to)
        image_path = fn

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO markers (lat, lng, text, image_path) VALUES (?, ?, ?, ?)",
        (float(lat), float(lng), text, image_path)
    )
    db.commit()
    new_id = cur.lastrowid
    return jsonify({
        "id": new_id,
        "lat": float(lat),
        "lng": float(lng),
        "text": text,
        "image_url": ("/uploads/" + image_path) if image_path else None
    }), 201

@app.route('/markers/<int:marker_id>/updates', methods=['GET'])
def get_marker_updates(marker_id):
    db = get_db()
    cur = db.execute(
        "SELECT id AS update_id, text, image_path, updated_at FROM marker_updates WHERE marker_id = ? ORDER BY updated_at ASC",
        (marker_id,)
    )
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "update_id": r["update_id"],
            "text": r["text"],
            "image_url": ("/uploads/" + r["image_path"]) if r["image_path"] else None,
            "updated_at": r["updated_at"]
        })
    return jsonify(out)

@app.route('/markers/<int:marker_id>/updates', methods=['POST'])
def post_marker_update(marker_id):
    text = request.form.get('text', None)
    file = request.files.get('image')

    image_path = None
    if file and allowed_file(file.filename):
        fn = secure_filename(file.filename)
        name, ext = os.path.splitext(fn)
        fn = f"{name}_{int(sqlite3.time.time())}{ext}"
        save_to = os.path.join(UPLOAD_FOLDER, fn)
        file.save(save_to)
        image_path = fn

    if (text is None or text.strip() == "") and image_path is None:
        return jsonify({"error": "nothing to update"}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO marker_updates (marker_id, text, image_path) VALUES (?, ?, ?)",
        (marker_id, text, image_path)
    )
    db.commit()
    upd_id = cur.lastrowid

    return jsonify({
        "update_id": upd_id,
        "marker_id": marker_id,
        "text": text,
        "image_url": ("/uploads/" + image_path) if image_path else None
    }), 201

if __name__ == '__main__':
    # 啟動時若資料庫不存在，初始化（開發時用）
    if not os.path.exists(DATABASE):
        os.makedirs(DATA_DIR, exist_ok=True)
        init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
