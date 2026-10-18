"""
Markdown rendering of every text written on the site (news, comments, page content).

python-markdown lets raw HTML through and the templates print the result with `|safe`, so a comment holding
`<script>` would run in the browser of whoever reads it. nh3 keeps only harmless HTML.
"""

import nh3
from markdownx.utils import markdownify

# What markdown itself produces (tables, code highlighting, footnotes) and nothing that runs.
ALLOWED_ATTRIBUTES = {
    **{tag: set(attributes) for tag, attributes in nh3.ALLOWED_ATTRIBUTES.items()},
    "*": {"class", "id", "title"},
    "a": {"href", "hreflang", "title"},
    "img": {"src", "alt", "title", "width", "height"},
}


def markdownify_safe(text):
    """
    Render markdown, then strip scripts, event handlers and `javascript:` links.
    Also the `MARKDOWNX_MARKDOWNIFY_FUNCTION`, so the editor preview shows what the site will show.
    :param text: The markdown source.
    :return: Html output.
    """
    return nh3.clean(markdownify(str(text or "")), attributes=ALLOWED_ATTRIBUTES)
