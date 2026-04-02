![logo](https://github.com/user-attachments/assets/3af4e228-79b2-4fa0-a45c-c38276c6db91)

# AIPen (CTF Web Pentest AI) - Agent 2.0

**AI-Powered Python & Python-Powered AI**

AIPen 是基于 `aipyapp` 框架二次开发的 **CTF Web 自动化渗透测试系统**。它继承了 **Agent 2.0 (Code is Agent)** 的理念。

与依赖于死板的 Workflow 节点或受限工具的传统 Agent 不同，AIPen 为大语言模型 (LLM) 提供了一个完整的 Python 执行沙箱。在这里，AI 扮演着 **安全指挥官 (Security Commander)** 的角色，通过动态编写、执行和修正 Python/Shell Payload 来挖掘漏洞并获取 Flag。

> **任务 (Task) → 规划 (Plan) → 编码 (Code) → 执行 (Execute) → 反馈 (Feedback)**

## 二开核心特性 (CTF 定制版)

我们将原本通用的 AI Python 解释器，深度改造为了一个支持高并发、专注于渗透测试的专业安全 Agent：

1. **“指挥官”架构 (主从并发机制)**
   - 告别单线阻塞：AI 不再是因为网络 IO 或字典爆破而挂起的单线程机器人。
   - 扮演 **指挥官**：主 Agent 负责统筹规划，使用 `SubTask` 并发派发多个子任务进行侦察（例如：同时让子任务 1 扫描目录，让子任务 2 测试 SQL 盲注）。
   - **异构模型调度**: 允许主 Agent 使用推理能力强但昂贵的模型（如 GPT-4o），同时指定子任务使用速度快、成本低的模型（如 `gpt-4o-mini` 或 `ollama`）。

2. **专属 CTF Hacker 角色与上下文隔离**
   - 内置了经过专业渗透方法论训练的 `CTF_Hacker` 提示词。
   - 子任务独立执行，避免了长篇的报错日志或 HTML 源码污染主 Agent 的推理上下文。

3. **高级安全工具插件 (`p_security_tools`)**
   - 提供了基于异步 `aiohttp` 的高性能 Fuzzing 函数 (`concurrent_fuzz`)，专供 AI 进行大批量的 WAF 绕过和盲注测试。
   - 内置了各种 Payload 的编码、解码与加解密函数。

4. **无缝对接 MCP (Model Context Protocol)**
   - 能够通过 MCP 协议与专业的安全扫描器 (如 Nmap, Sqlmap, Xray) 通信。AI 可以直接获取结构化的漏洞 JSON 报告，而无需去艰难解析终端里的纯文本。

---

## 背景理念: Code is Agent

传统 AI（Agent 1.0）严重依赖 Function Calling、Workflow 和各种插件客户端，门槛高且工具间协同极差。

**Python-Use** 提出了一种极简的执行架构：**无需 Agent，无需 Workflow，无需定制客户端… Code is Agent**。

在这里，AI 拥有两大核心能力：
- **调用 API**: 自动编写和执行代码来调用任何第三方接口。
- **调用生态**: 灵活使用 Python 庞大的生态包（如 `requests`, `pwntools`, `bs4`）来编排自己的工作流。

## 部署与启动指南

由于 AI 生成并执行的漏洞利用脚本具有不可预测性，我们 **强烈建议** 将 AIPen 运行在隔离的 Docker 环境中。

### 方式一：Docker 隔离运行 (强烈推荐)

1. **构建镜像**:
   ```bash
   docker build -t aipyapp/aipy:latest -f docker/Dockerfile .
   ```
2. **运行 Agent**:
   ```bash
   # 标准交互模式
   ./docker/run.sh
   ```
3. **切换到 CTF 模式**:
   进入容器终端后，激活 Hacker 角色：
   ```bash
   /role ctf_hacker
   ```

### 方式二：本地直接运行 (仅供开发调试)

1. **使用 `uv` 安装依赖**:
   ```bash
   pip install uv
   uv sync
   ```
2. **带 CTF 角色启动**:
   ```bash
   uv run aipy --role ctf_hacker
   ```

## 渗透流程示例

**You:**
> "目标网址是 `http://192.168.1.100/login.php`，请帮我分析该页面的漏洞并获取 `/flag` 的内容。"

**AIPen 指挥官:**
1. **Plan**: 派发 SubTask 1 去后台扫描目录，派发 SubTask 2 针对登录框测试 SQL 注入。
2. **Execute**: 子任务在后台调用 `concurrent_fuzz` 异步爆破。
3. **Feedback**: SubTask 2 汇报发现存在报错型 SQL 注入。
4. **Code**: 主 Agent 亲自编写定制化的 Python 脚本，提取数据库名和最终的 Flag。
5. **Result**: 成功获取 `flag{ai_is_the_new_hacker}`。

## ⚠️ 安全警告与免责声明

- **必须运行在沙箱中**: AI 生成的代码可能具有破坏性。严禁在带有宿主机核心权限的环境下运行本系统。
- **网络隔离**: 请通过 Docker 网络配置，限制本 Agent 仅能访问目标靶机网段，防止 AI 对内网或外网发起非授权攻击。
- **仅限授权使用**: 本项目仅供网络安全教学、CTF 竞赛和取得合法授权的渗透测试使用。一切由于非法使用造成的后果由使用者自行承担。

## 鸣谢
- 感谢 Python-use 社区开源的原始 `aipyapp` 框架。
- AIPy 官网: https://www.aipy.app/