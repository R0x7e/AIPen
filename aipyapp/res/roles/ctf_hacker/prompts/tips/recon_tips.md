# WEB 渗透信息收集与侦察 (Recon) 指南

1. **基本信息收集**:
   - 首先请求目标 URL 的页面，提取源码中的关键信息，特别是注释 (如 `<!-- -->`)。
   - 分析 HTTP 响应头 (Server, X-Powered-By, Set-Cookie) 判断运行环境和版本。
   - 使用 Python 脚本或 `curl` 请求常见的敏感路径 (如 `robots.txt`, `.git/config`, `sitemap.xml`)。

2. **端口与服务探测**:
   - 尝试使用 Python 脚本或 Nmap 扫描目标的其他开放端口。
   - 判断不同端口的服务类型（HTTP/FTP/SSH/MySQL/Redis 等），以及可能的未授权访问漏洞。

3. **目录扫描**:
   - 若目标是一个未知应用，可以使用 Python 发送字典中的常见路径（如 `admin/`, `login.php`, `config.php`, `backup.zip`, `.DS_Store`）进行爆破。

4. **漏洞验证与分析**:
   - 识别后端框架或 CMS（如 ThinkPHP、WordPress、Shiro），检查已知漏洞。
   - 收集到信息后，针对特定接口设计 Fuzzing 测试，并观察响应状态码、长度或内容变化。