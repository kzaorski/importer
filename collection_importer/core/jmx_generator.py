"""JMX Generator for creating JMeter test plans from parsed collections.

Generates valid JMeter JMX files using xml.etree.ElementTree.
Uses HTTP Request Defaults pattern for centralized server configuration.

Note: defusedxml is available as a dependency for secure XML parsing when needed.
This module only creates XML (no parsing of untrusted input), so standard library is safe.
"""

import json
import logging

# Use standard library for XML creation (defusedxml is for parsing)
# JMX generation creates XML, so standard library is safe here
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.dom import minidom

from collection_importer.core.data_types import CollectionRequest, ParsedCollection
from collection_importer.exceptions import JMXGenerationException

logger = logging.getLogger(__name__)


class JMXGenerator:
    """Generate JMeter JMX test plans from parsed collections.

    Creates JMX files with:
    - TestPlan (root container)
    - HTTP Request Defaults (server configuration)
    - User Defined Variables (collection variables)
    - ThreadGroup (load profile)
    - HTTP Samplers (one per request)
    - Header Managers (request-specific headers)
    - JSR223 PreProcessors (pre-request scripts, Groovy)
    - JSR223 PostProcessors (post-response scripts, Groovy)
    - JSONPostProcessor (for response value extraction)
    """

    # JMeter version info for JMX header
    JMX_VERSION = "1.2"
    PROPERTIES_VERSION = "5.0"
    JMETER_VERSION = "5.6"

    # Default test configuration
    DEFAULT_THREADS = 1
    DEFAULT_RAMPUP = 0
    DEFAULT_DURATION = None

    # Validation limits
    MAX_THREADS = 100000
    MAX_RAMPUP = 3600  # 1 hour
    MAX_DURATION = 86400  # 24 hours

    # Suspicious XML patterns to detect
    SUSPICIOUS_XML_PATTERNS = (
        "<?xml",
        "<!DOCTYPE",
        "<![CDATA[",
        "<!ENTITY",
    )

    def _validate_collection(self, collection: Any) -> None:
        """Validate collection object.

        Args:
            collection: Collection to validate.

        Raises:
            JMXGenerationException: If collection is invalid.
        """
        if collection is None:
            raise JMXGenerationException("Collection cannot be None")

        if not isinstance(collection, ParsedCollection):
            raise JMXGenerationException(
                f"Expected ParsedCollection, got {type(collection).__name__}"
            )

        if collection.metadata is None:
            raise JMXGenerationException("Collection metadata is required")

        if not collection.metadata.name:
            raise JMXGenerationException(
                "Collection name is required and cannot be empty"
            )

        if not isinstance(collection.metadata.name, str):
            raise JMXGenerationException(
                f"Collection name must be string, got {type(collection.metadata.name).__name__}"
            )

        if len(collection.metadata.name.strip()) == 0:
            raise JMXGenerationException("Collection name cannot be whitespace only")

    def _validate_output_path(self, output_path: Any) -> None:
        """Validate output file path.

        Args:
            output_path: Path to validate.

        Raises:
            JMXGenerationException: If output path is invalid.
        """
        if not output_path:
            raise JMXGenerationException("Output path is required")

        if not isinstance(output_path, str):
            raise JMXGenerationException(
                f"Output path must be string, got {type(output_path).__name__}"
            )

        path = Path(output_path)

        # Check parent directory exists
        if not path.parent.exists():
            raise JMXGenerationException(
                f"Output directory does not exist: {path.parent}"
            )

        # Check parent directory is a directory
        if not path.parent.is_dir():
            raise JMXGenerationException(
                f"Output path parent is not a directory: {path.parent}"
            )

    def _validate_thread_params(
        self,
        threads: int,
        rampup: int,
        duration: int | None,
    ) -> None:
        """Validate thread group parameters.

        Args:
            threads: Number of threads.
            rampup: Ramp-up period.
            duration: Test duration.

        Raises:
            JMXGenerationException: If parameters are invalid.
        """
        # Validate threads
        if not isinstance(threads, int):
            raise JMXGenerationException(
                f"Threads must be integer, got {type(threads).__name__}"
            )
        if threads < 1:
            raise JMXGenerationException(f"Threads must be >= 1, got {threads}")
        if threads > self.MAX_THREADS:
            raise JMXGenerationException(
                f"Threads exceeds maximum ({self.MAX_THREADS}), got {threads}"
            )

        # Validate rampup
        if not isinstance(rampup, int):
            raise JMXGenerationException(
                f"Ramp-up must be integer, got {type(rampup).__name__}"
            )
        if rampup < 0:
            raise JMXGenerationException(f"Ramp-up must be >= 0, got {rampup}")
        if rampup > self.MAX_RAMPUP:
            raise JMXGenerationException(
                f"Ramp-up exceeds maximum ({self.MAX_RAMPUP} seconds), got {rampup}"
            )

        # Validate duration
        if duration is not None:
            if not isinstance(duration, int):
                raise JMXGenerationException(
                    f"Duration must be integer, got {type(duration).__name__}"
                )
            if duration < 1:
                raise JMXGenerationException(f"Duration must be >= 1, got {duration}")
            if duration > self.MAX_DURATION:
                raise JMXGenerationException(
                    f"Duration exceeds maximum ({self.MAX_DURATION} seconds), got {duration}"
                )

    def _validate_base_url(self, base_url: str) -> None:
        """Validate base URL.

        Args:
            base_url: URL to validate.

        Raises:
            JMXGenerationException: If base URL is invalid.
        """
        if not isinstance(base_url, str):
            raise JMXGenerationException(
                f"Base URL must be string, got {type(base_url).__name__}"
            )

        if not base_url.strip():
            raise JMXGenerationException("Base URL cannot be empty or whitespace")

        parsed = urlparse(base_url)

        # Must have a scheme
        if not parsed.scheme:
            raise JMXGenerationException(
                f"Base URL must include scheme (http/https): {base_url}"
            )

        # Must be http or https
        if parsed.scheme not in ("http", "https"):
            raise JMXGenerationException(
                f"Base URL scheme must be http/https, got {parsed.scheme}: {base_url}"
            )

        # Must have a hostname
        if not parsed.hostname:
            raise JMXGenerationException(f"Base URL must include hostname: {base_url}")

        # Port must be valid if specified
        if parsed.port:
            if not 1 <= parsed.port <= 65535:
                raise JMXGenerationException(
                    f"Base URL port must be 1-65535, got {parsed.port}: {base_url}"
                )

    def _validate_xml_string(self, value: str, field_name: str) -> str:
        """Validate and return string for XML insertion.

        Checks for suspicious XML patterns that might indicate injection attempts.
        ElementTree escapes values automatically, but this provides defense in depth.

        Args:
            value: String value to validate.
            field_name: Name of the field (for error messages).

        Returns:
            Validated string (stripped).

        Raises:
            JMXGenerationException: If value contains suspicious patterns.
        """
        if not isinstance(value, str):
            raise JMXGenerationException(f"{field_name} must be a string")

        value_lower = value.lower()
        for pattern in self.SUSPICIOUS_XML_PATTERNS:
            if pattern.lower() in value_lower:
                raise JMXGenerationException(
                    f"{field_name} contains suspicious XML pattern: {pattern}",
                    details="This may indicate an XML injection attempt",
                )

        return value.strip()

    def generate(
        self,
        collection: ParsedCollection,
        output_path: str,
        base_url: str | None = None,
        threads: int = DEFAULT_THREADS,
        rampup: int = DEFAULT_RAMPUP,
        duration: int | None = DEFAULT_DURATION,
    ) -> dict[str, Any]:
        """Generate JMeter JMX file from parsed collection.

        Args:
            collection: Parsed collection data.
            output_path: Path where to save JMX file.
            base_url: Override base URL (uses collection base_url if not provided).
            threads: Number of virtual users (default: 1).
            rampup: Ramp-up period in seconds (default: 0).
            duration: Test duration in seconds (None = use loop count).

        Returns:
            Dictionary with generation results:
            {
                "success": bool,
                "jmx_path": str,
                "samplers_created": int,
                "threads": int,
                "rampup": int,
                "duration": int | None,
            }

        Raises:
            JMXGenerationException: If generation fails.
        """
        # Validate inputs first (before try block for clear error messages)
        self._validate_collection(collection)
        self._validate_output_path(output_path)
        self._validate_thread_params(threads, rampup, duration)

        # Determine effective base URL
        effective_base_url = (
            base_url or collection.metadata.base_url or "http://localhost:8080"
        )

        # Validate base URL if explicitly provided
        if base_url:
            self._validate_base_url(base_url)

        try:
            # Parse URL components
            domain, port, protocol = self._parse_url(effective_base_url)

            # Build JMX structure
            root = self._create_root()
            main_tree = ET.SubElement(root, "hashTree")

            # Create test plan
            test_plan = self._create_test_plan(collection.metadata.name)
            main_tree.append(test_plan)
            test_plan_tree = ET.SubElement(main_tree, "hashTree")

            # Add User Defined Variables (if collection has variables)
            # Filter out base_url variants - they belong in HTTP Request Defaults
            variables = {
                k: v for k, v in collection.metadata.variables.items()
                if k.lower().replace("_", "") != "baseurl"
            }
            if variables:
                udv = self._create_user_defined_variables(variables)
                test_plan_tree.append(udv)
                ET.SubElement(test_plan_tree, "hashTree")

            # Add HTTP Request Defaults
            http_defaults = self._create_http_defaults(domain, port, protocol)
            test_plan_tree.append(http_defaults)
            ET.SubElement(test_plan_tree, "hashTree")

            # Create Thread Group
            thread_group = self._create_thread_group(
                name=f"{collection.metadata.name} Users",
                threads=threads,
                rampup=rampup,
                duration=duration,
            )
            test_plan_tree.append(thread_group)
            thread_group_tree = ET.SubElement(test_plan_tree, "hashTree")

            # Add HTTP Samplers for each request
            samplers_created = 0
            for request in collection.requests:
                sampler = self._create_http_sampler(request)
                thread_group_tree.append(sampler)
                sampler_tree = ET.SubElement(thread_group_tree, "hashTree")

                # Add JSR223 PreProcessor if request has pre-script
                if request.pre_script:
                    pre_processor = self._create_jsr223_pre_processor(
                        script=request.pre_script,
                        name=f"{request.name} - Pre-Request",
                    )
                    sampler_tree.append(pre_processor)
                    ET.SubElement(sampler_tree, "hashTree")

                # Add Header Manager if request has headers
                if request.headers:
                    header_manager = self._create_header_manager(request.headers)
                    sampler_tree.append(header_manager)
                    ET.SubElement(sampler_tree, "hashTree")

                # Add JSONPostProcessor for each correlation
                for correlation in request.correlations:
                    json_processor = self._create_json_post_processor(
                        variable_name=correlation["variable_name"],
                        json_path=correlation["json_path"],
                    )
                    sampler_tree.append(json_processor)
                    ET.SubElement(sampler_tree, "hashTree")
                    logger.debug(
                        f"Added JSONPostProcessor: {correlation['variable_name']} = {correlation['json_path']}"
                    )

                # Add JSR223 PostProcessor if request has post-script (and no correlations extracted)
                # Only add raw script if we couldn't extract correlations from it
                if request.post_script and not request.correlations:
                    post_processor = self._create_jsr223_post_processor(
                        script=request.post_script,
                        name=f"{request.name} - Post-Response",
                    )
                    sampler_tree.append(post_processor)
                    ET.SubElement(sampler_tree, "hashTree")

                samplers_created += 1

            # Add listeners
            results_tree = self._create_view_results_tree()
            test_plan_tree.append(results_tree)
            ET.SubElement(test_plan_tree, "hashTree")

            aggregate_report = self._create_aggregate_report()
            test_plan_tree.append(aggregate_report)
            ET.SubElement(test_plan_tree, "hashTree")

            # Prettify XML
            try:
                xml_string = self._prettify_xml(root)
            except Exception as e:
                raise JMXGenerationException(
                    "Failed to format XML output",
                    details=str(e),
                ) from e

            # Write to file
            try:
                Path(output_path).write_text(xml_string, encoding="utf-8")
            except PermissionError as e:
                raise JMXGenerationException(
                    f"Permission denied writing to: {output_path}",
                    details=str(e),
                ) from e
            except OSError as e:
                raise JMXGenerationException(
                    f"Failed to write JMX file: {output_path}",
                    details=str(e),
                ) from e

            return {
                "success": True,
                "jmx_path": output_path,
                "samplers_created": samplers_created,
                "threads": threads,
                "rampup": rampup,
                "duration": duration,
            }

        except JMXGenerationException:
            # Re-raise our own exceptions as-is
            raise
        except ValueError as e:
            raise JMXGenerationException(
                "Invalid value during JMX generation",
                details=str(e),
            ) from e
        except ET.ParseError as e:
            raise JMXGenerationException(
                "XML parsing error during generation",
                details=str(e),
            ) from e
        except Exception as e:
            # Catch unexpected exceptions with context
            logger.exception("Unexpected error during JMX generation")
            raise JMXGenerationException(
                f"Unexpected error during JMX generation: {type(e).__name__}",
                details=str(e),
            ) from e

    def _create_root(self) -> ET.Element:
        """Create JMX root element."""
        return ET.Element(
            "jmeterTestPlan",
            {
                "version": self.JMX_VERSION,
                "properties": self.PROPERTIES_VERSION,
                "jmeter": self.JMETER_VERSION,
            },
        )

    def _create_test_plan(self, name: str) -> ET.Element:
        """Create TestPlan element."""
        test_plan = ET.Element(
            "TestPlan",
            {
                "guiclass": "TestPlanGui",
                "testclass": "TestPlan",
                "testname": name,
                "enabled": "true",
            },
        )

        ET.SubElement(test_plan, "stringProp", {"name": "TestPlan.comments"}).text = ""
        ET.SubElement(
            test_plan, "boolProp", {"name": "TestPlan.functional_mode"}
        ).text = "false"
        ET.SubElement(
            test_plan, "boolProp", {"name": "TestPlan.serialize_threadgroups"}
        ).text = "false"

        # Empty user defined variables (actual UDV added separately)
        udv_elem = ET.SubElement(
            test_plan,
            "elementProp",
            {"name": "TestPlan.user_defined_variables", "elementType": "Arguments"},
        )
        ET.SubElement(udv_elem, "collectionProp", {"name": "Arguments.arguments"})

        ET.SubElement(
            test_plan, "stringProp", {"name": "TestPlan.user_define_classpath"}
        ).text = ""

        return test_plan

    def _create_user_defined_variables(self, variables: dict[str, str]) -> ET.Element:
        """Create User Defined Variables element."""
        udv = ET.Element(
            "Arguments",
            {
                "guiclass": "ArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )

        collection_prop = ET.SubElement(
            udv, "collectionProp", {"name": "Arguments.arguments"}
        )

        for name, value in variables.items():
            arg = ET.SubElement(
                collection_prop,
                "elementProp",
                {"name": name, "elementType": "Argument"},
            )
            ET.SubElement(arg, "stringProp", {"name": "Argument.name"}).text = name
            ET.SubElement(arg, "stringProp", {"name": "Argument.value"}).text = value
            ET.SubElement(arg, "stringProp", {"name": "Argument.metadata"}).text = "="

        return udv

    def _create_http_defaults(
        self, domain: str, port: str, protocol: str
    ) -> ET.Element:
        """Create HTTP Request Defaults element."""
        defaults = ET.Element(
            "ConfigTestElement",
            {
                "guiclass": "HttpDefaultsGui",
                "testclass": "ConfigTestElement",
                "testname": "HTTP Request Defaults",
                "enabled": "true",
            },
        )

        # Arguments (empty)
        args = ET.SubElement(
            defaults,
            "elementProp",
            {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "enabled": "true",
            },
        )
        ET.SubElement(args, "collectionProp", {"name": "Arguments.arguments"})

        # Server settings
        ET.SubElement(
            defaults, "stringProp", {"name": "HTTPSampler.domain"}
        ).text = domain
        ET.SubElement(defaults, "stringProp", {"name": "HTTPSampler.port"}).text = port
        ET.SubElement(
            defaults, "stringProp", {"name": "HTTPSampler.protocol"}
        ).text = protocol
        ET.SubElement(
            defaults, "stringProp", {"name": "HTTPSampler.contentEncoding"}
        ).text = "UTF-8"
        ET.SubElement(defaults, "stringProp", {"name": "HTTPSampler.path"}).text = ""
        ET.SubElement(
            defaults, "stringProp", {"name": "HTTPSampler.concurrentPool"}
        ).text = "6"
        ET.SubElement(
            defaults, "stringProp", {"name": "HTTPSampler.connect_timeout"}
        ).text = ""
        ET.SubElement(
            defaults, "stringProp", {"name": "HTTPSampler.response_timeout"}
        ).text = ""

        return defaults

    def _create_thread_group(
        self,
        name: str,
        threads: int,
        rampup: int,
        duration: int | None,
    ) -> ET.Element:
        """Create ThreadGroup element."""
        thread_group = ET.Element(
            "ThreadGroup",
            {
                "guiclass": "ThreadGroupGui",
                "testclass": "ThreadGroup",
                "testname": name,
                "enabled": "true",
            },
        )

        ET.SubElement(
            thread_group, "stringProp", {"name": "ThreadGroup.on_sample_error"}
        ).text = "continue"

        # Loop Controller
        loop_controller = ET.SubElement(
            thread_group,
            "elementProp",
            {"name": "ThreadGroup.main_controller", "elementType": "LoopController"},
        )
        ET.SubElement(
            loop_controller, "boolProp", {"name": "LoopController.continue_forever"}
        ).text = "false"
        ET.SubElement(
            loop_controller, "stringProp", {"name": "LoopController.loops"}
        ).text = "-1" if duration else "1"

        # Thread settings
        ET.SubElement(
            thread_group, "stringProp", {"name": "ThreadGroup.num_threads"}
        ).text = str(threads)
        ET.SubElement(
            thread_group, "stringProp", {"name": "ThreadGroup.ramp_time"}
        ).text = str(rampup)

        # Scheduler settings
        use_scheduler = duration is not None
        ET.SubElement(
            thread_group, "boolProp", {"name": "ThreadGroup.scheduler"}
        ).text = str(use_scheduler).lower()
        ET.SubElement(
            thread_group, "stringProp", {"name": "ThreadGroup.duration"}
        ).text = str(duration) if duration else ""
        ET.SubElement(
            thread_group, "stringProp", {"name": "ThreadGroup.delay"}
        ).text = "0"

        return thread_group

    def _create_http_sampler(self, request: CollectionRequest) -> ET.Element:
        """Create HTTPSamplerProxy element."""
        sampler_name = request.full_name
        if not sampler_name.startswith(request.method):
            sampler_name = f"{request.method} {request.path}"

        sampler = ET.Element(
            "HTTPSamplerProxy",
            {
                "guiclass": "HttpTestSampleGui",
                "testclass": "HTTPSamplerProxy",
                "testname": sampler_name,
                "enabled": "true",
            },
        )

        # Handle body
        has_body = request.has_body
        if has_body:
            ET.SubElement(
                sampler, "boolProp", {"name": "HTTPSampler.postBodyRaw"}
            ).text = "true"

        # Arguments
        args = ET.SubElement(
            sampler,
            "elementProp",
            {"name": "HTTPsampler.Arguments", "elementType": "Arguments"},
        )
        args_collection = ET.SubElement(
            args, "collectionProp", {"name": "Arguments.arguments"}
        )

        if has_body:
            arg = ET.SubElement(
                args_collection,
                "elementProp",
                {"name": "", "elementType": "HTTPArgument"},
            )
            ET.SubElement(
                arg, "boolProp", {"name": "HTTPArgument.always_encode"}
            ).text = "false"

            # Serialize body to JSON if dict
            body_value = request.body
            if isinstance(body_value, dict):
                body_value = json.dumps(body_value, indent=2)
            ET.SubElement(
                arg, "stringProp", {"name": "Argument.value"}
            ).text = str(body_value)
            ET.SubElement(arg, "stringProp", {"name": "Argument.metadata"}).text = "="

        # Empty domain/port/protocol (inherited from defaults)
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.domain"}).text = ""
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.port"}).text = ""
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.protocol"}).text = ""
        ET.SubElement(
            sampler, "stringProp", {"name": "HTTPSampler.contentEncoding"}
        ).text = ""

        # Path and method
        ET.SubElement(
            sampler, "stringProp", {"name": "HTTPSampler.path"}
        ).text = request.path
        ET.SubElement(
            sampler, "stringProp", {"name": "HTTPSampler.method"}
        ).text = request.method

        # Standard settings
        ET.SubElement(
            sampler, "boolProp", {"name": "HTTPSampler.follow_redirects"}
        ).text = "true"
        ET.SubElement(
            sampler, "boolProp", {"name": "HTTPSampler.auto_redirects"}
        ).text = "false"
        ET.SubElement(
            sampler, "boolProp", {"name": "HTTPSampler.use_keepalive"}
        ).text = "true"
        ET.SubElement(
            sampler, "boolProp", {"name": "HTTPSampler.DO_MULTIPART_POST"}
        ).text = "false"
        ET.SubElement(
            sampler, "stringProp", {"name": "HTTPSampler.embedded_url_re"}
        ).text = ""
        ET.SubElement(
            sampler, "stringProp", {"name": "HTTPSampler.connect_timeout"}
        ).text = ""
        ET.SubElement(
            sampler, "stringProp", {"name": "HTTPSampler.response_timeout"}
        ).text = ""

        return sampler

    def _create_header_manager(self, headers: dict[str, str]) -> ET.Element:
        """Create HeaderManager element."""
        manager = ET.Element(
            "HeaderManager",
            {
                "guiclass": "HeaderPanel",
                "testclass": "HeaderManager",
                "testname": "HTTP Header Manager",
                "enabled": "true",
            },
        )

        collection = ET.SubElement(
            manager, "collectionProp", {"name": "HeaderManager.headers"}
        )

        for name, value in headers.items():
            header = ET.SubElement(
                collection, "elementProp", {"name": "", "elementType": "Header"}
            )
            ET.SubElement(header, "stringProp", {"name": "Header.name"}).text = name
            ET.SubElement(header, "stringProp", {"name": "Header.value"}).text = value

        return manager

    def _create_view_results_tree(self) -> ET.Element:
        """Create View Results Tree listener."""
        return ET.Element(
            "ResultCollector",
            {
                "guiclass": "ViewResultsFullVisualizer",
                "testclass": "ResultCollector",
                "testname": "View Results Tree",
                "enabled": "true",
            },
        )

    def _create_aggregate_report(self) -> ET.Element:
        """Create Aggregate Report listener."""
        return ET.Element(
            "ResultCollector",
            {
                "guiclass": "StatVisualizer",
                "testclass": "ResultCollector",
                "testname": "Aggregate Report",
                "enabled": "true",
            },
        )

    def _create_json_post_processor(
        self,
        variable_name: str,
        json_path: str,
        match_number: int = 1,
        default_value: str = "NOT_FOUND",
    ) -> ET.Element:
        """Create JSONPostProcessor element for extracting values from JSON responses.

        Args:
            variable_name: Name of JMeter variable to store extracted value.
            json_path: JSONPath expression to extract value (e.g., "$.id", "$.data[0].name").
            match_number: Which match to use (1 = first, 0 = random, -1 = all).
            default_value: Value to use if JSONPath expression finds no match.

        Returns:
            JSONPostProcessor XML element.
        """
        processor = ET.Element(
            "JSONPostProcessor",
            {
                "guiclass": "JSONPostProcessorGui",
                "testclass": "JSONPostProcessor",
                "testname": f"Extract {variable_name}",
                "enabled": "true",
            },
        )

        ET.SubElement(
            processor, "stringProp", {"name": "JSONPostProcessor.referenceNames"}
        ).text = variable_name
        ET.SubElement(
            processor, "stringProp", {"name": "JSONPostProcessor.jsonPathExprs"}
        ).text = json_path
        ET.SubElement(
            processor, "stringProp", {"name": "JSONPostProcessor.match_numbers"}
        ).text = str(match_number)
        ET.SubElement(
            processor, "stringProp", {"name": "JSONPostProcessor.defaultValues"}
        ).text = default_value

        return processor

    def _create_jsr223_pre_processor(
        self,
        script: str,
        name: str = "Pre-Request Script",
        language: str = "groovy",
    ) -> ET.Element:
        """Create JSR223 PreProcessor element for pre-request scripts.

        Converts collection pre-request scripts to JMeter JSR223 PreProcessor.
        Uses Groovy as the default scripting language for best performance.

        Args:
            script: Script code to execute before request.
            name: Name for the preprocessor element.
            language: Script language (default: groovy). Supports: groovy, javascript, jython, beanshell.

        Returns:
            JSR223PreProcessor XML element.
        """
        processor = ET.Element(
            "JSR223PreProcessor",
            {
                "guiclass": "TestBeanGUI",
                "testclass": "JSR223PreProcessor",
                "testname": name,
                "enabled": "true",
            },
        )

        ET.SubElement(
            processor, "stringProp", {"name": "scriptLanguage"}
        ).text = language
        ET.SubElement(processor, "stringProp", {"name": "parameters"}).text = ""
        ET.SubElement(processor, "stringProp", {"name": "filename"}).text = ""
        ET.SubElement(processor, "stringProp", {"name": "cacheKey"}).text = "true"
        ET.SubElement(processor, "stringProp", {"name": "script"}).text = script

        return processor

    def _create_jsr223_post_processor(
        self,
        script: str,
        name: str = "Post-Response Script",
        language: str = "groovy",
    ) -> ET.Element:
        """Create JSR223 PostProcessor element for post-response scripts.

        Converts collection post-response/test scripts to JMeter JSR223 PostProcessor.
        Uses Groovy as the default scripting language for best performance.

        Args:
            script: Script code to execute after response.
            name: Name for the postprocessor element.
            language: Script language (default: groovy). Supports: groovy, javascript, jython, beanshell.

        Returns:
            JSR223PostProcessor XML element.
        """
        processor = ET.Element(
            "JSR223PostProcessor",
            {
                "guiclass": "TestBeanGUI",
                "testclass": "JSR223PostProcessor",
                "testname": name,
                "enabled": "true",
            },
        )

        ET.SubElement(
            processor, "stringProp", {"name": "scriptLanguage"}
        ).text = language
        ET.SubElement(processor, "stringProp", {"name": "parameters"}).text = ""
        ET.SubElement(processor, "stringProp", {"name": "filename"}).text = ""
        ET.SubElement(processor, "stringProp", {"name": "cacheKey"}).text = "true"
        ET.SubElement(processor, "stringProp", {"name": "script"}).text = script

        return processor

    def _parse_url(self, url: str) -> tuple[str, str, str]:
        """Parse URL into domain, port, and protocol.

        Args:
            url: Full URL or base URL.

        Returns:
            Tuple of (domain, port, protocol).
        """
        parsed = urlparse(url)

        domain = parsed.hostname or "localhost"
        protocol = parsed.scheme or "http"

        # Determine port
        if parsed.port:
            port = str(parsed.port)
        elif protocol == "https":
            port = "443"
        else:
            port = "80"

        return domain, port, protocol

    def _prettify_xml(self, element: ET.Element) -> str:
        """Pretty-print XML with proper indentation.

        Args:
            element: Root XML element.

        Returns:
            Formatted XML string.
        """
        rough_string = ET.tostring(element, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        # Get pretty XML and remove extra blank lines
        pretty = reparsed.toprettyxml(indent="  ")
        # Remove the XML declaration that minidom adds (we'll add our own)
        lines = pretty.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]
        # Add proper XML declaration
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(lines)
