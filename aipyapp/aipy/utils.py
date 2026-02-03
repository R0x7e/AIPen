#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import re
import sys
import errno
import time
from pathlib import Path
from typing import Union, Tuple
from functools import wraps
from importlib.resources import read_text

from loguru import logger
from rich.panel import Panel

from .. import T, __respkg__

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

def confirm_disclaimer(console):
    DISCLAIMER_TEXT = read_text(__respkg__, "DISCLAIMER.md")
    console.print()
    panel = Panel.fit(DISCLAIMER_TEXT, title="[red]免责声明", border_style="red", padding=(1, 2))
    console.print(panel)

    while True:
        console.print("\n[red]是否确认已阅读并接受以上免责声明？[/red](yes/no):", end=" ")
        response = input().strip().lower()
        if response in ("yes", "y"):
            console.print("[green]感谢确认，程序继续运行。[/green]")
            return True
        elif response in ("no", "n"):
            console.print("[red]您未接受免责声明，程序将退出。[/red]")
            return False
        else:
            console.print("[yellow]请输入 yes 或 no。[/yellow]")

def safe_rename(path: Path, input_str: str, max_length=16, max_retries=3) -> Path:
    input_str = input_str.strip()
    safe_str = re.sub(r'[\\/:*?"<>|\s]', '', input_str).strip()
    if not safe_str:
        safe_str = "Task"

    name = safe_str[:max_length]
    # 对于目录，suffix 为空，所以直接使用名称
    new_path = path.parent / f"{name}{path.suffix}"
    counter = 1

    while True:
        if not new_path.exists():
            # 添加重试机制处理 PermissionError
            for attempt in range(max_retries):
                try:
                    path.rename(new_path)
                    return new_path  # 成功时返回新路径
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        # 指数退避重试：1秒、2秒、4秒
                        delay = 2 ** attempt
                        time.sleep(delay)
                        continue
                    else:
                        # 重试失败，返回原路径并记录警告
                        logger.warning(f"重命名失败（权限错误），使用原路径: {path} -> {new_path}")
                        return path
                except FileExistsError:
                    # 并发创建导致的文件已存在，跳出重试循环，继续尝试下一个名称
                    break
                except OSError as e:
                    if e.errno in (errno.EEXIST, errno.ENOTEMPTY):
                        # 文件或目录已存在，继续尝试下一个名称
                        break
                    else:
                        # 其他错误，重新抛出
                        raise

        # 如果新路径已存在或重试失败，尝试下一个名称
        new_path = path.parent / f"{name}_{counter}{path.suffix}"
        counter += 1

def validate_file(path: Union[str, Path]) -> None:
    """验证文件格式和存在性"""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Task file not found: {path}")

    if not path.name.endswith('.json'):
        raise ValueError("Task file must be a .json file")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")


def try_parse_json(json_str: str) -> bool:
    """Try to parse JSON, return True if successful."""
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False


def fix_json_trailing_content(json_str: str) -> str:
    """
    Remove trailing content after valid JSON by finding longest valid prefix.

    This handles cases like: {"key": "value"}extra_content
    by searching for the longest prefix that is valid JSON.

    Strategy: Try parse the whole string first. If invalid, try to find
    the longest prefix that parses successfully.
    """
    if not json_str:
        return json_str

    # First try: the whole string might be valid
    if try_parse_json(json_str):
        return json_str

    # Second try: find the longest valid prefix
    # We use a smart approach: try parsing and progressively shorten
    # But we need to be careful not to cut in the middle of valid JSON
    # that just happens to have extra content at the end

    # Start from near the end (keep most of the content) and work backwards
    # We skip the last few characters first as they're most likely to be noise
    for end_pos in range(len(json_str) - 1, max(0, len(json_str) - 100), -1):
        prefix = json_str[:end_pos]
        if try_parse_json(prefix):
            return prefix

    # Fallback: try from the end but only at boundaries that look like JSON end
    # A JSON document typically ends with } or ]
    for i in range(len(json_str) - 1, 0, -1):
        char = json_str[i]
        if char in '}]':  # Possible JSON ending
            prefix = json_str[:i+1]
            if try_parse_json(prefix):
                return prefix

    return json_str


