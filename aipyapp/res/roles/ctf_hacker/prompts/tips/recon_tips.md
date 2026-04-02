# CTF WEB 渗透侦察与信息收集 (Recon) 指南

在 Web 类 CTF 题目中，目标通常是**指定的唯一 URL**。**严禁进行无意义的端口扫描（如 Nmap）**。你应该将所有精力集中在应用层的逻辑分析、目录探测和接口 Fuzzing 上。

1. **基础信息与页面源码分析 (Basic Recon)**:
   - **第一步永远是**获取目标 URL 的页面源码，仔细阅读 HTML 结构，寻找隐藏的 HTML 注释 (`<!-- -->`)、隐藏的表单字段 (`<input type="hidden">`) 或内联 JavaScript。
   - 检查 `robots.txt`, `sitemap.xml`, 以及源码中引入的 `.js` / `.css` 文件。很多时候接口和路由会硬编码在前端静态文件中。
   - 检查并分析 HTTP 响应头（如 `Server`, `X-Powered-By`, `Set-Cookie` 等），判断其后端语言和框架版本。

2. **敏感目录与文件泄露探测 (Directory & File Fuzzing)**:
   - Web 题目常常隐藏着关键源码或备份文件。
   - 利用 `p_security_tools` 提供的并发工具或自行编写 Python 脚本，快速探测以下常见泄漏点：
     - **源码泄露**: `.git/config`, `.svn/entries`, `.DS_Store`, `www.zip`, `backup.rar`, `source.tar.gz` 等。
     - **后台或隐藏接口**: `/admin`, `/login.php`, `/api/v1/user`, `/flag.php`, `/config.php`。
   - **效率提示**: 当需要爆破大量目录时，请优先使用内置的 `concurrent_fuzz` 高级函数，并将此任务作为 `SubTask` 委派出去，避免阻塞主线程。

3. **请求参数与交互分析 (Parameter Analysis)**:
   - 如果页面有交互功能（如登录、搜索、留言、文件上传），仔细分析数据是如何提交的（GET/POST, JSON 还是 Form-Data）。
   - 检查 URL 栏是否存在可疑参数（例如 `?page=about`, `?id=1`, `?file=index.php`），这些往往是本地文件包含 (LFI)、SQL 注入或 SSRF 的切入点。

4. **漏洞验证与框架识别 (Vulnerability Identification)**:
   - 尝试引发报错（如在参数中输入单引号 `'`，或输入非法数据类型），通过错误堆栈信息 (Error Traceback) 识别后端框架（如 ThinkPHP、Werkzeug、Flask、Spring Boot）。
   - 一旦确认框架，立刻检索其历史 CVE 漏洞（如反序列化、RCE），并尝试针对性地构造 Payload。

5. **总结与指派 (Commander Mode)**:
   - 侦察过程中，如果发现多个潜在的攻击面（例如既有文件上传口，又有带参数的查询口），**立即使用 SubTask 并发派发任务**，让子任务分别去探测这几个独立的攻击面。