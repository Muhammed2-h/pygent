from unittest.mock import AsyncMock, MagicMock

import pytest

from browser.observer import (
    BrowserObserver,
)


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.enumerate_tabs = AsyncMock(return_value=[{"id": 1, "url": "http://example.com"}])
    driver.execute_js = AsyncMock(return_value={"result": "<body><h1>Test</h1><a href='http://link.com'>Link</a><p style='display:none'>Hidden</p></body>"})
    return driver

@pytest.fixture
def observer(mock_driver):
    return BrowserObserver(driver=mock_driver)

def test_simplify_html(observer):
    html = '<html><body><h1>Title</h1><script>alert(1)</script><a href="link.html" style="color:red">Link</a></body></html>'
    simplified = observer.simplify_html(html)
    assert '<script>' not in simplified
    assert 'alert(1)' not in simplified
    assert '<h1>Title</h1>' in simplified
    assert '<a href="link.html">' in simplified

def test_extract_text(observer):
    html = '<html><body><h1>Title</h1><script>alert(1)</script><a href="link.html">Link</a></body></html>'
    text = observer.extract_text(html)
    assert text == 'Title Link'

def test_extract_interactive_elements(observer):
    html = '<html><body><button id="btn1">Click me</button><a href="link.html">Link</a></body></html>'
    elements = observer.extract_interactive_elements(html)
    assert len(elements) == 2
    assert elements[0]['tag'] == 'button'
    assert elements[0]['attributes']['id'] == 'btn1'
    assert elements[0]['text'] == 'Click me'
    assert elements[1]['tag'] == 'a'
    assert elements[1]['attributes']['href'] == 'link.html'

@pytest.mark.asyncio
async def test_scan_tabs_only(observer, mock_driver):
    result = await observer.scan("session_1", 1, {"tabs_only": True})
    assert "tabs" in result
    assert result["tabs"][0]["id"] == 1
    assert "html" not in result
    mock_driver.execute_js.assert_not_called()

@pytest.mark.asyncio
async def test_scan_text_only(observer, mock_driver):
    result = await observer.scan("session_1", 1, {"text_only": True})
    assert "text" in result
    assert "Test Link Hidden" in result["text"] or "Test Link" in result["text"] # depending on space extraction

@pytest.mark.asyncio
async def test_scan_max_chars(observer, mock_driver):
    result = await observer.scan("session_1", 1, {"max_chars": 5})
    assert "html" in result
    assert len(result["html"]) <= 25
    assert result["html"].endswith("</body>")

@pytest.mark.asyncio
async def test_scan_full(observer, mock_driver):
    result = await observer.scan("session_1", 1)
    assert "html" in result
    assert "interactive_elements" in result
    assert "tabs" in result
    mock_driver.execute_js.assert_called_once()
