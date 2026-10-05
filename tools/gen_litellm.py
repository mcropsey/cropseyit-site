#!/usr/bin/env python3
"""Build litellm.html (LiteLLM AI Gateway Lab Workbook) in the style of rhcsa.html.

Usage: python3 tools/gen_litellm.py [SITE_DIR]
Reads rhcsa.html for the shared <style> and <script>, writes litellm.html. Edit the
lab content here, regenerate, then copy litellm.html to /var/www/html.
"""
import html
import os
import re
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rh = open(f'{SITE}/rhcsa.html', encoding='utf-8').read()
STYLE = re.search(r'<style>.*?</style>', rh, re.S).group(0)
SCRIPT = re.search(r'<script>.*?</script>', rh, re.S).group(0)

e = html.escape


def code(src):
    """Escape a code block and dim full-line and trailing '  # ' comments."""
    out = []
    for line in src.strip('\n').split('\n'):
        s = line.lstrip()
        if s.startswith('#') and not s.startswith('#!'):
            out.append(f'<span class="c">{e(line)}</span>')
            continue
        m = re.search(r'\s{2,}# ', line)
        if m:
            out.append(e(line[:m.start()]) + f'<span class="c">{e(line[m.start():])}</span>')
        else:
            out.append(e(line))
    return ('<div class="term"><button class="copy" type="button" aria-label="Copy commands">Copy</button>'
            '<pre><code>' + '\n'.join(out) + '</code></pre></div>')


def ul(items):
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def table(head, rows):
    h = ''.join(f'<th>{c}</th>' for c in head)
    b = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<div class="tablewrap"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def goal(t, label='Goal'):
    return f'<p class="goal"><span>{label}</span>{t}</p>'


def h3(t):
    return f'<h3>{t}</h3>'


def p(t):
    return f'<p>{t}</p>'


def warn(t):
    return f'<p class="callout warn"><strong>Warning:</strong> {t}</p>'


def note(t, label='Note:'):
    return f'<p class="callout note"><strong>{label}</strong> {t}</p>'


LABS = []


def lab(n, title, hosts, *parts):
    LABS.append((n, title))
    body = ''.join(parts)
    return f'''<section class="lab" id="lab-{n}" data-lab="{n}">
  <header class="labhead">
    <div class="labnum" aria-hidden="true">{n}</div>
    <div class="labtitle">
      <h2>Lab {n}: {e(title)}</h2>
      <span class="hosts">{hosts}</span>
    </div>
    <label class="done"><input type="checkbox" data-done="{n}"> Done</label>
  </header>
  {body}
  <a class="top" href="#top">Back to top</a>
</section>
'''


C = '<code>{}</code>'.format

# ---------------------------------------------------------------- overview
overview = f'''<section class="intro" id="overview">
  <h1>LiteLLM AI Gateway Labs</h1>
  <p class="sub">Hands-on labs for running an AI gateway in a two-host home lab: one API for many models, fallbacks, virtual keys and budgets, caching, guardrails, observability, MCP, Claude Code and A2A agents.</p>
  <p>Hosts: <strong>docker</strong> = 192.168.1.100 (Postgres, Redis, Langfuse, the A2A agent) | <strong>gateway</strong> = 192.168.1.101 (an <em>existing</em> LiteLLM proxy on port 4000) | <strong>workstation</strong> = wherever you run curl, jq and the check scripts.</p>
  <p>These labs assume LiteLLM is already running and add to it rather than replacing it. If you don&#x27;t have one yet, Lab 0 installs it. Lab 1 is read-only, Lab 2 only touches .100, and Lab 3 is the one change window on .101, with a backup taken first and a rollback in <a href="#readme">Appendix B</a>. Labs 4&ndash;13 exercise what Lab 3 turned on, and each ends with a small check script so you can re-run every lab at once (<a href="#runner">Appendix A</a>).</p>
  <h2>What runs where</h2>
  <p>Only LiteLLM needs to exist before you start, and Lab 0 installs it if it doesn&#x27;t. You build everything on .100 during the labs.</p>
  {table(['Host', 'Service', 'Port', 'Set up in', 'Used by'], [
      ['192.168.1.101', 'LiteLLM proxy + admin UI (<code>/ui</code>)', '4000', '<strong>Already running</strong>, or install it in Lab 0; config changed in Lab 3', 'every lab'],
      ['192.168.1.100', 'Postgres 16 (virtual keys, teams, spend logs)', '5432', 'Lab 2, <strong>skip</strong> if Lab 1 shows <code>&quot;db&quot;: &quot;connected&quot;</code>', 'Labs 3, 6, 9'],
      ['192.168.1.100', 'Redis 7 (response cache)', '6379', 'Lab 2', 'Labs 3, 7'],
      ['192.168.1.100', 'Langfuse web', '3000', 'Lab 9, Part B (optional)', 'Lab 9'],
      ['192.168.1.100', 'A2A Hello World agent', '9999', 'Lab 12', 'Lab 12'],
      ['internet', 'OpenAI, Anthropic, mcp.deepwiki.com', '443', 'Nothing to install; you need OpenAI and Anthropic API keys', 'Labs 4&ndash;12'],
  ])}
  <h2>Ground rules</h2>
  <ul>
    <li><strong>Look before you change.</strong> Don&#x27;t modify or restart the existing LiteLLM until you&#x27;ve read its config (Lab 1) and backed it up (Lab 3).</li>
    <li><strong>Never print a key in full.</strong> Read secrets with <code>read -rsp</code> so they stay out of shell history, and show only the last four characters: <code>echo &quot;****${{KEY: -4}}&quot;</code>.</li>
    <li><strong>Pin every image.</strong> No <code>latest</code>, <code>main-stable</code> or bare major tags. LiteLLM had a PyPI supply-chain incident in March 2026, so know exactly which build you run and pin it by version or digest.</li>
    <li><strong>Use real IPs across hosts.</strong> From .101, the services on .100 are <code>192.168.1.100</code>. Inside a container, <code>localhost</code> and <code>host.docker.internal</code> point at that container or its own host, never at the other machine.</li>
    <li><strong>One phase at a time.</strong> Finish a lab, verify it, then move on. If something fails, find out whether it&#x27;s networking, config, version or license tier before you change anything.</li>
  </ul>
  <h2>What you need</h2>
  <ul>
    <li>SSH with sudo on both hosts. Docker with the Compose plugin on .100. LiteLLM on .101 (Docker, Podman, systemd or a venv; Lab 1 finds out which), or let Lab 0 install it.</li>
    <li>An OpenAI API key and an Anthropic API key for the <code>gpt-mini</code> and <code>claude-fast</code> aliases. No cloud keys? Point both aliases at local models instead (see Lab 3 notes); everything except the provider names still works.</li>
    <li>On the workstation: <code>curl</code>, <code>jq</code> and <code>bash</code>. Python 3 is optional (Lab 4).</li>
    <li>LiteLLM <strong>1.80 or newer</strong> for the A2A gateway. These labs were written against <strong>v1.103.0</strong>. All features used here are in the open-source build; none need an enterprise license.</li>
  </ul>
  <h2>Workstation setup (do this once per shell)</h2>
  <p>Every check script sources a shared <code>labs/common.sh</code>. Create it now, then export the gateway URL and master key in each new shell.</p>
  {code(r"""
mkdir -p ~/litellm-labs/labs && cd ~/litellm-labs
cat > labs/common.sh <<'EOF'
# labs/common.sh: sourced by every check script
GW=${GW:-http://192.168.1.101:4000}
: "${MK:?set the master key first: read -rsp 'Master key: ' MK; export MK}"
OUT=${TMPDIR:-/tmp}/litellm-lab.$$.json
HDR=${TMPDIR:-/tmp}/litellm-lab.$$.hdr
trap 'rm -f "$OUT" "$HDR"' EXIT
mask() { printf '****%s' "${1: -4}"; }
# chat KEY MODEL PROMPT [EXTRA_JSON]: prints the HTTP code; body in $OUT, headers in $HDR
chat() {
  local extra=${4:-}; [ -n "$extra" ] || extra='{}'
  curl -s -o "$OUT" -D "$HDR" -w '%{http_code}' "$GW/v1/chat/completions" \
    -H "Authorization: Bearer $1" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg m "$2" --arg p "$3" --argjson x "$extra" \
          '{model:$m, messages:[{role:"user", content:$p}]} + $x')"
}
# api METHOD PATH [JSON]: admin call with the master key
api() { curl -s -X "$1" "$GW$2" -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' ${3:+-d "$3"}; }
hdr() { grep -i "^$1:" "$HDR" | head -1 | cut -d' ' -f2- | tr -d '\r'; }
pass() { echo "PASS  $*"; exit 0; }
fail() { echo "FAIL  $*"; exit 1; }
EOF

export GW=http://192.168.1.101:4000
read -rsp 'Master key: ' MK; echo; export MK
echo "master key ****${MK: -4}"
""")}
  <h2>Lab order &amp; dependencies</h2>
  {table(['Lab', 'Needs first', 'Notes'], [
      ['0 Install', 'none', 'Only if LiteLLM isn&#x27;t running yet; gives it its own Postgres on .101'],
      ['1 Discover', 'none', 'Read-only; tells you which parts of Labs 2&ndash;3 you can skip'],
      ['2 Services on .100', '1', 'Postgres + Redis; skip Postgres if Lab 1 shows a working database'],
      ['3 Wire up LiteLLM', '1, 2', 'The only change to .101; adds models, cache, guardrail, MCP'],
      ['4&ndash;8, 10, 13', '3', 'Independent of each other; any order'],
      ['9 Observability', '3', 'Langfuse part is optional and needs ~4 GB free RAM on .100'],
      ['11 Claude Code', '3, 6', 'Uses a virtual key, so do Lab 6 first'],
      ['12 A2A', '3', 'Builds the agent on .100, registers it on .101'],
  ])}
</section>
'''


