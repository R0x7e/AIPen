#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from functools import wraps
from typing import Any, Dict, List
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown

from aipyapp.display import RichDisplayPlugin
from live_display import LiveDisplay
from aipyapp import T

def restore_output(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

        try:
            return func(self, *args, **kwargs)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
    return wrapper

class DisplayModern(RichDisplayPlugin):
    """Modern display style"""
    name = "modern"
    version = "1.0.0"
    description = "Modern display style"
    author = "AiPy Team"

    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.current_block = None
        self.execution_status = {}
        self.live_display = None
        
    def on_task_started(self, event):
        """任务开始事件处理"""
        instruction = event.typed_event.instruction
        title = event.typed_event.title or instruction
        
        # 显示任务开始信息
        title_text = Text("🚀 任务开始", style="bold blue")
        content = Text(title, style="white")
        panel = Panel(content, title=title_text, border_style="blue")
        self.console.print(panel)
        self.console.print()

    def on_step_started(self, event):
        """步骤开始事件处理"""
        instruction = event.typed_event.instruction
        title = event.typed_event.title or instruction
        
        # 显示回合开始信息
        title_text = Text("🔄 回合开始", style="bold yellow")
        content = Text(title, style="white")
        panel = Panel(content, title=title_text, border_style="yellow")
        self.console.print(panel)
        self.console.print()
        
    def on_request_started(self, event):
        """查询开始事件处理"""
        llm = event.typed_event.llm
        self.console.print(f"📤 {T('Sending message to {}')}...".format(llm), style="dim cyan")
        
    def on_stream_started(self, event):
        """流式开始事件处理"""
        if not self.quiet:
            self.live_display = LiveDisplay()
            self.live_display.__enter__()
            self.console.print(f"📥 {T('Streaming started')}...", style="dim cyan")
    
    def on_stream_completed(self, event):
        """流式结束事件处理"""
        if self.live_display:
            self.live_display.__exit__(None, None, None)
            self.live_display = None
        self.console.print()
        
    def on_stream(self, event):
        """LLM 流式响应事件处理"""
        lines = event.typed_event.lines
        reason = event.typed_event.reason
        
        if self.live_display:
            self.live_display.update_display(lines, reason=reason)
        
    def on_response_completed(self, event):
        """LLM 响应完成事件处理"""
        llm = event.typed_event.llm
        msg = event.typed_event.msg

        if not msg:
            self.console.print(f"❌ {T('LLM response is empty')}", style="red")
            return

        if msg.role == 'error':
            self.console.print(f"❌ {msg.content}", style="red")
            return

        # 处理响应内容
        if msg.reason:
            content = f"{msg.reason}\n\n-----\n\n{msg.content}"
        else:
            content = msg.content

        # 智能解析和显示内容
        self._parse_and_display_content(content, llm, msg)
        
    def on_task_status(self, event):
        """任务状态事件处理"""
        status = event.typed_event.status
        completed = status.completed
        style = "success" if completed else "error"
        
        if completed:
            title = Text("✅ 任务状态", style="bold green")
            content_lines = [
                Text("已完成", style="green"),
                Text(f"置信度: {status.confidence}", style="cyan")
            ]
        else:
            title = Text("❌ 任务状态", style="bold red")
            content_lines = [
                Text(status.status, style="red"),
                Text(f"原因: {status.reason}", style="yellow"),
                Text(f"建议: {status.suggestion}", style="cyan")
            ]
        
        from rich.console import Group
        content = Group(*content_lines)
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)
        
    def on_parse_reply_completed(self, event):
        """消息解析结果事件处理"""
        response = event.typed_event.response
        if response is None:
            return
        if not (response.code_blocks or response.tool_calls or response.errors):
            return
            
        # 显示解析结果摘要
        if response.code_blocks:
            block_count = len(response.code_blocks)
            self.console.print(f"📝 {T('Found {} code blocks').format(block_count)}", style="dim green")
        
        if response.tool_calls:
            tool_count = len(response.tool_calls)
            subtask_count = sum(1 for tool_call in response.tool_calls if tool_call.name == tool_call.name.SUBTASK)
            if subtask_count > 0:
                self.console.print(f"🔧 {T('Found {} tool calls ({} SubTasks)').format(tool_count, subtask_count)}", style="dim blue")
            else:
                self.console.print(f"🔧 {T('Found {} tool calls').format(tool_count)}", style="dim blue")

        if response.errors:
            error_count = len(response.errors)
            first_error = response.errors.errors[0].message if response.errors.errors else ""
            suffix = f": {first_error}" if first_error else ""
            self.console.print(
                f"❌ {T('Found {} errors').format(error_count)}{suffix}",
                style="dim red",
            )
                
    def on_exec_started(self, event):
        """代码执行开始事件处理"""
        block = event.typed_event.block
        if not block:
            return
            
        block_name = getattr(block, 'name', 'Unknown')
        self.current_block = block_name
        self.execution_status[block_name] = 'running'
        
        # 显示代码块
        self._show_code_block(block)
        
        # 显示执行状态
        self.console.print(f"⏳ {T('Executing')}...", style="yellow")
        
    def on_exec_completed(self, event):
        """代码执行结果事件处理"""
        result = event.typed_event.result
        block = event.typed_event.block
        
        if block and hasattr(block, 'name'):
            self.current_block = block.name
            self.execution_status[block.name] = 'success'
            
        # 显示执行结果
        self._show_execution_result(result)
        
    def on_edit_started(self, event):
        """代码编辑开始事件处理"""
        block_name = event.typed_event.block_name
        old_str = event.typed_event.old
        new_str = event.typed_event.new
        
        # 显示编辑操作信息
        title = Text(f"✏️ 编辑代码块: {block_name}", style="bold yellow")
        
        # 创建编辑预览内容
        content_lines = []
        if old_str:
            old_preview = old_str[:50] + '...' if len(old_str) > 50 else old_str
            content_lines.append(Text(f"替换: {repr(old_preview)}", style="red"))
        if new_str:
            new_preview = new_str[:50] + '...' if len(new_str) > 50 else new_str
            content_lines.append(Text(f"为: {repr(new_preview)}", style="green"))
        
        from rich.console import Group
        content = Group(*content_lines) if content_lines else Text("编辑操作", style="white")
        panel = Panel(content, title=title, border_style="yellow")
        self.console.print(panel)
        
    def on_edit_completed(self, event):
        """代码编辑结果事件处理"""
        success = event.typed_event.success
        block_name = event.typed_event.block_name
        new_version = event.typed_event.new_version
        
        if success:
            title = Text(f"✅ 编辑成功: {block_name}", style="bold green")
            content_lines = []
            
            if new_version:
                content_lines.append(Text(f"新版本: v{new_version}", style="cyan"))
                
            from rich.console import Group
            content = Group(*content_lines) if content_lines else Text("编辑完成", style="white")
            panel = Panel(content, title=title, border_style="green")
        else:
            title = Text(f"❌ 编辑失败: {block_name}", style="bold red")
            content = Text("编辑操作失败", style="red")
            panel = Panel(content, title=title, border_style="red")
            
        self.console.print(panel)
        
    def on_tool_call_started(self, event):
        """工具调用开始事件处理"""
        tool_call = event.typed_event.tool_call
        title = Text(f"🔧 工具调用: {tool_call.tool_name}", style="bold blue")
        args = tool_call.arguments.model_dump_json()
        content = Syntax(args, 'json', line_numbers=False, word_wrap=True)
        panel = Panel(content, title=title, border_style="blue")
        self.console.print(panel)

    def on_tool_call_completed(self, event):
        """工具调用结果事件处理"""
        result = event.typed_event.result

        # 显示工具调用结果
        title = Text(f"🔧 工具结果: {result.tool_name}", style="bold green")
        content = Syntax(result.result.model_dump_json(indent=2, exclude_none=True), 'json', line_numbers=False, word_wrap=True)
        panel = Panel(content, title=title, border_style="green")
        self.console.print(panel)
        
    def on_step_completed(self, event):
        """步骤结束事件处理"""
        summary = event.typed_event.summary
        response = event.typed_event.response
        
        # 显示统计信息
        if 'usages' in summary and summary['usages']:
            self._show_usage_table(summary['usages'])
            
        # 显示总结信息
        summary_text = summary.get('summary', '')
        if summary_text:
            title = Text("📊 执行统计", style="bold cyan")
            content = Text(summary_text, style="white")
            panel = Panel(content, title=title, border_style="cyan")
            self.console.print(panel)
            
        # 显示最终响应
        if response:
            self.console.print()
            self._parse_and_display_content(response, "Final Response")
            
    def on_step_cleanup_completed(self, event):
        """Step清理完成事件处理"""
        cleaned_messages = event.typed_event.cleaned_messages
        title = Text("🧹 上下文清理完成", style="bold cyan")
        content = Text(f"已清理 {cleaned_messages} 条错误消息，上下文已优化", style="cyan")
        panel = Panel(content, title=title, border_style="cyan", padding=(0, 1))
        self.console.print(panel)

    def on_task_completed(self, event):
        """任务结束事件处理"""
        path = event.typed_event.path or ''
        title = Text("✅ 任务完成", style="bold green")
        content = Text(f"结果已保存到: {path}", style="white") if path else Text("任务完成", style="white")
        panel = Panel(content, title=title, border_style="green")
        self.console.print(panel)
        
    def on_upload_result(self, event):
        """云端上传结果事件处理"""
        status_code = event.typed_event.status_code
        url = event.typed_event.url
        
        if url:
            title = Text("☁️ 上传成功", style="bold green")
            content = Text(f"链接: {url}", style="white")
            panel = Panel(content, title=title, border_style="green")
            self.console.print(panel)
        else:
            title = Text("❌ 上传失败", style="bold red")
            content = Text(f"状态码: {status_code}", style="white")
            panel = Panel(content, title=title, border_style="red")
            self.console.print(panel)
            
    def on_exception(self, event):
        """异常事件处理"""
        import traceback
        msg = event.typed_event.msg
        exception = event.typed_event.exception
        
        title = Text("💥 异常", style="bold red")
        if exception:
            try:
                tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
                tb_str = ''.join(tb_lines)
                content = Syntax(tb_str, 'python', line_numbers=True, word_wrap=True)
            except:
                content = Text(f"{msg}: {exception}", style="red")
        else:
            content = Text(msg, style="red")
            
        panel = Panel(content, title=title, border_style="red")
        self.console.print(panel)
        
    def on_runtime_message(self, event):
        """Runtime消息事件处理"""
        message = event.typed_event.message
        status = event.typed_event.status or 'info'
        if message:
            if status == 'error':
                self.console.print(message, style="red")
            elif status == 'warning':
                self.console.print(message, style="yellow")
            else:
                self.console.print(message, style="dim white")
            
    def on_runtime_input(self, event):
        """Runtime输入事件处理"""
        # 输入事件通常不需要特殊处理，因为input_prompt已经处理了
        pass
    
    @restore_output
    def on_function_call_started(self, event):
        """函数调用开始事件处理"""
        funcname = event.typed_event.funcname
        kwargs = event.typed_event.kwargs
        title = Text(f"🔧 {T('Start calling function {}').format(funcname)}", style="bold blue")
        args_text = json.dumps(kwargs, ensure_ascii=False, default=str) if kwargs else ""
        content = Text(args_text, style="white")
        panel = Panel(content, title=title, border_style="blue")
        self.console.print(panel)
    
    @restore_output
    def on_function_call_completed(self, event):
        """函数调用结果事件处理"""
        funcname = event.typed_event.funcname
        success = event.typed_event.success
        result = event.typed_event.result
        error = event.typed_event.error
        
        if success:
            title = Text(f"✅ {T('Function call result {}')}".format(funcname), style="bold green")
            
            if result is not None:
                # 格式化并显示结果
                if isinstance(result, (dict, list)):
                    content = Syntax(json.dumps(result, ensure_ascii=False, indent=2, default=str), 'json', line_numbers=False, word_wrap=True)
                else:
                    content = Text(str(result), style="white")
            else:
                content = Text(T("No return value"), style="dim white")
            
            panel = Panel(content, title=title, border_style="green")
            self.console.print(panel)
        else:
            title = Text(f"❌ {T('Function call failed {}')}".format(funcname), style="bold red")
            content = Text(error if error else T("Unknown error"), style="red")
            panel = Panel(content, title=title, border_style="red")
            self.console.print(panel)
        
    def _parse_and_display_content(self, content: str, llm: str = "", msg=None):
        """智能解析并显示内容"""
        if not content:
            return

        # 检测是否包含代码块
        if '```' in content:
            self._show_content_with_code_blocks(content, llm, msg)
        else:
            self._show_text_content(content, llm, msg)
            
    def _show_content_with_code_blocks(self, content: str, llm: str = "", msg=None):
        """显示包含代码块的内容"""
        lines = content.split('\n')
        in_code_block = False
        code_lang = ""
        code_content = []
        text_content = []
        first_block = True  # Track first block for title display

        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # 结束代码块
                    if code_content:
                        self._show_code_block_content(code_lang, '\n'.join(code_content), llm, msg if first_block else None)
                        first_block = False
                    in_code_block = False
                    code_content = []
                else:
                    # 开始代码块
                    in_code_block = True
                    code_lang = line[3:].strip()
            elif in_code_block:
                code_content.append(line)
            else:
                # 普通文本行
                text_content.append(line)

        # 显示文本内容
        if text_content:
            text = '\n'.join(text_content).strip()
            if text:
                self._show_text_content(text, llm, msg)
                    
    def _show_text_content(self, content: str, llm: str = "", msg=None):
        """显示纯文本内容"""
        if not content.strip():
            return

        # 使用 Markdown 渲染文本内容
        try:
            markdown = Markdown(content)
            if llm:
                # Build title with token statistics if available
                base_title = Text(f"🤖 {llm}", style="bold cyan")

                if msg and hasattr(msg, 'usage') and msg.usage:
                    input_tokens = msg.usage.get('input_tokens', 0)
                    output_tokens = msg.usage.get('output_tokens', 0)
                    total_tokens = msg.usage.get('total_tokens', 0)

                    # Add token stats in Modern style: [gpt-4: ↑123 ↓45 Σ789]
                    stats_text = Text()
                    stats_text.append(" [", style="dim white")
                    stats_text.append(f"{llm}:", style="cyan")
                    stats_text.append(f" ↑{input_tokens}", style="green")
                    stats_text.append(f" ↓{output_tokens}", style="yellow")
                    stats_text.append(f" Σ{total_tokens}", style="magenta")
                    stats_text.append("]", style="dim white")

                    title = base_title
                    title.append(stats_text)
                else:
                    title = base_title

                panel = Panel(markdown, title=title, border_style="cyan")
            else:
                panel = Panel(markdown, border_style="white")
            self.console.print(panel)
        except:
            # 如果 Markdown 渲染失败，直接显示文本
            if llm:
                self.console.print(f"🤖 {llm}:", style="bold cyan")
            self.console.print(content)
            
    def _show_code_block(self, block: Any):
        """显示代码块"""
        if hasattr(block, 'code') and hasattr(block, 'lang'):
            self._show_code_block_content(block.lang, block.code, block.name)
        else:
            # 兼容其他格式
            self.console.print(f"📝 {T('Code block')}", style="dim white")
            
    def _show_code_block_content(self, lang: str, code: str, name: str = None, llm: str = None, msg=None):
        """显示代码块内容"""
        if not code.strip():
            return

        # Build title with LLM name and token stats if available
        if llm and msg and hasattr(msg, 'usage') and msg.usage:
            input_tokens = msg.usage.get('input_tokens', 0)
            output_tokens = msg.usage.get('output_tokens', 0)
            total_tokens = msg.usage.get('total_tokens', 0)

            # Create title with token stats: 📝 Code (python) [gpt-4: ↑123 ↓45 Σ789]
            title_parts = []
            title_parts.append(f"📝 {name or T('Code')} ({lang})")

            stats_text = Text()
            stats_text.append(" [", style="dim white")
            stats_text.append(f"{llm}:", style="cyan")
            stats_text.append(f" ↑{input_tokens}", style="green")
            stats_text.append(f" ↓{output_tokens}", style="yellow")
            stats_text.append(f" Σ{total_tokens}", style="magenta")
            stats_text.append("]", style="dim white")

            title = Text()
            title.append(" ".join(title_parts), style="bold blue")
            title.append(stats_text)
        elif llm:
            title = f"📝 {name or T('Code')} ({lang}) - {llm}"
        else:
            title = f"📝 {name or T('Code')} ({lang})"

        # 使用语法高亮显示代码
        syntax = Syntax(code, lang, line_numbers=True, word_wrap=True)
        panel = Panel(syntax, title=title, border_style="blue")
        self.console.print(panel)
        
    def _show_execution_result(self, result: Any):
        """显示执行结果"""
        if isinstance(result, dict):
            self._show_structured_result(result)
        else:
            self._show_simple_result(result)
            
    def _show_structured_result(self, result: Dict[str, Any]):
        """显示结构化结果"""
        # 检查是否有错误
        if 'traceback' in result or 'error' in result:
            title = Text("❌ 执行失败", style="bold red")
            if 'traceback' in result:
                content = Syntax(result['traceback'], 'python', line_numbers=True, word_wrap=True)
            else:
                content = Text(str(result.get('error', 'Unknown error')), style="red")
            panel = Panel(content, title=title, border_style="red")
            self.console.print(panel)
        else:
            # 显示成功结果
            title = Text("✅ 执行成功", style="bold green")
            output_parts = []
            
            # 收集输出信息
            if 'output' in result and result['output']:
                output_parts.append(f"📤 {T('Output')}: {result['output']}")
            if 'stdout' in result and result['stdout']:
                output_parts.append(f"📤 {T('Stdout')}: {result['stdout']}")
            if 'stderr' in result and result['stderr']:
                output_parts.append(f"⚠️ {T('Stderr')}: {result['stderr']}")
                
            if output_parts:
                content = Text('\n'.join(output_parts), style="white")
                panel = Panel(content, title=title, border_style="green")
                self.console.print(panel)
            else:
                self.console.print("✅ 执行成功", style="green")
                
    def _show_simple_result(self, result: Any):
        """显示简单结果"""
        if result is None:
            self.console.print("✅ 执行完成", style="green")
        else:
            title = Text("✅ 执行结果", style="bold green")
            content = Text(str(result), style="white")
            panel = Panel(content, title=title, border_style="green")
            self.console.print(panel)
            
    def _show_usage_table(self, usages: List[Dict[str, Any]]):
        """显示使用统计表格"""
        if not usages:
            return

        table = Table(title=T("执行统计"), show_lines=True)

        table.add_column(T("回合"), justify="center", style="bold cyan", no_wrap=True)
        table.add_column(T("时间(s)"), justify="right")
        table.add_column(T("输入Token"), justify="right")
        table.add_column(T("输出Token"), justify="right")
        table.add_column(T("总计Token"), justify="right", style="bold magenta")

        for i, usage in enumerate(usages, 1):
            table.add_row(
                str(i),
                str(usage.get("time", 0)),
                str(usage.get("input_tokens", 0)),
                str(usage.get("output_tokens", 0)),
                str(usage.get("total_tokens", 0)),
            )

        self.console.print(table)
        self.console.print()

    @restore_output
    def on_operation_started(self, event):
        """长时间操作开始事件处理"""
        operation_name = event.typed_event.operation_name
        total = event.typed_event.total

        title = Text(f"⚙️ {T('Operation started')}: {operation_name}", style="bold cyan")
        content_lines = []
        if total:
            content_lines.append(Text(f"{T('Total items')}: {total}", style="white"))

        from rich.console import Group
        content = Group(*content_lines) if content_lines else Text(operation_name, style="white")
        panel = Panel(content, title=title, border_style="cyan")
        self.console.print(panel)

    @restore_output
    def on_operation_progress(self, event):
        """操作进度更新事件处理"""
        message = event.typed_event.message
        self.console.print(f"  ℹ️  {message}", style="dim cyan")

    @restore_output
    def on_operation_finished(self, event):
        """操作完成事件处理"""
        success = event.typed_event.success
        message = event.typed_event.message

        style = "success" if success else "error"
        title = Text(f"{'✅' if success else '❌'} {T('Operation completed')}", style=f"bold {style}")
        content = Text(message if message else T("Operation completed"), style="white")
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)

    @restore_output
    def on_progress_report(self, event):
        """简单进度报告事件处理"""
        progress = event.typed_event.progress
        message = event.typed_event.message

        # 现代风格的进度报告
        text = f"📊 {T('Progress')}: {progress}"
        if message:
            text += f" - {message}"
        self.console.print(text, style="cyan") 