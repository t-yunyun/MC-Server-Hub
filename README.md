# MC服务器枢纽 **(MC-Server-Hub)**

一个轻量级、高颜值的 Minecraft 服务器状态监控与资源分发面板。支持实时检测服务器在线状态、玩家数据展示、整合包下载，以及为管理员提供便捷的资源库与服务器配置管理功能。

## 核心特性

- **实时状态监控**：自动巡检服务器状态，展示延迟、在线人数、MOTD 及近 2 小时在线状态图表。
- **资源库管理**：支持上传本地文件或外部链接，一键关联至指定服务器的额外文件列表。
- **隐私与可见性控制**：资源支持“隐藏”模式，隐藏资源仅在关联的服务器详情页可见，不在首页公开展示。
- **现代化 UI**：基于 Tailwind CSS 构建，完美支持亮色/暗色模式切换，响应式适配移动端与桌面端。
- ️**安全与隔离**：前后端分离设计，敏感配置（如密码、密钥）通过独立的 `config.json` 管理，该文件已被版本控制忽略。
- **国际化文件名下载兼容**：资源下载接口遵循 RFC 5987 标准，自动处理中文等非 ASCII 文件名。现代浏览器优先使用 UTF-8 编码的原始文件名，旧客户端或终端自动回退至 `unnamed.<后缀>` 语义化命名，彻底避免乱码与空文件名问题。

## ️ 技术栈

- **后端**：Python / Flask
- **前端**：HTML5 / Tailwind CSS / Chart.js
- **版本控制**：Git

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip 包管理器

### 2. 配置

> **请复制 `config.json.example` 并设置配置文件**，重命名为 `config.json` 后按需修改。

全部配置项的类型、默认值、是否必填及部署前检查清单，见 **[CONFIG.md](CONFIG.md)**。

部署前请务必修改 `SECRET_KEY` 与 `ADMIN_PASSWORD`。

### 3. 启动

```bash
pip install -r requirements.txt
python app.py
```

启动后访问 `http://127.0.0.1:5000`（端口由 `PORT` 配置）。

---

## 其他注意事项

以下内容与日常启动运行无关，仅在修改前端样式或部署到国内网络环境时需要关注。

### 1.本地 Tailwind 构建

项目不再引用 `https://cdn.tailwindcss.com`，改为加载预构建的本地样式文件 `static/css/tailwind.min.css`（约 22 KB，仅包含模板实际用到的类）。

**普通部署无需执行构建**，仓库内的 `tailwind.min.css` 已是最新产物，直接 `python app.py` 启动即可，页面不依赖任何 Tailwind 外网资源。

只有在**修改了模板/JS 里的 Tailwind 类名**，或调整了主题配置时，才需要重新构建。构建仅用于开发阶段，运行环境不需要 Node.js。所有构建相关文件集中在 `build/` 目录，不污染项目根目录。

```bash
# 首次构建前安装依赖（需要 Node.js 18+），在 build/ 目录内执行
cd build
npm install

# 重新生成 static/css/tailwind.min.css（同样在 build/ 目录内执行）
npm run build:css
```

构建配置与产物均以 `build/tailwind.config.js` 中的 `__dirname` 锚定到项目根，因此从项目根目录直接调用构建器同样可行：

```bash
node build/node_modules/tailwindcss/lib/cli.js -c build/tailwind.config.js -i build/tailwind.input.css -o static/css/tailwind.min.css --minify
```

相关文件说明：

| 文件                            | 作用                                                                                      |
|:----------------------------- |:--------------------------------------------------------------------------------------- |
| `build/package.json`          | 构建依赖与 `build:css` 脚本                                                                    |
| `build/tailwind.config.js`    | 构建配置，`darkMode: 'class'` 与 `mcgreen` / `mcdark` 自定义色与页面内联样式保持一致；扫描路径以 `__dirname` 锚定项目根 |
| `build/tailwind.input.css`    | 构建入口，仅包含三条 `@tailwind` 指令                                                               |
| `static/css/tailwind.min.css` | 构建产物，模板实际引用此文件（属运行时资源，故留在 `static/`，请勿手动编辑）                                             |

构建器会扫描 `templates/**/*.html` 与 `static/js/**/*.js` 提取类名。注意：JS 中以字符串字面量形式出现的类名（含模板字符串三元表达式）可被正确识别，但**运行时用变量拼接的类名无法被扫描到**，若新增此类写法，需将其加入 `build/tailwind.config.js` 的 `safelist`。

### 2.外部静态资源镜像

项目仍有两类资源走公网 CDN，均已切换为国内镜像：

| 资源                 | 主源                       | 回退源               | 使用页面   |
|:------------------ |:------------------------ |:----------------- |:------ |
| Font Awesome 6.4.0 | `registry.npmmirror.com` | `cdn.bootcdn.net` | 全部三个页面 |
| ECharts 5.5.0      | `registry.npmmirror.com` | `cdn.bootcdn.net` | 服务器详情页 |

回退机制：

- Font Awesome 用 `<link onerror>` 切换 `href`，样式表加载失败时自动改用备用源。
- ECharts 沿用原有的 `window.echarts || document.write(...)` 检测，脚本未成功加载时写入备用源。

若希望完全脱离公网（内网部署，或镜像整体不可用时），可将这两个资源下载到 `static/` 目录并改为本地路径

---

# MC 服务器状态查询 API 使用说明

本项目使用 [MineBBS MC 服务器状态查询 API](https://motd.minebbs.com/docs) 来获取 Minecraft 服务器的实时状态信息。该 API 为广大 Minecraft 服主提供免费、快捷的服务器状态查询工具，支持 Java 版和基岩版。

## 项目中的调用方式

本项目在后台通过 Flask 定时任务调用 `/api/status` 接口，实现以下功能：

1. **定时巡检**：按照 `config.json` 中 `CHECK_INTERVAL` 配置的间隔（默认 60 秒），自动请求所有已添加服务器的状态。
2. **状态缓存**：将查询结果写入 `Server_status.json`，供前端页面实时展示。
3. **历史图表**：保留最近 `MAX_HISTORY` 条（默认 120 条）状态记录，用于在服务器详情页绘制服务器在线状态图。
4. **日志记录**：所有 API 请求记录写入 `api_response.json`，便于排查巡检失败问题。 

## 注意事项

* **频率限制**：建议不要将 `CHECK_INTERVAL` 设置过低（低于 30 秒），以免被 API 服务限流。
* **默认端口**：如果不指定 `port` 参数，API 会根据 `stype` 自动选择默认端口（Java 版 25565，基岩版 19132）。
* **查询类型**：`stype=je` 仅查询 Java 版服务器，`stype=be` 仅查询基岩版服务器，`stype=auto`（默认）自动识别。
* **HTTPS 要求**：API 服务通过 HTTPS 提供，请确保你的服务器可以正常访问外网。