# ---------------------------------------------------------------- lab 0
L0 = lab(0, 'Install LiteLLM (skip if it is already running)', '192.168.1.101',
    goal('install a LiteLLM proxy on .101 from scratch: a pinned image, its own Postgres for keys and spend logs, a master key, and the admin UI, all with Docker Compose (or Podman), so the rest of the labs have something to work on.'),
    note('If <code>curl http://192.168.1.101:4000/health/liveliness</code> already answers, skip to Lab 1. Lab 1 examines the gateway you already have, whoever installed it.', 'Already have LiteLLM?'),
    h3('1. A container runtime with Compose'),
    code(r"""
ssh "$USER"@192.168.1.101   # your login on .101

# Option A: Docker (a fresh Rocky/RHEL 9 or 10 host)
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
COMPOSE="sudo docker compose"

# Option B: the host already runs Podman (don't install Docker beside it)
sudo dnf -y install epel-release && sudo dnf -y install podman-compose
COMPOSE="sudo podman compose"

$COMPOSE version
"""),
    h3('2. Secrets in .env'),
    code(r"""
sudo mkdir -p /opt/litellm && cd /opt/litellm
sudo touch .env && sudo chmod 600 .env
read -rsp 'Admin UI password: ' UIP; echo
printf '%s\n' \
  "LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)" \
  "LITELLM_SALT_KEY=sk-$(openssl rand -hex 24)" \
  "POSTGRES_PASSWORD=$(openssl rand -hex 24)" \
  "UI_USERNAME=admin" "UI_PASSWORD=$UIP" | sudo tee .env >/dev/null
unset UIP
sudo sed -E 's/=(.*)(.{4})$/=****\2/' .env       # masked check
"""),
    h3('3. A starter config.yaml'),
    p('One mock model is enough to prove the install works, with no provider keys yet. Lab 3 adds the real models.'),
    code(r"""
sudo tee /opt/litellm/config.yaml >/dev/null <<'EOF'
model_list:
  - model_name: echo-test             # answers without calling any provider
    litellm_params:
      model: openai/echo-test
      mock_response: "Hello from LiteLLM. The install works."

litellm_settings:
  drop_params: true

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
EOF
"""),
    h3('4. compose.yml: LiteLLM + Postgres'),
    code(r"""
sudo tee /opt/litellm/compose.yml >/dev/null <<'EOF'
name: litellm
services:
  litellm:
    image: ghcr.io/berriai/litellm:v1.103.3
    restart: unless-stopped
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql://litellm:${POSTGRES_PASSWORD}@db:5432/litellm
    ports: ["0.0.0.0:4000:4000"]
    volumes:
      - ./config.yaml:/app/config.yaml:ro,Z
    depends_on:
      db:
        condition: service_healthy

  db:
    image: docker.io/library/postgres:16.15
    restart: unless-stopped
    environment:
      POSTGRES_USER: litellm
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: litellm
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U litellm -d litellm"]
      interval: 10s
      retries: 5

volumes:
  pgdata:
EOF
"""),
    h3('5. Start it'),
    code(r"""
cd /opt/litellm
$COMPOSE up -d
$COMPOSE logs -f litellm 2>&1 | grep -m1 -E 'Uvicorn running|Error|Traceback'    # first start: 1-2 min of DB migrations
$COMPOSE ps
"""),
    h3('Verify (from the workstation)'),
    code(r"""
GW=http://192.168.1.101:4000
curl -s $GW/health/liveliness; echo                    # "I'm alive!"
curl -s $GW/health/readiness | jq '{status, db}'        # db: "connected"
curl -s $GW/openapi.json | jq -r .info.version          # 1.103.3
read -rsp 'Master key (from /opt/litellm/.env): ' MK; echo; export MK GW
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model":"echo-test","messages":[{"role":"user","content":"hi"}]}' | jq -r '.choices[0].message.content'
"""),
    p('Then open <code>http://192.168.1.101:4000/ui</code> and log in as <code>admin</code> with the UI password you chose.'),
    h3('Notes &amp; gotchas'),
    warn('Pin the version. <code>v1.103.3</code> was the newest patch of the release these labs were tested on (v1.104.0 also existed). Don&#x27;t use <code>main-latest</code> or <code>main-stable</code>, and never <code>pip install litellm</code> without a version: compromised releases were published to PyPI in March 2026. For full reproducibility, pin the digest: <code>sudo docker image inspect --format &#x27;{{index .RepoDigests 0}}&#x27; ghcr.io/berriai/litellm:v1.103.3</code>.'),
    ul([
        'With this install, LiteLLM&#x27;s database runs right here on .101, so <strong>skip Postgres in Lab 2</strong> and set up only Redis there.',
        '<code>LITELLM_SALT_KEY</code> encrypts provider keys stored in the database. Set it before adding any model or credential in the UI and never change it afterwards, or the stored keys become unreadable.',
        'The master key must start with <code>sk-</code>. Keep it for admin work only; Labs 6, 11 and 12 show how to hand out limited virtual keys instead.',
        'Postgres isn&#x27;t published to the network; only LiteLLM reaches it, over the compose network by the name <code>db</code>.',
        'If the workstation can&#x27;t reach port 4000 but <code>curl localhost:4000/health/liveliness</code> works on .101, open the firewall: <code>sudo firewall-cmd --permanent --add-port=4000/tcp &amp;&amp; sudo firewall-cmd --reload</code>.',
        '<strong>Lab 3 with this install:</strong> secrets go in <code>/opt/litellm/.env</code> (not <code>litellm.env</code>). Instead of writing <code>run-litellm.sh</code>, add <code>- ./guard.py:/app/guard.py:ro,Z</code> under <code>volumes:</code> and run <code>$COMPOSE up -d</code>, which recreates the container whenever <code>.env</code> or <code>compose.yml</code> changes. After editing only <code>config.yaml</code>, run <code>$COMPOSE restart litellm</code>.',
        'Upgrade: change the image tag, then <code>$COMPOSE pull &amp;&amp; $COMPOSE up -d</code>. Back up first with <code>$COMPOSE exec db pg_dump -U litellm litellm &gt; litellm-$(date +%F).sql</code>. Uninstall: <code>$COMPOSE down</code> (add <code>-v</code> only to delete the database).',
        'No Docker or Podman? <code>pip install &#x27;litellm[proxy]==1.103.3&#x27;</code> in a venv, then <code>litellm --config config.yaml --port 4000</code>, works too. You&#x27;d run Postgres separately and write a systemd unit to keep it running.',
    ]),
)

# ---------------------------------------------------------------- lab 1
L1 = lab(1, 'Discover the Existing Gateway (read-only)', 'workstation and 192.168.1.101',
    goal('find out how LiteLLM is deployed on .101, which version it runs, where its config lives, and which pieces these labs need are missing, without changing anything.'),
    h3('1. Is it up, and which version?'),
    code(r"""
GW=http://192.168.1.101:4000
curl -s $GW/health/liveliness; echo                  # "I'm alive!"
curl -s $GW/health/readiness | jq                     # "db": "connected" means Postgres is wired up
curl -s $GW/openapi.json | jq -r .info.version        # the LiteLLM version, no key needed
"""),
    h3('2. How is it deployed?'),
    code(r"""
ssh "$USER"@192.168.1.101   # your login on .101
sudo docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null
sudo podman ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null
systemctl list-units --all --no-pager | grep -i litellm   # systemd unit or Podman quadlet?
pgrep -af 'litellm|uvicorn'                               # pip/venv install shows up here
"""),
    p('If it&#x27;s a container, set two variables from that output and inspect it:'),
    code(r"""
CTR="sudo podman"        # or CTR="sudo docker"
C=litellm                # container name from the ps output
$CTR inspect $C --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
$CTR inspect $C --format 'image={{.Config.Image}}  cmd={{json .Config.Cmd}}  restart={{.HostConfig.RestartPolicy.Name}}'
$CTR inspect $C --format 'networks: {{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
$CTR image inspect "$($CTR inspect $C --format '{{.Image}}')" --format '{{index .RepoDigests 0}}'
"""),
    p('The mount whose destination is <code>/app/config.yaml</code> (or whatever <code>--config</code> points at) is the file you&#x27;ll edit in Lab 3. Note the networks too: if LiteLLM reaches its database by container name, the recreated container must join the same network.'),
    h3('3. Environment and config, masked'),
    code(r"""
$CTR inspect $C --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -E 'KEY|SECRET|PASSWORD|TOKEN|_URL|_BASE|HOST' \
  | sed -E 's/=(.*)(.{4})$/=****\2/'

CFG=/opt/litellm/config.yaml       # the Source path of the config mount
sudo sed -E '/os\.environ\//!s/((key|password|secret|token)[a-z_]*:[[:space:]]*)[^[:space:]#]+/\1****/I' "$CFG"
sudo grep -nE 'master_key|database_url|cache|redis|guardrails|mcp_servers|callbacks|fallbacks' "$CFG"
"""),
    h3('4. Call it'),
    code(r"""
# back on the workstation
read -rsp 'Master key: ' MK; echo; export MK GW
curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[].id'
M=$(curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[0].id')   # or pick one from the list
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hi in five words.\"}]}" \
  | jq -r '.choices[0].message.content'
"""),
    h3('5. Gap report'),
    p('Fill this in from what you found. Anything marked missing is what Labs 2 and 3 add.'),
    table(['Lab', 'Needs', 'How to check'], [
        ['4 Unified API', 'two providers in <code>model_list</code>', '<code>/v1/models</code>'],
        ['5 Fallbacks / LB', '<code>router_settings.fallbacks</code>', 'grep the config'],
        ['6 Keys, teams, budgets', 'master key <strong>and</strong> a database', 'readiness shows <code>&quot;db&quot;: &quot;connected&quot;</code>'],
        ['7 Caching', 'Redis + <code>cache: true</code>', '<code>/cache/ping</code> (fails without a cache)'],
        ['8 Guardrail', '<code>guardrails:</code> + guard.py', '<code>/guardrails/list</code>'],
        ['9 Observability', 'database (spend logs); Langfuse optional', '<code>/spend/logs</code>'],
        ['10 MCP', '<code>mcp_servers:</code>', '<code>/v1/mcp/server</code>'],
        ['11 Claude Code', '<code>/v1/messages</code> route (any 1.6x+ build)', '<code>openapi.json</code>'],
        ['12 A2A', 'v1.80+ (<code>/a2a/{agent_id}</code>)', '<code>jq -r \'.paths | keys[]\' | grep a2a</code> on openapi.json'],
        ['13 Health / UI', 'master key; UI needs the database', '<code>/health</code>, <code>/ui</code>'],
    ]),
    h3('Notes &amp; gotchas'),
    warn('Check the version against the LiteLLM security advisories. After the March 2026 PyPI incident, treat any LiteLLM installed with an unpinned <code>pip install litellm</code> in that window as suspect, and rotate any keys that host held. A floating image tag such as <code>main-stable</code> or <code>main-latest</code> isn&#x27;t compromised by itself, but you can&#x27;t tell which build you&#x27;ll get on the next pull. Record the digest from step 2; Lab 3 pins it.'),
    ul([
        '<code>/health/liveliness</code> and <code>/health/liveness</code> are both valid. Neither needs a key.',
        'A master key in the config (<code>general_settings.master_key</code>) or env (<code>LITELLM_MASTER_KEY</code>) must start with <code>sk-</code>.',
        'Without a database, LiteLLM still proxies calls with the master key, but <code>/key/generate</code>, teams, budgets, spend logs and most of the admin UI fail with &quot;No connected db&quot;.',
        'The masking <code>sed</code> leaves <code>os.environ/NAME</code> references visible on purpose. They hold no secret, and you need them to know which env var feeds which model.',
        'Don&#x27;t open <code>/health</code> (without <code>/liveliness</code>) yet. It sends a real request to every model, which costs tokens and makes LM Studio or Ollama load each local model in turn.',
    ]),
)

