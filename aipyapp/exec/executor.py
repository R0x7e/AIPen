#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback

from loguru import logger

from .python import PythonRuntime, PythonExecutor
from .html import HtmlExecutor
from .prun import BashExecutor, PowerShellExecutor, AppleScriptExecutor, NodeExecutor, MarkdownExecutor
from .types import ExecResult

EXECUTORS = {executor.name: executor for executor in [
    PythonExecutor,
    HtmlExecutor,
    BashExecutor,
    PowerShellExecutor,
    AppleScriptExecutor,
    NodeExecutor,
    MarkdownExecutor
]}

class BlockExecutor:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.executors = {}
        self.runtimes = {}
        self.log = logger.bind(src='block_executor', task_id=task_id)

    def _set_runtime(self, lang, runtime):
        if lang not in self.runtimes:
            if lang not in EXECUTORS:
                self.log.warning(f'No executor found for {lang}')
            self.runtimes[lang] = runtime
            self.log.info(f'Registered runtime for {lang}: {runtime}')               
        else:
            self.log.warning(f'Runtime for {lang} already registered: {self.runtimes[lang]}')

    def set_python_runtime(self, runtime):
        assert isinstance(runtime, PythonRuntime), "Expected a PythonRuntime instance"
        self._set_runtime('python', runtime)

    def get_executor(self, block):
        lang = block.get_lang()
        if lang in self.executors:
            return self.executors[lang]
        
        if lang not in EXECUTORS:
            self.log.warning(f'No executor found for {lang}')
            return None 
        
        runtime = self.runtimes.get(lang)
        executor = EXECUTORS[lang](runtime)
        self.executors[lang] = executor
        self.log.info(f'Registered executor for {lang}: {executor}')
        return executor

    def __call__(self, block) -> ExecResult:
        self.log.info(f'Exec: {block}')
        executor = self.get_executor(block)
        if executor:
            import threading
            import ctypes
            
            # 使用线程机制实现代码执行超时中断，防止恶意死循环或无限扫描
            timeout_sec = 600  # 默认 10 分钟超时
            
            class TimeoutException(Exception):
                pass
                
            def async_raise(thread_id, exctype):
                res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(exctype))
                if res == 0:
                    raise ValueError("Invalid thread id")
                elif res != 1:
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
                    raise SystemError("PyThreadState_SetAsyncExc failed")
                    
            def run_with_timeout():
                nonlocal result
                try:
                    result = executor(block)
                except Exception as e:
                    result = ExecResult(errstr=str(e), traceback=traceback.format_exc())
            
            result = None
            thread = threading.Thread(target=run_with_timeout)
            thread.start()
            thread.join(timeout_sec)
            
            if thread.is_alive():
                # 如果线程还在运行，抛出异常强制中断
                async_raise(thread.ident, TimeoutException)
                thread.join(5)
                self.log.error(f'Exec timeout after {timeout_sec}s for block: {block}')
                result = ExecResult(errstr=f'Execution timed out after {timeout_sec} seconds. Please optimize your code or avoid infinite loops.')
        else:
            result = ExecResult(errstr=f'Exec: Ignore unsupported block: {block}')

        return result