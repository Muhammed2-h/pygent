"""
Browser Observer Module.

Listens to and handles events emitted by the browser subsystem.
"""

from typing import Any, Dict, List, Optional
import html.parser

class SimplifiedHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.ignore_tags = {'script', 'style', 'noscript', 'meta', 'link', 'svg', 'path', 'iframe'}
        self.keep_attrs = {'id', 'class', 'href', 'src', 'alt', 'type', 'name', 'value', 'placeholder', 'role', 'aria-label'}
        self.skip_subtree = False
        self.skip_tag = None
        self.depth = 0
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        self.depth += 1
        if self.skip_subtree:
            return
        
        if tag in self.ignore_tags:
            self.skip_subtree = True
            self.skip_depth = self.depth
            return
            
        attr_str = ""
        for k, v in attrs:
            if k in self.keep_attrs:
                if v is None:
                    attr_str += f' {k}'
                else:
                    attr_str += f' {k}="{v}"'
        self.result.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag):
        if self.skip_subtree:
            if self.depth == self.skip_depth:
                self.skip_subtree = False
            self.depth -= 1
            return
            
        self.result.append(f"</{tag}>")
        self.depth -= 1

    def handle_data(self, data):
        if not self.skip_subtree:
            text = data.strip()
            if text:
                self.result.append(text)

class TextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.ignore_tags = {'script', 'style', 'noscript'}
        self.skip = False
        self.depth = 0
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        self.depth += 1
        if not self.skip and tag in self.ignore_tags:
            self.skip = True
            self.skip_depth = self.depth

    def handle_endtag(self, tag):
        if self.skip and self.depth == self.skip_depth:
            self.skip = False
        self.depth -= 1

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.text.append(text)

class InteractiveExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.interactive_tags = {'a', 'button', 'input', 'select', 'textarea', 'form'}
        self.current_element = None

    def handle_starttag(self, tag, attrs):
        if tag in self.interactive_tags:
            attrs_dict = dict(attrs)
            self.elements.append({
                'tag': tag,
                'attributes': attrs_dict,
                'text': ''
            })
            self.current_element = self.elements[-1]

    def handle_endtag(self, tag):
        if tag in self.interactive_tags:
            self.current_element = None

    def handle_data(self, data):
        if self.current_element:
            self.current_element['text'] += data.strip()

class BrowserObserver:
    """Observer for browser events."""
    def __init__(self, driver=None):
        self.driver = driver

    def simplify_html(self, html_content: str) -> str:
        """Simplify HTML by removing scripts, styles, and keeping relevant attributes."""
        parser = SimplifiedHTMLParser()
        parser.feed(html_content)
        return "".join(parser.result)

    def extract_text(self, html_content: str) -> str:
        """Extract plain text from HTML."""
        parser = TextExtractor()
        parser.feed(html_content)
        return " ".join(parser.text)

    def extract_interactive_elements(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract interactive elements like links and buttons from HTML."""
        parser = InteractiveExtractor()
        parser.feed(html_content)
        return parser.elements

    async def scan(self, session_id: str, tab_id: int, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scan the active tab.
        Options:
          - tabs_only: return only tab information.
          - text_only: return only extracted text.
          - max_chars: truncate text/html output to max_chars.
        """
        if options is None:
            options = {}
            
        tabs_only = options.get("tabs_only", False)
        text_only = options.get("text_only", False)
        max_chars = options.get("max_chars", 0)

        # Retrieve tabs first
        tabs = await self.driver._enumerate_tabs(session_id)
        
        if tabs_only:
            return {"tabs": tabs}
            
        # JS script to extract simplified DOM, ignoring hidden elements
        js_script = """
        function getCleanHTML(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                return node.textContent.trim() ? node.textContent.trim() + ' ' : '';
            }
            if (node.nodeType !== Node.ELEMENT_NODE) return '';
            
            const style = window.getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                return '';
            }
            
            const tag = node.tagName.toLowerCase();
            if (['script', 'style', 'noscript', 'meta', 'link', 'svg', 'path', 'iframe'].includes(tag)) {
                return '';
            }
            
            let html = '<' + tag;
            const allowedAttrs = ['id', 'class', 'href', 'src', 'alt', 'type', 'name', 'value', 'placeholder', 'role', 'aria-label'];
            for (let i = 0; i < node.attributes.length; i++) {
                const attr = node.attributes[i];
                if (allowedAttrs.includes(attr.name)) {
                    html += ' ' + attr.name + '="' + attr.value.replace(/"/g, '&quot;') + '"';
                }
            }
            html += '>';
            
            for (let i = 0; i < node.childNodes.length; i++) {
                html += getCleanHTML(node.childNodes[i]);
            }
            html += '</' + tag + '>';
            return html;
        }
        return getCleanHTML(document.body);
        """
        
        try:
            resp = await self.driver.execute_js(session_id, tab_id, js_script)
            html_content = resp.get("result", "")
        except Exception as e:
            html_content = ""
            
        # Optional processing using python side parser to further normalize or extract text
        if text_only:
            text = self.extract_text(html_content)
            if max_chars > 0 and len(text) > max_chars:
                text = text[:max_chars]
            return {"text": text, "tabs": tabs}
            
        simplified = self.simplify_html(html_content)
        if max_chars > 0 and len(simplified) > max_chars:
            simplified = simplified[:max_chars]
            
        interactives = self.extract_interactive_elements(html_content)
        
        return {
            "html": simplified,
            "interactive_elements": interactives,
            "tabs": tabs
        }
