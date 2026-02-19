"""Parse a .tex resume using comment markers.

Markers (inserted by the resume analyzer LLM):
  % SUMMARY_START / % SUMMARY_END
  % SKILLS_START / % SKILLS_END  (with % SKILL_CAT:name sub-markers)
  % EXPERIENCE_START / % EXPERIENCE_END  (with % EXP:name sub-markers)
  % PROJECTS_START / % PROJECTS_END  (with % PROJECT:name sub-markers)
"""

import re

from app.models import ResumeSections
from app.core.logger import logger


def extract_between_markers(tex: str, start_marker: str, end_marker: str) -> str:
    """Extract content between two comment markers (exclusive of markers)."""
    pattern = re.compile(
        rf"^{re.escape(start_marker)}\s*$\n(.*?)^{re.escape(end_marker)}\s*$",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(tex)
    if m:
        return m.group(1)
    logger.warning(f"Markers not found: {start_marker} ... {end_marker}")
    return ""


def _parse_sub_blocks(content: str, prefix: str) -> dict[str, str]:
    """Parse content into named blocks using sub-markers like % SKILL_CAT:name."""
    blocks = {}
    current_name = None
    current_lines = []

    for line in content.split("\n"):
        match = re.match(rf"^% {re.escape(prefix)}:(\S+)", line)
        if match:
            if current_name is not None:
                blocks[current_name] = "\n".join(current_lines)
            current_name = match.group(1)
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        blocks[current_name] = "\n".join(current_lines)

    return blocks


def parse_resume_sections(tex: str) -> ResumeSections:
    """Parse a .tex file into named sections.

    Args:
        tex: The LaTeX content to parse (with comment markers).

    Returns:
        {
            "summary": "AI/LLM Engineer and Full-Stack Developer...",
            "skills": {"languages": "\\skillline{...}", "backend": "...", ...},
            "experience": {"company": "\\experienceentry{...}", ...},
            "projects": {"project_name": "\\projectentry{...}", ...},
        }
    """
    sections: ResumeSections = {
        "summary": "",
        "skills": {},
        "experience": {},
        "projects": {},
    }

    sections["summary"] = extract_between_markers(tex, "% SUMMARY_START", "% SUMMARY_END").strip()

    skills_content = extract_between_markers(tex, "% SKILLS_START", "% SKILLS_END")
    sections["skills"] = _parse_sub_blocks(skills_content, "SKILL_CAT")

    exp_content = extract_between_markers(tex, "% EXPERIENCE_START", "% EXPERIENCE_END")
    sections["experience"] = _parse_sub_blocks(exp_content, "EXP")

    projects_content = extract_between_markers(tex, "% PROJECTS_START", "% PROJECTS_END")
    sections["projects"] = _parse_sub_blocks(projects_content, "PROJECT")

    logger.debug(
        f"Parsed: {len(sections['skills'])} skill cats, "
        f"{len(sections['projects'])} projects, "
        f"{len(sections['experience'])} experience entries"
    )

    return sections


def get_skills_on_resume(sections: ResumeSections) -> dict[str, list[str]]:
    """Extract the list of skill keywords currently on the resume per category.

    Parses the \\skillline{Category}{skill1, skill2, ...} lines.
    """
    skills_on_resume = {}
    for cat, content in sections.get("skills", {}).items():
        # Match the skills inside \skillline{...}{THESE SKILLS}
        m = re.search(r"\\skillline\{[^}]*\}\{([^}]*)\}", content)
        if m:
            raw = m.group(1)
            skills_on_resume[cat] = [s.strip() for s in raw.split(",") if s.strip()]
        else:
            skills_on_resume[cat] = []
    return skills_on_resume
