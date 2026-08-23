"""邮件发送模块。

只负责构造与发送邮件：离线告警邮件、SMTP 测试邮件。
不包含巡检、状态机、文件 I/O 逻辑。配置常量统一从 app 模块的 CFG 读取。
"""
import smtplib
import time
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate

# 独立读取配置，避免与 app.py 循环导入
with open('config.json', 'r', encoding='utf-8') as _f:
    CFG = json.load(_f)
ALERT_ENABLED = CFG.get('ALERT_ENABLED', False)
ALERT_OFFLINE_MINUTES = CFG.get('ALERT_OFFLINE_MINUTES', 60)
SMTP_HOST = CFG.get('SMTP_HOST', '')
SMTP_PORT = CFG.get('SMTP_PORT', 465)
SMTP_USER = CFG.get('SMTP_USER', '')
SMTP_PASSWORD = CFG.get('SMTP_PASSWORD', '')
SMTP_FROM = CFG.get('SMTP_FROM') or SMTP_USER
SMTP_USE_SSL = CFG.get('SMTP_USE_SSL', True)


def _open_smtp():
    """建立 SMTP 连接并登录。"""
    if SMTP_USE_SSL:
        smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20)
    else:
        smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
        smtp.starttls()
    smtp.login(SMTP_USER, SMTP_PASSWORD)
    return smtp


def _missing_smtp_keys():
    """返回 SMTP 必填字段中为空的键名列表。"""
    return [
        k for k, v in (
            ("SMTP_HOST", SMTP_HOST),
            ("SMTP_USER", SMTP_USER),
            ("SMTP_PASSWORD", SMTP_PASSWORD),
        ) if not v
    ]


def build_alert_message(server, status, emails):
    """构造离线告警邮件。

    - server: data.json 中的服务器配置 dict
    - status: Server_status.json 中的状态 dict（需含 offline_since）
    - emails: 收件人列表（至少 1 个）
    """
    offline_ts = datetime.strptime(status["offline_since"], "%Y-%m-%d %H:%M:%S").timestamp()
    minutes = int((time.time() - offline_ts) / 60)

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr(("MC-Server-Hub 告警", SMTP_FROM))
    msg["To"] = emails[0]
    if len(emails) > 1:
        msg["Bcc"] = ", ".join(emails[1:])
    msg["Subject"] = f"[告警] 服务器「{server['name']}」已离线 {minutes} 分钟"
    msg["Date"] = formatdate(localtime=True)

    body = f"""服务器离线告警

服务器名称：{server['name']}
服务器地址：{server['ip']}:{server.get('port', 25565)}
离线起始：{status['offline_since']}
已离线时长：{minutes} 分钟
最后检测：{status.get('last_check_at', '-')}
当前在线人数:{status.get('players_online', 0)} / {status.get('players_max', 0)}

请尽快登录管理后台排查。

—— MC-Server-Hub 自动告警
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def send_alert_email(server, status, emails):
    """异步线程调用：构造并发送离线告警邮件。

    任何异常都只打印日志，不抛出（线程内独立运行）。
    """
    try:
        msg = build_alert_message(server, status, emails)
        smtp = _open_smtp()
        try:
            smtp.sendmail(SMTP_USER, emails, msg.as_string())
        finally:
            smtp.quit()
    except Exception as e:
        print(f"⚠️ 告警邮件发送失败 [{server.get('name', '?')}]: {type(e).__name__}: {e}")


def send_test_email():
    """发送测试邮件到 SMTP_USER 自己，验证 SMTP 配置可用性。

    返回 (success: bool, msg: str)
    """
    if not ALERT_ENABLED:
        return False, "告警未启用（ALERT_ENABLED=false）"
    missing = _missing_smtp_keys()
    if missing:
        return False, f"SMTP 配置不完整：{','.join(missing)}"

    recipient = SMTP_USER
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr(("MC-Server-Hub 测试", SMTP_FROM))
    msg["To"] = recipient
    msg["Subject"] = "[测试] MC-Server-Hub 邮件告警配置正常"
    msg["Date"] = formatdate(localtime=True)
    body = "这是一封来自 MC-Server-Hub 的测试邮件。\n\n若你收到此邮件，说明 SMTP 配置正常，服务器离线告警将能成功发送。\n"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        smtp = _open_smtp()
        try:
            smtp.sendmail(SMTP_FROM, [recipient], msg.as_string())
        finally:
            smtp.quit()
        return True, f"测试邮件已发送至 {recipient}"
    except Exception as e:
        return False, f"发送失败：{type(e).__name__}: {e}"


def check_smtp_config():
    """启动时 SMTP 配置自检：打印警告。"""
    if not ALERT_ENABLED:
        return
    missing = _missing_smtp_keys()
    if missing:
        print(f"⚠️ ALERT_ENABLED=true 但 SMTP 配置不完整：{','.join(missing)}，告警邮件将无法发送")
    else:
        print(f"📧 告警已启用：阈值 {ALERT_OFFLINE_MINUTES} 分钟，SMTP {SMTP_HOST}:{SMTP_PORT}")
