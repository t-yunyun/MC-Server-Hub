"""项目配置加载与常量集中暴露。

只读取 config.json 并派生常量，不含任何业务逻辑。
其他模块统一从此处导入常量，避免重复 load_config。
"""
import json
import os

CONFIG_FILE = 'config.json'


def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


CFG = load_config()

# ==================== Flask / 服务启动 ====================
HOST = CFG.get('HOST', '0.0.0.0')
PORT = CFG.get('PORT', 5000)
SECRET_KEY = CFG['SECRET_KEY']
ADMIN_PASSWORD = CFG['ADMIN_PASSWORD']

# ==================== 文件路径 ====================
DATA_FILE = CFG['DATA_FILE']
STATUS_FILE = CFG['STATUS_FILE']
API_LOG_FILE = CFG['API_LOG_FILE']
UPLOAD_DIR = CFG['UPLOAD_DIR']
PACKS_DIR = os.path.join(UPLOAD_DIR, 'packs')
RESOURCES_DIR = os.path.join(UPLOAD_DIR, 'resources')

# ==================== 巡检相关 ====================
MAX_HISTORY = CFG['MAX_HISTORY']
MAX_API_LOGS = CFG['MAX_API_LOGS']
CHECK_INTERVAL = CFG['CHECK_INTERVAL']

# ==================== 上传扩展名白名单 ====================
ALLOWED_PACK_EXTENSIONS = {'zip', 'rar', '7z', 'tar', 'gz', 'jar', 'xz', 'bz2', 'lz'}
ALLOWED_RESOURCE_EXTENSIONS = {
    'zip', 'rar', '7z', 'tar', 'gz', 'jar',
    'png', 'jpg', 'jpeg', 'pdf', 'txt',
    'json', 'cfg', 'config',
}

# ==================== 业务常量 ====================
MAX_DESCRIPTION_LENGTH = 200

# ==================== 告警 / SMTP ====================
ALERT_ENABLED = CFG.get('ALERT_ENABLED', False)
ALERT_OFFLINE_MINUTES = CFG.get('ALERT_OFFLINE_MINUTES', 60)
SMTP_HOST = CFG.get('SMTP_HOST', '')
SMTP_PORT = CFG.get('SMTP_PORT', 465)
SMTP_USER = CFG.get('SMTP_USER', '')
SMTP_PASSWORD = CFG.get('SMTP_PASSWORD', '')
SMTP_FROM = CFG.get('SMTP_FROM') or SMTP_USER
SMTP_USE_SSL = CFG.get('SMTP_USE_SSL', True)
