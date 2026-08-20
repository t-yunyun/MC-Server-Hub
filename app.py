from flask import Flask, render_template, request, jsonify, session, send_file, make_response
import requests
import json
import os
import re
import time
from datetime import datetime
from threading import Thread
from urllib.parse import quote

#项目配置
CONFIG_FILE = 'config.json'

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

CFG = load_config()


app = Flask(__name__)
app.secret_key = CFG['SECRET_KEY']
ADMIN_PASSWORD = CFG['ADMIN_PASSWORD']

MAX_HISTORY = CFG['MAX_HISTORY']
MAX_API_LOGS = CFG['MAX_API_LOGS']
DATA_FILE = CFG['DATA_FILE']
STATUS_FILE = CFG['STATUS_FILE']
API_LOG_FILE = CFG['API_LOG_FILE']
CHECK_INTERVAL = CFG['CHECK_INTERVAL']
UPLOAD_DIR = CFG['UPLOAD_DIR']
PACKS_DIR = os.path.join(UPLOAD_DIR, 'packs')
RESOURCES_DIR = os.path.join(UPLOAD_DIR, 'resources')

ALLOWED_PACK_EXTENSIONS = {'zip', 'rar', '7z', 'tar', 'gz', 'jar', 'xz', 'bz2', 'lz'}
ALLOWED_RESOURCE_EXTENSIONS = {
    'zip', 'rar', '7z', 'tar', 'gz', 'jar',
    'png', 'jpg', 'jpeg', 'pdf', 'txt',
    'json', 'cfg', 'config'
}


def safe_keep_filename(filename):
    filename = os.path.basename(filename)
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    if filename.startswith('.'):
        filename = '_' + filename
    return filename or 'unnamed_file'


def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 自动补全缺失的键
            if filename == DATA_FILE and isinstance(data, dict):
                if "resources" not in data:
                    data["resources"] = []
                    print("⚠️ 检测到 data.json 缺少 resources 字段，已自动补全。")
                    save_json(filename, data)
            
            return data
        except Exception:
            return default
    return default