# ---------------------------------------------------------------- lab 2
L2 = lab(2, 'Supporting Services on .100: Postgres & Redis', '192.168.1.100, tested from 192.168.1.101',
    goal('run Postgres 16 and Redis 7 on .100 with pinned tags, persistent volumes and generated passwords, published on 0.0.0.0 and reachable from .101.'),
    h3('1. Check Docker and the ports'),
    code(r"""
ssh "$USER"@192.168.1.100   # your login on .100
docker version --format 'engine {{.Server.Version}}'; docker compose version
sudo ss -ltnp | grep -E ':(5432|6379|3000|9999)\b'      # should print nothing
"""),
    h3('2. Write the .env and compose file'),
    code(r"""
mkdir -p ~/litellm-lab && cd ~/litellm-lab
umask 077
cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)
EOF

cat > docker-compose.yml <<'EOF'
name: litellm-lab
services:
  postgres:
    image: docker.io/library/postgres:16.15
    restart: unless-stopped
    environment:
      POSTGRES_USER: litellm
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: litellm
    ports: ["0.0.0.0:5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U litellm -d litellm"]
      interval: 10s
      retries: 5

  redis:
    image: docker.io/library/redis:7.4.11
    restart: unless-stopped
    user: redis
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD}
    command: ["sh", "-c", "exec redis-server --requirepass \"$$REDIS_PASSWORD\" --appendonly yes"]
    ports: ["0.0.0.0:6379:6379"]
    volumes: [redisdata:/data]
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a \"$$REDIS_PASSWORD\" --no-auth-warning ping | grep -q PONG"]
      interval: 10s
      retries: 5

volumes:
  pgdata:
  redisdata:
EOF
"""),
    h3('3. Start and check'),
    code(r"""
docker compose up -d
docker compose ps                                      # both "healthy" after ~10 s
sudo ss -ltn | grep -E '0.0.0.0:(5432|6379)'
"""),
    h3('Verify from .101'),
    p('Test from the gateway host the same way LiteLLM will connect: from a container on .101, by IP, with the password.'),
    code(r"""
ssh "$USER"@192.168.1.101   # your login on .101
for p in 5432 6379; do timeout 3 bash -c "</dev/tcp/192.168.1.100/$p" && echo "$p open" || echo "$p CLOSED"; done

read -rsp 'Redis password (from .100 ~/litellm-lab/.env): ' RP; echo
sudo podman run --rm -e RP="$RP" docker.io/library/redis:7.4.11 \
  sh -c 'redis-cli -h 192.168.1.100 -a "$RP" --no-auth-warning ping'          # PONG
sudo podman run --rm docker.io/library/postgres:16.15 pg_isready -h 192.168.1.100 -U litellm
unset RP
"""),
    h3('Notes &amp; gotchas'),
    ul([
        '<strong>Skip Postgres if Lab 1 showed <code>&quot;db&quot;: &quot;connected&quot;</code>.</strong> Pointing LiteLLM at a new, empty database starts you over with no keys, teams or spend history. Delete the <code>postgres</code> service from the file in that case.',
        'Ports published by Docker usually bypass firewalld, because Docker inserts its own forwarding rules. If the <code>/dev/tcp</code> test says CLOSED anyway, open them: <code>sudo firewall-cmd --permanent --add-port={5432,6379,3000,9999}/tcp &amp;&amp; sudo firewall-cmd --reload</code>.',
        '<code>$$REDIS_PASSWORD</code> is deliberate: Compose turns <code>$$</code> into a literal <code>$</code>, so the shell inside the container expands it and the password never appears in <code>docker inspect</code>&#x27;s command line.',
        'The tags were current when this was written. Moving to a newer patch (16.x, 7.4.x) is safe; moving Postgres to a new major version is not, because the data directory format changes.',
        'Use <code>openssl rand -hex</code> rather than <code>-base64</code>. Base64 output can contain <code>/</code> and <code>+</code>, which break the <code>DATABASE_URL</code> in Lab 3 unless URL-encoded.',
        'Redis is published with a password but no TLS, which is fine on an isolated lab LAN. For anything else, bind it to the one interface .101 uses and add a firewall rule allowing only 192.168.1.101.',
    ]),
)

# ---------------------------------------------------------------- lab 3
L3 = lab(3, 'Wire Up LiteLLM: Models, Database, Cache, Guardrail, MCP', '192.168.1.101',
    goal('back up the running config, add two model aliases, the database, a fallback, the Redis cache, an SSN guardrail and the DeepWiki MCP server, then recreate LiteLLM on a pinned image and confirm it&#x27;s healthy.'),
    note('Installed with Lab 0? Follow the &quot;Lab 3 with this install&quot; note at the end of Lab 0 for steps 1, 3 and 6. These steps assume a container with the config file bind-mounted at <code>/app/config.yaml</code> and secrets in an env file, a common setup. For a systemd/venv install, the YAML is the same: put <code>guard.py</code> next to the config file, add the variables to the unit&#x27;s <code>EnvironmentFile</code>, and run <code>systemctl restart</code> instead of step 6.', 'Layout:'),
    h3('1. Back up everything you&#x27;re about to touch'),
    code(r"""
CTR="sudo podman"; C=litellm; D=/opt/litellm        # from Lab 1
TS=$(date +%Y%m%d-%H%M%S)
sudo cp -a $D/config.yaml   $D/config.yaml.bak-$TS
sudo cp -a $D/litellm.env   $D/litellm.env.bak-$TS 2>/dev/null
$CTR inspect $C | sudo tee $D/inspect.bak-$TS.json >/dev/null    # how it was run, for rollback
echo $TS | sudo tee $D/LAST_BACKUP
"""),
    h3('2. Make sure the env file holds every variable the container has'),
    p('A container&#x27;s environment is fixed when it&#x27;s created. If some variables were passed with <code>-e</code> instead of <code>--env-file</code>, recreating it in step 6 would quietly drop them. This prints any variable that&#x27;s in the container but in neither the image nor the env file:'),
    code(r"""
names() { cut -d= -f1 | sed '/^$/d' | sort -u; }
$CTR inspect $C --format '{{range .Config.Env}}{{println .}}{{end}}' | names > /tmp/ctr.env
$CTR image inspect "$($CTR inspect $C --format '{{.Image}}')" \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | names > /tmp/img.env
sudo grep -vE '^\s*(#|$)' $D/litellm.env | names > /tmp/file.env
comm -23 /tmp/ctr.env /tmp/img.env | comm -23 - /tmp/file.env      # must print nothing
"""),
    h3('3. Add the new secrets (typed, never echoed)'),
    code(r"""
read -rsp 'OpenAI key: ' OAK; echo
read -rsp 'Anthropic key: ' ANK; echo
read -rsp 'Redis password (from .100): ' RP; echo
printf '%s\n' "OPENAI_API_KEY=$OAK" "ANTHROPIC_API_KEY=$ANK" "REDIS_PASSWORD=$RP" \
  | sudo tee -a $D/litellm.env >/dev/null
unset OAK ANK RP

# Only if Lab 1 found no master key / no database:
#   echo "LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)" | sudo tee -a $D/litellm.env >/dev/null
#   read -rsp 'Postgres password: ' PP; echo
#   echo "DATABASE_URL=postgresql://litellm:$PP@192.168.1.100:5432/litellm" | sudo tee -a $D/litellm.env >/dev/null; unset PP

sudo chmod 600 $D/litellm.env
sudo grep -oE '^[A-Z_]+=' $D/litellm.env                  # names only, no values
"""),
    h3('4. Write the guardrail'),
    p('LiteLLM loads <code>guard.SSNGuard</code> from <code>guard.py</code> in the same directory as the config file. Lab 8 explains how it works.'),
    code(r"""
sudo tee $D/guard.py >/dev/null <<'EOF'
import re

from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail

SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def _texts(data):
    # every user-supplied string in a chat, messages or responses request
    for msg in data.get("messages") or []:
        content = msg.get("content")
        if isinstance(content, str):
            yield content
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    yield part["text"]
    if isinstance(data.get("input"), str):
        yield data["input"]


class SSNGuard(CustomGuardrail):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if any(SSN.search(t) for t in _texts(data)):
            raise HTTPException(
                status_code=400,
                detail={"error": "Blocked by ssn-guard: the prompt contains a US Social Security number."},
            )
        return data
EOF
sudo chmod 644 $D/guard.py
"""),
    h3('5. Edit config.yaml (merge, don&#x27;t replace)'),
    p('Run <code>sudo vi $D/config.yaml</code>. Add the two models to the end of your existing <code>model_list</code>, and merge the other blocks into any top-level keys you already have. Keep your existing models and settings.'),
    code(r"""
model_list:
  # ...your existing models stay above...
  - model_name: gpt-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY
  - model_name: claude-fast
    litellm_params:
      model: anthropic/claude-haiku-4-5-20251001
      api_key: os.environ/ANTHROPIC_API_KEY

litellm_settings:
  num_retries: 2              # retry the same deployment before falling back
  request_timeout: 120
  cache: true
  cache_params:
    type: redis
    host: 192.168.1.100       # the Docker host, never localhost
    port: 6379
    password: os.environ/REDIS_PASSWORD
    ttl: 600                  # seconds

router_settings:
  routing_strategy: simple-shuffle
  fallbacks:
    - gpt-mini: ["claude-fast"]

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL

guardrails:
  - guardrail_name: ssn-guard
    litellm_params:
      guardrail: guard.SSNGuard     # guard.py next to config.yaml, class SSNGuard
      mode: pre_call
      default_on: true

mcp_servers:
  deepwiki:
    url: https://mcp.deepwiki.com/mcp
    transport: http
"""),
    p('Check the YAML parses and review the diff before going further:'),
    code(r"""
TS=$(cat $D/LAST_BACKUP)
sudo diff -u $D/config.yaml.bak-$TS $D/config.yaml
$CTR exec -i $C python -c "import yaml,sys; yaml.safe_load(sys.stdin); print('YAML OK')" < <(sudo cat $D/config.yaml)
"""),
    h3('6. Recreate LiteLLM on a pinned image'),
    p('Env-file changes and new mounts only take effect in a new container, so <code>restart</code> isn&#x27;t enough. Save the run command as a script so it&#x27;s the single source of truth from now on. Paste the digest from Lab 1 into <code>IMG</code>, and list every network Lab 1 showed in <code>NETS</code>.'),
    code(r"""
sudo tee $D/run-litellm.sh >/dev/null <<'EOF'
#!/usr/bin/env bash
# Recreates the LiteLLM container. Rerun after editing litellm.env or upgrading IMG.
set -euo pipefail
IMG="ghcr.io/berriai/litellm@sha256:<digest-from-lab-1>"
NETS="--network podman"     # e.g. "--network docker_default --network podman" if the DB is a container
D=/opt/litellm
podman rm -f litellm 2>/dev/null || true
podman run -d --name litellm --restart=always $NETS \
  --env-file $D/litellm.env \
  -v $D/config.yaml:/app/config.yaml:ro,Z \
  -v $D/guard.py:/app/guard.py:ro,Z \
  -p 4000:4000 \
  "$IMG" --config /app/config.yaml --port 4000
EOF
sudo chmod 700 $D/run-litellm.sh
sudo $D/run-litellm.sh
sudo podman logs -f litellm 2>&1 | grep -m1 -E 'Uvicorn running|Error|Traceback'
"""),
    h3('Verify'),
    code(r"""
# workstation (with GW and MK exported)
curl -s $GW/health/liveliness; echo
curl -s $GW/health/readiness | jq '{status, db, cache, litellm_version}'
curl -s $GW/cache/ping -H "Authorization: Bearer $MK" | jq '{status, cache_type}'      # healthy / redis
curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[].id'              # gpt-mini, claude-fast + yours
curl -s $GW/guardrails/list -H "Authorization: Bearer $MK" | jq -r '.guardrails[].guardrail_name'
curl -s $GW/v1/mcp/server -H "Authorization: Bearer $MK" | jq -r '.[] | .server_name // .alias'
"""),
    h3('Notes &amp; gotchas'),
    warn('A YAML file may contain each top-level key only once. If you paste a second <code>litellm_settings:</code> under the first, the parser silently keeps only the last one and your earlier settings vanish. Merge into the existing block instead.'),
    ul([
        'Rollback is in <a href="#readme">Appendix B</a>: copy the <code>.bak-$TS</code> files back and rerun the script.',
        '<code>cache: true</code> caches every model, including any you already had. To make caching opt-in, add <code>mode: default_off</code> under <code>cache_params</code>; requests then opt in with <code>&quot;cache&quot;: {&quot;use-cache&quot;: true}</code>.',
        'If you already had <code>fallbacks:</code>, add <code>- gpt-mini: [&quot;claude-fast&quot;]</code> as another list item. Don&#x27;t start a second <code>fallbacks:</code> key.',
        'If the existing config has a literal <code>master_key: sk-...</code>, you can leave it. Moving it into the env file keeps it out of <code>config.yaml</code> and its backups.',
        'No cloud keys? Point the aliases at a local OpenAI-compatible server instead, e.g. <code>model: openai/&lt;local-model&gt;</code> plus <code>api_base: os.environ/LMSTUDIO_API_BASE</code>. Labs 4&ndash;8 work the same, though Lab 5&#x27;s fallback then goes from one local model to another.',
        '<code>:Z</code> relabels the mounted files for SELinux (Rocky/RHEL). Without it the container gets &quot;permission denied&quot; reading <code>guard.py</code>.',
        'Single-file bind mounts follow the inode. Some editors save by writing a new file, so the running container keeps reading the old one. Recreating with the script (or <code>podman restart</code>) picks up the new file.',
        'Startup errors to look for: <code>Could not import SSNGuard from guard</code> (missing mount or typo), <code>ConnectionError ... 6379</code> (Redis password or firewall), <code>P1001</code> (Prisma can&#x27;t reach Postgres).',
    ]),
)

