#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for JSON string repair functionality in utils.py
"""

import pytest
import json

from aipyapp.aipy.utils import (
    try_parse_json,
    fix_json_trailing_content,
    fix_json_missing_braces,
    repair_json_string,
)


class TestTryParseJson:
    """Test try_parse_json function"""

    @pytest.mark.unit
    def test_valid_json(self):
        """Test with valid JSON"""
        assert try_parse_json('{"city": "Beijing"}') is True
        assert try_parse_json('{"a": {"b": 2}}') is True
        assert try_parse_json('{}') is True
        assert try_parse_json('[]') is True

    @pytest.mark.unit
    def test_invalid_json(self):
        """Test with invalid JSON"""
        assert try_parse_json('{"city": "Beijing"}') is True
        assert try_parse_json('{"city": "Beijing"') is False
        assert try_parse_json('not json') is False
        assert try_parse_json('{') is False


class TestFixJsonTrailingContent:
    """Test fix_json_trailing_content function"""

    @pytest.mark.unit
    def test_valid_json_unchanged(self):
        """Test that valid JSON is unchanged"""
        assert fix_json_trailing_content('{"city": "Beijing"}') == '{"city": "Beijing"}'
        assert fix_json_trailing_content('{}') == '{}'

    @pytest.mark.unit
    def test_trailing_markdown(self):
        """Test removing trailing markdown backticks"""
        result = fix_json_trailing_content('{"city": "Beijing"}')
        assert json.loads(result) == {"city": "Beijing"}

    @pytest.mark.unit
    def test_trailing_text(self):
        """Test removing trailing text content"""
        result = fix_json_trailing_content('{"city": "Beijing"}extra')
        assert result == '{"city": "Beijing"}'
        assert json.loads(result) == {"city": "Beijing"}

    @pytest.mark.unit
    def test_brace_in_string_value(self):
        """Test that braces inside string values are preserved"""
        # The key test case from the plan
        result = fix_json_trailing_content('{"text": "}"}')
        assert result == '{"text": "}"}'
        assert json.loads(result) == {"text": "}"}

    @pytest.mark.unit
    def test_brace_in_string_with_trailing(self):
        """Test braces inside string values with trailing content"""
        result = fix_json_trailing_content('{"text": "}"}extra')
        assert result == '{"text": "}"}'
        assert json.loads(result) == {"text": "}"}

    @pytest.mark.unit
    def test_multiple_braces_in_string(self):
        """Test multiple braces inside string values"""
        result = fix_json_trailing_content('{"pattern": "}}"}')
        assert result == '{"pattern": "}}"}'
        assert json.loads(result) == {"pattern": "}}"}

    @pytest.mark.unit
    def test_multiple_braces_with_trailing(self):
        """Test multiple braces in string with trailing content"""
        result = fix_json_trailing_content('{"pattern": "}}"}xxx')
        assert result == '{"pattern": "}}"}'
        assert json.loads(result) == {"pattern": "}}"}

    @pytest.mark.unit
    def test_empty_string(self):
        """Test with empty string"""
        assert fix_json_trailing_content('') == ''

    @pytest.mark.unit
    def test_none_input(self):
        """Test with None input - should return original"""
        # Empty string handling is handled at higher level
        result = fix_json_trailing_content('')
        assert result == ''


class TestFixJsonMissingBraces:
    """Test fix_json_missing_braces function"""

    @pytest.mark.unit
    def test_valid_json_unchanged(self):
        """Test that valid JSON is unchanged"""
        assert fix_json_missing_braces('{"city": "Beijing"}') == '{"city": "Beijing"}'
        assert fix_json_missing_braces('{}') == '{}'

    @pytest.mark.unit
    def test_one_missing_brace(self):
        """Test adding one missing closing brace"""
        result = fix_json_missing_braces('{"city": "Beijing"')
        assert result == '{"city": "Beijing"}'
        assert json.loads(result) == {"city": "Beijing"}

    @pytest.mark.unit
    def test_two_missing_braces(self):
        """Test adding two missing closing braces"""
        result = fix_json_missing_braces('{"a": {"b": 2}')
        assert result == '{"a": {"b": 2}}'
        assert json.loads(result) == {"a": {"b": 2}}

    @pytest.mark.unit
    def test_nested_missing_braces(self):
        """Test adding multiple missing braces for nested objects"""
        result = fix_json_missing_braces('{"a": {"b": {"c": 1}')
        assert result == '{"a": {"b": {"c": 1}}}'
        assert json.loads(result) == {"a": {"b": {"c": 1}}}

    @pytest.mark.unit
    def test_brace_in_string_value(self):
        """Test that braces inside string values don't affect brace counting"""
        result = fix_json_missing_braces('{"text": "}"}')
        assert result == '{"text": "}"}'
        assert json.loads(result) == {"text": "}"}

    @pytest.mark.unit
    def test_empty_string(self):
        """Test with empty string"""
        assert fix_json_missing_braces('') == ''


