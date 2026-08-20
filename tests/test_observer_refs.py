import pytest
import asyncio
from browser.observer import BrowserObserver

class DummyDriver:
    async def _enumerate_tabs(self, session_id):
        return [{"id": 1, "url": "http://example.com"}]
        
    async def execute_js(self, session_id, tab_id, script):
        # We need a JS environment to test the JS. So we mock the execute_js result?
        # Mocking JS execution is hard unless we use real JS. Let's return a fake result.
        return {
            "result": {
                "html": "[element:42]\n<button id=\"btn\" class=\"c\">Submit</button>",
                "refs": {42: "button#btn"}
            },
            "navigated": False,
            "new_tabs": []
        }

@pytest.mark.asyncio
async def test_element_references():
    observer = BrowserObserver(driver=DummyDriver())
    res = await observer.scan("sess_1", 1)
    
    assert "html" in res
    assert "[element:42]" in res["html"]
    
    assert "element_references" in res
    assert res["element_references"][42] == "button#btn"

