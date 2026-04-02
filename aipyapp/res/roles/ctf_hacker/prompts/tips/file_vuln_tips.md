# 文件上传与包含 (File Upload & LFI/RFI) 漏洞指南

在 Web CTF 中，文件上传和文件包含漏洞是直接获取服务器 Shell 或读取敏感文件（如 `/flag`）的高效途径。

## 一、 文件上传 (File Upload)

1. **探测与绕过 (Bypass)**:
   - **前端绕过**: 如果有前端 JS 限制，直接使用 Python `requests` 构造 multipart/form-data 数据包绕过。
   - **MIME 绕过**: 修改请求头中的 `Content-Type: image/jpeg`。
   - **后缀名绕过**: 
     - 尝试大小写 (`.pHp`)、双写 (`.pphphp`)。
     - 尝试可执行的变体后缀（PHP: `.php3`, `.php4`, `.php5`, `.phtml`, `.phar`；JSP: `.jspx`, `.jspf`）。
     - 尝试空字节截断 (`shell.php%00.jpg`) 或空格/点号绕过 (`shell.php .`)。
   - **内容绕过**: 
     - 在文件头部添加图片幻数 (Magic Bytes)，如 `GIF89a`。
     - 使用各种短标签，如 `<?=system($_GET[1]);?>` 或 `<script language="php">`。

2. **条件竞争 (Race Condition)**:
   - 如果发现文件上传后会被立刻删除，尝试利用并发发送多个请求：一边疯狂上传文件，一边疯狂访问文件。
   - 这类任务非常适合指派 `SubTask`，并在其中编写 `aiohttp` 或 `threading` 脚本并发执行。

3. **`.htaccess` / `.user.ini` 技巧**:
   - 上传恶意的 `.htaccess` 改变解析规则（如：`AddType application/x-httpd-php .jpg`）。
   - 上传 `.user.ini` 包含其他文件 (`auto_prepend_file=shell.jpg`)。

## 二、 文件包含 (Local/Remote File Inclusion)

1. **本地文件包含 (LFI)**:
   - 目标参数：通常类似 `?file=`, `?page=`, `?include=`, `?module=`。
   - **读取敏感文件**: 首先尝试读取 `/etc/passwd` 验证漏洞。
   - **绕过路径过滤**: 
     - 使用 `../` 的变体：`....//`, `%2e%2e%2f`, `%252e%252e%252f` (双重 URL 编码)。
   - **伪协议利用 (PHP)**:
     - `php://filter/read=convert.base64-encode/resource=index.php` -> 极度常用，用于读取带 PHP 代码的源码，防止其被执行而导致无法看到源码。
     - `php://input` -> 结合 POST 数据执行代码。
     - `data://text/plain;base64,PD9waHAgcGhwaW5mbygpOz8+` -> 直接执行代码。

2. **日志包含 (Log Poisoning)**:
   - 如果存在 LFI 但无法直接上传文件，尝试将恶意 PHP 代码（如 `<?php system($_GET['c']); ?>`）写入日志中：
     - 在 HTTP 头的 `User-Agent` 中写入 Payload，然后通过 LFI 包含 Web 服务器的访问日志（如 `/var/log/nginx/access.log`, `/var/log/apache2/access.log`）。
     - 包含 SSH 日志 `/var/log/auth.log`。

3. **Session 包含**:
   - 寻找 PHP session 文件（通常位于 `/tmp/sess_PHPSESSID` 或 `/var/lib/php/sessions/`），将 Payload 写入 Session 中然后包含。