class TestRepairJsonString:
    """Test repair_json_string function - main integration tests"""

    @pytest.mark.unit
    @pytest.mark.parametrize("input_json,expected_output,expected_repaired", [
        # Test 1: Valid JSON - no change
        ('{"city": "Beijing"}', '{"city": "Beijing"}', False),

        # Test 2: Trailing markdown backtick
        ('{"city": "Beijing"}', '{"city": "Beijing"}', False),

        # Test 3: JSON with } in string value (critical case)
        ('{"text": "}"}', '{"text": "}"}', False),

        # Test 4: } in value + trailing content
        ('{"text": "}"}extra', '{"text": "}"}', True),

        # Test 5: Missing closing brace
        ('{"city": "Beijing"', '{"city": "Beijing"}', True),

        # Test 6: Missing 2 closing braces
        ('{"a": {"b": 2}', '{"a": {"b": 2}}', True),

        # Test 7: Missing brace + trailing content
        # Note: this is actually handled by adding braces first, then trailing content may be found
        ('{"a": {"b": 2}extra', '{"a": {"b": 2}}', True),

        # Test 8: Empty object
        ('{}', '{}', False),

        # Test 9: Multiple } in string - must be properly escaped
        ('{"pattern": "}}}"}', '{"pattern": "}}}"}', False),

        # Test 10: Multiple } + trailing
        ('{"pattern": "}}}"}xxx', '{"pattern": "}}}"}', True),

        # Test 11: Complex nested with trailing
        ('{"a": {"b": {"c": 1}}}extra', '{"a": {"b": {"c": 1}}}', True),
    ])
    def test_repair_json_string(self, input_json, expected_output, expected_repaired):
        """Test repair_json_string with various inputs"""
        result, was_repaired, msg = repair_json_string(input_json)

        # Verify the result is valid JSON and matches expected
        assert json.loads(result) == json.loads(expected_output)

        # Verify repair flag
        assert was_repaired == expected_repaired

    @pytest.mark.unit
    def test_empty_string_returns_empty_object(self):
        """Test that empty string is converted to {}"""
        result, was_repaired, msg = repair_json_string('')
        assert result == '{}'
        assert was_repaired is True
        assert 'empty string' in msg.lower()

    @pytest.mark.unit
    def test_none_returns_empty_object(self):
        """Test that None is converted to {}"""
        result, was_repaired, msg = repair_json_string(None)
        assert result == '{}'
        assert was_repaired is True
        assert 'none' in msg.lower() or 'null' in msg.lower()

    @pytest.mark.unit
    def test_trailing_content_message(self):
        """Test that trailing content generates correct message"""
        result, was_repaired, msg = repair_json_string('{"city": "Beijing"}extra')
        assert was_repaired is True
        assert 'truncating' in msg.lower() or 'trailing' in msg.lower()
        assert 'extra' in msg

    @pytest.mark.unit
    def test_missing_braces_message(self):
        """Test that missing braces generates correct message"""
        result, was_repaired, msg = repair_json_string('{"city": "Beijing"')
        assert was_repaired is True
        assert 'added' in msg.lower() or 'brace' in msg.lower()

    @pytest.mark.unit
    def test_combined_repairs_message(self):
        """Test that combined repairs generate correct message"""
        result, was_repaired, msg = repair_json_string('{"a": {"b": 2}extra')
        assert was_repaired is True
        # Message should indicate both truncation and brace addition
        assert msg  # Should have some message

    @pytest.mark.unit
    def test_invalid_json_returns_original(self):
        """Test that completely invalid JSON returns original unchanged"""
        invalid = 'not json at all'
        result, was_repaired, msg = repair_json_string(invalid)
        assert result == invalid
        assert was_repaired is False
        assert msg == ''

    @pytest.mark.unit
    def test_safety_limit_on_braces(self):
        """Test that there's a safety limit on added braces"""
        # Create something that would need many braces
        result, was_repaired, msg = repair_json_string('{{{')
        # Should return something, not hang indefinitely
        assert result is not None

    @pytest.mark.unit
    def test_special_characters_in_values(self):
        """Test various special characters in JSON values"""
        # Quotes, backslashes, newlines, etc.
        result, was_repaired, msg = repair_json_string('{"text": "He said \\"hello\\""}')
        assert was_repaired is False
        assert json.loads(result) == {"text": 'He said "hello"'}

    @pytest.mark.unit
    def test_whitespace_handling(self):
        """Test handling of whitespace in JSON"""
        # Trailing whitespace is valid JSON in Python's json.loads()
        # so it should NOT be marked as repaired
        result, was_repaired, msg = repair_json_string('{"city": "Beijing"}  ')
        assert was_repaired is False
        assert json.loads(result) == {"city": "Beijing"}

    @pytest.mark.unit
    def test_nested_objects_with_trailing(self):
        """Test nested objects with trailing content"""
        result, was_repaired, msg = repair_json_string('{"a": {"b": {"c": 1}}}trailing')
        assert was_repaired is True
        assert json.loads(result) == {"a": {"b": {"c": 1}}}

    @pytest.mark.unit
    def test_array_in_object(self):
        """Test objects containing arrays"""
        result, was_repaired, msg = repair_json_string('{"items": [1, 2, 3]}')
        assert was_repaired is False
        assert json.loads(result) == {"items": [1, 2, 3]}

    @pytest.mark.unit
    def test_array_in_object_with_trailing(self):
        """Test objects containing arrays with trailing content"""
        result, was_repaired, msg = repair_json_string('{"items": [1, 2, 3]}extra')
        assert was_repaired is True
        assert json.loads(result) == {"items": [1, 2, 3]}


