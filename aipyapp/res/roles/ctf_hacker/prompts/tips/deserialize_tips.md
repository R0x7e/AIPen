# 反序列化 (Deserialization) 漏洞指南

反序列化漏洞通常出现在应用程序将不可信的数据转换为对象时，可能导致远程代码执行 (RCE)、访问控制绕过或敏感数据泄露。

## 1. 识别反序列化数据

- **PHP**:
  - 数据格式特征：`O:4:"User":2:{s:8:"username";s:5:"admin";}`
  - 关注参数、Cookie（尤其 base64 编码后看起来像乱码的 Cookie）。
- **Java**:
  - 数据特征：十六进制 `AC ED 00 05` 或 base64 的 `rO0AB` 开头。
  - 常见位置：RMI、JMX、HTTP 请求体、Header 中的鉴权字段。
- **Python**:
  - 寻找 `pickle.loads()`, `yaml.load()`, `jsonpickle` 的输入点。
- **Node.js/JavaScript**:
  - 寻找 `node-serialize`，或者处理 `JSON.parse` 结合原型链污染。

## 2. PHP 反序列化 (POP Chain)

- **核心目标**: 寻找魔术方法 (Magic Methods)，如 `__wakeup()`, `__destruct()`, `__toString()`, `__call()`, `__invoke()`。
- **构造 POP 链 (Property Oriented Programming)**:
  - 仔细阅读提供的（或通过其他漏洞泄露的）源码。
  - 从入口点 (如 `__destruct`) 逆推，寻找可以触发危险函数（如 `eval()`, `system()`, `file_get_contents()`）的代码执行流。
- **绕过技巧**:
  - **CVE-2016-7124 (绕过 `__wakeup`)**: 改变序列化字符串中对象属性的个数，使其大于实际个数，即可跳过 `__wakeup()`。
    - 如：`O:4:"Test":2:{...}` 改为 `O:4:"Test":3:{...}`
  - **字符逃逸**: 若序列化数据在反序列化前经过了字符串替换（如 `str_replace` 导致长度变化），利用增长或缩短的差值，把后续恶意序列化字符串“顶”出来。
  - **Phar 反序列化**: 
    - 如果存在文件读取或操作函数（如 `file_exists()`, `file_get_contents()`），但参数可控，可以使用 `phar://` 伪协议触发反序列化，无需反序列化函数本身。

## 3. Java 反序列化

由于 CTF 中 Java 环境配置复杂，建议直接借助强大的生态。
- 不要尝试手写 Java 字节码。使用 Python 脚本调用 `ysoserial` (如果环境中安装了的话) 生成 Payload，或寻找现成的在线工具/脚本生成常见的利用链（如 `CommonsCollections`, `URLDNS`）。
- **Shiro 反序列化**: 寻找响应头中的 `rememberMe=deleteMe`，使用脚本枚举 Key，然后结合利用链构造 Cookie 发送。

## 4. Python 反序列化 (Pickle)

Python 反序列化最简单直接，通常通过定义 `__reduce__` 魔术方法实现 RCE。

```python
# 编写生成 Payload 的脚本示例：
import pickle
import base64
import os

class Exploit(object):
    def __reduce__(self):
        # 将这里的命令替换为你要执行的命令，如读取 flag 或反弹 shell
        return (os.system, ("cat /flag > /tmp/flag.txt",))

payload = base64.b64encode(pickle.dumps(Exploit())).decode()
print("Payload:", payload)
```

将生成的 `Payload` 提交到存在 `pickle.loads()` 的输入点。