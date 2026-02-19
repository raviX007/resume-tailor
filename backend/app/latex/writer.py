"""Write modified sections back into the .tex file."""

import re

from app.core.logger import logger


def replace_between_markers(
    tex: str,
    start_marker: str,
    end_marker: str,
    new_content: str,
) -> str:
    """Replace content between two markers, preserving the markers themselves."""
    pattern = re.compile(
        rf"(^{re.escape(start_marker)}\s*$\n)(.*?)(^{re.escape(end_marker)}\s*$)",
        re.DOTALL | re.MULTILINE,
    )
    result = pattern.sub(lambda m: m.group(1) + new_content + "\n" + m.group(3), tex)
    if result == tex:
        logger.warning(f"replace_between_markers: no change for {start_marker}")
    return result


def rebuild_skills_section(
    skills_dict: dict[str, str],
    category_order: list[str],
    injectable: dict[str, list[str]],
) -> str:
    """Rebuild the skills section in the specified category order,
    injecting any additional matched keywords.

    Args:
        skills_dict: {cat_name: raw LaTeX content} from parser
        category_order: ordered list of category names (most relevant first)
        injectable: {cat_name: [keyword, ...]} to append
    """
    lines = []
    for cat in category_order:
        if cat not in skills_dict:
            continue

        content = skills_dict[cat].strip()

        # Inject keywords into the \skillline{...}{THESE} content
        if injectable.get(cat):
            # Find the \skillline and append new keywords before the closing }
            m = re.search(r"(\\skillline\{[^}]*\}\{)([^}]*)\}", content)
            if m:
                existing = m.group(2)
                existing_lower = {s.strip().lower() for s in existing.split(",")}
                new_keywords = [
                    kw for kw in injectable[cat]
                    if kw.lower() not in existing_lower
                ]
                if new_keywords:
                    updated = existing.rstrip() + ", " + ", ".join(new_keywords)
                    content = content[:m.start()] + m.group(1) + updated + "}" + content[m.end():]
                    logger.info(f"Injected into {cat}: {new_keywords}")

        lines.append(f"% SKILL_CAT:{cat}")
        lines.append(content)

    return "\n".join(lines)


def rebuild_projects_section(
    projects_dict: dict[str, str],
    project_order: list[str],
) -> str:
    """Rebuild projects section in the specified order."""
    blocks = []
    for proj in project_order:
        if proj not in projects_dict:
            continue
        blocks.append(f"% PROJECT:{proj}")
        blocks.append(projects_dict[proj].strip())
        blocks.append("")  # blank line between projects

    return "\n".join(blocks).rstrip()
