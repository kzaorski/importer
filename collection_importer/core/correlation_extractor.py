"""Correlation extractor for post-response scripts.

Extracts variable capture patterns from Bruno, Postman, and Insomnia scripts
and converts them to JMeter-compatible JSONPath expressions.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedCorrelation:
    """A single extracted correlation from a post-response script.

    Attributes:
        variable_name: Name of the variable to store the extracted value.
        json_path: JSONPath expression to extract the value (e.g., "$.id").
        source_format: Original format (bruno, postman, insomnia).
    """

    variable_name: str
    json_path: str
    source_format: str


class CorrelationExtractor:
    """Extract variable correlations from post-response scripts.

    Supports:
    - Bruno: bru.setVar('name', data.path) or bru.setVar('name', res.body.path)
    - Postman: pm.environment.set('name', jsonData.path) or pm.globals.set(...)
    - Insomnia: insomnia.setEnvironmentVariable('name', data.path)

    Converts JavaScript property access to JSONPath:
    - data.id -> $.id
    - data.user.name -> $.user.name
    - data.items[0].id -> $.items[0].id
    """

    # Bruno patterns
    # bru.setVar('varName', data.path) or bru.setVar('varName', res.body.path)
    BRUNO_PATTERN = re.compile(
        r"bru\.setVar\s*\(\s*['\"](\w+)['\"]\s*,\s*"
        r"(?:data|res\.body|res\.getBody\(\))\.([a-zA-Z0-9_.\[\]]+)\s*\)",
        re.MULTILINE,
    )

    # Postman patterns
    # pm.environment.set('varName', jsonData.path) or pm.globals.set(...)
    POSTMAN_PATTERN = re.compile(
        r"pm\.(?:environment|globals|collectionVariables)\.set\s*\(\s*['\"](\w+)['\"]\s*,\s*"
        r"(?:jsonData|data|responseJson|json)\.([a-zA-Z0-9_.\[\]]+)\s*\)",
        re.MULTILINE,
    )

    # Insomnia patterns
    # insomnia.setEnvironmentVariable('varName', data.path)
    INSOMNIA_PATTERN = re.compile(
        r"insomnia\.setEnvironmentVariable\s*\(\s*['\"](\w+)['\"]\s*,\s*"
        r"(?:data|response|json)\.([a-zA-Z0-9_.\[\]]+)\s*\)",
        re.MULTILINE,
    )

    def extract_correlations(
        self, script: str | None, source_format: str
    ) -> list[ExtractedCorrelation]:
        """Extract correlations from a post-response script.

        Args:
            script: Post-response script content.
            source_format: Source format (bruno, postman, insomnia).

        Returns:
            List of extracted correlations.
        """
        if not script:
            return []

        correlations: list[ExtractedCorrelation] = []

        # Select pattern based on format
        if source_format == "bruno":
            pattern = self.BRUNO_PATTERN
        elif source_format == "postman":
            pattern = self.POSTMAN_PATTERN
        elif source_format == "insomnia":
            pattern = self.INSOMNIA_PATTERN
        else:
            logger.warning(f"Unknown format for correlation extraction: {source_format}")
            return []

        # Find all matches
        matches = pattern.findall(script)

        for var_name, js_path in matches:
            json_path = self._convert_to_jsonpath(js_path)

            if json_path:
                correlations.append(
                    ExtractedCorrelation(
                        variable_name=var_name,
                        json_path=json_path,
                        source_format=source_format,
                    )
                )
                logger.debug(
                    f"Extracted correlation: {var_name} = {json_path} (from {source_format})"
                )

        return correlations

    def _convert_to_jsonpath(self, js_path: str) -> str | None:
        """Convert JavaScript property access to JSONPath.

        Args:
            js_path: JavaScript property path (e.g., "user.id", "items[0].name").

        Returns:
            JSONPath expression (e.g., "$.user.id", "$.items[0].name") or None if invalid.
        """
        if not js_path:
            return None

        # Clean up the path
        js_path = js_path.strip()

        # Validate path - should only contain valid characters
        if not re.match(r"^[a-zA-Z0-9_.\[\]]+$", js_path):
            logger.warning(f"Invalid JavaScript path for JSONPath conversion: {js_path}")
            return None

        # Check for unsupported patterns
        if "(" in js_path or ")" in js_path:
            logger.warning(f"Function calls not supported in JSONPath: {js_path}")
            return None

        # Convert to JSONPath by prepending $
        return f"$.{js_path}"

    def has_complex_logic(self, script: str | None) -> bool:
        """Check if script contains complex logic that can't be converted.

        Args:
            script: Script content to check.

        Returns:
            True if script contains unsupported patterns.
        """
        if not script:
            return False

        # Patterns that indicate complex logic
        complex_patterns = [
            r"\bif\s*\(",  # if statements
            r"\belse\b",  # else clauses
            r"\bfor\s*\(",  # for loops
            r"\bwhile\s*\(",  # while loops
            r"\bswitch\s*\(",  # switch statements
            r"\.map\s*\(",  # array map
            r"\.filter\s*\(",  # array filter
            r"\.reduce\s*\(",  # array reduce
            r"\.forEach\s*\(",  # forEach loops
            r"\btry\s*\{",  # try blocks
            r"\bcatch\s*\(",  # catch blocks
        ]

        for pattern in complex_patterns:
            if re.search(pattern, script):
                return True

        return False
