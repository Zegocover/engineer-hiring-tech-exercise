from tests.integration.helpers.website import Page

# Static site specs: name -> {path: Page}. Entries needing the live host
# (e.g. protocol_relative) are built by a factory instead; see SITE_FACTORIES.
SITES: dict[str, dict[str, Page]] = {
    "self_link": {
        "/": Page('<a href="/">me</a>'),
    },
    "cycle": {
        "/": Page('<a href="/b">b</a>'),
        "/b": Page('<a href="/">home</a>'),
    },
    "hundred_links": {
        "/": Page("".join(f'<a href="/target">{i}</a>' for i in range(100))),
        "/target": Page("done"),
    },
    "nested_relative": {
        "/deep/nested/page": Page('<a href="../sibling">up</a>'),
        "/deep/sibling": Page("ok"),
    },
    "off_domain_mix": {
        "/": Page(
            '<a href="https://other.test/a">a</a>'
            '<a href="mailto:x@y.test">m</a>'
            '<a href="/local">l</a>'
        ),
        "/local": Page("ok"),
    },
    "redirect_loop": {
        "/a": Page(status=302, headers={"Location": "/b"}),
        "/b": Page(status=302, headers={"Location": "/a"}),
    },
    "redirect_offsite": {
        "/": Page('<a href="/leave">go</a>'),
        "/leave": Page(status=302, headers={"Location": "https://other.test/landing"}),
    },
    "server_error": {
        "/": Page('<a href="/boom">b</a><a href="/fine">f</a>'),
        "/boom": Page(status=500),
        "/fine": Page("ok"),
    },
    "timeout": {
        "/": Page('<a href="/slow">s</a><a href="/fine">f</a>'),
        "/slow": Page(delay=30.0),
        "/fine": Page("ok"),
    },
    "big_asset": {
        "/": Page('<a href="/huge.pdf">pdf</a>'),
        "/huge.pdf": Page(content_type="application/pdf", size=50_000_000),
    },
    "no_content_type": {
        "/": Page('<a href="/mystery">m</a>'),
        "/mystery": Page("<a href='/hidden'>h</a>", omit_content_type=True),
        "/hidden": Page("ok"),
    },
    "binary_claiming_html": {
        "/": Page('<a href="/liar">l</a>'),
        "/liar": Page(content_type="text/html", size=4096),
    },
    "commented_link": {
        "/": Page('<!-- <a href="/ghost">g</a> --><a href="/real">r</a>'),
        "/real": Page("ok"),
        "/ghost": Page("should not be reached"),
    },
    "base_tag": {
        "/deep/page": Page('<base href="/other/"><a href="thing">t</a>'),
        "/other/thing": Page("ok"),
    },
    "meta_refresh": {
        "/": Page('<meta http-equiv="refresh" content="0; url=/next">'),
        "/next": Page("ok"),
    },
}

# Sites whose page bodies depend on the host the app is served under.
# Each factory takes the host (e.g. "testsite.local") and returns a page spec.
SITE_FACTORIES = {
    "protocol_relative": lambda host: {
        "/": Page(
            f'<a href="//elsewhere.test/x">off</a><a href="//{host}/inside">in</a>'
        ),
        "/inside": Page("ok"),
    },
}
