import io

import pypdf

from app.ingestion.extractor import clean_text, extract_html, extract_pdf_text


class TestExtractHtml:
    def test_extracts_title_headings_text_and_links(self):
        html = """
        <html>
          <head><title>My Page</title></head>
          <body>
            <nav>Home | About</nav>
            <h1>Welcome</h1>
            <h2>Section</h2>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
            <a href="/a">A</a>
            <a href="https://example.com/b">B</a>
            <footer>copyright</footer>
          </body>
        </html>
        """
        page = extract_html(html)
        assert page.title == "My Page"
        assert page.headings == ["Welcome", "Section"]
        assert "First paragraph." in page.text
        assert "Second paragraph." in page.text
        assert page.links == ["/a", "https://example.com/b"]

    def test_excludes_nav_footer_script_style_aside(self):
        html = """
        <html><body>
          <script>var x = 1;</script>
          <style>.a{color:red}</style>
          <aside>sidebar text</aside>
          <p>Real content.</p>
        </body></html>
        """
        page = extract_html(html)
        assert page.text == "Real content."

    def test_missing_title_is_empty_string(self):
        page = extract_html("<html><body><p>Hi</p></body></html>")
        assert page.title == ""

    def test_no_paragraphs_gives_empty_text(self):
        page = extract_html("<html><body><h1>Only heading</h1></body></html>")
        assert page.text == ""

    def test_href_without_text_is_still_a_link(self):
        page = extract_html('<html><body><a href="/x"></a></body></html>')
        assert page.links == ["/x"]

    def test_anchor_without_href_is_ignored(self):
        page = extract_html('<html><body><a name="top">Top</a></body></html>')
        assert page.links == []


class TestCleanText:
    def test_drops_short_lines_without_trailing_period(self):
        text = "Home\nAbout\nThis is a long enough sentence to keep."
        cleaned = clean_text(text)
        assert cleaned == "This is a long enough sentence to keep."

    def test_keeps_short_lines_ending_in_period(self):
        text = "Yes."
        assert clean_text(text, min_line_length=40) == "Yes."

    def test_drops_blank_lines(self):
        text = "\n\nThis line is definitely long enough to survive cleaning.\n\n"
        assert clean_text(text) == "This line is definitely long enough to survive cleaning."

    def test_empty_input_returns_empty_string(self):
        assert clean_text("") == ""


class TestExtractPdfText:
    def test_extracts_text_from_generated_pdf(self):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        text = extract_pdf_text(buf.getvalue())
        assert text == ""  # blank page has no extractable text, but must not raise