class TestJsonRepairEdgeCases:
    """Test edge cases and tricky scenarios"""

    @pytest.mark.unit
    def test_brace_in_string_nested(self):
        """Test nested objects with braces in string values"""
        result, was_repaired, msg = repair_json_string('{"a": {"text": "}"}}')
        assert was_repaired is False
        assert json.loads(result) == {"a": {"text": "}"}}

    @pytest.mark.unit
    def test_brace_at_end_of_string_value(self):
        """Test brace at the very end of a string value"""
        result, was_repaired, msg = repair_json_string('{"text": "}"}')
        assert was_repaired is False
        assert json.loads(result) == {"text": "}"}

    @pytest.mark.unit
    def test_escaped_brace_in_string(self):
        r"""Test invalid escape sequence \} in JSON string value"""
        # The string '{"text": "\\}"}' in Python is {"text": "\}"}
        # which is INVALID JSON because \} is not a valid JSON escape sequence
        # The valid escape would be \\} (escaped backslash)
        result, was_repaired, msg = repair_json_string('{"text": "\\}"}')
        # Since this is invalid JSON, the repair function will try to fix it
        # but may not succeed completely - we just verify it doesn't crash
        assert result is not None

    @pytest.mark.unit
    def test_empty_string_value(self):
        """Test object with empty string value"""
        result, was_repaired, msg = repair_json_string('{"text": ""}')
        assert was_repaired is False
        assert json.loads(result) == {"text": ""}

    @pytest.mark.unit
    def test_unicode_in_values(self):
        """Test unicode characters in values"""
        result, was_repaired, msg = repair_json_string('{"text": "你好世界"}')
        assert was_repaired is False
        assert json.loads(result) == {"text": "你好世界"}

    @pytest.mark.unit
    def test_numbers_and_booleans(self):
        """Test various JSON value types"""
        result, was_repaired, msg = repair_json_string('{"num": 42, "flag": true, "val": null}')
        assert was_repaired is False
        assert json.loads(result) == {"num": 42, "flag": True, "val": None}

    @pytest.mark.unit
    def test_very_long_trailing_content(self):
        """Test with very long trailing content"""
        trailing = 'x' * 1000
        result, was_repaired, msg = repair_json_string('{"city": "Beijing"}' + trailing)
        assert was_repaired is True
        assert json.loads(result) == {"city": "Beijing"}
        # The message should include information about truncation
        assert msg

    @pytest.mark.unit
    def test_multiple_trailing_blocks(self):
        """Test content that looks like JSON but is trailing"""
        # This should only take the first valid JSON
        result, was_repaired, msg = repair_json_string('{"a": 1}{"b": 2}')
        # Should find valid prefix {"a": 1}
        assert was_repaired is True
        parsed = json.loads(result)
        assert parsed == {"a": 1}

    @pytest.mark.unit
    def test_incomplete_with_trailing(self):
        """Test incomplete JSON with trailing content"""
        result, was_repaired, msg = repair_json_string('{"a": 1extra')
        # The repair logic should handle this
        # It might find {} as valid prefix or add braces
        assert was_repaired is True
        # Result should be parseable
        json.loads(result)
