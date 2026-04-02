# SQL 注入 (SQLi) 自动化检测与利用指南

1. **探测点寻找**:
   - GET 参数 (如 `?id=1`)、POST 表单数据 (登录、搜索)、HTTP Header (User-Agent, X-Forwarded-For, Cookie 等)。

2. **初步验证 (Fuzzing)**:
   - 输入单引号 `'` 或双引号 `"` 观察页面是否报错。
   - 输入逻辑运算 `AND 1=1` (正常) 和 `AND 1=2` (异常或内容不同) 验证盲注。
   - 输入时间延迟 `SLEEP(5)` 或 `WAITFOR DELAY '0:0:5'` 验证时间盲注。

3. **过滤绕过 (Bypass WAF)**:
   - **空格过滤**: 使用 `/**/`、`%0a`、`%09`、`%0c`、`+` 或 `()` 绕过。
   - **关键字过滤** (如 `select`, `union`): 尝试大小写混写 `SeLeCt`、双写 `selselectect`、URL 编码 `%73%65%6c%65%63%74` 或十六进制。
   - **等号过滤**: 使用 `LIKE`、`IN`、`REGEXP` 代替 `=`。

4. **利用策略**:
   - **联合查询 (UNION)**: 先用 `ORDER BY N` 判断列数，再用 `UNION SELECT 1,2,3...` 找出回显点，获取 `database()`, `version()`, `user()`，进而获取表名、列名和数据。
   - **报错注入 (Error-Based)**: 尝试 `EXTRACTVALUE()`, `UPDATEXML()`, `FLOOR(RAND())`。
   - **盲注 (Blind)**: 编写 Python 脚本二分查找法逐位猜解数据。

5. **获取 Flag**:
   - 查询 `flag` 数据库或表中的内容，如 `SELECT flag FROM flag`。
   - 如果是文件读取注入，尝试 `LOAD_FILE('/flag')`。