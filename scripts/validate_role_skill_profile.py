from __future__ import annotations

import json
import re
from pathlib import Path

profile = json.loads(Path('docs/role-skills/project-skill-profile.json').read_text(encoding='utf-8'))
skill_contract = Path('docs/role-skills/SKILL.md').read_text(encoding='utf-8')
errors: list[str] = []
required = ['SKILL-005', 'SKILL-025', 'SKILL-035', 'SKILL-041', 'SKILL-050']
all_skills = [*profile.get('required_skills', []), *profile.get('domain_skills', [])]
active_skill_set = set(all_skills)

if profile.get('venue_id') != 'AGENT-OPENJARVIS':
    errors.append('unexpected venue_id')
if profile.get('repository') != 'SirBoely/OpenJarvis':
    errors.append('repository identity mismatch')
policy = profile.get('policy', {})
if policy.get('fail_closed') is not True:
    errors.append('fail_closed required')
if policy.get('independent_verifier_required') is not True:
    errors.append('independent verifier required')
if policy.get('runtime_capability_verification') is not True:
    errors.append('runtime capability verification required')
if policy.get('no_live_external_assumption') is not True:
    errors.append('live external capabilities must not be assumed')

for skill_id in required:
    if skill_id not in profile.get('required_skills', []):
        errors.append(f'missing required {skill_id}')
for skill_id in all_skills:
    if re.fullmatch(r'SKILL-\d{3}', skill_id) is None:
        errors.append(f'invalid skill id {skill_id}')
if len(active_skill_set) != len(all_skills):
    errors.append('duplicate active skill declaration')

bindings = profile.get('bindings')
bound_skills: list[str] = []
if not isinstance(bindings, dict) or not bindings:
    errors.append('bindings must be a non-empty object')
else:
    for binding_name, skill_ids in bindings.items():
        if not isinstance(binding_name, str) or not binding_name.strip():
            errors.append('binding names must be non-empty strings')
        if not isinstance(skill_ids, list) or not skill_ids:
            errors.append(f'binding {binding_name!r} must contain at least one skill')
            continue
        for skill_id in skill_ids:
            if not isinstance(skill_id, str) or re.fullmatch(r'SKILL-\d{3}', skill_id) is None:
                errors.append(f'binding {binding_name!r} has invalid skill id {skill_id!r}')
                continue
            if skill_id not in active_skill_set:
                errors.append(f'binding {binding_name!r} references undeclared {skill_id}')
            bound_skills.append(skill_id)

bound_skill_set = set(bound_skills)
for skill_id in required:
    if skill_id not in bound_skill_set:
        errors.append(f'required skill is not bound: {skill_id}')
for skill_id in active_skill_set:
    if skill_id not in bound_skill_set:
        errors.append(f'active skill is not bound: {skill_id}')

frontmatter_match = re.match(r'\A---\s*\n(?P<body>.*?)\n---\s*\n', skill_contract, re.DOTALL)
if frontmatter_match is None:
    errors.append('SKILL.md must start with YAML frontmatter')
else:
    frontmatter: dict[str, str] = {}
    for raw_line in frontmatter_match.group('body').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        key, value = line.split(':', 1)
        frontmatter[key.strip()] = value.strip().strip('"\'')

    name = frontmatter.get('name', '')
    description = frontmatter.get('description', '')
    if not name:
        errors.append('SKILL.md frontmatter requires name')
    elif re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) is None:
        errors.append('SKILL.md name must use lowercase alphanumeric hyphen format')
    if not description:
        errors.append('SKILL.md frontmatter requires description')

if errors:
    print('ROLE_SKILL_PROFILE=FAIL')
    for error in errors:
        print(f'- {error}')
    raise SystemExit(1)

print('ROLE_SKILL_PROFILE=PASS')
print(f'ACTIVE_SKILLS={len(all_skills)}')
print(f'BOUND_SKILLS={len(bound_skill_set)}')
print('SKILL_FRONTMATTER=PASS')
