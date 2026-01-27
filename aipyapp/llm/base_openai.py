#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from typing import Any, Dict
from collections import Counter

import httpx
import openai

from .base import BaseClient, MessageRole, AIMessage, ToolCall, ToolFunction


# https://platform.openai.com/docs/api-reference/chat/create
# https://api-docs.deepseek.com/api/create-chat-completion
class OpenAIBaseClient(BaseClient):
    """OpenAI compatible client"""

    def get_api_params(self, **kwargs):
        params = super().get_api_params(**kwargs)

        # OpenAI 特定的流式选项
        if self.config.stream:
            params['stream_options'] = {'include_usage': True}

        params.update(self.config.extra_fields)
        params.update(kwargs)

        return params

    def usable(self):
        return super().usable() and self.config.api_key

    def _get_client(self):
        return openai.Client(api_key=self.config.api_key, base_url=self.base_url, timeout=self.config.timeout, http_client=httpx.Client(verify=self.config.tls_verify))

    def _parse_usage(self, usage) -> Counter:
        try:
            reasoning_tokens = int(usage.completion_tokens_details.reasoning_tokens)
        except Exception:
            reasoning_tokens = 0

        usage = Counter({'total_tokens': usage.prompt_tokens + usage.completion_tokens, 'input_tokens': usage.prompt_tokens, 'output_tokens': usage.completion_tokens, 'reasoning_tokens': reasoning_tokens, 'missing_tokens': usage.total_tokens - usage.prompt_tokens - usage.completion_tokens})
        return usage

    def _parse_stream_response(self, response, stream_processor) -> AIMessage:
        usage = Counter()
        tool_calls_chunks = []
        finish_reason = None
        with stream_processor as lm:
            for chunk in response:
                # print(chunk)
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    usage = self._parse_usage(chunk.usage)

                if chunk.choices:
                    content = None
                    delta = chunk.choices[0].delta
                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason

                    if delta.content:
                        reason = False
                        content = delta.content
                    elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reason = True
                        content = delta.reasoning_content

                    if delta.tool_calls:
                        tool_calls_chunks.append(delta.tool_calls)

                    if content:
                        lm.process_chunk(content, reason=reason)

        tool_calls = self._reconstruct_tool_calls(tool_calls_chunks)
        return AIMessage(role=MessageRole.ASSISTANT, content=lm.content, reason=lm.reason, finish_reason=finish_reason, usage=usage, tool_calls=tool_calls)

    def _reconstruct_tool_calls(self, tool_calls_chunks):
        if not tool_calls_chunks:
            return None

        tool_calls = {}
        for chunk in tool_calls_chunks:
            for tool_call in chunk:
                index = tool_call.index
                function = tool_call.function
                if index not in tool_calls:
                    tool_calls[index] = {'id': tool_call.id, 'type': tool_call.type or 'function', 'function': {'name': function.name, 'arguments': function.arguments}}
                    continue

                fn = tool_calls[index]['function']
                if function.name:
                    fn['name'] += function.name
                if function.arguments:
                    fn['arguments'] += function.arguments

        result = []
        for index in sorted(tool_calls.keys()):
            tc = tool_calls[index]
            function = tc['function']
            tool_function = ToolFunction(name=function['name'])
            tool_function._arguments_text = function['arguments']
            tool_call = ToolCall(id=tc['id'], type=tc['type'], function=tool_function)
            result.append(tool_call)
        return result

    def _parse_response(self, response) -> AIMessage:
        message = response.choices[0].message
        reason = getattr(message, "reasoning_content", None)
        finish_reason = response.choices[0].finish_reason
        return AIMessage(role=message.role, content=message.content, reason=reason, finish_reason=finish_reason, usage=self._parse_usage(response.usage), tool_calls=message.tool_calls)

    def get_completion(self, messages: list[Dict[str, Any]], **kwargs) -> AIMessage:
        if not self._client:
            self._client = self._get_client()

        # 获取 API 参数
        api_params = self.get_api_params(**kwargs)

        response = self._client.chat.completions.create(messages=messages, **api_params)
        return response