# ---------------------------------------------------------------- lab 4
L4 = lab(4, 'Unified API: One Client, Two Providers', 'workstation → 192.168.1.101',
    goal('call OpenAI and Anthropic models through one OpenAI-format endpoint, changing only the model name.'),
    h3('Steps: curl'),
    code(r"""
for m in gpt-mini claude-fast; do
  curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$m\",\"messages\":[{\"role\":\"user\",\"content\":\"Who trained you? One sentence.\"}]}" \
    | jq -r --arg m "$m" '"\($m) -> \(.model): \(.choices[0].message.content)"'
done
"""),
    h3('Steps: Python with the OpenAI SDK'),
    code(r"""
python3 -m venv ~/litellm-labs/.venv && . ~/litellm-labs/.venv/bin/activate
pip install 'openai>=1.40,<3'
python3 - <<'EOF'
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ["GW"], api_key=os.environ["MK"])
for model in ("gpt-mini", "claude-fast"):
    r = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": "Name one planet."}], max_tokens=20)
    print(f"{model:12} {r.model:32} {r.choices[0].message.content}")
EOF
"""),
    h3('Check script'),
    code(r"""
cat > labs/04-unified.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
for m in gpt-mini claude-fast; do
  code=$(chat "$MK" "$m" "Reply with the single word: pong")
  [ "$code" = 200 ] || fail "$m returned HTTP $code: $(jq -r '.error.message // .' "$OUT" | head -c 160)"
  echo "  $m -> $(jq -r .model "$OUT"): $(jq -r '.choices[0].message.content' "$OUT" | head -c 40)"
done
pass "unified API: gpt-mini and claude-fast both answered"
EOF
chmod +x labs/04-unified.sh && labs/04-unified.sh
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'The response&#x27;s <code>model</code> field shows the real provider model (<code>gpt-4o-mini-2024-07-18</code>, <code>claude-haiku-4-5-20251001</code>), while the client only ever asked for an alias. That indirection is what lets you swap providers without touching clients.',
        'LiteLLM translates the request for Anthropic: the system prompt moves to Anthropic&#x27;s <code>system</code> field and <code>max_tokens</code> gets a default, because Anthropic requires one.',
        '<code>drop_params: true</code> in <code>litellm_settings</code> silently drops OpenAI-only parameters that a provider doesn&#x27;t support, instead of returning a 400.',
        'Response headers tell you what happened: <code>curl -sD - -o /dev/null ...</code> shows <code>x-litellm-model-id</code>, <code>x-litellm-response-cost</code> and <code>x-litellm-response-duration-ms</code>.',
    ]),
)

# ---------------------------------------------------------------- lab 5
L5 = lab(5, 'Fallbacks, Retries & Load Balancing', 'workstation → 192.168.1.101',
    goal('prove that a failing <code>gpt-mini</code> call falls back to <code>claude-fast</code>, then (optionally) spread one alias across two deployments.'),
    h3('Steps: forced fallback'),
    p('<code>mock_testing_fallbacks</code> makes the first deployment fail on purpose, without needing to break anything.'),
    code(r"""
curl -s -D /tmp/fb.hdr -o /tmp/fb.json $GW/v1/chat/completions \
  -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model":"gpt-mini","mock_testing_fallbacks":true,
       "messages":[{"role":"user","content":"Which model are you?"}]}'
jq -r .model /tmp/fb.json                                    # claude-haiku-4-5-20251001
grep -iE '^x-litellm-(attempted-fallbacks|model-group|model-id)' /tmp/fb.hdr
"""),
    h3('Stretch: load balancing'),
    p('Two entries with the same <code>model_name</code> form one model group, and the router spreads requests across them. Add a second <code>gpt-mini</code> deployment to <code>model_list</code>, then rerun <code>run-litellm.sh</code>:'),
    code(r"""
  - model_name: gpt-mini
    litellm_params:
      model: openai/gpt-4.1-mini
      api_key: os.environ/OPENAI_API_KEY
"""),
    code(r"""
for i in $(seq 1 8); do
  curl -s -D - -o /dev/null $GW/v1/chat/completions -H "Authorization: Bearer $MK" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"gpt-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"lb test $i $RANDOM\"}]}" \
    | grep -i '^x-litellm-model-id'
done | sort | uniq -c                                           # two different ids
"""),
    h3('Check script'),
    code(r"""
cat > labs/05-fallback.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
code=$(chat "$MK" gpt-mini "Say hi" '{"mock_testing_fallbacks": true}')
model=$(jq -r '.model // empty' "$OUT")
echo "  HTTP $code, answered by $model, attempted fallbacks: $(hdr x-litellm-attempted-fallbacks)"
[ "$code" = 200 ] && [[ $model == *claude* ]] && pass "fallback: gpt-mini -> $model" \
  || fail "fallback: expected a Claude answer, got HTTP $code model=$model"
EOF
chmod +x labs/05-fallback.sh && labs/05-fallback.sh
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'Order of operations: <code>num_retries</code> retries the same model group first, then <code>fallbacks</code> moves to the next group. Retries on a rate-limited provider just burn time, so keep them low.',
        'Fallbacks also fire on real errors: a wrong <code>OPENAI_API_KEY</code>, a 429, or a timeout. Try one by setting a deliberately bad key, recreating, and watching Claude answer.',
        'Other fallback types: <code>context_window_fallbacks</code> (prompt too long for the model) and <code>content_policy_fallbacks</code> (provider refused the content).',
        'Without <code>RANDOM</code> in the load-balancing prompts, the Redis cache from Lab 3 would answer repeats and you&#x27;d only see one deployment id.',
        'Other routing strategies include <code>least-busy</code>, <code>latency-based-routing</code> and <code>usage-based-routing-v2</code>. Some need Redis to share state across proxy instances.',
    ]),
)

# ---------------------------------------------------------------- lab 6
L6 = lab(6, 'Virtual Keys, Teams & Budgets', 'workstation → 192.168.1.101',
    goal('create a team with a tiny budget and a key limited to <code>gpt-mini</code> at 5 requests per minute, then trigger each control: a disallowed model, a 429, and a budget error.'),
    h3('1. Create the team and key'),
    code(r"""
TEAM=$(curl -s $GW/team/new -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"team_alias":"lab-team","max_budget":0.0002,"models":["gpt-mini"]}' | jq -r .team_id)
KEY=$(curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d "{\"team_id\":\"$TEAM\",\"key_alias\":\"lab-key\",\"models\":[\"gpt-mini\"],\"rpm_limit\":5}" | jq -r .key)
echo "team $TEAM  key ****${KEY: -4}"
"""),
    h3('2. Disallowed model'),
    code(r"""
curl -s -w '\nHTTP %{http_code}\n' $GW/v1/chat/completions -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"claude-fast","messages":[{"role":"user","content":"hi"}]}' | jq -Rr '. as $l | try (fromjson | .error.message) catch $l'
# ... not allowed to access model ...   HTTP 401
"""),
    h3('3. Rate limit (rpm_limit 5)'),
    code(r"""
for i in 1 2 3 4 5 6 7; do
  curl -s -o /dev/null -w '%{http_code} ' $GW/v1/chat/completions -H "Authorization: Bearer $KEY" \
    -H 'Content-Type: application/json' -d "{\"model\":\"gpt-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"count $i\"}]}"
done; echo                                                      # 200 200 200 200 200 429 429
"""),
    h3('4. Budget'),
    p('Wait a minute for the rate window to reset, then spend the $0.0002 with a few longer answers, staying under 5 rpm:'),
    code(r"""
sleep 60
for i in $(seq 1 15); do
  code=$(curl -s -o /tmp/b.json -w '%{http_code}' $GW/v1/chat/completions -H "Authorization: Bearer $KEY" \
    -H 'Content-Type: application/json' \
    -d '{"model":"gpt-mini","messages":[{"role":"user","content":"Write about 150 words on network routers."}]}')
  echo "request $i: $code"; [ "$code" = 200 ] || break; sleep 13
done
jq -r .error.message /tmp/b.json              # Budget has been exceeded! Team=... Current cost: ..., Max budget: 0.0002
curl -s "$GW/team/info?team_id=$TEAM" -H "Authorization: Bearer $MK" | jq '.team_info | {team_alias, spend, max_budget}'
"""),
    h3('Check script'),
    code(r"""
cat > labs/06-keys.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
TEAM=$(api POST /team/new '{"team_alias":"lab-check-team","max_budget":0.0002,"models":["gpt-mini"]}' | jq -r .team_id)
KEY=$(api POST /key/generate "$(jq -n --arg t "$TEAM" '{team_id:$t,key_alias:"lab-check-key",models:["gpt-mini"],rpm_limit:5}')" | jq -r .key)
cleanup() { api POST /key/delete "$(jq -n --arg k "$KEY" '{keys:[$k]}')" >/dev/null
            api POST /team/delete "$(jq -n --arg t "$TEAM" '{team_ids:[$t]}')" >/dev/null; rm -f "$OUT" "$HDR"; }
trap cleanup EXIT
[[ $KEY == sk-* ]] || fail "could not create team/key (is a database connected?)"
echo "  team $TEAM, key $(mask "$KEY")"

c=$(chat "$KEY" claude-fast hi)
[[ $c == 40[13] ]] || fail "disallowed model: expected 401/403, got $c"
echo "  disallowed model -> $c"

codes=""; for i in 1 2 3 4 5 6 7; do codes+="$(chat "$KEY" gpt-mini "count $i") "; done
echo "  7 quick requests -> $codes"
[[ $codes == *429* ]] || fail "rpm_limit 5 produced no 429"

echo "  waiting 61 s for the rate window..."; sleep 61
for i in $(seq 1 15); do
  c=$(chat "$KEY" gpt-mini "Write about 150 words on network routers."); [ "$c" = 200 ] || break; sleep 13
done
msg=$(jq -r '.error.message // empty' "$OUT")
echo "  budget -> $c ${msg:0:70}"
[[ $msg == *"Budget has been exceeded"* ]] || fail "expected a budget error, got $c"
pass "keys/teams: disallowed model, 429 and budget error all enforced"
EOF
chmod +x labs/06-keys.sh && labs/06-keys.sh                    # takes about 2 minutes
"""),
    h3('Cleanup'),
    code(r"""
curl -s $GW/key/delete  -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d "{\"keys\":[\"$KEY\"]}"
curl -s $GW/team/delete -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d "{\"team_ids\":[\"$TEAM\"]}"
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'Limits stack: a request must pass the key&#x27;s, the team&#x27;s and the user&#x27;s models, budgets and rate limits. The tightest one wins.',
        'Spend is recorded after each successful call and checked before the next, so you can go slightly over a budget. The request that crosses it succeeds; the one after it fails.',
        'Budgets are in US dollars, computed from LiteLLM&#x27;s price map. For local models with no price, set <code>input_cost_per_token</code>/<code>output_cost_per_token</code> in <code>model_info</code>, or every call costs $0 and no budget ever trips.',
        'Add <code>&quot;budget_duration&quot;: &quot;30d&quot;</code> to reset a budget on a schedule.',
        'The key is shown only once, at creation. LiteLLM stores a hash, so a lost key can&#x27;t be recovered, only regenerated.',
        'With a single proxy instance, rate limits are counted in memory. With several instances behind a load balancer, add Redis to <code>router_settings</code> so they share counters.',
        'Everything here can also be done in the admin UI at <code>http://192.168.1.101:4000/ui</code> under <strong>Teams</strong> and <strong>Virtual Keys</strong>.',
    ]),
)

# ---------------------------------------------------------------- lab 7
L7 = lab(7, 'Response Caching with Redis', 'workstation → 192.168.1.101, cache on 192.168.1.100',
    goal('show that a repeated identical request is answered from Redis on .100: faster, at no cost, and marked with an <code>x-litellm-cache-key</code> header.'),
    h3('Steps'),
    code(r"""
Q="{\"model\":\"gpt-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"Name three primes. $(date +%s)\"}]}"
for i in 1 2; do
  echo "--- call $i"
  curl -s -D - -o /dev/null $GW/v1/chat/completions -H "Authorization: Bearer $MK" \
    -H 'Content-Type: application/json' -d "$Q" \
    | grep -iE '^x-litellm-(cache-key|response-cost|response-duration-ms)'
done
"""),
    p('Call 2 carries <code>x-litellm-cache-key</code>, a much lower duration, and a cost of 0. Look at the entry in Redis:'),
    code(r"""
# on 192.168.1.100
cd ~/litellm-lab
docker compose exec redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning --scan --count 1000 | head'
docker compose exec redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning info keyspace'
"""),
    h3('Per-request controls'),
    code(r"""
# skip the cache for one call
-d '{"model":"gpt-mini","cache":{"no-cache":true},"messages":[...]}'
# accept only entries younger than 60 seconds
-d '{"model":"gpt-mini","cache":{"s-maxage":60},"messages":[...]}'
"""),
    h3('Check script'),
    code(r"""
cat > labs/07-cache.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
P="Name three prime numbers. nonce $(date +%s%N)"     # fresh prompt: call 1 must miss
c1=$(chat "$MK" gpt-mini "$P"); d1=$(hdr x-litellm-response-duration-ms)
c2=$(chat "$MK" gpt-mini "$P"); d2=$(hdr x-litellm-response-duration-ms); k=$(hdr x-litellm-cache-key)
echo "  call 1: HTTP $c1, ${d1:-?} ms;  call 2: HTTP $c2, ${d2:-?} ms, cache key ${k:0:16}..."
[ "$c1" = 200 ] && [ "$c2" = 200 ] && [ -n "$k" ] && pass "cache: second identical request was a cache hit" \
  || fail "cache: no x-litellm-cache-key on the repeat (check /cache/ping)"
EOF
chmod +x labs/07-cache.sh && labs/07-cache.sh
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'The cache key is a hash of the model, messages and parameters, so changing <code>temperature</code> or a single character of the prompt is a miss.',
        'Cache hits show <code>cache_hit: true</code> in the spend logs (Lab 9) and cost $0, which is why caching doubles as a cost control.',
        'Don&#x27;t cache what should vary. Creative or tool-calling flows usually want <code>no-cache</code>, or opt-in caching with <code>mode: default_off</code>.',
        'If <code>/cache/ping</code> fails, the usual causes are a wrong <code>REDIS_PASSWORD</code> in the env file, <code>host: localhost</code> instead of 192.168.1.100, or the container not recreated after the env change.',
        'Semantic caching (similar prompts, not just identical ones) is available as <code>type: redis-semantic</code>. It needs Redis Stack and an embedding model.',
    ]),
)

