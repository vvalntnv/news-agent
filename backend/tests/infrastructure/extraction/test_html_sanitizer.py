from infrastructure.extraction.html_sanitizer import HtmlSanitizer


def test_sanitize_html_uses_full_document_when_root_is_none() -> None:
    sanitizer = HtmlSanitizer(attrs_to_retain=("href",))
    html = """
    <html>
      <head><script>ignored()</script><title>Title</title></head>
      <body class="page"><a href="/x" data-id="1">Link</a></body>
    </html>
    """

    sanitized = sanitizer.sanitize_html(html, root_of_analysis=None)

    assert "<html>" in sanitized
    assert "script" not in sanitized
    assert 'href="/x"' in sanitized
    assert "data-id=" not in sanitized
    assert "class=" not in sanitized


def test_sanitize_html_scopes_to_requested_root() -> None:
    sanitizer = HtmlSanitizer(attrs_to_retain=("href",))
    html = """
    <html>
      <head><title>Title</title></head>
      <body><article class="content"><a href="/news" rel="nofollow">Read</a></article></body>
    </html>
    """

    sanitized = sanitizer.sanitize_html(html, root_of_analysis="article")

    assert sanitized.startswith("<article")
    assert "<html>" not in sanitized
    assert 'href="/news"' in sanitized
    assert "rel=" not in sanitized
    assert "class=" not in sanitized


def test_sanitize_html_falls_back_to_document_when_root_missing() -> None:
    sanitizer = HtmlSanitizer()
    html = "<html><body><p>Hello</p></body></html>"

    sanitized = sanitizer.sanitize_html(html, root_of_analysis="article")

    assert "<html>" in sanitized
    assert "<p>Hello</p>" in sanitized


def test_sanitize_html_removes_selector_matches() -> None:
    sanitizer = HtmlSanitizer()
    html = """
    <article>
      <p>keep</p>
      <div class="remove-me"><p>drop</p></div>
    </article>
    """

    sanitized = sanitizer.sanitize_html(
        html,
        root_of_analysis="article",
        selectors_to_remove=[".remove-me"],
    )

    assert "keep" in sanitized
    assert "drop" not in sanitized
