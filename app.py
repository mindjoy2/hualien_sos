import os
import sqlite3
from flask import Flask, render_template, request, jsonify, g
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ========== 設定資料庫與上傳資料夾 ==========

# 這個路徑為 Render Disk 的掛載點（你部署時設定）
DISK_PATH = "/mnt/data"  # <- 這個要跟你在 Render 上掛載 Disk 的路徑一致

# 資料庫檔案放在 Disk 上
DATABASE = os.path.join(DISK_PATH, "markers.db")

# 圖片上傳資料夾也設在 Disk 上
UPLOAD_FOLDER = os.path.join(DISK_PATH, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 允許的圖片副檔名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== 資料庫連線與初始化 ==========

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g._database = conn
    return g._database

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.route('/initdb')
def initdb_route():
    # 注意：在正式環境時，你可能不希望暴露這條 route
    init_db()
    return "Database initialized!"

# ========== 路由 ==========

@app.route('/')
def index():
    return render_template('index.html')

# 在 app.py 裡加這段
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # 從硬碟的 UPLOAD_FOLDER 回傳圖片
    return flask.send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
            "image_url": r["image_path"],
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
        return jsonify({"error": "lat or lng missing"}), 400

    image_path = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        # 加時間戳避免檔名衝突
        filename = f"{name}_{int(sqlite3.time.time())}{ext}"
        savepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(savepath)
        image_path = f"/uploads/{filename}"

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
        "image_url": image_path
    }), 201

@app.route('/markers/<int:marker_id>/updates', methods=['POST'])
def post_marker_update(marker_id):
    db = get_db()
    cur = db.execute("SELECT id, text, image_path FROM markers WHERE id = ?", (marker_id,))
    base = cur.fetchone()
    if base is None:
        return jsonify({"error": "marker not found"}), 404

    text = request.form.get('text', None)
    file = request.files.get('image')

    image_path = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(sqlite3.time.time())}{ext}"
        savepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(savepath)
        image_path = f"/uploads/{filename}"

    if (text is None or text.strip() == "") and image_path is None:
        return jsonify({"error": "nothing to update"}), 400

    cur2 = db.cursor()
    cur2.execute(
        "INSERT INTO marker_updates (marker_id, text, image_path) VALUES (?, ?, ?)",
        (marker_id, text, image_path)
    )
    db.commit()
    new_upd_id = cur2.lastrowid

    return jsonify({
        "update_id": new_upd_id,
        "marker_id": marker_id,
        "text": text,
        "image_url": image_path
    }), 201

@app.route('/markers/<int:marker_id>/updates', methods=['GET'])
def get_marker_updates(marker_id):
    db = get_db()
    cur = db.execute(
        "SELECT id, text, image_path, updated_at FROM marker_updates WHERE marker_id = ? ORDER BY updated_at ASC",
        (marker_id,)
    )
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "update_id": r["id"],
            "text": r["text"],
            "image_url": r["image_path"],
            "updated_at": r["updated_at"]
        })
    return jsonify(out)

if __name__ == '__main__':
    # 如果資料庫檔案不存在，就初始化
    if not os.path.exists(DATABASE):
        with app.app_context():
            init_db()
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 5000))
