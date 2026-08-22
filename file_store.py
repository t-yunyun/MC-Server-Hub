"""文件 I/O 工具集合。

只提供与本地文件/目录相关的通用操作：文件名安全处理、JSON 读写、
初始化数据文件、清理孤儿文件。不涉及业务逻辑（巡检、告警等）。
所有路径与配置常量统一从 config 导入。
"""
import json
import os
import re

from config import (
    DATA_FILE,
    STATUS_FILE,
    API_LOG_FILE,
    UPLOAD_DIR,
    PACKS_DIR,
    RESOURCES_DIR,
)


def safe_keep_filename(filename):
    """将任意文件名转为安全的本地文件名（去掉路径分隔与非法字符）。"""
    filename = os.path.basename(filename)
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    if filename.startswith('.'):
        filename = '_' + filename
    return filename or 'unnamed_file'


def load_json(filename, default):
    """读取 JSON 文件。文件不存在或解析失败时返回 default。

    对 data.json 做"resources 字段兜底"补全：旧数据缺 resources 时自动写入空数组。
    """
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
    """写入 JSON 文件（ensure_ascii=False, indent=2）。"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_data():
    """初始化数据目录与三份默认数据文件（data/Server_status/api_response）。

    仅在文件不存在时写入默认内容，已存在的不覆盖。
    """
    # 自动创建 DATA_FILE 所在的目录
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
    """启动时自动清理未被 data.json 引用的孤儿文件。

    - uploads/resources：清理未被任何 resource.file_path 引用的文件
    - uploads/packs：清理未被任何 server.pack_filename 引用的文件
    """
    data = load_json(DATA_FILE, {"servers": [], "resources": []})

    # 1. 清理 uploads/resources 目录
    used_resources = {r["file_path"] for r in data.get("resources", []) if r.get("file_path")}
    if os.path.exists(RESOURCES_DIR):
        for filename in os.listdir(RESOURCES_DIR):
            if filename not in used_resources:
                file_path = os.path.join(RESOURCES_DIR, filename)
                try:
                    os.remove(file_path)
                    print(f"🧹 已清理无用资源文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 清理资源文件失败 {file_path}: {e}")

    # 2. 清理 uploads/packs 目录
    used_packs = {s["pack_filename"] for s in data.get("servers", []) if s.get("pack_filename")}
    if os.path.exists(PACKS_DIR):
        for filename in os.listdir(PACKS_DIR):
            if filename not in used_packs:
                file_path = os.path.join(PACKS_DIR, filename)
                try:
                    os.remove(file_path)
                    print(f"🧹 已清理无用整合包文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 清理整合包文件失败 {file_path}: {e}")
