import html
import html.parser
from typing import Any, Dict, List, Optional
import hashlib

class SimplifiedHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.ignore_tags = {'script', 'style', 'noscript', 'meta', 'link', 'svg', 'path', 'iframe'}
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
        self.keep_attrs = {'id', 'class', 'href', 'src', 'alt', 'type', 'name', 'value', 'placeholder', 'role', 'aria-label'}
        self.skip_subtree = False
        self.skip_depth = 0
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        is_void = tag in self.void_tags
        if not is_void:
            self.depth += 1
            
        if self.skip_subtree:
            return
            
        if tag in self.ignore_tags:
            if not is_void:
                self.skip_subtree = True
                self.skip_depth = self.depth
            return
            
        attr_str = ""
        for k, v in attrs:
            if k in self.keep_attrs:
                if v is None:
                    attr_str += f' {k}'
                else:
                    escaped_v = html.escape(v, quote=True)
                    attr_str += f' {k}="{escaped_v}"'
        self.result.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag):
        if tag in self.void_tags:
            return
            
        if self.skip_subtree:
            if self.depth == self.skip_depth:
                self.skip_subtree = False
            self.depth -= 1
            return
            
        self.result.append(f"</{tag}>")
        self.depth -= 1

    def handle_data(self, data):
        if not self.skip_subtree:
            text = data
            if text.strip():
                # Add spaces around to prevent concatenation if original had spaces
                # but simplified
                clean_text = text.strip()
                if text.startswith((' ', '\t', '\n')):
                    clean_text = ' ' + clean_text
                if text.endswith((' ', '\t', '\n')):
                    clean_text = clean_text + ' '
                self.result.append(clean_text)
            elif ' ' in text or '\n' in text:
                self.result.append(' ')

class TextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.ignore_tags = {'script', 'style', 'noscript'}
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
        self.skip = False
        self.depth = 0
        self.skip_depth = 0
        self.seen_hashes = set()
        
    def handle_starttag(self, tag, attrs):
        is_void = tag in self.void_tags
        if not is_void:
            self.depth += 1
        if not self.skip and tag in self.ignore_tags:
            if not is_void:
                self.skip = True
                self.skip_depth = self.depth

    def handle_endtag(self, tag):
        if tag in self.void_tags:
            return
        if self.skip and self.depth == self.skip_depth:
            self.skip = False
        self.depth -= 1

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                # Remove duplicate content logic
                text_hash = hashlib.md5(text.encode()).hexdigest()
                if text_hash not in self.seen_hashes:
                    self.seen_hashes.add(text_hash)
                    self.text.append(text)

class InteractiveExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.interactive_tags = {'a', 'button', 'input', 'select', 'textarea', 'form'}
        self.void_tags = {'input', 'img', 'area', 'base', 'br', 'col', 'embed', 'hr', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag in self.interactive_tags:
            attrs_dict = dict(attrs)
            element = {
                'tag': tag,
                'attributes': attrs_dict,
                'text': ''
            }
            self.elements.append(element)
            if tag not in self.void_tags:
                self.stack.append(element)

    def handle_endtag(self, tag):
        if tag in self.interactive_tags and tag not in self.void_tags:
            if self.stack and self.stack[-1]['tag'] == tag:
                self.stack.pop()

    def handle_data(self, data):
        text = data.strip()
        if text:
            for el in self.stack:
                el['text'] += text + ' '

class HtmlTruncator(html.parser.HTMLParser):
    def __init__(self, max_chars):
        super().__init__()
        self.max_chars = max_chars
        self.result = []
        self.current_chars = 0
        self.stopped = False
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if self.stopped:
            return
        attr_str = ""
        for k, v in attrs:
            if v is None:
                attr_str += f' {k}'
            else:
                escaped_v = html.escape(v, quote=True)
                attr_str += f' {k}="{escaped_v}"'
        tag_str = f"<{tag}{attr_str}>"
        self.result.append(tag_str)
        self.current_chars += len(tag_str)
        if tag not in self.void_tags:
            self.stack.append(tag)
        self.check_stop()

    def handle_endtag(self, tag):
        if self.stopped:
            return
        if tag in self.void_tags:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        tag_str = f"</{tag}>"
        self.result.append(tag_str)
        self.current_chars += len(tag_str)
        self.check_stop()

    def handle_data(self, data):
        if self.stopped:
            return
        if self.current_chars + len(data) > self.max_chars:
            allowed = self.max_chars - self.current_chars
            data = data[:allowed]
            self.stopped = True
        self.result.append(data)
        self.current_chars += len(data)
        self.check_stop()

    def check_stop(self):
        if self.current_chars >= self.max_chars and not self.stopped:
            self.stopped = True

    def get_result(self):
        res = "".join(self.result)
        if self.stopped:
            # close unclosed tags
            for tag in reversed(self.stack):
                res += f"</{tag}>"
        return res

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
        # trim trailing spaces
        for el in parser.elements:
            el['text'] = el['text'].strip()
        return parser.elements

    def _truncate_html(self, html_content: str, max_chars: int) -> str:
        if max_chars <= 0:
            return html_content
        truncator = HtmlTruncator(max_chars)
        truncator.feed(html_content)
        return truncator.get_result()

    async def scan(self, session_id: str, tab_id: int, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if options is None:
            options = {}
            
        tabs_only = options.get("tabs_only", False)
        text_only = options.get("text_only", False)
        max_chars = options.get("max_chars", 0)

        # Retrieve tabs first
        try:
            tabs = await self.driver._enumerate_tabs(session_id)
        except Exception:
            tabs = []
        
        if tabs_only:
            return {"tabs": tabs}
            
        # JS script to extract simplified DOM, ignoring hidden elements
        js_script = """
        function getCleanHTML(node, seenText = new Set()) {
            if (node.nodeType === Node.TEXT_NODE) {
                const txt = node.textContent.trim();
                if (txt) {
                    // Remove duplicate content logic
                    if (seenText.has(txt)) return '';
                    seenText.add(txt);
                    return node.textContent;
                }
                return node.textContent.includes(' ') || node.textContent.includes('\\n') ? ' ' : '';
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
            
            let childrenHtml = '';
            let validChildren = 0;
            for (let i = 0; i < node.childNodes.length; i++) {
                const childHtml = getCleanHTML(node.childNodes[i], seenText);
                if (childHtml) {
                    childrenHtml += childHtml;
                    validChildren++;
                }
            }
            
            // Remove irrelevant containers (e.g. div/span with no attributes and only one valid child or just text)
            // Wait, we want to retain forms, labels, structure. Let's just remove div/span if they have NO attributes and 1 child element.
            const hasAttributes = node.attributes.length > 0;
            if (['div', 'span'].includes(tag) && !hasAttributes && validChildren === 1 && childrenHtml.startsWith('<')) {
                return childrenHtml;
            }
            
            let html = '<' + tag;
            const allowedAttrs = ['id', 'class', 'href', 'src', 'alt', 'type', 'name', 'value', 'placeholder', 'role', 'aria-label'];
            for (let i = 0; i < node.attributes.length; i++) {
                const attr = node.attributes[i];
                if (allowedAttrs.includes(attr.name)) {
                    // escape quotes
                    const escapedVal = attr.value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    html += ' ' + attr.name + '="' + escapedVal + '"';
                }
            }
            
            const voidTags = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'];
            if (voidTags.includes(tag)) {
                html += '>';
            } else {
                html += '>';
                html += childrenHtml;
                html += '</' + tag + '>';
            }
            
            return html;
        }
        return getCleanHTML(document.body);
        """
        
        try:
            resp = await self.driver.execute_js(session_id, tab_id, js_script)
            html_content = resp.get("result", "")
        except Exception:
            html_content = ""
            
        if text_only:
            text = self.extract_text(html_content)
            if max_chars > 0 and len(text) > max_chars:
                text = text[:max_chars]
            return {"text": text, "tabs": tabs}
            
        # JS already simplifies the HTML, so we don't need to run simplify_html again, 
        # but we do need to truncate it if requested.
        simplified = html_content
        if max_chars > 0:
            simplified = self._truncate_html(simplified, max_chars)
            
        interactives = self.extract_interactive_elements(html_content)
        
        return {
            "html": simplified,
            "interactive_elements": interactives,
            "tabs": tabs
        }
