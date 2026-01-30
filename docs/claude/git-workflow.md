# Git Workflow and Worktree Syncing

Complete guide for GitHub issues, commits, worktree template syncing, and documentation requirements.

## Table of Contents

- [GitHub Issue Workflow](#github-issue-workflow)
- [Syncing Changes with Worktree Template](#syncing-changes-with-worktree-template)
- [Git Commit Guidelines](#git-commit-guidelines)
- [Documentation Requirements for GitHub Issues](#documentation-requirements-for-github-issues)

---

## GitHub Issue Workflow

When working on GitHub issues, follow this workflow:

### Step 0: Review Issue Context (REQUIRED BEFORE STARTING)

**CRITICAL**: Before making any changes, you MUST review the issue against the current codebase:

1. **Read the issue carefully** - Understand what's being requested
2. **Search/explore affected files** - Use Glob/Grep/Read to understand current implementation
3. **Check for recent changes** - Review git history to see if issue was already addressed:
   ```bash
   git log --oneline --all --grep="<issue_keyword>" -10
   git log --oneline -- path/to/relevant/file.py -5
   ```
4. **Verify current architecture** - Patterns may have evolved since issue was created:
   - Check current RBAC implementation (decorator-based `roles` parameter)
   - Verify error handling approach (unified vs individual)
   - Check middleware stack and configuration
   - Look for refactored or renamed components
5. **Identify dependencies** - Find related functionality that might be affected
6. **Ask clarifying questions** - If issue is outdated or conflicts with current code

**Why this matters:**
- Prevents working on already-fixed issues
- Avoids using outdated patterns or assumptions
- Ensures compatibility with recent architectural changes
- Saves time by understanding context first

### Steps 1-7: Implementation and Deployment

1. **Fix the issue** - Make the necessary code changes
2. **Sync to worktree** - If changes affect `app/` or `tests/`, replicate to `.worktree/` template
3. **Commit to develop** - Commit changes to the `develop` branch with descriptive message including "Fixes #<issue_number>"
4. **Push to develop** - Push the commit to `origin/develop`
5. **Commit to worktree** - If worktree files were modified, commit them to the `project-template-develop` branch
6. **Push worktree** - Push worktree changes to `origin/project-template-develop`
7. **Close the issue** - Use `gh issue close <number>` with a descriptive comment

**CRITICAL**: Before committing and pushing changes to `.worktree/` folder, you MUST ask the user for confirmation first.

---

## Syncing Changes with Worktree Template

**CRITICAL RULE**: When making changes to code files in the main project (`app/`, `tests/`, etc.), you MUST replicate those changes to the corresponding files in the `.worktree/` cookiecutter template.

- Main project files in `app/` → `.worktree/{{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/`
- Main project files in `tests/` → `.worktree/{{cookiecutter.project_slug}}/tests/` (if applicable)
- **Exception**: Do NOT sync `CLAUDE.md` between main project and worktree (they have different purposes)

This ensures new projects generated from the cookiecutter template include all bug fixes and improvements.

### Cookiecutter Placeholder Requirements

**CRITICAL**: When syncing files to `.worktree/`, you MUST replace project-specific references with cookiecutter placeholders:

1. **Import statements** - Replace `app.` with `{{cookiecutter.module_name}}.`:
   ```python
   # Main project
   from app.api.ws.websocket import PackageAuthWebSocketEndpoint

   # Worktree template
   from {{cookiecutter.module_name}}.api.ws.websocket import PackageAuthWebSocketEndpoint
   ```

2. **Test patch paths** - Use cookiecutter placeholders in mock paths:
   ```python
   # Main project
   with patch("app.api.ws.consumers.web.rate_limiter") as mock:

   # Worktree template
   with patch("{{cookiecutter.module_name}}.api.ws.consumers.web.rate_limiter") as mock:
   ```

3. **Project-specific code** - Replace with generic template equivalents:
   ```python
   # Main project uses Author model
   PkgID.GET_AUTHORS
   from app.repositories.author_repository import AuthorRepository

   # Worktree template uses generic test handler
   PkgID.TEST_HANDLER
   # No project-specific repository imports
   ```

4. **API method calls** - Template may use different method names:
   ```python
   # Main project (current)
   ResponseModel.success(pkg_id, req_id, data={})

   # Worktree template (if different)
   ResponseModel.ok_msg(pkg_id, req_id, data={})
   ```

5. **Configuration patterns** - Template may have evolved (check before syncing):
   - RBAC: Uses decorator-based `roles` parameter (no external config file)
   - Error handling: Check for unified patterns
   - Middleware: Verify middleware stack matches template

### Verification Steps

- Use `sed` or similar to replace all `"app\.` with `"{{cookiecutter.module_name}}.`
- Search for hardcoded project names (e.g., "Author", "Book")
- Verify enum values match template (e.g., `PkgID.TEST_HANDLER`)
- Check that method signatures match template's current implementation
- Test generated project after syncing to ensure it works

---

## Git Commit Guidelines

When committing changes:
- Use conventional commit format: `fix:`, `feat:`, `refactor:`, etc.
- Include `Fixes #<issue_number>` in the commit message if closing an issue
- Always include the Claude Code footer:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```
- For worktree commits, clearly indicate it's syncing changes from the main project

---

## Documentation Requirements for GitHub Issues

**CRITICAL**: When creating GitHub issues, ALWAYS include documentation update requirements in the acceptance criteria.

### Required Documentation Checks

For EVERY new GitHub issue, the acceptance criteria MUST include:

1. **Documentation Impact Assessment**:
   - [ ] Check if CLAUDE.md needs updates
   - [ ] Check if docs_site/ needs updates
   - [ ] Check if README.md needs updates
   - [ ] Check if inline code comments need updates

2. **Specific Documentation Tasks**:
   - List specific files that need documentation updates
   - Specify what sections need to be added/modified
   - Include examples of correct vs incorrect documentation

3. **Documentation Verification**:
   - [ ] All code examples in documentation reflect actual implementation
   - [ ] No outdated patterns or deprecated methods in docs
   - [ ] Architecture diagrams updated if structural changes made

### Documentation Update Checklist by Change Type

**For API Changes** (new endpoints, modified signatures):
- [ ] Update `docs_site/api-reference/http-api.md` or `websocket-api.md`
- [ ] Update CLAUDE.md examples if pattern is reusable
- [ ] Add/update docstrings with examples

**For Architecture Changes** (new patterns, refactored components):
- [ ] Update `docs_site/architecture/overview.md`
- [ ] Update CLAUDE.md architecture section
- [ ] Update relevant design pattern guides
- [ ] Update Mermaid diagrams if flow changes

**For New Features** (handlers, middleware, utilities):
- [ ] Add guide to `docs_site/guides/`
- [ ] Update CLAUDE.md with usage examples
- [ ] Update quickstart if feature is core functionality
- [ ] Add configuration docs if feature is configurable

**For Bug Fixes** (especially for common issues):
- [ ] Update `docs_site/deployment/troubleshooting.md`
- [ ] Add warning/note to relevant guide sections
- [ ] Update FAQ if applicable

**For Testing Changes** (new patterns, centralized mocks):
- [ ] Update `docs_site/development/testing.md`
- [ ] Update CLAUDE.md testing section
- [ ] Document new test helpers/fixtures

**For Configuration Changes** (new settings, changed defaults):
- [ ] Update `docs_site/getting-started/configuration.md`
- [ ] Update `.env.*.example` files
- [ ] Add migration notes if breaking change

### Issue Template Example

When creating issues, include this section in acceptance criteria:

```markdown
## Documentation Updates Required

- [ ] Update CLAUDE.md section: [specify section and what to change]
- [ ] Update docs_site file: [specify file path and changes]
- [ ] Add code examples showing correct usage
- [ ] Update architecture diagram: [if applicable]
- [ ] Add troubleshooting entry: [if common issue]

**Files to update**:
1. `CLAUDE.md` lines XXX-YYY: [description]
2. `docs_site/guides/feature-name.md`: [description]
3. `app/path/to/file.py`: [update docstrings with examples]
```

### Common Documentation Mistakes to Avoid

❌ **Don't**:
- Create issues without documentation requirements
- Assume documentation is up-to-date after code changes
- Use outdated patterns in examples (e.g., Active Record vs Repository)
- Reference deleted files or deprecated methods
- Skip updating examples when refactoring

✅ **Do**:
- Always check if code examples match actual implementation
- Update documentation in the same commit/PR as code changes
- Verify all file paths and method signatures are current
- Include "before/after" examples for refactoring
- Cross-reference related documentation sections

### Documentation Consistency Review

Before closing ANY issue:
1. Run grep to find all mentions of changed components in docs
2. Verify code examples actually work (copy-paste test)
3. Check that terminology is consistent across all docs
4. Ensure architecture diagrams reflect current structure

**Example verification commands**:
```bash
# Find all documentation references to changed component
grep -r "MyChangedClass" CLAUDE.md docs_site/

# Find potentially outdated CRUD patterns
grep -r "Model\.create\|Model\.get_list" docs_site/ CLAUDE.md

# Find references to deleted files
grep -r "connection_registry\|ws_clients" docs_site/ CLAUDE.md
```

---

## Related Documentation

- [Architecture Guide](architecture-guide.md) - System design and patterns
- [Development Guide](development-guide.md) - Running the application
- [Code Quality Guide](code-quality-guide.md) - Linting and type safety
