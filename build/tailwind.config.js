/**
 * Tailwind CSS 构建配置（与原 CDN 运行时配置保持一致）
 *
 * 项目已改为加载本地精简样式文件 static/css/tailwind.min.css，
 * 修改模板中的类名后需重新构建，见 README「本地 Tailwind 构建」章节。
 *
 * 本文件位于 build/ 目录，扫描与输出路径均以 __dirname 锚定到项目根，
 * 因此无论从项目根还是 build/ 目录调用构建器，结果都一致。
 */
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');

module.exports = {
    darkMode: 'class',
    content: [
        path.join(projectRoot, 'templates', '**', '*.html'),
        path.join(projectRoot, 'static', 'js', '**', '*.js'),
    ],
    theme: {
        extend: {
            colors: {
                mcgreen: '#5D8C47',
                mcdark: '#1a1a2e',
            },
        },
    },
    plugins: [],
};
