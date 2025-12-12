"""Integration tests for end-to-end workflows.

Tests cover:
- Full workflow: collection -> import -> JMX -> validate
- Cross-format consistency
- Real-world collection imports
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from collection_importer.core.collection_analyzer import CollectionAnalyzer
from collection_importer.core.importers.bruno import BrunoImporter
from collection_importer.core.importers.insomnia import InsomniaImporter
from collection_importer.core.importers.postman import PostmanImporter
from collection_importer.core.jmx_generator import JMXGenerator


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_bruno_to_jmx_full_workflow(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test full Bruno -> JMX workflow."""
        # Step 1: Analyze
        analyzer = CollectionAnalyzer()
        analysis = analyzer.analyze_project(str(bruno_collection_dir))
        assert analysis["collections_found"]

        # Step 2: Import
        importer = BrunoImporter()
        collection = importer.import_collection(bruno_collection_dir)
        assert collection.request_count > 0

        # Step 3: Generate JMX
        generator = JMXGenerator()
        output = str(tmp_path / "test.jmx")
        result = generator.generate(collection, output)
        assert result["success"]

        # Step 4: Validate XML structure
        tree = ET.parse(output)
        root = tree.getroot()
        assert root.tag == "jmeterTestPlan"
        assert root.find(".//TestPlan") is not None
        assert root.find(".//ThreadGroup") is not None
        assert len(root.findall(".//HTTPSamplerProxy")) == collection.request_count

    def test_postman_to_jmx_full_workflow(
        self, postman_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test full Postman -> JMX workflow."""
        importer = PostmanImporter()
        collection = importer.import_collection(postman_collection_file)

        generator = JMXGenerator()
        output = str(tmp_path / "test.jmx")
        result = generator.generate(collection, output)

        assert result["success"]
        tree = ET.parse(output)
        root = tree.getroot()
        assert root.find(".//TestPlan") is not None

    def test_insomnia_to_jmx_full_workflow(
        self, insomnia_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test full Insomnia -> JMX workflow."""
        importer = InsomniaImporter()
        collection = importer.import_collection(insomnia_collection_file)

        generator = JMXGenerator()
        output = str(tmp_path / "test.jmx")
        result = generator.generate(collection, output)

        assert result["success"]
        tree = ET.parse(output)
        root = tree.getroot()
        assert root.find(".//TestPlan") is not None


class TestJMXStructureValidation:
    """Tests for validating generated JMX structure."""

    def test_jmx_has_required_elements(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test JMX contains all required elements."""
        importer = BrunoImporter()
        collection = importer.import_collection(bruno_collection_dir)

        generator = JMXGenerator()
        output = str(tmp_path / "test.jmx")
        generator.generate(collection, output)

        tree = ET.parse(output)
        root = tree.getroot()

        # Required elements
        assert root.find(".//TestPlan") is not None
        assert root.find(".//ThreadGroup") is not None
        # HTTP Request Defaults
        config_elements = root.findall(".//ConfigTestElement")
        assert len(config_elements) > 0

    def test_jmx_thread_config(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test JMX thread configuration."""
        importer = BrunoImporter()
        collection = importer.import_collection(bruno_collection_dir)

        generator = JMXGenerator()
        output = str(tmp_path / "test.jmx")
        generator.generate(
            collection, output, threads=50, rampup=10, duration=300
        )

        tree = ET.parse(output)
        root = tree.getroot()

        # Check thread group configuration
        thread_group = root.find(".//ThreadGroup")
        assert thread_group is not None

        # Find the num_threads element
        for elem in thread_group.iter():
            if elem.get("name") == "ThreadGroup.num_threads":
                assert elem.text == "50"
                break

    def test_jmx_sampler_count_matches(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test JMX sampler count matches request count."""
        importer = BrunoImporter()
        collection = importer.import_collection(bruno_collection_dir)

        generator = JMXGenerator()
        output = str(tmp_path / "test.jmx")
        generator.generate(collection, output)

        tree = ET.parse(output)
        root = tree.getroot()

        samplers = root.findall(".//HTTPSamplerProxy")
        assert len(samplers) == collection.request_count


class TestCrossFormatConsistency:
    """Tests for cross-format consistency."""

    def test_all_formats_produce_valid_jmx(
        self,
        bruno_collection_dir: Path,
        postman_collection_file: Path,
        insomnia_collection_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test all formats produce valid JMX files."""
        collections = [
            (BrunoImporter(), bruno_collection_dir, "bruno.jmx"),
            (PostmanImporter(), postman_collection_file, "postman.jmx"),
            (InsomniaImporter(), insomnia_collection_file, "insomnia.jmx"),
        ]

        generator = JMXGenerator()

        for importer, path, filename in collections:
            collection = importer.import_collection(path)
            output = str(tmp_path / filename)
            result = generator.generate(collection, output)

            assert result["success"], f"Failed for {importer.format_name}"

            # Verify valid XML
            tree = ET.parse(output)
            root = tree.getroot()
            assert root.tag == "jmeterTestPlan"

    def test_all_formats_have_http_samplers(
        self,
        bruno_collection_dir: Path,
        postman_collection_file: Path,
        insomnia_collection_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test all formats produce JMX with HTTP samplers."""
        collections = [
            (BrunoImporter(), bruno_collection_dir, "bruno.jmx"),
            (PostmanImporter(), postman_collection_file, "postman.jmx"),
            (InsomniaImporter(), insomnia_collection_file, "insomnia.jmx"),
        ]

        generator = JMXGenerator()

        for importer, path, filename in collections:
            collection = importer.import_collection(path)
            output = str(tmp_path / filename)
            generator.generate(collection, output)

            tree = ET.parse(output)
            root = tree.getroot()

            samplers = root.findall(".//HTTPSamplerProxy")
            assert len(samplers) > 0, f"No samplers for {importer.format_name}"


class TestRealWorldCollections:
    """Tests for real-world collection imports."""

    def test_jsonplaceholder_bruno(
        self, bruno_real_world_jsonplaceholder: Path, tmp_path: Path
    ) -> None:
        """Test importing JSONPlaceholder Bruno collection."""
        importer = BrunoImporter()
        collection = importer.import_collection(bruno_real_world_jsonplaceholder)

        generator = JMXGenerator()
        output = str(tmp_path / "jsonplaceholder.jmx")
        result = generator.generate(collection, output)

        assert result["success"]
        assert collection.request_count > 0

        # Validate JMX structure
        tree = ET.parse(output)
        root = tree.getroot()
        assert len(root.findall(".//HTTPSamplerProxy")) == collection.request_count

    def test_jsonplaceholder_postman(
        self, postman_real_world_jsonplaceholder: Path, tmp_path: Path
    ) -> None:
        """Test importing JSONPlaceholder Postman collection."""
        importer = PostmanImporter()
        collection = importer.import_collection(postman_real_world_jsonplaceholder)

        generator = JMXGenerator()
        output = str(tmp_path / "jsonplaceholder.jmx")
        result = generator.generate(collection, output)

        assert result["success"]
        assert collection.request_count > 0


class TestVariableConversion:
    """Tests for variable conversion in JMX output."""

    def test_variables_converted_in_jmx(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test that {{var}} is converted to ${var} in JMX."""
        importer = BrunoImporter()
        collection = importer.import_collection(bruno_collection_dir)

        generator = JMXGenerator()
        output = str(tmp_path / "test.jmx")
        generator.generate(collection, output)

        # Read the JMX content
        with open(output) as f:
            content = f.read()

        # Check that no {{var}} style variables remain
        assert "{{" not in content
        assert "}}" not in content


class TestAnalyzerIntegration:
    """Tests for analyzer integration with importers."""

    def test_analyzer_detects_and_imports_bruno(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test analyzer detects Bruno and import works."""
        analyzer = CollectionAnalyzer()
        format_name = analyzer.detect_format(str(bruno_collection_dir))
        assert format_name == "bruno"

        importer = BrunoImporter()
        assert importer.can_import(bruno_collection_dir)

        collection = importer.import_collection(bruno_collection_dir)
        assert collection.metadata.format == "bruno"

    def test_analyzer_detects_and_imports_postman(
        self, postman_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test analyzer detects Postman and import works."""
        analyzer = CollectionAnalyzer()
        format_name = analyzer.detect_format(str(postman_collection_file))
        assert format_name == "postman"

        importer = PostmanImporter()
        assert importer.can_import(postman_collection_file)

        collection = importer.import_collection(postman_collection_file)
        assert collection.metadata.format == "postman"

    def test_analyzer_detects_and_imports_insomnia(
        self, insomnia_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test analyzer detects Insomnia and import works."""
        analyzer = CollectionAnalyzer()
        format_name = analyzer.detect_format(str(insomnia_collection_file))
        assert format_name == "insomnia"

        importer = InsomniaImporter()
        assert importer.can_import(insomnia_collection_file)

        collection = importer.import_collection(insomnia_collection_file)
        assert collection.metadata.format == "insomnia"
