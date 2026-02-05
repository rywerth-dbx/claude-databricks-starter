# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Databricks-related project with a custom skills directory for extending Claude Code capabilities.

## Repository Structure

```
/
├── .claude/                   # Claude Code configuration directory
│   └── skills/               # Custom skills directory
│       ├── README.md         # Skills documentation
│       └── skill-creator/    # Skill for creating and packaging new skills
│           ├── SKILL.md             # Main skill documentation
│           ├── scripts/
│           │   ├── init_skill.py     # Initialize new skill structure
│           │   ├── package_skill.py  # Package skill for distribution
│           │   └── quick_validate.py # Validate skill format
│           └── license.txt
└── CLAUDE.md                 # This file
```

## Skills Development

This repository includes the `skill-creator` skill for developing custom Claude Code skills.

### Creating a New Skill

1. **Initialize a skill structure:**
   ```bash
   python .claude/skills/skill-creator/scripts/init_skill.py <skill-name> --path .claude/skills/ [--resources scripts,references,assets] [--examples]
   ```

2. **Edit the skill:**
   - Update `SKILL.md` with proper YAML frontmatter (name, description)
   - Add scripts to `scripts/` for reusable code
   - Add references to `references/` for documentation
   - Add assets to `assets/` for templates and files

3. **Package the skill:**
   ```bash
   python .claude/skills/skill-creator/scripts/package_skill.py .claude/skills/<skill-name>
   ```
   This validates and creates a distributable `.skill` file.

### Skill Naming Conventions

- Use lowercase letters, digits, and hyphens only
- Prefer short, verb-led phrases (e.g., `pdf-editor`, `data-processor`)
- Keep under 64 characters
- Namespace by tool when needed (e.g., `gh-address-comments`)

## Development Commands

(To be added: build, test, lint commands for the main project)

## Architecture

(To be added: high-level architecture overview once code is written)

## Important Notes

- This repository is located at `/Users/ryan.werth/Documents/Databricks/ClaudeCodeDatabricks`
- Authentication with Databricks should be done using the `fe-databricks-tools:databricks-authentication` skill
- When working with Databricks features, consider using available skills like:
  - `fe-databricks-tools:databricks-query` for executing queries
  - `fe-databricks-tools:databricks-apps` for building full-stack apps
  - `fe-databricks-tools:databricks-lakebase` for database operations
  - `fe-databricks-tools:databricks-workspace-files` for exploring workspace files