# ---------------------------------------------------------------- lab 8
L8 = lab(8, 'Custom Guardrail: Block SSNs', 'workstation → 192.168.1.101',
    goal('a prompt containing a US Social Security number is rejected before it reaches any provider, and a clean prompt passes.'),
    h3('How it works'),
    p('Lab 3 installed <code>guard.py</code> and registered it as <code>ssn-guard</code> with <code>mode: pre_call</code> and <code>default_on: true</code>. LiteLLM calls <code>async_pre_call_hook</code> after authentication and before routing, for every request on every model. Raising an <code>HTTPException</code> there ends the request: the model never sees the prompt, and nothing is billed.'),
    h3('Steps'),
    code(r"""
curl -s $GW/guardrails/list -H "Authorization: Bearer $MK" | jq '.guardrails[] | {guardrail_name, litellm_params}'

for msg in "My SSN is 123-45-6789, is that a valid format?" "What is the capital of Ohio?"; do
  curl -s -w '\nHTTP %{http_code}\n' $GW/v1/chat/completions -H "Authorization: Bearer $MK" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"claude-fast\",\"messages\":[{\"role\":\"user\",\"content\":\"$msg\"}]}" \
    | jq -Rr '. as $l | try (fromjson | .error.message // .choices[0].message.content) catch $l'
done
"""),
    h3('Check script'),
    code(r"""
cat > labs/08-guardrail.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
c=$(chat "$MK" gpt-mini "My SSN is 123-45-6789. Remember it.")
[ "$c" != 200 ] && grep -qi 'ssn' "$OUT" || fail "SSN prompt was not blocked (HTTP $c)"
echo "  SSN prompt   -> HTTP $c: $(jq -r '.error.message // .' "$OUT" | head -c 80)"
c=$(chat "$MK" gpt-mini "What is the capital of Ohio?")
[ "$c" = 200 ] || fail "clean prompt failed with HTTP $c"
echo "  clean prompt -> HTTP $c: $(jq -r '.choices[0].message.content' "$OUT" | head -c 40)"
pass "guardrail: SSN blocked, clean prompt passed"
EOF
chmod +x labs/08-guardrail.sh && labs/08-guardrail.sh
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'The regex only matches the dashed form. <code>123456789</code> or <code>123 45 6789</code> get through. Extend it as an exercise, and watch for false positives on phone and order numbers.',
        'Other modes: <code>post_call</code> inspects the model&#x27;s answer, and <code>during_call</code> runs alongside the model call. To mask instead of block, change the message text in <code>data</code> and return it.',
        'With <code>default_on: false</code>, the guardrail runs only for requests that ask for it with <code>&quot;guardrails&quot;: [&quot;ssn-guard&quot;]</code>, or for keys and teams that have it attached.',
        'This is a lab control, not DLP. Anything that encodes, splits or paraphrases the number gets past a regex. For production, use a real PII engine (LiteLLM integrates Presidio and several vendors) and keep regexes as a cheap first layer.',
        'Requests blocked by the guardrail show up in the spend logs as failures and under <strong>Guardrails</strong> in the UI. That&#x27;s useful evidence that the control works.',
    ]),
)

# ---------------------------------------------------------------- lab 9
L9 = lab(9, 'Observability: Spend Logs & Langfuse', 'workstation, 192.168.1.101, Langfuse on 192.168.1.100',
    goal('see every request from the previous labs in LiteLLM&#x27;s spend logs, then (optionally) send full traces to a self-hosted Langfuse.'),
    h3('Part A: spend logs (built in)'),
    code(r"""
TODAY=$(date -u +%F); TOMORROW=$(date -u -d tomorrow +%F)
curl -s "$GW/spend/logs?start_date=$TODAY&end_date=$TOMORROW&summarize=false" -H "Authorization: Bearer $MK" \
  | jq -r 'if type=="array" then . else .data end | sort_by(.startTime) | .[-10:][]
           | [.startTime[11:19], .model_group // .model, .status // "-", (.spend|tostring), (.cache_hit|tostring)] | @tsv'
"""),
    p('Each row has the time, the model alias, the status, cost in dollars, and whether it was a cache hit. The UI shows the same data under <strong>Logs</strong> and <strong>Usage</strong>.'),
    h3('Part B: Langfuse on .100 (optional)'),
    p('Langfuse v4 runs as six containers (web, worker, Postgres, ClickHouse, Redis, MinIO) and needs about 4 GB of free RAM. Its compose file publishes its own Postgres and Redis on 127.0.0.1:5432 and :6379, which collide with Lab 2&#x27;s, so an override file removes those ports and pins the images.'),
    code(r"""
# on 192.168.1.100
cd ~/litellm-lab
git clone --depth 1 --branch v4.50.0 https://github.com/langfuse/langfuse.git
cd langfuse
umask 077
PG=$(openssl rand -hex 16); MINIO=$(openssl rand -hex 16)
cat > .env <<EOF
POSTGRES_VERSION=17.11
POSTGRES_PASSWORD=$PG
DATABASE_URL=postgresql://postgres:$PG@postgres:5432/postgres
SALT=$(openssl rand -hex 16)
ENCRYPTION_KEY=$(openssl rand -hex 32)
NEXTAUTH_SECRET=$(openssl rand -hex 32)
NEXTAUTH_URL=http://192.168.1.100:3000
CLICKHOUSE_PASSWORD=$(openssl rand -hex 16)
REDIS_AUTH=$(openssl rand -hex 16)
MINIO_ROOT_PASSWORD=$MINIO
LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY=$MINIO
LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY=$MINIO
LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY=$MINIO
LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT=http://192.168.1.100:9090
TELEMETRY_ENABLED=false
LANGFUSE_INIT_ORG_ID=lab
LANGFUSE_INIT_ORG_NAME=Lab
LANGFUSE_INIT_PROJECT_ID=litellm-lab
LANGFUSE_INIT_PROJECT_NAME=litellm-lab
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-$(openssl rand -hex 12)
LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-$(openssl rand -hex 24)
LANGFUSE_INIT_USER_EMAIL=admin@lab.local
LANGFUSE_INIT_USER_NAME=admin
LANGFUSE_INIT_USER_PASSWORD=$(openssl rand -hex 12)
EOF
unset PG MINIO

cat > docker-compose.override.yml <<'EOF'
services:
  langfuse-web:
    image: docker.langfuse.com/langfuse/langfuse:4.50.0
  langfuse-worker:
    image: docker.langfuse.com/langfuse/langfuse-worker:4.50.0
  redis:
    image: docker.io/library/redis:7.4.11
    ports: !reset []
  postgres:
    ports: !reset []
EOF

docker compose config | grep -E 'image:|published:'     # no 5432/6379; web 3000, minio 9090
docker compose up -d
docker compose ps                                       # wait until langfuse-web is up (~1-2 min)
grep -E 'INIT_(PROJECT_PUBLIC_KEY|USER_EMAIL)' .env     # public key and login are safe to show
"""),
    p('Log in at <code>http://192.168.1.100:3000</code> with the init email and the password from <code>.env</code>. Then add the Langfuse keys to LiteLLM on .101:'),
    code(r"""
# on 192.168.1.101
read -rsp 'Langfuse public key: ' LPK; echo
read -rsp 'Langfuse secret key: ' LSK; echo
printf '%s\n' "LANGFUSE_PUBLIC_KEY=$LPK" "LANGFUSE_SECRET_KEY=$LSK" "LANGFUSE_HOST=http://192.168.1.100:3000" \
  | sudo tee -a /opt/litellm/litellm.env >/dev/null; unset LPK LSK
sudo vi /opt/litellm/config.yaml       # under litellm_settings add:   callbacks: ["langfuse_otel"]
sudo /opt/litellm/run-litellm.sh
"""),
    h3('Check script'),
    code(r"""
cat > labs/09-observability.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
T=$(date -u +%F); T2=$(date -u -d tomorrow +%F)
n=$(api GET "/spend/logs?start_date=$T&end_date=$T2&summarize=false" | jq 'if type=="array" then . else .data end | length')
echo "  spend log entries today: $n"
[ "${n:-0}" -gt 0 ] || fail "no spend logs today (database connected? did Labs 4-8 run?)"
if [ -n "${LF_PK:-}" ] && [ -n "${LF_SK:-}" ]; then
  t=$(curl -s -u "$LF_PK:$LF_SK" "http://192.168.1.100:3000/api/public/traces?limit=5" | jq '.data | length')
  echo "  Langfuse traces visible: $t"
  [ "${t:-0}" -gt 0 ] || fail "Langfuse has no traces yet"
fi
pass "observability: $n spend log entries${LF_PK:+, Langfuse traces present}"
EOF
chmod +x labs/09-observability.sh && labs/09-observability.sh
# with Langfuse: read -rsp 'LF secret: ' LF_SK; export LF_SK LF_PK=pk-lf-...; labs/09-observability.sh
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'Spend log rows are written in batches, so the newest requests can take 10&ndash;60 seconds to appear.',
        '<code>langfuse_otel</code> sends OpenTelemetry spans to Langfuse&#x27;s <code>/api/public/otel</code> endpoint, which current Langfuse versions prefer. The older <code>langfuse</code> callback (Langfuse SDK v2 ingestion) still exists if you&#x27;re on an older Langfuse.',
        'Traces include full prompts and completions. To keep content out of Langfuse but still log metadata, set <code>turn_off_message_logging: true</code> in <code>litellm_settings</code>.',
        '<code>!reset</code> in an override file needs Docker Compose 2.24 or newer. If <code>docker compose config</code> still shows 5432 or 6379 published, your Compose is older; edit those lines out of Langfuse&#x27;s file instead.',
        'MinIO from <code>cgr.dev/chainguard/minio</code> is only published as <code>latest</code> on the free tier. Pin it by digest (<code>docker compose images</code> shows it) if you need full reproducibility.',
        'Prometheus metrics (<code>/metrics</code>) are an enterprise feature in LiteLLM. The spend logs and Langfuse/OTel callbacks used here are all open source.',
    ]),
)

