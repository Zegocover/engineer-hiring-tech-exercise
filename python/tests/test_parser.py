"""Tests for HTML parsing helpers."""

from pathlib import Path

import pytest

from crawler import parser

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param(
            "basic.html",
            ["/about", "https://example.com/contact"],
            id="basic",
        ),
        pytest.param(
            "mixed.html",
            [
                "/",
                "/products?ref=nav#top",
                "#section",
                "mailto:hello@example.com",
                "https://example.com/blog",
            ],
            id="mixed",
        ),
        pytest.param(
            "malformed.html",
            ["/a", "/b", "/c"],
            id="malformed",
        ),
        pytest.param(
            "cc0_zero6.html",
            [
                "work-zero.html",
                "work-zero.html",
                "#",
                "#",
                "http://wiki.creativecommons.org/Frequently_Asked_Questions"
                "#When_are_publicity_rights_relevant.3F",
                "#",
                "#",
                "./legalcode",
                "http://creativecommons.org/",
                "http://creativecommons.org/choose/zero/",
            ],
            id="cc0-zero6",
        ),
        pytest.param(
            "cc0_pd6.html",
            [
                "work.html",
                "work.html",
                "http://www.flickr.com/photos/nationaalarchief/",
                "#",
                "http://wiki.creativecommons.org/Frequently_Asked_Questions"
                "#When_are_publicity_rights_relevant.3F",
                "#",
                "http://wiki.creativecommons.org/Frequently_Asked_Questions"
                "#What_are_moral_rights.2C_and_how_could_I_exercise_them_to_prevent_uses_of_my_work_that_I_don.E2.80.99t_like.3F",
                "#",
                "#",
                "http://creativecommons.org/",
                "http://creativecommons.org/publicdomain/",
            ],
            id="cc0-pd6",
        ),
        pytest.param(
            "cc0_work.html",
            [
                "http://www.flickr.com/photos/nationaalarchief/2839787636/",
                "http://www.flickr.com/photos/nationaalarchief/",
                "http://www.flickr.com/photos/nationaalarchief/2839787636/",
                "pd6.html",
                "pd6.html",
            ],
            id="cc0-work",
        ),
    ],
)
def test_extract_links_from_fixtures(
    fixture: str, expected: list[str]
) -> None:
    html = (FIXTURES / fixture).read_text()
    assert parser.extract_links(html) == expected
