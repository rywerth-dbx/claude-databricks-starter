# Skills Directory

This directory contains custom Claude Code skills for extending capabilities.

## Available Skills

### skill-creator

A meta-skill for creating and packaging new Claude Code skills. Use this skill when designing, structuring, or packaging skills with scripts, references, and assets.

**Key Features:**
- Initialize new skill structures with proper templates
- Validate skill format and structure
- Package skills for distribution

**Usage:**
```bash
# Create a new skill
python skill-creator/scripts/init_skill.py <skill-name> --path . --resources scripts,references,assets

# Validate and package a skill
python skill-creator/scripts/package_skill.py <skill-folder>
```

## Creating New Skills

Skills are modular packages that extend Claude Code with specialized knowledge, workflows, and tools. Each skill consists of:

- **SKILL.md** (required): YAML frontmatter with name/description + markdown instructions
- **scripts/** (optional): Executable code for deterministic tasks
- **references/** (optional): Documentation loaded into context as needed
- **assets/** (optional): Files used in output (templates, boilerplate)

See `skill-creator/SKILL.md` for complete guidance on creating effective skills.

## Skill Structure Example

```
my-skill/
├── SKILL.md            # Required: metadata + instructions
├── scripts/            # Optional: executable code
│   └── process.py
├── references/         # Optional: documentation
│   └── api-docs.md
└── assets/             # Optional: templates/files
    └── template.html
```
