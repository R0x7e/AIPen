# WAF 绕过与安全机制逃逸指南 (WAF Bypass)

在 CTF Web 题目中，经常会遇到各种形式的 WAF（Web 应用防火墙）或自定义的输入过滤机制。当你发现 Payload 触发了 403 Forbidden、"Hacker Detected" 或空响应时，不要轻易放弃漏洞，必须尝试绕过。

## 1. 架构与协议层绕过

利用 WAF 和后端服务器对 HTTP 协议解析的不一致性（HTTP Desync）进行绕过。

- **分块传输编码 (Chunked Transfer Encoding)**:
  - 许多 WAF 不支持解析 Chunked 编码的请求体，但后端服务器（如 Nginx, Tomcat）支持。
  - 在 HTTP 请求头中加入 `Transfer-Encoding: chunked`，然后将 Payload 分成极小的块（例如 1 或 2 个字符一块）进行传输。
- **参数污染 (HTTP Parameter Pollution, HPP)**:
  - 提供多个同名参数，如 `?id=1&id=2`。
  - 不同的后端框架取值不同：PHP/Apache 取最后一个值 (`2`)，ASP.NET/Tomcat 取第一个或拼接 (`1,2`)。如果 WAF 只检查第一个参数，可以通过 HPP 绕过。
- **畸形请求头/空字节**:
  - 尝试在 URL 参数中插入 `%00` 空字节。
  - 使用不受支持的 HTTP 方法（将 `GET` 改为 `POST`, `PUT`, `PATCH`, 甚至乱写的 `HACK`）来规避规则。

## 2. 编码与字符混淆 (Encoding & Obfuscation)

WAF 通常基于正则匹配关键字，通过编码可以将关键字拆散或改变形式。

- **URL 编码变体**:
  - URL 双重编码 (`%2527` 代替 `'`)。
  - URL 宽字节编码 (如 `%bf%27` 绕过 PHP `addslashes` 引发的单引号转义，常用于 GBK 环境的 SQL 注入)。
- **Unicode 与 Hex 编码**:
  - 将字符转换为 Unicode (如 `\u0027`) 或 Hex 形式，特别是在 JSON 载荷或 JavaScript 环境中 (如 `\x3c\x73\x63\x72\x69\x70\x74\x3e` 代替 `<script>`)。
- **HTML 实体编码**:
  - 在允许 HTML 注入的地方，使用 `&#x3C;` 代替 `<`。
- **SQL 特殊混淆**:
  - `/*!50000SELECT*/` (MySQL 内联注释，WAF 会当作注释忽略，但 MySQL 会执行)。
  - 大小写替换 (`SeLeCt`)，内联注释插入 (`SEL/**/ECT`)。

## 3. 命令注入与 Linux Shell 绕过

在 RCE (Remote Code Execution) 漏洞中，经常会过滤空格、特殊符号或敏感命令。

- **过滤空格**:
  - 使用 `<` 重定向符：`cat<flag`
  - 使用内部字段分隔符 `$IFS`：`cat${IFS}flag` 或 `cat$IFS$9flag`
  - 使用 URL 编码的 Tab `%09`
- **过滤关键字 (如 `flag`, `cat`, `sh`)**:
  - **通配符**: `cat /fl*`，`/bin/c?t /fl?g`
  - **拼接**: `a=fl;b=ag;cat /$a$b`，或 `cat /fl""ag`，`cat /fl''ag`
  - **反斜杠**: `c\at /fl\ag`
  - **Base64 执行**: `echo "Y2F0IC9mbGFn" | base64 -d | bash`
- **过滤斜杠 `/`**:
  - 使用环境变量截取：`${HOME:0:1}` 通常表示 `/`。
- **绕过长度限制**:
  - 利用 `>a` 技巧将命令写入多个短文件，然后用 `ls -t > x` 和 `sh x` 执行 (Hit and Run)。

## 4. SQL 注入绕过总结

- **过滤 `AND` / `OR`**: 替换为 `&&`, `||`
- **过滤 `=`**: 替换为 `LIKE`, `RLIKE`, `REGEXP`, `<>`, `<`, `>`
- **过滤 `SPACE` (空格)**: 替换为 `%09`, `%0a`, `%0b`, `%0c`, `%0d`, `%a0`, 或 `/**/`
- **过滤逗号 `,`**:
  - `LIMIT 1,1` -> `LIMIT 1 OFFSET 1`
  - `SUBSTR(str, 1, 1)` -> `SUBSTR(str FROM 1 FOR 1)`
  - `MID(str, 1, 1)` -> `MID(str FROM 1 FOR 1)`

## 5. 指挥官实战策略

遇到 WAF 时，作为指挥官，不要轻易放弃。
1. **分析 WAF 行为**: 派发 SubTask，分别发送正常的请求、轻微畸形的请求、恶意的请求，分析 WAF 是基于什么（关键字、正则、长度还是请求频率）进行拦截的。
2. **利用 Fuzzing 自动化绕过**: 编写 Python 脚本或调用 `concurrent_fuzz`，将常见的绕过字典（如各类空格替代符、各种编码格式的单引号）进行自动化投递，观察哪些 Payload 能引发不一样的响应状态码（如 500 而不是 403）。