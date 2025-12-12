"""Variable management utilities.

Handles variable syntax conversion between collection formats and JMeter.
All collection formats use {{var}} syntax which is converted to ${var} for JMeter.
"""

import re
from typing import Any


class VariableManager:
    """Manage variable conversion and extraction.

    Converts variables from collection format ({{var}}) to JMeter format (${var}).
    Also provides utilities for extracting and analyzing variable usage.
    """

    # Patterns for variable detection
    # Standard format with optional spaces: {{ var }} or {{var}}
    DOUBLE_BRACE_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")
    # Insomnia format with underscore prefix: {{ _.var }} or {{_.var}}
    INSOMNIA_VAR_PATTERN = re.compile(r"\{\{\s*_\.(\w+)\s*\}\}")
    DOLLAR_BRACE_PATTERN = re.compile(r"\$\{(\w+)\}")

    # Variable names that suggest sensitive data
    SENSITIVE_PATTERNS = (
        "token",
        "secret",
        "password",
        "key",
        "auth",
        "api_key",
        "apikey",
        "credential",
        "private",
    )

    def convert_variable_syntax(self, text: str) -> str:
        """Convert {{var}} to ${var} syntax.

        Args:
            text: Text containing {{var}} placeholders.

        Returns:
            Text with ${var} placeholders.

        Example:
            >>> vm = VariableManager()
            >>> vm.convert_variable_syntax("{{base_url}}/users/{{id}}")
            '${base_url}/users/${id}'
        """
        # Handle None explicitly - return empty string
        if text is None:
            return ""
        # Handle non-string types - convert to string first
        # Note: 0 and False are valid values, not empty
        if not isinstance(text, str):
            text = str(text)
        # First convert Insomnia format {{ _.var }} -> ${var}
        text = self.INSOMNIA_VAR_PATTERN.sub(r"${\1}", text)
        # Then convert standard format {{ var }} -> ${var}
        return self.DOUBLE_BRACE_PATTERN.sub(r"${\1}", text)

    def convert_payload_variables(
        self, payload: dict[str, Any] | list[Any] | str | Any
    ) -> dict[str, Any] | list[Any] | str | Any:
        """Recursively convert variables in a payload structure.

        Handles nested dicts and lists, converting string values.

        Args:
            payload: Request payload (dict, list, or string).

        Returns:
            Payload with converted variable syntax.

        Example:
            >>> vm = VariableManager()
            >>> vm.convert_payload_variables({"user": "{{username}}"})
            {'user': '${username}'}
        """
        if isinstance(payload, dict):
            return {k: self.convert_payload_variables(v) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [self.convert_payload_variables(item) for item in payload]
        elif isinstance(payload, str):
            return self.convert_variable_syntax(payload)
        return payload

    def extract_variables(self, text: str) -> set[str]:
        """Extract variable names from text.

        Finds both {{var}} and ${var} patterns.

        Args:
            text: Text to scan for variables.

        Returns:
            Set of variable names found.

        Example:
            >>> vm = VariableManager()
            >>> vm.extract_variables("{{base_url}}/users/${id}")
            {'base_url', 'id'}
        """
        if text is None:
            return set()

        double_brace = set(self.DOUBLE_BRACE_PATTERN.findall(text))
        dollar_brace = set(self.DOLLAR_BRACE_PATTERN.findall(text))
        return double_brace | dollar_brace

    def is_sensitive_variable(self, name: str) -> bool:
        """Check if a variable name suggests sensitive data.

        Uses word boundary matching to avoid false positives (e.g., "tokenize"
        should not match "token").

        Args:
            name: Variable name to check.

        Returns:
            True if the name contains sensitive patterns as whole words or
            word parts separated by underscores.

        Example:
            >>> vm = VariableManager()
            >>> vm.is_sensitive_variable("auth_token")
            True
            >>> vm.is_sensitive_variable("user_id")
            False
            >>> vm.is_sensitive_variable("tokenize")
            False
        """
        name_lower = name.lower()
        # Split on underscores and check each part
        name_parts = set(name_lower.split("_"))
        for pattern in self.SENSITIVE_PATTERNS:
            # Check if pattern is a complete word part
            if pattern in name_parts:
                return True
            # Also check with word boundaries in the full name
            if re.search(rf"\b{re.escape(pattern)}\b", name_lower):
                return True
        return False

    def extract_path_from_url(self, url: str) -> str:
        """Extract path portion from a URL, preserving variables.

        Removes protocol, host, and variable prefixes to get clean path.

        Args:
            url: Full URL or path with variables.

        Returns:
            Clean path starting with /. Returns "/" for empty or whitespace-only input.

        Example:
            >>> vm = VariableManager()
            >>> vm.extract_path_from_url("https://api.example.com/users/123")
            '/users/123'
            >>> vm.extract_path_from_url("{{base_url}}/users/{{id}}")
            '/users/${id}'
            >>> vm.extract_path_from_url("")
            '/'
        """
        # Handle None or empty input
        if not url or not url.strip():
            return "/"

        # First convert variables
        url = self.convert_variable_syntax(url)

        # Remove protocol and host
        url = re.sub(r"^https?://[^/]+", "", url)

        # Remove variable prefixes like ${base_url}
        url = re.sub(r"^\$\{[^}]+\}", "", url)

        # Handle case where URL was just a variable or host
        if not url or not url.strip():
            return "/"

        # Ensure starts with /
        if not url.startswith("/"):
            url = "/" + url

        return url

    def extract_base_url(self, url: str) -> str | None:
        """Extract base URL (protocol + host) from a full URL.

        Args:
            url: Full URL.

        Returns:
            Base URL or None if not found.

        Example:
            >>> vm = VariableManager()
            >>> vm.extract_base_url("https://api.example.com/users")
            'https://api.example.com'
        """
        match = re.match(r"^(https?://[^/]+)", url)
        return match.group(1) if match else None

    def mask_sensitive_value(self, name: str, value: str) -> str:
        """Mask a value if the variable name is sensitive.

        Args:
            name: Variable name.
            value: Variable value.

        Returns:
            Masked value if sensitive, original value otherwise.

        Example:
            >>> vm = VariableManager()
            >>> vm.mask_sensitive_value("auth_token", "secret123")
            '***'
            >>> vm.mask_sensitive_value("user_id", "123")
            '123'
        """
        if self.is_sensitive_variable(name):
            return "***"
        return value


# Singleton instance for convenience
_variable_manager = VariableManager()


def convert_variables(text: str) -> str:
    """Convert {{var}} to ${var} syntax (convenience function).

    Args:
        text: Text containing {{var}} placeholders.

    Returns:
        Text with ${var} placeholders.
    """
    return _variable_manager.convert_variable_syntax(text)


def convert_payload(payload: Any) -> Any:
    """Convert variables in payload (convenience function).

    Args:
        payload: Request payload.

    Returns:
        Payload with converted variables.
    """
    return _variable_manager.convert_payload_variables(payload)