def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_data():
    #自动创建 DATA_FILE 所在的目录
    data_dir = os.path.dirname(DATA_FILE)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(PACKS_DIR, exist_ok=True)
    os.makedirs(RESOURCES_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        save_json(DATA_FILE, {
            "servers": [
                {
                    "id": 1,
                    "name": "mc服务器",
                    "ip": "play.example.cn",
                    "port": 25565,
                    "version": "1.21.1",
                    "key": "",
                    "extra_files": [],  # 存储资源 ID 数组
                    "pack_filename": ""
                }
            ],
            "resources": []
        })

    if not os.path.exists(STATUS_FILE):
        save_json(STATUS_FILE, {})
    if not os.path.exists(API_LOG_FILE):
        save_json(API_LOG_FILE, {"history": []})


def cleanup_orphan_files():
    """启动时自动清理未被 data.json 引用的孤儿文件"""
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    
    # 1. 清理 uploads/resources 目录
    # 提取 data.json 中所有正在使用的资源文件名
    used_resources = {r["file_path"] for r in data.get("resources", []) if r.get("file_path")}
    res_dir = os.path.join(UPLOAD_DIR, 'resources')
    if os.path.exists(res_dir):
        for filename in os.listdir(res_dir):
            if filename not in used_resources:
                file_path = os.path.join(res_dir, filename)
                try:
                    os.remove(file_path)
                    print(f"🧹 已清理无用资源文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 清理资源文件失败 {file_path}: {e}")

    # 2. 清理 uploads/packs 目录
    # 提取 data.json 中所有正在使用的整合包文件名
    used_packs = {s["pack_filename"] for s in data.get("servers", []) if s.get("pack_filename")}
    packs_dir = os.path.join(UPLOAD_DIR, 'packs')
    if os.path.exists(packs_dir):
        for filename in os.listdir(packs_dir):
            if filename not in used_packs:
                file_path = os.path.join(packs_dir, filename)
                try:
                    os.remove(file_path)
                    print(f"🧹 已清理无用整合包文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 清理整合包文件失败 {file_path}: {e}")


def check_server_status(ip, port=25565):
    url = f"https://motd.minebbs.com/api/status?ip={ip}&t={int(time.time() * 1000)}"
    if port != 25565:
        url += f"&port={port}"

    start_time = time.time()
    result = {
        "request_url": url,
        "request_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cost_ms": 0,
        "http_status": 0,
        "raw_response": {}
    }

    try:
        resp = requests.get(url, timeout=10)
        result["cost_ms"] = int((time.time() - start_time) * 1000)
        result["http_status"] = resp.status_code
        data = resp.json()
        result["raw_response"] = data

        is_online = data.get("status") == "online"
        players = data.get("players", {})

        return {
            "success": True,
            "is_online": is_online,
            "version": data.get("version", ""),
            "motd": data.get("pureMotd", ""),
            "latency": data.get("delay", 0),
            "players_online": players.get("online", 0),
            "players_max": players.get("max", 0),
            "players_sample": sorted(p for p in (players.get("sample") or "").split(", ") if p and p != "无"),
            "icon": data.get("icon", ""),
            "log": result
        }
    except Exception as e:
        result["cost_ms"] = int((time.time() - start_time) * 1000)
        result["error"] = str(e)
        return {"success": False, "is_online": False, "log": result}


def save_api_log(log_entry):
    logs = load_json(API_LOG_FILE, {"history": []})
    key = f"{log_entry['request_time']}_{log_entry['request_url'].split('ip=')[1].split('&')[0]}"
    logs["history"].insert(0, {key: log_entry})
    if len(logs["history"]) > MAX_API_LOGS:
        logs["history"] = logs["history"][:MAX_API_LOGS]
    save_json(API_LOG_FILE, logs)


def run_check():
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    statuses = load_json(STATUS_FILE, {})

    for server in data["servers"]:
        sid = str(server["id"])
        check_result = check_server_status(server["ip"], server.get("port", 25565))
        save_api_log(check_result["log"])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if sid not in statuses:
            statuses[sid] = {
                "server_id": server["id"],
                "host": f"{server['ip']}:{server.get('port', 25565)}",
                "last_check_at": now,
                "is_online": check_result["is_online"],
                "version": check_result.get("version", server["version"]),
                "motd": check_result.get("motd", ""),
                "latency": check_result.get("latency", 0),
                "players_online": check_result.get("players_online", 0),
                "players_max": check_result.get("players_max", 0),
                "players_sample": check_result.get("players_sample", []),
                "icon": check_result.get("icon", ""),
                "status_history": []
            }
        else:
            statuses[sid]["last_check_at"] = now
            statuses[sid]["is_online"] = check_result["is_online"]
            if check_result["success"]:
                statuses[sid]["version"] = check_result.get("version", statuses[sid]["version"])
                statuses[sid]["motd"] = check_result.get("motd", statuses[sid]["motd"])
                statuses[sid]["latency"] = check_result.get("latency", 0)
                statuses[sid]["players_online"] = check_result.get("players_online", 0)
                statuses[sid]["players_max"] = check_result.get("players_max", 0)
                statuses[sid]["players_sample"] = check_result.get("players_sample", [])
                statuses[sid]["icon"] = check_result.get("icon", statuses[sid]["icon"])

        statuses[sid]["status_history"].append({
            "time": now,
            "is_online": check_result["is_online"],
            "latency": check_result.get("latency", 0),
            "players_online": check_result.get("players_online", 0),
            "players_sample": check_result.get("players_sample", [])
        })
        if len(statuses[sid]["status_history"]) > MAX_HISTORY:
            statuses[sid]["status_history"] = statuses[sid]["status_history"][-MAX_HISTORY:]

    save_json(STATUS_FILE, statuses)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 巡检完成，共检查 {len(data['servers'])} 台服务器")


def schedule_check():
    while True:
        try:
            run_check()
        except Exception as e:
            print(f"巡检出错: {e}")
        time.sleep(CHECK_INTERVAL)


# ==================== 页面路由 ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/server/<int:sid>')
def server_detail_page(sid):
    return render_template('server_detail.html')


# ==================== 公开 API ====================

@app.route('/api/servers')
def get_servers():
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    statuses = load_json(STATUS_FILE, {})
    result = []
    for s in data["servers"]:
        sid = str(s["id"])
        s_data = dict(s)
        if sid in statuses:
            s_data.update(statuses[sid])
        else:
            s_data["is_online"] = False
            s_data["last_check_at"] = "未检测"
            s_data["latency"] = 0
            s_data["players_online"] = 0
            s_data["players_max"] = 0
            s_data["motd"] = ""
        s_data.pop("status_history", None)
        s_data["has_pack"] = bool(s.get("pack_filename"))
        result.append(s_data)
    return jsonify(result)


@app.route('/api/resources')
def get_resources():
    """✅ 根据身份返回资源：管理员看全部，普通玩家只看未隐藏的"""
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    resources = data.get("resources", [])
    is_admin = session.get("is_admin", False)
    
    result = []
    for r in resources:
        # 如果不是管理员且资源被隐藏，则跳过
        if not is_admin and r.get("hidden", False):
            continue
            
        r_data = dict(r)
        r_data["has_file"] = bool(r.get("file_path"))
        r_data["original_filename"] = r.get("original_filename", "")
        result.append(r_data)
    return jsonify(result)


@app.route('/api/server/<int:sid>')
def get_server_detail(sid):
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    statuses = load_json(STATUS_FILE, {})

    server = None
    for s in data["servers"]:
        if s["id"] == sid:
            server = dict(s)
            break

    if not server:
        return jsonify({"success": False, "msg": "服务器不存在"}), 404

    sid_str = str(sid)
    if sid_str in statuses:
        server.update(statuses[sid_str])
    else:
        server["is_online"] = False
        server["last_check_at"] = "未检测"
        server["latency"] = 0
        server["players_online"] = 0
        server["players_max"] = 0
        server["motd"] = ""
        server["status_history"] = []

    history = server.get("status_history", [])
    two_hours_ago_idx = max(0, len(history) - 120)
    server["recent_history"] = history[two_hours_ago_idx:]

    # ✅ 解析 extra_files (资源 ID 数组)，并关联资源库完整信息
    ef_ids = server.get("extra_files", [])
    if not isinstance(ef_ids, list):
        ef_ids = []
        
    all_resources = data.get("resources", [])
    res_map = {r["id"]: r for r in all_resources}
    
    extra_files_list = []
    for rid in ef_ids:
        if rid in res_map:
            r = dict(res_map[rid])
            r["has_file"] = bool(r.get("file_path"))
            extra_files_list.append(r)
            
    server["extra_files_list"] = extra_files_list
    server["has_pack"] = bool(server.get("pack_filename"))
    return jsonify({"success": True, "data": server})

@app.route('/api/server/<int:sid>/metrics')
def get_server_metrics(sid):
    """返回详情页状态图所需的历史指标序列（延迟 / 在线玩家数）"""
    statuses = load_json(STATUS_FILE, {})
    st = statuses.get(str(sid))
    if not st:
        return jsonify({"success": False, "msg": "暂无状态数据"}), 404

    history = st.get("status_history", [])
    recent = history[max(0, len(history) - MAX_HISTORY):]
    metrics = []
    for h in recent:
        metrics.append({
            "time": h.get("time", ""),
            "is_online": bool(h.get("is_online", False)),
            "latency": h.get("latency", 0),
            "players_online": h.get("players_online", 0),
            "players_sample": h.get("players_sample", [])
        })
    return jsonify({
        "success": True,
        "data": {
            "history": metrics,
            "players_max": st.get("players_max", 0)
        }
    })


@app.route('/api/download/pack/<int:sid>')
def download_pack(sid):
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    for s in data["servers"]:
        if s["id"] == sid and s.get("pack_filename"):
            filepath = os.path.join(PACKS_DIR, s["pack_filename"])
            if not os.path.exists(filepath):
                return jsonify({"success": False, "msg": "文件不存在"}), 404

            download_name = s.get("pack_original_filename") or s["pack_filename"]
            response = make_response(send_file(filepath, as_attachment=True))
            encoded_name = quote(download_name.encode('utf-8'))
            response.headers['Content-Disposition'] = (
                f"attachment; filename=\"{download_name}\"; filename*=UTF-8''{encoded_name}"
            )
            return response

    return jsonify({"success": False, "msg": "文件不存在"}), 404


@app.route('/api/download/resource/<int:rid>')
def download_resource_file(rid):
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    for r in data["resources"]:
        if r["id"] == rid and r.get("file_path"):
            filepath = os.path.join(RESOURCES_DIR, r["file_path"])
            if not os.path.exists(filepath):
                return jsonify({"success": False, "msg": "文件不存在"}), 404

            download_name = r.get("original_filename") or r["file_path"]
            response = make_response(send_file(filepath, as_attachment=True))
            encoded_name = quote(download_name.encode('utf-8'))
            response.headers['Content-Disposition'] = (
                f"attachment; filename=\"{download_name}\"; filename*=UTF-8''{encoded_name}"
            )
            return response

    return jsonify({"success": False, "msg": "文件不存在"}), 404


# ==================== 管理员认证 ====================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    pwd = request.json.get("password", "")
    if pwd == ADMIN_PASSWORD:
        session["is_admin"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "msg": "密码错误"})


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True})


