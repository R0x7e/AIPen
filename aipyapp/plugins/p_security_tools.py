#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import urllib.parse
import html
import binascii
import random
import time

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    requests = None

from aipyapp.plugin import TaskPlugin

class SecurityToolsPlugin(TaskPlugin):
    """
    CTF WEB 自动化渗透安全工具插件
    提供各种 Payload 编码解码、页面源码获取等底层能力。
    """
    
    name = "security_tools"
    version = "1.0.0"
    author = "AIPy Security Team"
    description = "提供底层安全探测和 Payload 处理工具"

    def init(self):
        pass

    def fn_encode_payload(self, payload: str, method: str) -> str:
        """
        将 Payload 按照指定方式进行编码，用于绕过 WAF。

        Args:
            payload: 需要编码的原始字符串
            method: 编码方式，支持 'base64', 'url', 'url_all', 'hex', 'html', 'unicode'

        Returns:
            编码后的字符串
        """
        method = method.lower()
        if method == 'base64':
            return base64.b64encode(payload.encode('utf-8')).decode('utf-8')
        elif method == 'url':
            return urllib.parse.quote(payload)
        elif method == 'url_all':
            # 对所有字符进行 URL 编码
            return ''.join(f'%{b:02x}' for b in payload.encode('utf-8'))
        elif method == 'hex':
            return binascii.hexlify(payload.encode('utf-8')).decode('utf-8')
        elif method == 'html':
            return html.escape(payload)
        elif method == 'unicode':
            return ''.join(f'\\u{ord(c):04x}' for c in payload)
        else:
            return f"Error: Unsupported encoding method '{method}'"

    def fn_decode_payload(self, payload: str, method: str) -> str:
        """
        将编码后的 Payload 还原，用于分析加密数据。

        Args:
            payload: 需要解码的字符串
            method: 解码方式，支持 'base64', 'url', 'hex', 'html', 'unicode'

        Returns:
            解码后的字符串
        """
        method = method.lower()
        try:
            if method == 'base64':
                return base64.b64decode(payload).decode('utf-8', errors='ignore')
            elif method == 'url':
                return urllib.parse.unquote(payload)
            elif method == 'hex':
                return binascii.unhexlify(payload).decode('utf-8', errors='ignore')
            elif method == 'html':
                return html.unescape(payload)
            elif method == 'unicode':
                return payload.encode().decode('unicode_escape', errors='ignore')
            else:
                return f"Error: Unsupported decoding method '{method}'"
        except Exception as e:
            return f"Error during decoding: {str(e)}"

    def fn_get_page_source(self, url: str, method: str = 'GET', data: str = None, headers: dict = None) -> str:
        """
        安全地获取网页源码，自动处理随机 UA 和禁用 SSL 告警。
        
        Args:
            url: 目标 URL
            method: 请求方法 'GET' 或 'POST'
            data: POST 请求数据
            headers: 附加的请求头字典

        Returns:
            返回响应状态码和页面前 2000 个字符的源码
        """
        if not requests:
            return "Error: 'requests' library is not installed."
            
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0"
        ]
        
        req_headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        if headers:
            req_headers.update(headers)
            
        try:
            kwargs = {
                'url': url,
                'headers': req_headers,
                'timeout': 15,
                'verify': False,
                'allow_redirects': False
            }
            if method.upper() == 'POST':
                kwargs['data'] = data
                response = requests.post(**kwargs)
            else:
                response = requests.get(**kwargs)
                
            result = f"Status Code: {response.status_code}\n"
            result += f"Response Headers: {dict(response.headers)}\n\n"
            
            body = response.text
            if len(body) > 2000:
                body = body[:2000] + "\n...[Content Truncated]..."
                
            result += body
            return result
            
        except Exception as e:
            return f"Request failed: {str(e)}"
