# Skills Directory

This directory contains custom Claude Code skills for extending capabilities.

## Creating New Skills

To create new skills, install the [skill-creator](https://github.com/anthropics/claude-code-skill-creator) plugin:

```bash
claude plugin add skill-creator
```

Then ask Claude to use its skill-creator skill to design, structure, and package new skills.

Skills are modular packages that extend Claude Code with specialized knowledge, workflows, and tools. Each skill consists of:

- **SKILL.md** (required): YAML frontmatter with name/description + markdown instructions
- **scripts/** (optional): Executable code for deterministic tasks
- **references/** (optional): Documentation loaded into context as needed
- **assets/** (optional): Files used in output (templates, boilerplate)

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
