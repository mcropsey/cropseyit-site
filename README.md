# cropseyit-site

Source for the Cropsey IT Solutions website. Plain static HTML: no framework, no build step
except the blog generator. The live site is served from `/var/www/html`.

## Where the labs are

Each lab set is **one HTML page** in the repo root. A page holds every lab in that set, so
"Lab 1" or "Lab 5" refers to a section inside a page, not to a file.

> **Note on GitHub's file list:** the text GitHub shows next to each file is the message of the
> **last commit that changed that file**, not a description of the file. For example,
> `litellm.html` might show "Lab 5: ..." because the latest edit was in Lab 5 of that page.

| File | What it is |
|---|---|
| `index.html` | Home page. Links to the two lab workbooks and the blog. |
| `rhcsa.html` | **RHCSA Lab Workbook**: Labs 1–25 for a two-server RHEL 9/10 setup (EX200 practice). |
| `lab-diagram.html` | RHCSA lab diagram: the three VMs (server1, server2, utility) and what each one runs. Goes with `rhcsa.html`. |
| `cheatsheet.html` | RHCSA cheat sheet: one-page command reference taken from `rhcsa.html`. |
| `litellm.html` | **LiteLLM Gateway Labs**: Labs 0–11 on chat apps and AI agents through a LiteLLM gateway on rootful Podman. |
| `blog/` | Generated blog: `index.html`, `feed.xml` and one page per post. **Don't edit these files**; they're rebuilt from `posts/`. |
| `posts/*.md` | Blog posts in Markdown (the source for `blog/`). |
| `tools/` | Generators and the Python programs used by the LiteLLM labs (see below). |
| `favicon.png`, `logo.*` | Site images. |

### RHCSA Lab Workbook (`rhcsa.html`)

1. Network Configuration
2. DNF Repository from utility
3. Apache: move DocumentRoot + TCP/82 under SELinux & firewalld
4. Users & Groups
5. Collaboration Directory with SGID
6. NFS Client: Static Mounts & autofs
7. Scheduling with cron and at
8. File ACLs
9. Time Sync with chrony
10. Find & Copy Large Files
11. Create User with Specific UID
12. Archive & Compress
13. Default umask for natasha
14. Default Password Expiration
15. Passwordless sudo for admin
16. Script: Find & Copy Small Files
17. Root Password Reset via init=/bin/bash
18. LVM: VG datastore, LV database, mounted by UUID
19. Swap
20. Extend the LV
21. tuned & Process Priority
22. Flatpak: Install & Remove Applications
23. Passwordless SSH Between server1 and server2
24. Diagnostics Drill: ss, journalctl, ausearch
25. Grow the Root Filesystem After Enlarging the VM Disk

Related pages: `lab-diagram.html` (the lab setup) and `cheatsheet.html` (quick reference).

### LiteLLM Gateway Labs (`litellm.html`)

0. Reference: Setting Up LiteLLM (only if you need to)
1. Connect to the Gateway
2. Chat Through the Gateway: curl and Python
3. Virtual Keys: One Key per App
4. A Chat Web UI: Open WebUI on Podman
5. Agent 1: Your First Tool-Using Agent
6. Agent 2: Run Agents as Always-On Services
7. Agent 3: Publish Agents Through the Gateway (A2A)
8. Agent 4: Tools from an MCP Server, Through the Gateway
9. Agent 5: A Coordinator That Delegates to Other Agents
10. A Coding Agent Through the Gateway: opencode
11. Operate It: Reboots, Logs, Usage, Kill Switches, Upgrades

The labs publish these Python programs. They are kept in `tools/litellm-src/` and embedded in the page:
`chat.py`, `lab_tools.py`, `agent.py`, `a2a_server.py`, `mcp_agent.py`, `coordinator.py`.

## Tools

- `tools/gen_blog.py`: builds `blog/` from `posts/*.md`. Run `python3 tools/gen_blog.py`
  after adding or editing a post.
- `tools/gen_litellm.py`: the original generator for `litellm.html`. It copies the CSS and JS from
  `rhcsa.html` and the programs from `tools/litellm-src/`.
  **Stale since 2026-10-06:** since then, `litellm.html` has been edited by hand, so the
  generator no longer matches it. **Don't run it against the live repo**, because it would
  overwrite those edits. Edit `litellm.html` directly.

The lab pages share one style. `rhcsa.html` holds the main `<style>` and `<script>`.

## Workflow

```bash
cd ~/cropseyit-site
# edit files (or add posts/<slug>.md, then: python3 tools/gen_blog.py)
sudo cp -r *.html *.png *.webp blog /var/www/html/   # deploy
git add -A && git commit -m "..." && git push         # publish source to GitHub
```

Each commit message starts with the workbook name, then the lab, so it makes sense when GitHub
shows it next to a file: `LiteLLM Lab 5: ...`, `RHCSA Lab 1: ...`, `Blog: ...`, `Home: ...`.
(Older commits just say `Lab N:`. Up to 2026-10-04 they are RHCSA; from 2026-10-05 on they are LiteLLM.)
To see a page's change history, run `git log --oneline -- litellm.html`.