def fix_json_missing_braces(json_str: str) -> str:
    """
    Add missing closing braces by iterative trial.

    This handles cases like: {"key": "value"
    by incrementally adding '}' until JSON becomes valid.
    """
    if not json_str:
        return json_str

    current = json_str
    # Safety limit: don't add more than 10 braces
    for _ in range(10):
        if try_parse_json(current):
            return current
        current += '}'

    return json_str  # Return original if limit reached


def repair_json_string(json_str: str) -> Tuple[str, bool, str]:
    """
    Repair common JSON string issues in tool call arguments.

    Args:
        json_str: The JSON string to repair

    Returns:
        (repaired_json_str, was_repaired, repair_message)
        - repaired_json_str: The repaired JSON string (or original if failed)
        - was_repaired: True if any repair was applied
        - repair_message: Description of what was repaired
    """
    # Handle empty/None cases
    if json_str is None:
        return "{}", True, "Replaced None with '{}'"
    if isinstance(json_str, str) and not json_str.strip():
        return "{}", True, "Replaced empty string with '{}'"

    original = json_str

    # Attempt 1: Try parsing as-is
    if try_parse_json(json_str):
        return json_str, False, ""

    # Attempt 2: Fix trailing content first
    repaired = fix_json_trailing_content(json_str)
    if repaired != json_str:
        extra = json_str[len(repaired):]
        msg = f"Truncating trailing content: {extra!r}"
        if try_parse_json(repaired):
            return repaired, True, msg
        json_str = repaired

    # Attempt 3: Fix missing closing braces
    repaired = fix_json_missing_braces(json_str)
    if repaired != json_str:
        added = repaired[len(json_str):]
        msg = f"Added missing braces: {added!r}"
        if try_parse_json(repaired):
            return repaired, True, msg
        json_str = repaired

    # Attempt 4: Try adding braces first, then remove trailing content
    # This handles cases like {"a": {"b": 2}extra where we need to complete
    # the JSON before the trailing content becomes apparent
    with_braces = fix_json_missing_braces(original)
    if with_braces != original:
        # Now try to remove trailing content
        repaired = fix_json_trailing_content(with_braces)
        if repaired != with_braces and try_parse_json(repaired):
            added = with_braces[len(original):]
            extra = with_braces[len(repaired):]
            msg = f"Added braces: {added!r}, truncated {extra!r}"
            return repaired, True, msg

    # Attempt 5: Both fixes combined - trailing content first, then braces
    repaired = fix_json_missing_braces(fix_json_trailing_content(original))
    if repaired != original and try_parse_json(repaired):
        changes = []
        # Determine what changed
        trailing_fixed = fix_json_trailing_content(original)
        if trailing_fixed != original:
            extra = original[len(trailing_fixed):]
            changes.append(f"truncated {extra!r}")

        if repaired != trailing_fixed:
            added = repaired[len(trailing_fixed):]
            changes.append(f"added {added!r}")

        msg = ", ".join(changes) if changes else "Applied repairs"
        return repaired, True, msg

    # Attempt 6: Try a hybrid approach - iterate through possible split points
    # and try adding braces to each prefix
    for i in range(len(original), 0, -1):
        prefix = original[:i]
        with_braces = fix_json_missing_braces(prefix)
        if try_parse_json(with_braces):
            extra = original[len(prefix):]
            if with_braces != prefix:
                added = with_braces[len(prefix):]
                if extra:
                    msg = f"Added braces: {added!r}, truncated {extra!r}"
                else:
                    msg = f"Added braces: {added!r}"
                return with_braces, True, msg
            elif not extra:
                # No repair needed, but this shouldn't happen since we tried as-is first
                return with_braces, False, ""

    # All attempts failed - return original
    return original, False, ""