# ---------------------------------------------------------------- lab 10
L10 = lab(10, 'MCP Gateway: DeepWiki Through LiteLLM', 'workstation → 192.168.1.101 → mcp.deepwiki.com',
    goal('list the DeepWiki MCP tools through LiteLLM, then have a model call them through <code>/v1/responses</code>, where LiteLLM runs the tool calls itself.'),
    h3('1. See the server and its tools'),
    code(r"""
curl -s $GW/v1/mcp/server -H "Authorization: Bearer $MK" | jq '.[] | {server_name, url, transport, status}'
curl -s $GW/mcp-rest/tools/list -H "Authorization: Bearer $MK" | jq -r '.tools[].name'
# deepwiki-read_wiki_structure, deepwiki-read_wiki_contents, deepwiki-ask_question
"""),
    h3('2. Let the model use them'),
    code(r"""
jq -n --arg k "Bearer $MK" '{
  model: "gpt-mini",
  input: "Use DeepWiki to answer in two sentences: what does the BerriAI/litellm repository do?",
  tools: [{type:"mcp", server_label:"litellm", server_url:"litellm_proxy", require_approval:"never",
           headers:{"x-litellm-api-key":$k, "x-mcp-servers":"deepwiki"}}],
  tool_choice: "required"}' > /tmp/mcp.json
curl -s $GW/v1/responses -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d @/tmp/mcp.json \
  | tee /tmp/mcp.out | jq -r '.output[] | .type + "  " + (.name // "") ' ; \
  jq -r '[.output[] | select(.type=="message") | .content[]?.text] | join("\n")' /tmp/mcp.out
"""),
    p('<code>server_url: &quot;litellm_proxy&quot;</code> tells LiteLLM to use its own registered MCP servers; <code>x-mcp-servers</code> narrows that to DeepWiki. The output lists the <code>mcp_call</code> steps followed by the final message.'),
    h3('Check script'),
    code(r"""
cat > labs/10-mcp.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
n=$(api GET /mcp-rest/tools/list | jq '[.tools[]? | select(.name|test("deepwiki|wiki|ask_question"))] | length')
echo "  DeepWiki tools listed: $n"
[ "${n:-0}" -gt 0 ] || fail "no DeepWiki tools (is mcp_servers.deepwiki in config, and is outbound HTTPS allowed?)"
body=$(jq -n --arg k "Bearer $MK" '{model:"gpt-mini",
  input:"Use DeepWiki: in one sentence, what does the BerriAI/litellm repository do?",
  tools:[{type:"mcp",server_label:"litellm",server_url:"litellm_proxy",require_approval:"never",
          headers:{"x-litellm-api-key":$k,"x-mcp-servers":"deepwiki"}}], tool_choice:"required"}')
api POST /v1/responses "$body" > "$OUT"
jq -e '[.. | strings | select(test("ask_question|read_wiki"))] | length > 0' "$OUT" >/dev/null \
  || fail "the response shows no DeepWiki tool call: $(jq -c '.error // .output[0]' "$OUT" | head -c 160)"
pass "MCP: model called DeepWiki through litellm_proxy"
EOF
chmod +x labs/10-mcp.sh && labs/10-mcp.sh
"""),
    h3('Use the MCP gateway from other clients'),
    code(r"""
# Claude Code (with a virtual key from Lab 6 or 11)
claude mcp add --transport http litellm http://192.168.1.101:4000/mcp/ \
  --header "x-litellm-api-key: Bearer <virtual-key>"
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'If <code>/mcp-rest/tools/list</code> says &quot;The key is not allowed to access any MCP servers&quot;, LiteLLM found no server it could use: check the <code>mcp_servers:</code> block loaded (startup log) and that .101 can reach <code>https://mcp.deepwiki.com</code>.',
        'LiteLLM prefixes tool names with the server name (<code>deepwiki-ask_question</code>) so tools from different servers can&#x27;t collide.',
        'MCP access follows keys and teams: give a key <code>object_permission.mcp_servers</code> to restrict which servers it can use. A key with no restriction sees every public server.',
        'DeepWiki is public and needs no auth. For servers that do, LiteLLM can store per-server credentials or pass the caller&#x27;s headers through, so clients never hold the upstream token.',
        'If listing works but the responses call hangs, the model is probably looping on tool calls. Lower <code>max_output_tokens</code> or ask a narrower question.',
        'Remote MCP servers run code and return text that the model will act on. Only add servers you trust; tool output is a prompt-injection path.',
    ]),
)

# ---------------------------------------------------------------- lab 11
L11 = lab(11, 'Claude Code Through /v1/messages', 'workstation → 192.168.1.101',
    goal('give Claude Code its own virtual key with a budget, confirm the Anthropic-format <code>/v1/messages</code> endpoint works, and print the exports to use (without running Claude Code here).'),
    h3('1. A key just for Claude Code'),
    code(r"""
CC_KEY=$(curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias":"claude-code","models":["claude-fast","gpt-mini"],"max_budget":5,"budget_duration":"30d"}' \
  | jq -r .key)
echo "claude-code key ****${CC_KEY: -4}"
"""),
    h3('2. Test the Anthropic Messages API'),
    code(r"""
for m in claude-fast gpt-mini; do
  curl -s $GW/v1/messages -H "Authorization: Bearer $CC_KEY" -H 'content-type: application/json' \
    -H 'anthropic-version: 2023-06-01' \
    -d "{\"model\":\"$m\",\"max_tokens\":60,\"messages\":[{\"role\":\"user\",\"content\":\"Say pong.\"}]}" \
    | jq -r --arg m "$m" '"\($m): \(.content[0].text) (stop: \(.stop_reason))"'
done
"""),
    p('Both answer in Anthropic format. For <code>gpt-mini</code>, LiteLLM translates the Messages request to OpenAI and the answer back.'),
    h3('3. The exports'),
    code(r"""
cat > labs/11-claude-code.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
K=${CC_KEY:-$MK}
c=$(curl -s -o "$OUT" -w '%{http_code}' "$GW/v1/messages" -H "Authorization: Bearer $K" \
  -H 'content-type: application/json' -H 'anthropic-version: 2023-06-01' \
  -d '{"model":"claude-fast","max_tokens":20,"messages":[{"role":"user","content":"Say pong."}]}')
[ "$c" = 200 ] || fail "/v1/messages returned HTTP $c"
cat <<OUT2
  Run these in the shell where you start Claude Code (key shown masked; paste your real one):
    export ANTHROPIC_BASE_URL=$GW
    export ANTHROPIC_AUTH_TOKEN=$(mask "$K")
    export ANTHROPIC_MODEL=claude-fast
    export ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-fast
OUT2
pass "Claude Code: /v1/messages answered with $(jq -r .model "$OUT")"
EOF
chmod +x labs/11-claude-code.sh && CC_KEY=$CC_KEY labs/11-claude-code.sh
"""),
    h3('Notes &amp; gotchas'),
    ul([
        '<code>ANTHROPIC_AUTH_TOKEN</code> is sent as <code>Authorization: Bearer</code>, which LiteLLM accepts. Use it rather than <code>ANTHROPIC_API_KEY</code>, which Claude Code may treat as a direct Anthropic key.',
        'Claude Code asks for real Anthropic model names unless told otherwise. <code>ANTHROPIC_MODEL</code> and the <code>ANTHROPIC_DEFAULT_*_MODEL</code> variables map its requests to your aliases. A name the key isn&#x27;t allowed to use returns 401.',
        'Haiku 4.5 is fine for trying this out. For real coding work, add a Sonnet or Opus alias to <code>model_list</code> and to the key&#x27;s <code>models</code>.',
        'Every Claude Code session now shows up in the spend logs under the <code>claude-code</code> key alias, and the $5 / 30-day budget is a hard cap on what it can spend.',
        'The SSN guardrail applies here too: Claude Code sends file contents as prompts, so a test fixture containing <code>123-45-6789</code> will be blocked. That&#x27;s the guardrail doing its job, but it can surprise you.',
    ]),
)

# ---------------------------------------------------------------- lab 12
L12 = lab(12, 'A2A Agent Gateway: hello-agent', '192.168.1.100 (agent) and 192.168.1.101 (gateway)',
    goal('run the A2A Hello World sample in a container on .100, advertising <code>http://192.168.1.100:9999</code>, register it in LiteLLM as <code>hello-agent</code>, and call it through <code>/a2a/hello-agent</code> with a virtual key.'),
    h3('1. Build the agent (on .100)'),
    p('The sample binds to 127.0.0.1 and advertises <code>http://127.0.0.1:9999</code> in its agent card, which is useless from another host. The Dockerfile pins the repo to a commit, then rewrites both.'),
    code(r"""
mkdir -p ~/litellm-lab/a2a-hello && cd ~/litellm-lab/a2a-hello
cat > Dockerfile <<'EOF'
FROM docker.io/library/python:3.12.15-slim-bookworm
ARG A2A_SAMPLES_COMMIT=6603ba3f2c31a7ef33e70b9d8b5b5f8be42ac9a3
ARG ADVERTISE_URL=http://192.168.1.100:9999
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init -q a2a-samples && cd a2a-samples \
 && git remote add origin https://github.com/a2aproject/a2a-samples.git \
 && git fetch -q --depth 1 origin "$A2A_SAMPLES_COMMIT" && git checkout -q FETCH_HEAD
WORKDIR /src/a2a-samples/samples/python/agents/helloworld
RUN pip install --no-cache-dir -r requirements.txt \
 && sed -i "s#url='http://127.0.0.1:9999'#url='${ADVERTISE_URL}'#g; s#host='127.0.0.1'#host='0.0.0.0'#" __main__.py \
 && grep -nE "url=|host=" __main__.py
RUN useradd -r -u 10001 agent
USER agent
EXPOSE 9999
CMD ["python", "__main__.py"]
EOF

cat > compose.yml <<'EOF'
name: a2a-hello
services:
  hello-agent:
    build: .
    image: local/a2a-hello:6603ba3
    restart: unless-stopped
    ports: ["0.0.0.0:9999:9999"]
EOF
docker compose up -d --build
"""),
    h3('2. Check the agent card from .101'),
    code(r"""
# on 192.168.1.101 (or anywhere on the LAN)
curl -s http://192.168.1.100:9999/.well-known/agent-card.json | jq '{name, version, supportedInterfaces}'
# supportedInterfaces[0].url must be http://192.168.1.100:9999
"""),
    h3('3. Register it with LiteLLM'),
    code(r"""
curl -s $GW/v1/agents -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d '{
  "agent_name": "hello-agent",
  "agent_card_params": {
    "protocolVersion": "1.0",
    "name": "Hello World Agent",
    "description": "Just a hello world agent",
    "url": "http://192.168.1.100:9999/",
    "version": "0.0.1",
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "capabilities": {"streaming": true},
    "skills": [{"id": "echo_bot", "name": "Echo Bot",
                "description": "Responds with a Hello World message", "tags": ["a2a", "echo-example"]}]
  }
}' | jq '{agent_id, agent_name}'
curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r '.[] | "\(.agent_name)  \(.agent_id)"'
"""),
    p('Or in the UI: <strong>Agents → Add Agent</strong>, choose A2A, name it <code>hello-agent</code> and give it the URL <code>http://192.168.1.100:9999/</code>.'),
    h3('4. Call it through the gateway with a virtual key'),
    code(r"""
A2A_KEY=$(curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias":"a2a-key"}' | jq -r .key)
curl -s $GW/a2a/hello-agent -H "Authorization: Bearer $A2A_KEY" -H 'Content-Type: application/json' -d '{
  "jsonrpc": "2.0", "id": "1", "method": "message/send",
  "params": {"message": {"role": "user", "messageId": "'"$(cat /proc/sys/kernel/random/uuid)"'",
                         "parts": [{"kind": "text", "text": "Say hello."}]}}}' \
  | jq '.result // .error'
"""),
    h3('Check script'),
    code(r"""
cat > labs/12-a2a.sh <<'EOF'
#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
AGENT=${AGENT:-hello-agent}
curl -sf -m 5 http://192.168.1.100:9999/.well-known/agent-card.json >/dev/null \
  || fail "agent card not reachable at 192.168.1.100:9999"
K=$(api POST /key/generate '{"key_alias":"lab-a2a-check"}' | jq -r .key)
trap 'api POST /key/delete "$(jq -n --arg k "$K" "{keys:[\$k]}")" >/dev/null; rm -f "$OUT" "$HDR"' EXIT
req=$(jq -n --arg id "$(cat /proc/sys/kernel/random/uuid)" \
  '{jsonrpc:"2.0",id:"1",method:"message/send",params:{message:{role:"user",messageId:$id,parts:[{kind:"text",text:"Say hello."}]}}}')
c=$(curl -s -o "$OUT" -w '%{http_code}' "$GW/a2a/$AGENT" -H "Authorization: Bearer $K" -H 'Content-Type: application/json' -d "$req")
grep -qi 'hello, world' "$OUT" || fail "no hello from $AGENT (HTTP $c): $(head -c 200 "$OUT")"
echo "  $AGENT answered via $GW/a2a/$AGENT with key $(mask "$K")"
echo "  waiting 30 s for spend logs..."; sleep 30
T=$(date -u +%F); T2=$(date -u -d tomorrow +%F)
n=$(api GET "/spend/logs?start_date=$T&end_date=$T2&summarize=false" \
  | jq '[ (if type=="array" then . else .data end)[] | select((.metadata.user_api_key_alias // "") == "lab-a2a-check") ] | length')
echo "  spend log entries for the check key: $n"
[ "${n:-0}" -gt 0 ] || fail "A2A call worked but isn't in the spend logs yet (re-run in a minute)"
pass "A2A: hello-agent answered through the gateway and was logged"
EOF
chmod +x labs/12-a2a.sh && labs/12-a2a.sh
"""),
    h3('Notes &amp; gotchas'),
    ul([
        'If <code>/a2a/hello-agent</code> returns &quot;agent not found&quot;, use the <code>agent_id</code> from the registration output instead: <code>AGENT=&lt;agent_id&gt; labs/12-a2a.sh</code>.',
        'The pinned sample commit speaks A2A protocol 1.0 (a2a-sdk 1.1.0). LiteLLM 1.103 accepts v0.3-style calls (<code>message/send</code>) from clients and converts them for 1.0 agents. With an older LiteLLM that only speaks v0.3, build the sample at commit <code>1cce9a59dc31</code> (a2a-sdk 0.3) and set <code>protocolVersion</code> to <code>0.3.0</code>.',
        'LiteLLM forwards to the <code>url</code> in the agent card you registered, not the one the agent advertises. If they differ, fix the registration.',
        'The agent itself has no authentication. Port 9999 is open to the whole LAN, and the gateway is the only place a key is checked. Restrict 9999 to 192.168.1.101 with firewalld if other hosts shouldn&#x27;t reach the agent directly.',
        'Treat everything an agent returns, including its card, as untrusted input. A malicious card&#x27;s description or skill text can carry a prompt injection into any LLM that reads it.',
    ]),
)

# ---------------------------------------------------------------- lab 13
L13 = lab(13, 'Health Checks & the Admin UI', 'workstation → 192.168.1.101',
    goal('list every deployment and whether it&#x27;s healthy, and find each lab&#x27;s results in the admin UI.'),
    h3('Health endpoints'),
    code(r"""
curl -s $GW/health/liveliness; echo                         # process up (no key)
curl -s $GW/health/readiness | jq                            # db + cache status (no key)
curl -s "$GW/health?model=gpt-mini"    -H "Authorization: Bearer $MK" | jq '{healthy_count, unhealthy_count}'
curl -s "$GW/health?model=claude-fast" -H "Authorization: Bearer $MK" | jq '{healthy_count, unhealthy_count}'

# every deployment (real calls to every model, see the warning below)
curl -s $GW/health -H "Authorization: Bearer $MK" \
  | jq -r '(.healthy_endpoints[]?   | "healthy    \(.model)"),
           (.unhealthy_endpoints[]? | "UNHEALTHY  \(.model)  \((.error // "") | tostring | .[0:80])")'
"""),
    h3('Admin UI tour'),
    p('Open <code>http://192.168.1.101:4000/ui</code> and log in with <code>UI_USERNAME</code>/<code>UI_PASSWORD</code> if they&#x27;re set, otherwise <code>admin</code> and the master key.'),
    table(['UI page', 'What to look at', 'Lab'], [
        ['Models + Endpoints', 'gpt-mini, claude-fast, health status', '3, 4, 13'],
        ['Virtual Keys / Teams', 'lab-key, claude-code, a2a-key; budgets and spend', '6, 11, 12'],
        ['Logs', 'each request, cache hits, guardrail blocks', '7, 8, 9'],
        ['Usage', 'spend by key, team and model', '6, 9'],
        ['Guardrails', 'ssn-guard and what it blocked', '8'],
        ['MCP Servers', 'deepwiki and its three tools', '10'],
        ['Agents', 'hello-agent', '12'],
    ]),
    h3('Check script'),
    code(r"""
cat > labs/13-health.sh <<'EOF'
#!/usr/bin/env bash
# Checks gpt-mini and claude-fast only. ALL=1 checks every deployment (calls every model).
source "$(dirname "$0")/common.sh"
[ "$(curl -s "$GW/health/liveliness")" != "" ] || fail "liveliness endpoint not answering"
if [ -n "${ALL:-}" ]; then targets=(""); else targets=("?model=gpt-mini" "?model=claude-fast"); fi
bad=0
for t in "${targets[@]}"; do
  api GET "/health$t" > "$OUT"
  jq -r '(.healthy_endpoints[]? | "  healthy    \(.model)"),
         (.unhealthy_endpoints[]? | "  UNHEALTHY  \(.model)  \((.error // "")|tostring|.[0:60])")' "$OUT"
  bad=$(( bad + $(jq '.unhealthy_endpoints | length' "$OUT") ))
done
[ "$bad" -eq 0 ] && pass "health: all checked deployments healthy" || fail "health: $bad unhealthy deployment(s)"
EOF
chmod +x labs/13-health.sh && labs/13-health.sh
"""),
    h3('Notes &amp; gotchas'),
    warn('A bare <code>/health</code> sends a real completion to every deployment in <code>model_list</code>. That costs tokens on cloud models, and with LM Studio or Ollama it loads each local model in turn, which can evict whatever was loaded and stall other users. Use <code>?model=&lt;alias&gt;</code> for routine checks.'),
    ul([
        'Embedding, image and audio models need <code>model_info.mode</code> set (e.g. <code>mode: embedding</code>), or the health check sends them a chat request and reports them unhealthy.',
        'To run health checks in the background instead of on demand, set <code>background_health_checks: true</code> and <code>health_check_interval: 300</code> in <code>general_settings</code>. <code>/health</code> then returns the latest cached result.',
        '<code>/health/readiness</code> is the right target for a container or load-balancer health probe. It doesn&#x27;t call any model.',
    ]),
)

# ---------------------------------------------------------------- appendices
appA = f'''<section class="appendix" id="runner">
  <h2>Appendix A: Run every check</h2>
  <p>With the check scripts from Labs 4&ndash;13 saved in <code>~/litellm-labs/labs/</code>, this runner executes them in order and prints a pass/fail table. Lab 6 takes about two minutes and Lab 12 about thirty seconds because of rate-limit and spend-log waits.</p>
  {code(r"""
cat > labs/run-all.sh <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
: "${MK:?export MK first}"
printf '%-4s %-22s %-5s %s\n' Lab Check Result Detail
pass=0; total=0
for s in [0-9][0-9]-*.sh; do
  out=$(bash "$s" 2>&1); rc=$?
  total=$((total + 1)); [ $rc -eq 0 ] && pass=$((pass + 1))
  name=${s%.sh}
  printf '%-4s %-22s %-5s %s\n' "${name%%-*}" "${name#*-}" "$([ $rc -eq 0 ] && echo PASS || echo FAIL)" \
    "$(tail -1 <<<"$out" | sed -E 's/^(PASS|FAIL) +//' | cut -c1-70)"
done
echo "$pass of $total passed"
EOF
chmod +x labs/run-all.sh && labs/run-all.sh
""")}
  {table(['Lab', 'What the check proves'], [
      ['04 unified', 'gpt-mini and claude-fast both answer through one OpenAI-format endpoint'],
      ['05 fallback', '<code>mock_testing_fallbacks</code> on gpt-mini returns a Claude answer'],
      ['06 keys', 'disallowed model &rarr; 401, rpm_limit 5 &rarr; 429, team budget &rarr; &quot;Budget has been exceeded&quot;'],
      ['07 cache', 'second identical request carries <code>x-litellm-cache-key</code>'],
      ['08 guardrail', '123-45-6789 is blocked, a clean prompt passes'],
      ['09 observability', 'today&#x27;s requests are in <code>/spend/logs</code> (plus Langfuse traces if <code>LF_PK</code>/<code>LF_SK</code> are set)'],
      ['10 mcp', 'DeepWiki tools are listed and the model calls one via <code>litellm_proxy</code>'],
      ['11 claude-code', '<code>/v1/messages</code> works; prints the exports'],
      ['12 a2a', 'hello-agent answers through <code>/a2a/hello-agent</code> with a virtual key and is logged'],
      ['13 health', 'the lab models are healthy (<code>ALL=1</code> for every deployment)'],
  ])}
</section>
'''

appB = f'''<section class="appendix" id="readme">
  <h2>Appendix B: README: start, stop, roll back</h2>
  <h3>What runs where</h3>
  {table(['Host', 'Directory', 'Containers', 'Ports'], [
      ['192.168.1.101', '<code>/opt/litellm/</code> (config.yaml, guard.py, litellm.env, run-litellm.sh, backups)', 'litellm (+ its own DB, if it had one)', '4000'],
      ['192.168.1.100', '<code>~/litellm-lab/</code>', 'postgres, redis', '5432, 6379'],
      ['192.168.1.100', '<code>~/litellm-lab/langfuse/</code>', 'langfuse-web, -worker, postgres, clickhouse, redis, minio', '3000, 9090 (others on 127.0.0.1)'],
      ['192.168.1.100', '<code>~/litellm-lab/a2a-hello/</code>', 'hello-agent', '9999'],
      ['workstation', '<code>~/litellm-labs/labs/</code>', 'none (check scripts)', '&ndash;'],
  ])}
  <h3>Start and stop</h3>
  {code(r"""
# 192.168.1.100: start in this order, stop in reverse
cd ~/litellm-lab && docker compose up -d
cd ~/litellm-lab/langfuse && docker compose up -d          # optional
cd ~/litellm-lab/a2a-hello && docker compose up -d
#   ...stop with "docker compose down" in each directory. Add -v only to DELETE the data volumes.

# 192.168.1.101
# installed with Lab 0: cd /opt/litellm && sudo docker compose stop | start | up -d
sudo podman stop litellm        # stop
sudo podman start litellm       # start (same container, same settings)
sudo /opt/litellm/run-litellm.sh   # recreate (after editing litellm.env or the image)
sudo podman logs --tail 50 -f litellm
""")}
  <h3>Roll back the LiteLLM config</h3>
  {code(r"""
D=/opt/litellm; TS=$(cat $D/LAST_BACKUP); ls $D/*.bak-$TS*
sudo cp -a $D/config.yaml.bak-$TS $D/config.yaml
sudo cp -a $D/litellm.env.bak-$TS $D/litellm.env
sudo $D/run-litellm.sh                      # guard.py is still mounted but unused, which is harmless
curl -s http://192.168.1.101:4000/health/readiness
""")}
  <p>To go all the way back to the original container (image tag, mounts, networks), rebuild the <code>podman run</code> command from <code>$D/inspect.bak-$TS.json</code>: <code>.Config.Image</code>, <code>.Config.Cmd</code>, <code>.HostConfig.Binds</code>, <code>.HostConfig.PortBindings</code> and <code>.NetworkSettings.Networks</code> hold everything you need.</p>
  <h3>Lab cleanup</h3>
  {code(r"""
# delete lab keys and teams (UI: Virtual Keys / Teams), and the agent
curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r '.[] | select(.agent_name=="hello-agent") | .agent_id' \
  | xargs -r -I{} curl -s -X DELETE $GW/v1/agents/{} -H "Authorization: Bearer $MK"
# 192.168.1.100: remove everything, data included
cd ~/litellm-lab/a2a-hello && docker compose down --rmi local
cd ~/litellm-lab/langfuse && docker compose down -v
cd ~/litellm-lab && docker compose down -v
""")}
</section>
'''

PROMPT = r"""I want to run a set of hands-on LiteLLM AI gateway labs in my home lab. Help me get it working end to end.

## My environment
- Docker host: 192.168.1.100 (this is where new containers like Redis, Postgres, Langfuse and the A2A agent should run)
- LiteLLM proxy: ALREADY RUNNING on 192.168.1.101, presumably on port 4000 (verify)
- I'm running you from my workstation. Figure out how you can reach each host (SSH, DOCKER_HOST=ssh://..., or the Docker API) and ask me for usernames or credentials instead of guessing.

## Ground rules
- Don't modify or restart the existing LiteLLM on 192.168.1.101 until you've shown me its current config and I've approved the change. Back up its config file first.
- Never print API keys or the master key in full. Mask all but the last 4 characters.
- Pin image tags rather than using `latest` (LiteLLM had a PyPI supply-chain incident in March 2026). Tell me which LiteLLM version is running and flag it if it looks old or suspect.
- Containers on 192.168.1.100 must bind to 0.0.0.0 and be reachable from 192.168.1.101. Don't use localhost or host.docker.internal for cross-host URLs. Use 192.168.1.100 explicitly, and check that firewall ports are open.
- Work in phases. Stop after each phase, show me the results, and wait for my go-ahead.

## Phase 1: Discover (read-only)
1. Confirm you can reach both hosts. Check that Docker and Compose work on .100.
2. On .101, find out how LiteLLM is deployed (Docker, systemd, pip/venv, Kubernetes), where its config.yaml lives, its version, and its environment variables (masked).
3. Check whether it has a master key, a Postgres DATABASE_URL (needed for virtual keys, teams, budgets and spend logs), and Redis (needed for caching).
4. Test it: `curl http://192.168.1.101:4000/health/liveliness` and a chat completion against whatever models are configured.
5. Report what's present and what's missing for these labs: unified API, fallbacks/load balancing, virtual keys/teams/budgets, Redis caching, custom guardrail, Langfuse/OTel observability, MCP gateway, Claude Code via /v1/messages, A2A agent gateway, admin UI/health.

## Phase 2: Supporting services on 192.168.1.100
Write a docker-compose.yml with pinned tags for whatever's missing: Postgres 16 and Redis 7, plus optionally Langfuse. Use persistent volumes, strong generated passwords stored in a .env file, and published ports. Bring it up and verify .101 can reach each port.

## Phase 3: Update the LiteLLM config (after my approval)
Propose a diff to the existing config.yaml that adds:
- Two model aliases, `gpt-mini` (openai/gpt-4o-mini) and `claude-fast` (anthropic/claude-haiku-4-5-20251001), using os.environ/ references for keys. Keep any models I already have.
- general_settings: master_key and a database_url pointing at Postgres on .100.
- router_settings / litellm_settings: retries, a fallback gpt-mini → claude-fast, and a Redis cache pointing at .100.
- A custom guardrail (guard.py) that blocks US SSNs in prompts, mode pre_call, plus the file mount or path it needs.
- An MCP server entry for https://mcp.deepwiki.com/mcp (transport http).
- Langfuse callbacks, if I set up Langfuse.
Show me the diff, apply it after I approve, restart LiteLLM, and tail the logs until it's healthy.

## Phase 4: A2A agent
On 192.168.1.100, run the A2A Hello World sample from https://github.com/a2aproject/a2a-samples (samples/python/agents/helloworld) in a container. Write a Dockerfile if needed, and make sure it listens on 0.0.0.0 and advertises http://192.168.1.100:<port> in its agent card. Check that `curl http://192.168.1.100:<port>/.well-known/agent-card.json` (or whatever path the sample uses) works from .101. Then register it with LiteLLM as `hello-agent` via the UI instructions or API, whichever this LiteLLM version supports. Check the LiteLLM docs for the exact A2A registration fields for this version.

## Phase 5: Verify each lab
Write a `labs/` folder with one small script per lab (bash with curl/jq, or Python with the openai SDK) that targets http://192.168.1.101:4000. Run each one and give me a pass/fail table:
1. Unified API: both models answer through one client.
2. Fallback: `mock_testing_fallbacks: true` returns a Claude response.
3. Keys/teams: create a team with a tiny budget and a key with rpm_limit 5, then show a disallowed-model rejection, a 429, and a budget error.
4. Caching: second identical request hits the cache (x-litellm-cache-key header).
5. Guardrail: a prompt with 123-45-6789 is blocked and a clean prompt passes.
6. Observability: /spend/logs shows the requests (and Langfuse traces, if configured).
7. MCP: /v1/responses with the litellm_proxy MCP tool uses deepwiki.
8. Claude Code: print the exact ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN exports to use (don't run them).
9. A2A: call hello-agent through http://192.168.1.101:4000/a2a/hello-agent with a virtual key and confirm it appears in spend logs.
10. Health: /health lists every deployment and its status.

If something fails, diagnose the cause (networking, config, version or license tier) before trying fixes, and tell me if a feature needs a newer LiteLLM version or an enterprise license.

At the end, give me a short README covering what's running where, ports, how to start and stop everything, and how to roll back the LiteLLM config."""

appC = f'''<section class="appendix" id="agent-prompt">
  <h2>Appendix C: Let Claude Code do it</h2>
  <p>Rather drive the whole thing with an agent? Paste this prompt into Claude Code on your workstation. It works through the same phases as Labs 1&ndash;13, inspects before it changes anything, stops for your approval after each phase, and asks for credentials instead of guessing them. Have SSH access to both hosts and your OpenAI and Anthropic keys ready.</p>
  <div class="term"><button class="copy" type="button" aria-label="Copy prompt">Copy</button><pre><code>{e(PROMPT)}</code></pre></div>
</section>
'''

labs_html = ''.join([L0, L1, L2, L3, L4, L5, L6, L7, L8, L9, L10, L11, L12, L13])
N = len(LABS)
nav = ''.join(
    f'<li><a href="#lab-{n}" data-lab="{n}"><span class="num">{n}</span><span class="nm">{e(t)}</span>'
    f'<span class="tick" aria-hidden="true"></span></a></li>' for n, t in LABS)

script = (SCRIPT.replace('var total = 25;', f'var total = {N};')
          .replace("'rhcsa-done'", "'litellm-done'")
          .replace("'rhcsa-theme'", "'litellm-theme'"))
assert 'rhcsa' not in script, 'unreplaced rhcsa key in script'

favicon = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='6' fill='%230d5c63'/%3E"
           "%3Ctext x='5' y='22' font-family='monospace' font-size='15' fill='%23e8f1ee'%3EAI%3C/text%3E%3C/svg%3E")

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LiteLLM Gateway Labs</title>
<meta name="description" content="Hands-on LiteLLM AI gateway labs for a two-host home lab: unified API, fallbacks, virtual keys, caching, guardrails, observability, MCP, Claude Code and A2A.">
<link rel="icon" href="{favicon}">
{STYLE}
</head>
<body id="top">
<button class="menu" type="button" aria-expanded="false" aria-controls="sidebar">Labs</button>
<div class="layout">
<aside id="sidebar">
  <div class="brand"><strong>LiteLLM Gateway Labs</strong><span>docker .100 &nbsp;/&nbsp; gateway .101:4000</span></div>
  <input class="search" type="search" placeholder="Search labs (e.g. fallbacks, mcp)" aria-label="Search labs">
  <div class="progress"><span id="prog">0 of {N} labs done</span><div class="bar"><i id="progbar"></i></div></div>
  <nav aria-label="Labs"><ul>{nav}</ul><p class="empty" id="empty">No lab mentions that.</p></nav>
  <div class="side-links">
    <a href="/"><strong>Cropsey IT</strong> home</a>
    <a href="rhcsa.html"><strong>RHCSA Labs</strong></a>
    <a href="#overview">Overview &amp; setup</a>
    <a href="#runner">Run every check</a>
    <a href="#readme">Start, stop, roll back</a>
    <a href="#agent-prompt">Claude Code prompt</a>
    <button class="theme" type="button" id="theme">Switch to dark</button>
  </div>
</aside>
<main>
{overview}
{labs_html}
{appA}
{appB}
{appC}
</main>
</div>
{script}
</body>
</html>
'''

out = f'{SITE}/litellm.html'
open(out, 'w', encoding='utf-8').write(page)
print(f'wrote {out}: {len(page):,} bytes, {N} labs')
