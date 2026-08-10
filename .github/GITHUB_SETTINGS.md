# GitHub Settings As Code

The repository's desired GitHub settings live in `repository-settings.yml` and
`rulesets/*.yml`. GitHub does not apply these files automatically. The Python
tooling validates them and applies them through GitHub's REST API.

Install the optional dependency group:

```bash
python -m pip install --editable '.[github-settings]'
```

Validate without contacting GitHub:

```bash
agents-github-settings validate
```

Preview drift before making changes:

```bash
agents-github-settings --repository GriffinBoris/Agents plan
```

Apply the reviewed plan:

```bash
agents-github-settings --repository GriffinBoris/Agents apply --yes
```

Export the current remote state as one YAML document:

```bash
agents-github-settings --repository GriffinBoris/Agents export
```

Authentication is read from `GH_TOKEN`, then `GITHUB_TOKEN`, and finally the
active `gh auth token`. Applying repository settings and rulesets requires a
token with repository Administration write permission. The tool creates or
updates configured rulesets by name and never deletes an unconfigured remote
ruleset.
