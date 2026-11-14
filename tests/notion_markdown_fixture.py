"""Render physical child tags like Notion v2, without changing legacy API fixtures."""


def page_markdown(api, id):
    data = dict(api.markdown[id])
    tags = []
    seen = set()

    def children(parent):
        if parent in seen:
            return
        seen.add(parent)
        for block in api.children.get(parent, []):
            type = block["type"]
            if type in {"child_page", "child_database"}:
                tag = "page" if type == "child_page" else "database"
                tags.append(f'<{tag} url="https://app.notion.com/p/{block["id"]}">Child</{tag}>')
            elif block.get("has_children"):
                children(block["id"])

    children(id)
    if tags:
        data["markdown"] += "\n" + "\n".join(tags)
    return data