@app.route('/api/admin/check')
def admin_check():
    return jsonify({"is_admin": session.get("is_admin", False)})


@app.route('/api/admin/check-now', methods=['POST'])
def manual_check():
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    Thread(target=run_check).start()
    return jsonify({"success": True, "msg": "已触发巡检"})


# ==================== 服务器管理 ====================

@app.route('/api/admin/servers', methods=['POST'])
def add_server():
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    new_s = request.json
    new_s["id"] = int(time.time())
    # ✅ extra_files 默认为空数组
    new_s.setdefault("extra_files", [])
    new_s.setdefault("pack_filename", "")
    data["servers"].append(new_s)
    save_json(DATA_FILE, data)
    Thread(target=run_check).start()
    return jsonify({"success": True, "data": new_s})


@app.route('/api/admin/servers/<int:sid>', methods=['PUT'])
def update_server(sid):
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    for i, s in enumerate(data["servers"]):
        if s["id"] == sid:
            update_data = request.json
            if "extra_files" in update_data:
                # ✅ 确保保存的是数组
                ef = update_data["extra_files"]
                data["servers"][i]["extra_files"] = ef if isinstance(ef, list) else []
            for key in ["name", "ip", "port", "version", "key", "description"]:
                if key in update_data:
                    data["servers"][i][key] = update_data[key]
            save_json(DATA_FILE, data)
            Thread(target=run_check).start()
            return jsonify({"success": True, "data": data["servers"][i]})
    return jsonify({"success": False, "msg": "服务器不存在"}), 404


