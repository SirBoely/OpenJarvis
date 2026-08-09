from __future__ import annotations

import json
import re
from pathlib import Path

profile = json.loads(Path('docs/role-skills/project-skill-profile.json').read_text(encoding='utf-8'))
errors: list[str] = []
required = ['SKILL-005', 'SKILL-025', 'SKILL-035', 'SKILL-041', 'SKILL-050']
all_skills = [*profile.get('required_skills', []), *profile.get('domain_skills', [])]

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
if len(set(all_skills)) != len(all_skills):
    errors.append('duplicate skill binding')

if errors:
    print('ROLE_SKILL_PROFILE=FAIL')
    for error in errors:
        print(f'- {error}')
    raise SystemExit(1)

print('ROLE_SKILL_PROFILE=PASS')
print(f'ACTIVE_SKILLS={len(all_skills)}')
