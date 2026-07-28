import json

from crawler.crawler import CrawlResult
from crawler.output import write_result


def _result() -> CrawlResult:
    return CrawlResult(
        completed=True,
        visited={"https://testsite.local/b", "https://testsite.local/"},
        found_urls_by_domain={
            "testsite.local": {"https://testsite.local/b", "https://testsite.local/"},
            "other.local": {"https://other.local/x"},
        },
    )


class TestWriteResult:
    def test_writes_one_file_named_for_the_crawled_domain(self, tmp_path):
        "A crawl should produce a single JSON file named after the start URL's domain."
        # Act
        path = write_result(_result(), "https://testsite.local/", output_dir=tmp_path)

        # Assert
        assert path == tmp_path / "testsite.local.json"
        assert [p.name for p in tmp_path.iterdir()] == ["testsite.local.json"]

    def test_document_contains_visited_and_found_urls(self, tmp_path):
        "The written document should carry the crawl metadata, visited pages and all found domains."
        # Act
        path = write_result(_result(), "https://testsite.local/", output_dir=tmp_path)
        document = json.loads(path.read_text())

        # Assert
        assert document["domain"] == "testsite.local"
        assert document["start_url"] == "https://testsite.local/"
        assert document["completed"] is True
        assert document["visited"] == [
            "https://testsite.local/",
            "https://testsite.local/b",
        ]
        assert document["found_urls_by_domain"] == {
            "other.local": ["https://other.local/x"],
            "testsite.local": [
                "https://testsite.local/",
                "https://testsite.local/b",
            ],
        }
        assert "crawled_at" in document

    def test_recrawling_a_domain_overwrites_its_file(self, tmp_path):
        "A second run of the same domain should replace the previous file, not add another."
        # Arrange
        write_result(_result(), "https://testsite.local/", output_dir=tmp_path)
        second = CrawlResult(
            completed=False,
            visited={"https://testsite.local/only"},
            found_urls_by_domain={},
        )

        # Act
        path = write_result(second, "https://testsite.local/", output_dir=tmp_path)
        document = json.loads(path.read_text())

        # Assert
        assert [p.name for p in tmp_path.iterdir()] == ["testsite.local.json"]
        assert document["completed"] is False
        assert document["visited"] == ["https://testsite.local/only"]

    def test_creates_the_output_directory_when_missing(self, tmp_path):
        "Writing into a directory that does not exist yet should create it."
        # Arrange
        target = tmp_path / "nested" / "output"

        # Act
        path = write_result(_result(), "https://testsite.local/", output_dir=target)

        # Assert
        assert path.exists()

    def test_a_port_in_the_domain_is_made_filename_safe(self, tmp_path):
        "A netloc carrying a port must not produce a ':' in the filename."
        # Act
        path = write_result(_result(), "http://localhost:8000/", output_dir=tmp_path)

        # Assert
        assert path.name == "localhost_8000.json"
        assert json.loads(path.read_text())["domain"] == "localhost:8000"