@app.route('/api/admin/servers/<int:sid>', methods=['DELETE'])
def delete_server(sid):
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    for s in data["servers"]:
        if s["id"] == sid and s.get("pack_filename"):
            old_path = os.path.join(PACKS_DIR, s["pack_filename"])
            if os.path.exists(old_path):
                os.remove(old_path)
            break
    data["servers"] = [s for s in data["servers"] if s["id"] != sid]
    save_json(DATA_FILE, data)
    statuses = load_json(STATUS_FILE, {})
    if str(sid) in statuses:
        del statuses[str(sid)]
        save_json(STATUS_FILE, statuses)
    return jsonify({"success": True})


@app.route('/api/admin/servers/<int:sid>/upload-pack', methods=['POST'])
def upload_pack(sid):
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    if 'file' not in request.files:
        return jsonify({"success": False, "msg": "没有文件"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "msg": "没有选择文件"})
    if '.' not in file.filename:
        return jsonify({"success": False, "msg": "文件扩展名无效"})
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_PACK_EXTENSIONS:
        return jsonify({"success": False, "msg": f"不支持的文件类型: {ext}"})

    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    server_found = any(s["id"] == sid for s in data["servers"])
    if not server_found:
        return jsonify({"success": False, "msg": "服务器不存在"}), 404

    original_name = file.filename
    safe_name = safe_keep_filename(original_name)

    for s in data["servers"]:
        if s["id"] == sid and s.get("pack_filename"):
            old_path = os.path.join(PACKS_DIR, s["pack_filename"])
            if os.path.exists(old_path):
                os.remove(old_path)
            break

    filepath = os.path.join(PACKS_DIR, safe_name)
    file.save(filepath)

    for i, s in enumerate(data["servers"]):
        if s["id"] == sid:
            data["servers"][i]["pack_filename"] = safe_name
            data["servers"][i]["pack_original_filename"] = original_name
            save_json(DATA_FILE, data)
            return jsonify({"success": True, "filename": safe_name})
    return jsonify({"success": False, "msg": "服务器不存在"}), 404


# ==================== 资源管理 ====================

@app.route('/api/admin/resources', methods=['POST'])
def add_resource():
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    new_r = request.json
    new_r["id"] = int(time.time())
    new_r.setdefault("file_path", "")
    new_r.setdefault("original_filename", "")
    new_r.setdefault("hidden", False) # ✅ 默认不隐藏
    data["resources"].append(new_r)
    save_json(DATA_FILE, data)
    return jsonify({"success": True, "data": new_r})


