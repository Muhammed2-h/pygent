from browser.state import BrowserState


def test_browser_state_initialization():
    state = BrowserState()
    assert state.active_tab is None
    assert state.tabs == []
    assert state.current_url is None
    assert state.title is None
    assert state.page_signature is None
    assert state.last_action is None
    assert state.last_result is None
    assert state.navigation == []
    assert state.new_tabs == []

def test_browser_state_update():
    state = BrowserState()
    
    state.update(
        active_tab=1,
        tabs=[1, 2],
        current_url="https://example.com",
        title="Example",
        page_signature="hash123",
        last_action={"action": "click", "target": "button"},
        last_result={"status": "success"},
        navigation=["https://example.com"],
        new_tabs=[2]
    )
    
    assert state.active_tab == 1
    assert state.tabs == [1, 2]
    assert state.current_url == "https://example.com"
    assert state.title == "Example"
    assert state.page_signature == "hash123"
    assert state.last_action == {"action": "click", "target": "button"}
    assert state.last_result == {"status": "success"}
    assert state.navigation == ["https://example.com"]
    assert state.new_tabs == [2]

def test_browser_state_partial_update():
    state = BrowserState(
        active_tab=1,
        current_url="https://old.com"
    )
    
    state.update(current_url="https://new.com", title="New Page")
    
    assert state.active_tab == 1
    assert state.current_url == "https://new.com"
    assert state.title == "New Page"

def test_browser_state_ignore_unknown_fields():
    state = BrowserState()
    state.update(active_tab=5, unknown_field="should_be_ignored")
    
    assert state.active_tab == 5
    assert not hasattr(state, "unknown_field")

def test_browser_state_privacy():
    state = BrowserState()
    state.update(
        last_result={"status": "success", "cookie": "sessionid=secret_token_123"},
        current_url="https://user:password123@example.com"
    )
    
    assert "[REDACTED_SESSION_TOKEN]" in str(state.last_result)
    assert "sessionid=secret_token_123" not in str(state.last_result)
    
    assert "password123" not in state.current_url
    assert "[REDACTED_CREDENTIALS]" in state.current_url
