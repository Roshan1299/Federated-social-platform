from django import template
import markdown

register = template.Library()

@register.filter
def markdown_to_html(text):
    """
    Converts Markdown text to HTML
    Usage: {{ content|markdown_to_html }}
    """
    return markdown.markdown(text)