@app.route('/api/admin/resources/upload-local', methods=['POST'])
def add_resource_local():
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    if 'file' not in request.files:
        return jsonify({"success": False, "msg": "没有文件"})

    file = request.files['file']
    name = request.form.get('name', '').strip()
    rtype = request.form.get('type', '').strip()
    # ✅ 获取隐藏状态 (FormData 中的 checkbox 如果勾选会传 'on' 或 'true')
    is_hidden = request.form.get('hidden', 'false').lower() in ['true', 'on', '1']

    if not name or not rtype:
        return jsonify({"success": False, "msg": "名称和类型为必填项"})
    if file.filename == '':
        return jsonify({"success": False, "msg": "没有选择文件"})

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_RESOURCE_EXTENSIONS:
        return jsonify({"success": False, "msg": f"不支持的文件类型: {ext}"})

    original_name = file.filename
    safe_name = safe_keep_filename(original_name)

    final_safe_name = safe_name
    counter = 1
    while os.path.exists(os.path.join(RESOURCES_DIR, final_safe_name)):
        base, extension = os.path.splitext(safe_name)
        final_safe_name = f"{base}_{counter}{extension}"
        counter += 1

    filepath = os.path.join(RESOURCES_DIR, final_safe_name)
    file.save(filepath)

    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    new_r = {
        "id": int(time.time()),
        "name": name,
        "type": rtype,
        "link": "",
        "file_path": final_safe_name,
        "original_filename": original_name,
        "hidden": is_hidden # ✅ 保存隐藏状态
    }
    data["resources"].append(new_r)
    save_json(DATA_FILE, data)
    return jsonify({"success": True, "data": new_r})


@app.route('/api/admin/resources/<int:rid>', methods=['PUT'])
def update_resource(rid):
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    for i, r in enumerate(data["resources"]):
        if r["id"] == rid:
            # ✅ 更新隐藏状态及其他字段
            update_data = request.json
            if "hidden" in update_data:
                data["resources"][i]["hidden"] = bool(update_data["hidden"])
            # 允许更新名称和类型（如果需要的话）
            if "name" in update_data: data["resources"][i]["name"] = update_data["name"]
            if "type" in update_data: data["resources"][i]["type"] = update_data["type"]
            
            save_json(DATA_FILE, data)
            return jsonify({"success": True, "data": data["resources"][i]})
    return jsonify({"success": False, "msg": "资源不存在"}), 404


@app.route('/api/admin/resources/<int:rid>', methods=['DELETE'])
def delete_resource(rid):
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    for r in data["resources"]:
        if r["id"] == rid and r.get("file_path"):
            fpath = os.path.join(RESOURCES_DIR, r["file_path"])
            if os.path.exists(fpath):
                os.remove(fpath)
            break
            
    # ✅ 删除资源时，同时从所有服务器的 extra_files 中移除该 ID
    for s in data["servers"]:
        if "extra_files" in s and isinstance(s["extra_files"], list):
            if rid in s["extra_files"]:
                s["extra_files"].remove(rid)
                
    data["resources"] = [r for r in data["resources"] if r["id"] != rid]
    save_json(DATA_FILE, data)
    return jsonify({"success": True})


@app.route('/api/admin/resources/<int:rid>/upload-file', methods=['POST'])
def upload_resource_file(rid):
    if not session.get("is_admin"):
        return jsonify({"success": False, "msg": "未授权"}), 403
    if 'file' not in request.files:
        return jsonify({"success": False, "msg": "没有文件"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "msg": "没有选择文件"})
    if '.' not in file.filename:
        return jsonify({"success": False, "msg": "文件扩展名无效"})
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_RESOURCE_EXTENSIONS:
        return jsonify({"success": False, "msg": f"不支持的文件类型: {ext}"})

    data = load_json(DATA_FILE, {"servers": [], "resources": []})
    resource_found = any(r["id"] == rid for r in data["resources"])
    if not resource_found:
        return jsonify({"success": False, "msg": "资源不存在"}), 404

    original_name = file.filename
    safe_name = safe_keep_filename(original_name)

    for r in data["resources"]:
        if r["id"] == rid and r.get("file_path"):
            old_path = os.path.join(RESOURCES_DIR, r["file_path"])
            if os.path.exists(old_path):
                os.remove(old_path)
            break

    filepath = os.path.join(RESOURCES_DIR, safe_name)
    file.save(filepath)

    for i, r in enumerate(data["resources"]):
        if r["id"] == rid:
            data["resources"][i]["file_path"] = safe_name
            data["resources"][i]["original_filename"] = original_name
            save_json(DATA_FILE, data)
            return jsonify({"success": True, "filename": safe_name})
    return jsonify({"success": False, "msg": "资源不存在"}), 404


# ==================== 启动 ====================

if __name__ == '__main__':
    host = CFG.get('HOST', '0.0.0.0')
    port = CFG.get('PORT', 5000)
    init_data()
    cleanup_orphan_files()
    Thread(target=run_check).start()
    check_thread = Thread(target=schedule_check, daemon=True)
    check_thread.start()
    print(f"✅ MC服务器大厅已启动: http://127.0.0.1:{port}")
    print(f"🔑 管理员密码: {ADMIN_PASSWORD}")
    print(f"⏱️  巡检间隔: {CHECK_INTERVAL}秒，保存最近{MAX_HISTORY}条历史")
    app.run(host=host, port=port, debug=False)