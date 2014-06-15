import markdown.inlinepatterns
from markdown.util import etree, AtomicString


WIDGET_RE = r'\!\!(.*?)\!\!'  # Like !!widget option option!!


class WidgetPattern(markdown.inlinepatterns.Pattern):
    """Return <widget>text</widget>."""
    def handleMatch(self, m):
        widget = m.group(2)
        el = etree.Element('widget')
        el.text = AtomicString(widget)
        return el


class WidgetExtension(markdown.Extension):
    """Widget Extension for Python-Markdown."""
    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns['widget'] = WidgetPattern(WIDGET_RE, md)
