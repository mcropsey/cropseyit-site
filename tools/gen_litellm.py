#!/usr/bin/env python3
"""Build litellm.html (LiteLLM Gateway Labs: chat and agents) in the style of rhcsa.html.

Usage: python3 tools/gen_litellm.py [SITE_DIR]
Reads rhcsa.html for the shared <style> and <script>, and the Python programs the labs
publish from tools/litellm-src/, then writes litellm.html. Edit the lab content here (or
the programs in litellm-src, which were tested against LiteLLM v1.104.0), regenerate,
then copy litellm.html to /var/www/html.
"""
import html
import os
import re
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rh = open(f'{SITE}/rhcsa.html', encoding='utf-8').read()
STYLE = re.search(r'<style>.*?</style>', rh, re.S).group(0)
SCRIPT = re.search(r'<script>.*?</script>', rh, re.S).group(0)
SRC = f'{SITE}/tools/litellm-src'

e = html.escape


def src(name):
    return open(f'{SRC}/{name}', encoding='utf-8').read().rstrip('\n')


def code(text):
    """Escape a code block and dim full-line and trailing '  # ' comments."""
    out = []
    for line in text.strip('\n').split('\n'):
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


def write_file(path, name, sudo=False):
    """A code block that saves one of the tested programs to PATH with a heredoc."""
    cmd = f"sudo tee {path} >/dev/null <<'EOF'" if sudo else f"cat > {path} <<'EOF'"
    return code(f"{cmd}\n{src(name)}\nEOF")


def ul(items):
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def ol(items):
    return '<ol>' + ''.join(f'<li>{i}</li>' for i in items) + '</ol>'


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


# ---------------------------------------------------------------- overview
overview = f'''<section class="intro" id="overview">
  <h1>LiteLLM Gateway Labs: Chat &amp; Agents</h1>
  <p class="sub">Hands-on labs for sending every chat and every AI agent in a home lab through one LiteLLM gateway: one address, one key per app, and one log of who asked what.</p>
  <p>You&#x27;ll start with plain chat requests, put a chat web UI in front of the gateway, then build five agents: a single tool-using agent, agents running as always-on services, agents published through the gateway over A2A, an agent whose tools come from an MCP server, and a coordinator that hands work to the other agents. Lab 10 then points a coding agent at the gateway too.</p>

  <h2>The hosts</h2>
  {table(['Host', 'Role', 'What runs there'], [
      ['<strong>gateway</strong> 192.168.1.101', 'The LiteLLM gateway, port 4000', 'LiteLLM and its Postgres database. <strong>Assumed to be running already</strong>; Lab 0 shows a basic install if it isn&#x27;t.'],
      ['<strong>agent host</strong> 192.168.1.100', 'Everything you build, and where you type the commands', 'Open WebUI (3000), ops-agent (8601), writer-agent (8602), the lab-tools MCP server (8701), and your Python scripts'],
      ['<strong>model server</strong> 192.168.1.194', 'Where the model actually runs', 'LM Studio on port 1234 serving <code>qwen/qwen3.8-27b</code>. Any OpenAI-compatible server, or a cloud provider, works the same way.'],
  ])}
  <p>Nothing talks to the model server directly. The chat UI, the agents and the coding agent all send their requests to the gateway, and the gateway checks the key and forwards the request to the model. That&#x27;s what lets you swap models, limit an app, or see what an agent did, in one place.</p>

  <h2>Podman, and keeping things running after a reboot</h2>
  <p>Every container in these labs runs under <strong>rootful Podman</strong> (<code>sudo podman</code>); there&#x27;s no Docker anywhere. A container started with plain <code>podman run</code> stops when the host reboots and stays stopped, because there&#x27;s no always-running daemon to bring it back, as there is with Docker. There are two ways to fix that:</p>
  {table(['Approach', 'How it works', 'Use it when'], [
      ['<strong>Quadlet</strong> (used in every lab)', 'You write a small <code>.container</code> file in <code>/etc/containers/systemd/</code>. Podman turns it into a normal systemd service, so <code>systemctl start</code>, <code>status</code>, <code>restart</code> and <code>journalctl</code> all work, and the <code>[Install]</code> section starts it at boot.', 'Anything that should keep running. This is the Red Hat-recommended way on Podman 4.4 and newer (Rocky 9 and 10 have Podman 5).'],
      ['<code>podman run --restart=always</code> plus <code>podman-restart.service</code>', '<code>--restart=always</code> restarts a crashed container. After a reboot, <code>podman-restart.service</code> (if it&#x27;s enabled) starts every container that has that restart policy.', 'A quick fix for a container someone already started by hand. Lab 1 shows how to check for this and how to convert to a Quadlet.'],
  ])}
  <p>A Quadlet file has three sections: <code>[Unit]</code> (a description and what it depends on), <code>[Container]</code> (everything you&#x27;d otherwise type after <code>podman run</code>: image, ports, volumes, environment), and <code>[Service]</code>/<code>[Install]</code> (systemd&#x27;s restart policy and &quot;start at boot&quot;). After adding or changing one, run <code>sudo systemctl daemon-reload</code> so systemd regenerates the service. You don&#x27;t run <code>systemctl enable</code> on Quadlet services; the <code>[Install]</code> section takes care of that.</p>

  <h2>Before you start</h2>
  <ul>
    <li>SSH with sudo on 192.168.1.100 and 192.168.1.101, both Rocky Linux 9 or 10 with Podman 5.</li>
    <li>LiteLLM running on .101 with a <strong>master key</strong> and a <strong>database</strong> (virtual keys, used from Lab 3 on, need the database). Lab 1 checks both.</li>
    <li>A model that can call tools. These labs use <code>qwen/qwen3.8-27b</code> in LM Studio. In LM Studio, set its default <strong>context length to at least 32k</strong> (gear icon on the model, then Context Length). LM Studio loads models on demand with that setting, and a small default leaves a &quot;thinking&quot; model no room to answer.</li>
    <li>The labs were tested with LiteLLM <strong>v1.104.0</strong>, Podman 5.8, Python 3.12, <code>openai</code> 3.24, <code>mcp</code> 2.3 and <code>a2a-sdk</code> 1.2.</li>
  </ul>

  <h2>Lab order</h2>
  {table(['Lab', 'What you build', 'Needs'], [
      ['0', 'A basic LiteLLM install with Podman (reference; skip if you have one)', 'none'],
      ['1', 'Check the gateway, make it survive reboots, add the lab model names', '0 or an existing gateway'],
      ['2&ndash;4', 'Chat: curl and Python, virtual keys, a chat web UI', '1'],
      ['5&ndash;9', 'Agents: first agent, agents as services, A2A through the gateway, MCP tools, a coordinator', '1, 3'],
      ['10', 'A coding agent (opencode or Claude Code) through the gateway', '1, 3 (8 for MCP)'],
      ['11', 'Operate it: reboot test, logs, usage per agent, kill switch, upgrades', 'any'],
  ])}
</section>
'''

# ---------------------------------------------------------------- lab 0
L0 = lab(0, 'A Basic LiteLLM Install with Podman', '192.168.1.101 (skip if LiteLLM is already running)',
    goal('see what a minimal LiteLLM install looks like: a config file, an env file of secrets, and two Quadlet units (LiteLLM and its Postgres database) that start at boot.'),
    note('If <code>curl -s http://192.168.1.101:4000/health/liveliness</code> already answers, read this lab for reference and go to Lab 1.', 'Already have LiteLLM?'),
    h3('1. Podman and a directory for the gateway'),
    code(r"""
sudo dnf -y install podman
podman --version                           # 5.x
sudo mkdir -p /opt/litellm
"""),
    h3('2. Secrets'),
    p('Two env files hold everything secret. Podman reads them when it starts each container, so the secrets never appear in the config file or in <code>ps</code> output. <code>openssl rand -hex 24</code> generates a random password; the master key must start with <code>sk-</code>.'),
    code(r"""
sudo install -m 600 /dev/null /opt/litellm/litellm.env      # create both files, readable by root only
sudo install -m 600 /dev/null /opt/litellm/db.env
DBPASS=$(openssl rand -hex 24)
read -rsp 'Admin UI password: ' UIPASS; echo

printf '%s\n' "POSTGRES_USER=litellm" "POSTGRES_PASSWORD=$DBPASS" "POSTGRES_DB=litellm" \
  | sudo tee /opt/litellm/db.env >/dev/null

printf '%s\n' \
  "LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)" \
  "LITELLM_SALT_KEY=sk-$(openssl rand -hex 24)" \
  "DATABASE_URL=postgresql://litellm:$DBPASS@litellm-db:5432/litellm" \
  "UI_USERNAME=admin" "UI_PASSWORD=$UIPASS" \
  "LMSTUDIO_API_BASE=http://192.168.1.194:1234/v1" \
  | sudo tee /opt/litellm/litellm.env >/dev/null
unset DBPASS UIPASS
"""),
    h3('3. The config file'),
    p('<code>model_list</code> maps the names clients ask for (<code>lab-chat</code>, <code>lab-agent</code>) to a real model. <code>os.environ/NAME</code> tells LiteLLM to read a value from the environment. Lab 1 explains these names.'),
    code(r"""
sudo tee /opt/litellm/config.yaml >/dev/null <<'EOF'
model_list:
  - model_name: lab-chat
    litellm_params:
      model: openai/qwen/qwen3.8-27b       # "openai/" = speak the OpenAI API to this server
      api_base: os.environ/LMSTUDIO_API_BASE
      api_key: not-needed
  - model_name: lab-agent
    litellm_params:
      model: openai/qwen/qwen3.8-27b
      api_base: os.environ/LMSTUDIO_API_BASE
      api_key: not-needed

litellm_settings:
  drop_params: true          # ignore request options the model server doesn't support
  request_timeout: 600       # local models can be slow on long prompts

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
EOF
"""),
    h3('4. The Quadlet units'),
    p('Four small files: a private network so LiteLLM can reach the database by the name <code>litellm-db</code>, a named volume for the database files, and one <code>.container</code> file per container. <code>Requires=</code> and <code>After=</code> make systemd start the database first, and <code>Notify=healthy</code> makes it wait until Postgres actually answers.'),
    code(r"""
sudo tee /etc/containers/systemd/litellm.network >/dev/null <<'EOF'
[Network]
NetworkName=litellm
EOF

sudo tee /etc/containers/systemd/litellm-db.volume >/dev/null <<'EOF'
[Volume]
VolumeName=litellm-db
EOF

sudo tee /etc/containers/systemd/litellm-db.container >/dev/null <<'EOF'
[Unit]
Description=Postgres for LiteLLM

[Container]
ContainerName=litellm-db
Image=docker.io/library/postgres:16.15
Network=litellm.network
Volume=litellm-db.volume:/var/lib/postgresql/data
EnvironmentFile=/opt/litellm/db.env
HealthCmd=pg_isready -U litellm -d litellm
HealthInterval=10s
Notify=healthy

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/containers/systemd/litellm.container >/dev/null <<'EOF'
[Unit]
Description=LiteLLM AI gateway
Requires=litellm-db.service
After=litellm-db.service

[Container]
ContainerName=litellm
Image=ghcr.io/berriai/litellm:v1.104.0
Network=litellm.network
PublishPort=4000:4000
EnvironmentFile=/opt/litellm/litellm.env
Volume=/opt/litellm/config.yaml:/app/config.yaml:ro,Z
Exec=--config /app/config.yaml --port 4000

[Service]
Restart=always
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
"""),
    h3('5. Start it'),
    code(r"""
sudo systemctl daemon-reload               # turn the Quadlet files into services
sudo systemctl start litellm               # starts litellm-db first; the first start pulls the images
systemctl status litellm --no-pager
sudo firewall-cmd --permanent --add-port=4000/tcp && sudo firewall-cmd --reload   # if firewalld is running
"""),
    h3('Verify'),
    code(r"""
curl -s http://192.168.1.101:4000/health/liveliness; echo     # "I'm alive!"
curl -s http://192.168.1.101:4000/health/readiness             # "db": "connected"
"""),
    p('Then log in to the admin UI at <code>http://192.168.1.101:4000/ui</code> as <code>admin</code> with the password you chose. To prove it survives a reboot, run <code>sudo systemctl reboot</code>, wait, and repeat the two <code>curl</code> commands.'),
    h3('Notes'),
    ul([
        'The first start runs database migrations and can take a minute or two. <code>sudo journalctl -u litellm -f</code> shows progress; wait for <code>Uvicorn running on http://0.0.0.0:4000</code>.',
        'Pin the image to a version (<code>v1.104.0</code>), not <code>main-stable</code> or <code>latest</code>, so a restart never silently changes the build you run. Lab 11 shows how to upgrade on purpose.',
        '<code>LITELLM_SALT_KEY</code> encrypts any provider keys you later store through the UI. Never change it after that, or LiteLLM can&#x27;t decrypt them.',
        '<code>:Z</code> on the config mount relabels the file for SELinux. Without it the container gets &quot;permission denied&quot; reading <code>config.yaml</code>.',
        'Postgres isn&#x27;t published on the network at all. Only LiteLLM reaches it, over the private <code>litellm</code> network.',
    ]),
)

# ---------------------------------------------------------------- lab 1
L1 = lab(1, 'Check the Gateway and Add the Lab Models', '192.168.1.101, tested from 192.168.1.100',
    goal('confirm the gateway is healthy and has a database, make sure it comes back after a reboot, and give it two model names, <code>lab-chat</code> and <code>lab-agent</code>, that the rest of the labs use.'),
    h3('1. Set up your shell on the agent host'),
    p('You type every command from here on on <strong>192.168.1.100</strong> unless a step says otherwise. Two shell variables hold the gateway address and the <strong>master key</strong>, LiteLLM&#x27;s admin password. Find the key on .101 with <code>sudo grep LITELLM_MASTER_KEY /opt/litellm/litellm.env</code>. <code>read -rsp</code> reads it without echoing it or saving it in your shell history.'),
    code(r"""
ssh 192.168.1.100
sudo dnf -y install jq                     # pretty-prints and filters JSON answers
export GW=http://192.168.1.101:4000
read -rsp 'LiteLLM master key: ' MK; echo; export MK
"""),
    note('Put the <code>export GW=...</code> line in <code>~/.bashrc</code> so new shells have it. Don&#x27;t do that with the master key; re-enter it when you need it.', 'Tip:'),
    h3('2. Is it healthy?'),
    code(r"""
curl -s $GW/health/liveliness; echo                        # "I'm alive!" (no key needed)
curl -s $GW/health/readiness | jq '{status, db}'            # db must be "connected"
curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[].id'   # models it serves now
"""),
    p('If <code>db</code> isn&#x27;t <code>connected</code>, chat still works, but virtual keys (Lab 3) and everything after them won&#x27;t. Add a <code>DATABASE_URL</code> as in Lab 0.'),
    h3('3. Will it come back after a reboot?'),
    p('On <strong>.101</strong>, ask Podman whether the container belongs to a systemd service:'),
    code(r"""
ssh 192.168.1.101
sudo podman inspect litellm --format 'unit={{index .Config.Labels "PODMAN_SYSTEMD_UNIT"}} restart={{.HostConfig.RestartPolicy.Name}}'
systemctl is-enabled podman-restart.service
"""),
    table(['What you see', 'Means', 'Do this'], [
        ['<code>unit=litellm.service</code>', 'It&#x27;s already a Quadlet or systemd service', 'Nothing. Go to step 4.'],
        ['<code>unit=</code> (empty), <code>restart=always</code>, and <code>podman-restart</code> is <code>enabled</code>', 'Started by hand; <code>podman-restart.service</code> starts it at boot', 'It works. Converting it to a Quadlet (below) is still better: you get <code>systemctl</code> and <code>journalctl</code>.'],
        ['<code>unit=</code> (empty) and anything else', 'It won&#x27;t come back after a reboot', 'Convert it to a Quadlet (below), or at least run <code>sudo systemctl enable --now podman-restart.service</code>.'],
    ]),
    p('<strong>Convert a hand-started container to a Quadlet.</strong> First read how it&#x27;s run now: its image, mounts, env file and networks.'),
    code(r"""
sudo podman inspect litellm --format 'image={{.Config.Image}}
cmd={{json .Config.Cmd}}
networks={{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}
{{range .Mounts}}mount={{.Source}} -> {{.Destination}}
{{end}}'
"""),
    p('Write the same settings into a <code>.container</code> file. This example matches a common layout (config and env file in <code>/opt/litellm</code>, a Postgres container reached over a network named <code>docker_default</code>). Use the image and networks your output showed: one <code>Network=</code> line per network, so LiteLLM can still reach its database by name.'),
    code(r"""
sudo tee /etc/containers/systemd/litellm.container >/dev/null <<'EOF'
[Unit]
Description=LiteLLM AI gateway

[Container]
ContainerName=litellm
Image=ghcr.io/berriai/litellm:v1.104.0
Network=docker_default
Network=podman
PublishPort=4000:4000
EnvironmentFile=/opt/litellm/litellm.env
Volume=/opt/litellm/config.yaml:/app/config.yaml:ro,Z
Exec=--config /app/config.yaml --port 4000

[Service]
Restart=always
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
sudo podman rm -f litellm                  # remove the hand-started container (config and data are untouched)
sudo systemctl daemon-reload
sudo systemctl start litellm
systemctl status litellm --no-pager
"""),
    warn('If your database is another container on the same host, its own unit has to start before LiteLLM. Add <code>After=&lt;db-unit&gt;.service</code> under <code>[Unit]</code>, using the <code>PODMAN_SYSTEMD_UNIT</code> label of the database container. Otherwise LiteLLM may start first after a reboot, fail to connect, and keep restarting until the database is up.'),
    h3('4. Add the lab model names'),
    p('Clients never name the real model. They ask for an <strong>alias</strong>, and the gateway decides which model answers. If you later move <code>lab-agent</code> to a bigger model or a cloud provider, you change one line here and every agent follows. Back up the config, then add these two entries to the end of the existing <code>model_list</code> with <code>sudo vi /opt/litellm/config.yaml</code>:'),
    code(r"""
sudo cp -a /opt/litellm/config.yaml /opt/litellm/config.yaml.bak-$(date +%F)
"""),
    code(r"""
  - model_name: lab-chat                   # what chat apps ask for
    litellm_params:
      model: openai/qwen/qwen3.8-27b
      api_base: os.environ/LMSTUDIO_API_BASE
      api_key: not-needed
  - model_name: lab-agent                  # what agents ask for (must support tool calling)
    litellm_params:
      model: openai/qwen/qwen3.8-27b
      api_base: os.environ/LMSTUDIO_API_BASE
      api_key: not-needed
"""),
    p('Both point at the same model for now, so LM Studio never has to swap models in and out of GPU memory. Restart the gateway to load the new config:'),
    code(r"""
sudo systemctl restart litellm             # or "sudo podman restart litellm" if you didn't convert it
sudo journalctl -u litellm -f              # Ctrl-C once you see "Uvicorn running"
"""),
    h3('Verify (back on .100)'),
    code(r"""
curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[].id' | grep lab-
# lab-chat
# lab-agent
"""),
    h3('Notes'),
    ul([
        '<code>LMSTUDIO_API_BASE</code> has to be in the env file (<code>LMSTUDIO_API_BASE=http://192.168.1.194:1234/v1</code>). If it&#x27;s missing, LiteLLM starts but every request to these models fails.',
        'Using a cloud model instead? Use <code>model: anthropic/claude-haiku-4-5-20251001</code> with <code>api_key: os.environ/ANTHROPIC_API_KEY</code>, or <code>model: openai/gpt-4.1-mini</code> with <code>OPENAI_API_KEY</code>, and add the key to the env file. A change to the env file needs <code>systemctl restart</code>; Podman reads it only when it creates the container, and a Quadlet restart re-creates it.',
        'Reasoning (&quot;thinking&quot;) models spend tokens thinking before they answer. If a reply comes back empty with <code>finish_reason: &quot;length&quot;</code>, the context length in LM Studio is too small; raise it.',
        'YAML is indentation-sensitive, and each top-level key (<code>model_list:</code>, <code>litellm_settings:</code>) may appear only once. If LiteLLM won&#x27;t start after an edit, <code>sudo journalctl -u litellm -n 50</code> shows the parse error; restore the backup to get going again.',
    ]),
)

# ---------------------------------------------------------------- lab 2
L2 = lab(2, 'Chat Through the Gateway: curl and Python', '192.168.1.100 → 192.168.1.101',
    goal('understand a chat request and its response, see why a chat client has to send the whole conversation every time, and build a small streaming chat program in Python.'),
    h3('1. One request, piece by piece'),
    code(r"""
curl -s $GW/v1/chat/completions \
  -H "Authorization: Bearer $MK" \
  -H 'Content-Type: application/json' \
  -d '{
        "model": "lab-chat",
        "messages": [
          {"role": "system", "content": "You are a helpful assistant. Answer in one sentence."},
          {"role": "user",   "content": "What does an AI gateway do?"}
        ]
      }' | jq
"""),
    ul([
        '<code>/v1/chat/completions</code> is the OpenAI chat API. LiteLLM speaks it no matter which provider is behind the alias, so any OpenAI-compatible app or library can use the gateway.',
        '<code>Authorization: Bearer</code> carries the key. The master key works for now; Lab 3 gives each app its own key.',
        '<code>messages</code> is the conversation: a <code>system</code> message sets the behaviour, and <code>user</code> messages are what you type.',
    ]),
    p('In the response, the answer is in <code>choices[0].message.content</code>, <code>usage</code> counts the tokens in and out, and <code>model</code> is the alias you asked for. To print just the answer, replace <code>jq</code> with <code>jq -r &#x27;.choices[0].message.content&#x27;</code>.'),
    h3('2. The API has no memory'),
    p('Ask a follow-up question on its own and the model has no idea what you mean:'),
    code(r"""
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model": "lab-chat", "messages": [{"role": "user", "content": "What did I just ask you?"}]}' \
  | jq -r '.choices[0].message.content'
"""),
    p('Every chat app, including ChatGPT-style web UIs, keeps the conversation itself and sends the whole history with every request, adding the model&#x27;s earlier answers as <code>assistant</code> messages:'),
    code(r"""
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model": "lab-chat", "messages": [
        {"role": "user",      "content": "My favourite distro is Rocky Linux."},
        {"role": "assistant", "content": "Nice choice!"},
        {"role": "user",      "content": "What is my favourite distro?"}
      ]}' | jq -r '.choices[0].message.content'
"""),
    p('That&#x27;s also why long conversations get slower and more expensive: every turn re-sends everything before it.'),
    h3('3. Streaming'),
    p('With <code>&quot;stream&quot;: true</code>, the gateway sends the answer in small pieces as the model produces them, the way chat UIs show text appearing word by word. <code>curl -N</code> turns off buffering so you see them arrive:'),
    code(r"""
curl -sN $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model": "lab-chat", "stream": true, "messages": [{"role": "user", "content": "Count from 1 to 5."}]}'
# data: {"choices":[{"delta":{"content":"1"}...}]}
# data: {"choices":[{"delta":{"content":","}...}]}
# ...
# data: [DONE]
"""),
    h3('4. A chat program in Python'),
    p('Install Python 3.12 and the libraries every lab uses into a virtual environment in <code>~/gw-labs</code>. The <code>openai</code> library works with any OpenAI-compatible server; pointing <code>base_url</code> at the gateway is all it takes.'),
    code(r"""
sudo dnf -y install python3.12 python3.12-pip
mkdir -p ~/gw-labs && cd ~/gw-labs
python3.12 -m venv .venv
. .venv/bin/activate                       # run this again in every new shell
pip install "openai==3.24.0" "httpx==0.28.1" "mcp==2.3.0"
"""),
    p('<code>chat.py</code> keeps the history in a list (step 2) and streams each answer (step 3):'),
    write_file('~/gw-labs/chat.py', 'chat.py'),
    code(r"""
KEY=$MK python chat.py
# you> My name is Pat.
# ai > Hi Pat! How can I help you today?
# you> What is my name?
# ai > Your name is Pat.
"""),
    h3('Notes'),
    ul([
        'Change the model per run with <code>MODEL=lab-agent KEY=$MK python chat.py</code>. The program doesn&#x27;t know or care which real model answers.',
        'The admin UI at <code>http://192.168.1.101:4000/ui</code> has a <strong>Playground</strong> page that does the same thing in the browser.',
        'If a request hangs for a minute and then answers, LM Studio was loading the model. The first request after a model unloads is always slow.',
    ]),
)

# ---------------------------------------------------------------- lab 3
L3 = lab(3, 'Virtual Keys: One Key per App', '192.168.1.100 → 192.168.1.101',
    goal('stop handing out the master key: create a virtual key for the chat UI that can only use the lab models, and see the gateway enforce it.'),
    h3('Why'),
    p('The master key can do everything, including creating and deleting keys. Every app and agent in these labs gets its own <strong>virtual key</strong> instead. A virtual key can be limited to certain models, a request rate, a budget, and (Labs 7&ndash;9) certain agents and tools. Every request is logged under the key&#x27;s name, and you can revoke one key without touching the others.'),
    h3('1. Create a key for the chat UI'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{
        "key_alias": "chat-ui",
        "models": ["lab-chat", "lab-agent"],
        "rpm_limit": 60
      }' | jq '{key_alias, key, models, rpm_limit}'
"""),
    ul([
        '<code>key_alias</code> is the name you&#x27;ll see in logs and in the UI. It must be unique: re-running a step that creates a key fails with &quot;Key with alias ... already exists&quot;, so delete the old key (Lab 11) or pick another alias.',
        '<code>models</code> is the allow-list. Leave it out and the key can use every model.',
        '<code>rpm_limit</code> is requests per minute. Request number 61 inside a minute gets HTTP 429.',
    ]),
    p('Copy the <code>key</code> value now. LiteLLM stores only a hash of it, so it can never show you the key again. Keep it in a variable for this lab:'),
    code(r"""
read -rsp 'chat-ui key: ' UIKEY; echo
"""),
    h3('2. See the limits work'),
    code(r"""
# allowed model: answers
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $UIKEY" -H 'Content-Type: application/json' \
  -d '{"model": "lab-chat", "messages": [{"role": "user", "content": "Say hello."}]}' \
  | jq -r '.choices[0].message.content'

# a model that isn't on the key's list: refused before it reaches any model
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $UIKEY" -H 'Content-Type: application/json' \
  -d '{"model": "gemma-4-31b-qat", "messages": [{"role": "user", "content": "Say hello."}]}' \
  | jq -r '.error.message'
# ... key not allowed to access model ...

# the key can't do admin work either
curl -s $GW/key/generate -H "Authorization: Bearer $UIKEY" -H 'Content-Type: application/json' -d '{}' | jq -r '.error.message'
"""),
    h3('3. Look a key up, change it, block it'),
    code(r"""
curl -s "$GW/key/info?key=$UIKEY" -H "Authorization: Bearer $MK" | jq '.info | {key_alias, models, rpm_limit, spend}'

# change a limit in place (the key itself stays the same)
curl -s $GW/key/update -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d "{\"key\": \"$UIKEY\", \"rpm_limit\": 30}" | jq '{key_alias, rpm_limit}'

# every key, by alias
curl -s "$GW/key/list?return_full_object=true" -H "Authorization: Bearer $MK" | jq -r '.keys[] | "\(.key_alias)\t\(.models)"'
"""),
    p('Blocking and deleting a key is in Lab 11.'),
    h3('Notes'),
    ul([
        'Budgets: add <code>&quot;max_budget&quot;: 5, &quot;budget_duration&quot;: &quot;30d&quot;</code> to cap a key at $5 a month. LiteLLM prices requests from its price list, so this works for cloud models. Local models cost $0, so a budget never trips for them; use <code>rpm_limit</code> instead.',
        'Everything here is also in the admin UI under <strong>Virtual Keys</strong>, including the one-time display of a new key.',
        'Store app keys the way the next labs do: in a root-only env file (<code>chmod 600</code>) that Podman passes to the container, never in a Quadlet file or a script.',
    ]),
)

# ---------------------------------------------------------------- lab 4
L4 = lab(4, 'A Chat Web UI: Open WebUI on Podman', '192.168.1.100 (Open WebUI) → 192.168.1.101',
    goal('run Open WebUI as a Quadlet on .100, connected to the gateway with the <code>chat-ui</code> key from Lab 3, so you get a ChatGPT-style web page that starts at boot.'),
    h3('1. The key goes in an env file'),
    code(r"""
sudo mkdir -p /opt/open-webui
sudo install -m 600 /dev/null /opt/open-webui/open-webui.env
printf '%s\n' \
  "OPENAI_API_BASE_URL=http://192.168.1.101:4000/v1" \
  "OPENAI_API_KEY=$UIKEY" \
  "WEBUI_SECRET_KEY=$(openssl rand -hex 32)" \
  | sudo tee /opt/open-webui/open-webui.env >/dev/null
"""),
    p('<code>OPENAI_API_BASE_URL</code> points Open WebUI at the gateway as if it were OpenAI. <code>WEBUI_SECRET_KEY</code> signs login sessions; keeping it fixed means you stay logged in across restarts. (In a new shell, <code>read -rsp</code> the key into <code>UIKEY</code> again first.)'),
    h3('2. The Quadlet units'),
    p('A named volume keeps Open WebUI&#x27;s users, chats and settings when the container is replaced. The container listens on 8080 inside; <code>PublishPort=3000:8080</code> makes that port 3000 on the host.'),
    code(r"""
sudo tee /etc/containers/systemd/open-webui.volume >/dev/null <<'EOF'
[Volume]
VolumeName=open-webui
EOF

sudo tee /etc/containers/systemd/open-webui.container >/dev/null <<'EOF'
[Unit]
Description=Open WebUI chat front end

[Container]
ContainerName=open-webui
Image=ghcr.io/open-webui/open-webui:v0.11.4
PublishPort=3000:8080
Volume=open-webui.volume:/app/backend/data
EnvironmentFile=/opt/open-webui/open-webui.env
Environment=ENABLE_OLLAMA_API=false

[Service]
Restart=always
TimeoutStartSec=900

[Install]
WantedBy=multi-user.target
EOF
"""),
    p('<code>ENABLE_OLLAMA_API=false</code> stops it looking for a local Ollama it doesn&#x27;t need. <code>TimeoutStartSec=900</code> gives the first start time to pull the image, which is several GB.'),
    h3('3. Start it'),
    code(r"""
sudo systemctl daemon-reload
sudo systemctl start open-webui            # first start pulls the image: a few minutes
systemctl status open-webui --no-pager
sudo firewall-cmd --permanent --add-port=3000/tcp && sudo firewall-cmd --reload   # if firewalld is running
curl -s http://localhost:3000/health; echo                     # {"status":true}
"""),
    h3('Verify'),
    ol([
        'Open <code>http://192.168.1.100:3000</code> and sign up. <strong>The first account becomes the admin.</strong>',
        'The model menu at the top lists <code>lab-chat</code> and <code>lab-agent</code>, the two models the <code>chat-ui</code> key allows, and nothing else the gateway serves.',
        'Send a message. Then, in the gateway UI (<code>http://192.168.1.101:4000/ui</code>, <strong>Logs</strong>), you&#x27;ll see the request under the key alias <code>chat-ui</code>.',
    ]),
    h3('Notes'),
    ul([
        'After you&#x27;ve made your admin account, stop strangers signing up: add <code>Environment=ENABLE_SIGNUP=false</code> to the <code>.container</code> file, then <code>sudo systemctl daemon-reload &amp;&amp; sudo systemctl restart open-webui</code>.',
        'Open WebUI also asks the model for chat titles and follow-up suggestions, so one message can show up as several requests in the gateway logs.',
        'Settings from the env file only seed the first start. After that, Open WebUI keeps its own copy (Admin Panel, Settings, Connections). Change the gateway URL or key there, or delete the volume to start over.',
    ]),
)

# ---------------------------------------------------------------- lab 5
L5 = lab(5, 'Agent 1: Your First Tool-Using Agent', '192.168.1.100 → 192.168.1.101',
    goal('build <code>ops-agent</code>, a small Python agent that answers questions about the lab by calling tools (check a URL, check a port, get the time), and see exactly what makes something an &quot;agent&quot;.'),
    h3('What makes it an agent'),
    p('A chat model only produces text. An agent is a loop around the model that lets it <em>do</em> things:'),
    ol([
        'You send the question, plus a description of each tool: its name, what it does, and its parameters as JSON Schema.',
        'Instead of answering, the model can reply with a <strong>tool call</strong>: &quot;run <code>check_port</code> with host=192.168.1.101, port=22&quot;.',
        'Your code runs that function and sends the result back as a <code>tool</code> message.',
        'Repeat until the model replies with plain text. That&#x27;s the answer.',
    ]),
    p('The model never runs anything itself; your code decides which functions exist and runs them. Every step of the loop is an ordinary chat request through the gateway.'),
    h3('1. A key for the agent'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias": "ops-agent", "models": ["lab-agent"], "rpm_limit": 30}' | jq -r .key
read -rsp 'ops-agent key: ' OPS_KEY; echo
"""),
    h3('2. The agent'),
    write_file('~/gw-labs/agent.py', 'agent.py'),
    p('Read it top to bottom: the tools are plain Python functions, <code>TOOL_SPECS</code> describes them to the model, and <code>run()</code> is the loop. <code>max_steps</code> stops a confused model from looping forever. The two settings near the middle (<code>AGENT_PROMPT</code>, <code>AGENT_TOOLS</code>) let Lab 6 reuse this file for a second agent.'),
    h3('3. Run it'),
    code(r"""
cd ~/gw-labs && . .venv/bin/activate
AGENT_KEY=$OPS_KEY python agent.py "Is http://192.168.1.101:4000/health/liveliness answering, is port 22 open on 192.168.1.100, and what time is it?"
#   [tool] check_url({'url': 'http://192.168.1.101:4000/health/liveliness'}) -> HTTP 200 in 16 ms
#   [tool] check_port({'host': '192.168.1.100', 'port': 22}) -> 192.168.1.100:22 is open
#   [tool] get_time({}) -> 2026-10-06T00:27:31+00:00
# - 192.168.1.101:4000/health/liveliness: HTTP 200 (16 ms)
# - 192.168.1.100 port 22: open
# - Time: 2026-10-06 00:27 UTC
"""),
    p('The <code>[tool]</code> lines are the loop at work: the model chose which tools to call and with what arguments, and the program ran them. Try a question that needs no tools (&quot;What is a TCP port?&quot;) and one about a port that&#x27;s closed.'),
    h3('Verify: what the gateway saw'),
    code(r"""
curl -s "$GW/spend/logs?start_date=$(date -u +%F)&end_date=$(date -u -d tomorrow +%F)&summarize=false" \
  -H "Authorization: Bearer $MK" \
  | jq -r '.[] | select(.metadata.user_api_key_alias == "ops-agent") | "\(.startTime)  \(.model_group)  tokens=\(.total_tokens)"'
"""),
    p('One question made several requests, one per pass around the loop, all under the alias <code>ops-agent</code>. Spend logs are written in batches, so the newest requests can take up to a minute to appear.'),
    h3('Notes'),
    ul([
        'The tool descriptions matter as much as the code. The model picks tools by reading <code>description</code>, so vague descriptions get the wrong tool, or none.',
        'Only give an agent tools you&#x27;d be happy for it to call with any arguments. <code>check_port</code> is harmless; a <code>run_shell</code> tool would let the model (and anyone who can put text in front of it) run anything.',
        'The model has to support tool calling. If it answers in prose without ever calling a tool, try a different model behind <code>lab-agent</code>.',
    ]),
)

# ---------------------------------------------------------------- lab 6
L6 = lab(6, 'Agent 2: Run Agents as Always-On Services', '192.168.1.100',
    goal('package the agent in a container image, run two agents from it as Quadlet services (<code>ops-agent</code> with tools and <code>writer-agent</code> without), each with its own key, and talk to them over A2A.'),
    h3('A2A in one paragraph'),
    p('A script is only useful to the person running it. To let other programs and other agents use an agent, it needs a network interface. <strong>A2A</strong> (Agent2Agent) is an open protocol for that. An A2A agent publishes an <strong>agent card</strong>, a JSON description of who it is and what it can do, at <code>/.well-known/agent-card.json</code>, and accepts messages as JSON-RPC <code>SendMessage</code> calls over HTTP. LiteLLM understands A2A, which is what Lab 7 uses.'),
    h3('1. The A2A wrapper'),
    p('This file turns the Lab 5 agent into an A2A server. It imports <code>agent.py</code> unchanged and calls <code>agent.run()</code> for every message that arrives. Settings come from environment variables, so one image can be several agents.'),
    code(r"""
sudo mkdir -p /opt/agents
sudo cp ~/gw-labs/agent.py /opt/agents/
"""),
    write_file('/opt/agents/a2a_server.py', 'a2a_server.py', sudo=True),
    h3('2. Build the image'),
    p('A <code>Containerfile</code> is Podman&#x27;s name for a Dockerfile; the syntax is the same. Pin the library versions so a rebuild next month gets the same code.'),
    code(r"""
sudo tee /opt/agents/Containerfile >/dev/null <<'EOF'
FROM docker.io/library/python:3.12.15-slim
RUN pip install --no-cache-dir "openai==3.24.0" "httpx==0.28.1" "a2a-sdk[http-server]==1.2.2" "uvicorn==0.54.0"
WORKDIR /app
COPY agent.py a2a_server.py ./
USER 1001
CMD ["python", "a2a_server.py"]
EOF
sudo podman build -t localhost/lab-agent:1 /opt/agents
"""),
    p('<code>USER 1001</code> runs the agent as an unprivileged user inside the container. The <code>localhost/</code> prefix marks an image you built yourself, so Podman never tries to pull it from a registry.'),
    h3('3. A second key, then one env file per agent'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias": "writer-agent", "models": ["lab-agent"], "rpm_limit": 30}' | jq -r .key
read -rsp 'writer-agent key: ' WRITER_KEY; echo

sudo install -m 600 /dev/null /opt/agents/ops-agent.env
sudo install -m 600 /dev/null /opt/agents/writer-agent.env
echo "AGENT_KEY=$OPS_KEY"    | sudo tee /opt/agents/ops-agent.env >/dev/null
echo "AGENT_KEY=$WRITER_KEY" | sudo tee /opt/agents/writer-agent.env >/dev/null
"""),
    h3('4. Two Quadlet units, one image'),
    p('The two files differ only in name, port and environment. <code>writer-agent</code> gets no tools and a different system prompt; it turns notes into a readable status update. <code>PUBLIC_URL</code> is the address other hosts use to reach the agent; it goes into the agent card.'),
    code(r"""
sudo tee /etc/containers/systemd/ops-agent.container >/dev/null <<'EOF'
[Unit]
Description=ops-agent (A2A)

[Container]
ContainerName=ops-agent
Image=localhost/lab-agent:1
PublishPort=8601:8601
EnvironmentFile=/opt/agents/ops-agent.env
Environment=GW=http://192.168.1.101:4000
Environment=AGENT_NAME=ops-agent
Environment=PORT=8601
Environment=PUBLIC_URL=http://192.168.1.100:8601
Environment=AGENT_DESCRIPTION="Checks home-lab hosts, ports, URLs and the time using live tools."

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/containers/systemd/writer-agent.container >/dev/null <<'EOF'
[Unit]
Description=writer-agent (A2A)

[Container]
ContainerName=writer-agent
Image=localhost/lab-agent:1
PublishPort=8602:8602
EnvironmentFile=/opt/agents/writer-agent.env
Environment=GW=http://192.168.1.101:4000
Environment=AGENT_NAME=writer-agent
Environment=PORT=8602
Environment=PUBLIC_URL=http://192.168.1.100:8602
Environment=AGENT_TOOLS=off
Environment=AGENT_DESCRIPTION="Turns notes and findings into a short, clear status update for people."
Environment=AGENT_PROMPT="You are writer-agent. Rewrite the notes you are given as a short, friendly status update (3-5 sentences). Do not invent facts."

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start ops-agent writer-agent
systemctl is-active ops-agent writer-agent                   # active, active
sudo firewall-cmd --permanent --add-port={8601,8602}/tcp && sudo firewall-cmd --reload   # if firewalld is running
"""),
    h3('Verify: talk to an agent directly'),
    code(r"""
# the agent card: who it is and where to reach it
curl -s http://192.168.1.100:8601/.well-known/agent-card.json | jq '{name, description, url: .supportedInterfaces[0].url}'

# an A2A message, saved to a file so the JSON is easy to read and reuse
cat > ~/gw-labs/ask.json <<'EOF'
{"jsonrpc": "2.0", "id": "1", "method": "SendMessage",
 "params": {"message": {"role": "ROLE_USER", "messageId": "msg-1",
                        "parts": [{"text": "Is port 22 open on 192.168.1.101?"}]}}}
EOF
curl -s http://192.168.1.100:8601/ -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d @$HOME/gw-labs/ask.json | jq -r '.result.task.status.message.parts[0].text'
# Yes, port 22 is open on 192.168.1.101.

sudo journalctl -u ops-agent -n 5 --no-pager                   # the [tool] lines show what it did
"""),
    p('The reply is an A2A <strong>task</strong>: it has a state (<code>TASK_STATE_COMPLETED</code>) and the answer as a message. Long-running agents use the same structure to report progress.'),
    h3('Notes'),
    ul([
        'Changed <code>agent.py</code> or <code>a2a_server.py</code>? Copy it to <code>/opt/agents</code>, rebuild the image, then <code>sudo systemctl restart ops-agent writer-agent</code>. A restart creates a fresh container from the current image.',
        'Changed only a <code>.container</code> file? <code>sudo systemctl daemon-reload</code>, then restart that service.',
        'Right now anyone on the LAN can call these agents directly on ports 8601 and 8602, with no key. Lab 7 puts them behind the gateway, which checks a key on every call. If you want only the gateway to reach them, allow only 192.168.1.101 to those ports in your firewall.',
        'If <code>systemctl start</code> fails, <code>sudo journalctl -u ops-agent -n 30</code> shows the Python traceback, usually a missing variable or a typo in the env file.',
    ]),
)

# ---------------------------------------------------------------- lab 7
L7 = lab(7, 'Agent 3: Publish Agents Through the Gateway (A2A)', '192.168.1.100 → 192.168.1.101 → agents on .100',
    goal('register both agents with LiteLLM, call <code>ops-agent</code> at <code>/a2a/ops-agent</code> on the gateway with a virtual key, and see that a key without permission can&#x27;t reach it.'),
    h3('Why go through the gateway'),
    p('Calling agents directly (Lab 6) works, but then every caller needs to know every agent&#x27;s address, and nothing checks who&#x27;s calling. Registered with the gateway, all agents live at one address, <code>http://192.168.1.101:4000/a2a/&lt;name&gt;</code>. Each call needs a virtual key that&#x27;s been granted that agent, and every call is logged. You can move an agent to another host by changing its registration, and no caller has to change anything.'),
    h3('1. Register the agents'),
    p('Registration is the agent card plus a name for the gateway. <code>url</code> is where LiteLLM forwards calls.'),
    code(r"""
cat > ~/gw-labs/ops-agent.json <<'EOF'
{
  "agent_name": "ops-agent",
  "agent_card_params": {
    "protocolVersion": "1.0",
    "name": "ops-agent",
    "description": "Checks home-lab hosts, ports, URLs and the time using live tools.",
    "url": "http://192.168.1.100:8601/",
    "version": "1.0.0",
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "capabilities": {"streaming": false},
    "skills": [{"id": "ops", "name": "Lab checks", "tags": ["ops"],
                "description": "Checks URLs, TCP ports and the time."}]
  }
}
EOF
cat > ~/gw-labs/writer-agent.json <<'EOF'
{
  "agent_name": "writer-agent",
  "agent_card_params": {
    "protocolVersion": "1.0",
    "name": "writer-agent",
    "description": "Turns notes and findings into a short, clear status update for people.",
    "url": "http://192.168.1.100:8602/",
    "version": "1.0.0",
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "capabilities": {"streaming": false},
    "skills": [{"id": "write", "name": "Status updates", "tags": ["writing"],
                "description": "Rewrites notes as a short status update."}]
  }
}
EOF

for a in ops-agent writer-agent; do
  curl -s $GW/v1/agents -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
    -d @$HOME/gw-labs/$a.json | jq '{agent_name, agent_id}'
done
"""),
    p('Each agent gets an <code>agent_id</code>. You&#x27;ll use the IDs to grant access. List them again any time with:'),
    code(r"""
curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r '.[] | "\(.agent_id)  \(.agent_name)"'
"""),
    h3('2. Call an agent through the gateway'),
    p('With the master key first, to prove the route works. It&#x27;s the same <code>ask.json</code> from Lab 6, sent to the gateway instead of to the agent:'),
    code(r"""
curl -s $GW/a2a/ops-agent -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d @$HOME/gw-labs/ask.json | jq -r '.result.task.status.message.parts[0].text'
"""),
    h3('3. A caller key that may use ops-agent only'),
    p('Virtual keys can&#x27;t see <em>any</em> agent until you grant one. The grant goes in <code>object_permission.agents</code> and takes agent <strong>IDs</strong>, not names:'),
    code(r"""
OPS_ID=$(curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r '.[] | select(.agent_name=="ops-agent") | .agent_id')
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d "{\"key_alias\": \"ops-caller\", \"models\": [\"lab-agent\"], \"object_permission\": {\"agents\": [\"$OPS_ID\"]}}" \
  | jq -r .key
read -rsp 'ops-caller key: ' CALLER_KEY; echo
"""),
    h3('Verify'),
    code(r"""
# the key sees only the agent it was granted
curl -s $GW/v1/agents -H "Authorization: Bearer $CALLER_KEY" | jq -r '.[].agent_name'
# ops-agent

# and can call it
curl -s $GW/a2a/ops-agent -H "Authorization: Bearer $CALLER_KEY" -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d @$HOME/gw-labs/ask.json | jq -r '.result.task.status.message.parts[0].text'

# the chat-ui key from Lab 3 was never granted any agent
curl -s $GW/v1/agents -H "Authorization: Bearer $UIKEY" | jq length
# 0
"""),
    h3('Notes'),
    ul([
        'There are two keys in every gateway call to an agent. The <strong>caller&#x27;s</strong> key decides whether it may reach the agent. The <strong>agent&#x27;s own</strong> key (in its env file) is what the agent uses for its model calls. The logs show both, so you can tell who asked and what the agent spent answering.',
        'LiteLLM also accepts older A2A v0.3 clients (<code>&quot;method&quot;: &quot;message/send&quot;</code>, parts with <code>&quot;kind&quot;: &quot;text&quot;</code>) and translates them for these 1.0 agents.',
        'The admin UI&#x27;s <strong>Agents</strong> page shows the same registrations, and can add or delete them.',
        'To change where an agent lives, delete its registration (<code>curl -X DELETE $GW/v1/agents/&lt;agent_id&gt;</code>) and register it again with the new <code>url</code>. Its ID changes, so update the keys that were granted the old one.',
        'Treat what an agent returns, including its card, as untrusted text. Another agent&#x27;s reply can contain instructions aimed at the model reading it.',
    ]),
)

# ---------------------------------------------------------------- lab 8
L8 = lab(8, 'Agent 4: Tools from an MCP Server, Through the Gateway', '192.168.1.100 (MCP server, agent) and 192.168.1.101',
    goal('move the lab tools out of the agent into an MCP server running as a Quadlet, register it with LiteLLM, and build an agent that finds its tools through the gateway.'),
    h3('MCP in one paragraph'),
    p('In Lab 5 the tools were written into the agent. <strong>MCP</strong> (Model Context Protocol) moves tools into a separate server that any agent or app can connect to and ask &quot;what tools do you have?&quot;. Register MCP servers with LiteLLM, and agents connect to one endpoint, <code>http://192.168.1.101:4000/mcp/</code>, with their virtual key. They see only the tools that key has been granted, and every tool call is logged.'),
    h3('1. The MCP server'),
    p('The <code>mcp</code> library turns plain Python functions into MCP tools; the docstring becomes the tool description the model reads.'),
    code(r"""
sudo mkdir -p /opt/lab-tools
"""),
    write_file('/opt/lab-tools/lab_tools.py', 'lab_tools.py', sudo=True),
    code(r"""
sudo tee /opt/lab-tools/Containerfile >/dev/null <<'EOF'
FROM docker.io/library/python:3.12.15-slim
RUN pip install --no-cache-dir "mcp==2.3.0" "httpx==0.28.1"
COPY lab_tools.py /app/lab_tools.py
USER 1001
EXPOSE 8701
CMD ["python", "/app/lab_tools.py"]
EOF
sudo podman build -t localhost/lab-tools:1 /opt/lab-tools

sudo tee /etc/containers/systemd/lab-tools.container >/dev/null <<'EOF'
[Unit]
Description=lab-tools MCP server

[Container]
ContainerName=lab-tools
Image=localhost/lab-tools:1
PublishPort=8701:8701

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl start lab-tools
systemctl is-active lab-tools
sudo firewall-cmd --permanent --add-port=8701/tcp && sudo firewall-cmd --reload   # if firewalld is running
"""),
    h3('2. Register it with LiteLLM (on .101)'),
    p('MCP servers are part of the gateway config. Add this block at the end of <code>/opt/litellm/config.yaml</code> as a new top-level key, then restart:'),
    code(r"""
mcp_servers:
  lab_tools:                               # the server's name in LiteLLM; tool names get this prefix
    url: http://192.168.1.100:8701/mcp
    transport: http
    description: Home-lab checks (URL, port, DNS)
"""),
    code(r"""
sudo systemctl restart litellm
"""),
    p('Back on .100, check that LiteLLM sees the tools:'),
    code(r"""
curl -s $GW/mcp-rest/tools/list -H "Authorization: Bearer $MK" | jq -r '.tools[].name'
# check_url
# check_port
# dns_lookup
"""),
    h3('3. A key that may use lab_tools'),
    p('As with agents, a virtual key sees no MCP servers until you grant them, in <code>object_permission.mcp_servers</code>. Server names work here.'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias": "mcp-agent", "models": ["lab-agent"], "object_permission": {"mcp_servers": ["lab_tools"]}}' \
  | jq -r .key
read -rsp 'mcp-agent key: ' MCP_KEY; echo
"""),
    h3('4. An agent with no tools of its own'),
    p('<code>mcp_agent.py</code> connects to the gateway&#x27;s MCP endpoint, asks which tools its key may use, hands them to the model, and sends each tool call back through the gateway. Compare it to <code>agent.py</code>: the loop is the same, and the tool code is gone.'),
    write_file('~/gw-labs/mcp_agent.py', 'mcp_agent.py'),
    h3('Verify'),
    code(r"""
cd ~/gw-labs && . .venv/bin/activate
AGENT_KEY=$MCP_KEY python mcp_agent.py "Resolve github.com, check whether port 4000 is open on 192.168.1.101, and fetch http://192.168.1.101:4000/health/liveliness."
# tools from the gateway: ['lab_tools-check_url', 'lab_tools-check_port', 'lab_tools-dns_lookup']
#   [mcp] lab_tools-dns_lookup({'name': 'github.com'}) -> 140.82.112.3
#   [mcp] lab_tools-check_port({'host': '192.168.1.101', 'port': 4000}) -> 192.168.1.101:4000 is open
#   [mcp] lab_tools-check_url({'url': 'http://192.168.1.101:4000/health/liveliness'}) -> HTTP 200 in 18 ms
# All three checks done: ...
"""),
    p('A key that was never granted <code>lab_tools</code> can&#x27;t even connect. Try the <code>ops-agent</code> key:'),
    code(r"""
curl -s $GW/mcp-rest/tools/list -H "Authorization: Bearer $OPS_KEY" | jq -r .message
# ... The key is not allowed to access any MCP servers.
"""),
    p('<code>mcp_agent.py</code> run with that key stops at the connect step with <code>MCPError: Server returned an error response</code> for the same reason.'),
    h3('Notes'),
    ul([
        'Through the gateway, tool names get the server name as a prefix (<code>lab_tools-check_port</code>), so two servers can both have a tool called <code>search</code>.',
        'Anything that speaks MCP can use the same endpoint and key, including the coding agents in Lab 10.',
        'To limit a key to some of a server&#x27;s tools, add <code>&quot;mcp_tool_permissions&quot;: {&quot;lab_tools&quot;: [&quot;check_port&quot;]}</code> to its <code>object_permission</code>.',
        'Remote MCP servers run code and return text the model will act on. Register only servers you trust.',
    ]),
)

# ---------------------------------------------------------------- lab 9
L9 = lab(9, 'Agent 5: A Coordinator That Delegates to Other Agents', '192.168.1.100 → 192.168.1.101 → agents on .100',
    goal('build a coordinator agent that can&#x27;t check anything itself. It asks the gateway which agents it may use, splits the job up, and delegates each part over A2A: checks to <code>ops-agent</code>, the write-up to <code>writer-agent</code>.'),
    h3('How it works'),
    p('The coordinator is the same loop as Lab 5 with a single tool, <code>ask_agent(agent, message)</code>. The list of agents isn&#x27;t hard-coded. It comes from <code>/v1/agents</code>, so the coordinator sees exactly the agents its key was granted, with their descriptions, and the model picks one by reading those descriptions. Every hop goes through the gateway: the coordinator&#x27;s own model calls, its calls to other agents, and those agents&#x27; model calls.'),
    h3('1. A key for the coordinator, granted both agents'),
    code(r"""
IDS=$(curl -s $GW/v1/agents -H "Authorization: Bearer $MK" \
  | jq -c '[.[] | select(.agent_name == "ops-agent" or .agent_name == "writer-agent") | .agent_id]')
echo "$IDS"                                 # two agent IDs
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d "{\"key_alias\": \"coordinator\", \"models\": [\"lab-agent\"], \"object_permission\": {\"agents\": $IDS}}" \
  | jq -r .key
read -rsp 'coordinator key: ' COORD_KEY; echo
"""),
    h3('2. The coordinator'),
    write_file('~/gw-labs/coordinator.py', 'coordinator.py'),
    p('Two details worth noticing. The <code>enum</code> in the tool&#x27;s parameters limits the model to agent names that actually exist. The system prompt says it can&#x27;t check anything itself, which stops it guessing instead of delegating.'),
    h3('Verify'),
    code(r"""
cd ~/gw-labs && . .venv/bin/activate
AGENT_KEY=$COORD_KEY python coordinator.py
# agents on the gateway: ['ops-agent', 'writer-agent']
#   -> ops-agent: Check http://192.168.1.101:4000/health/liveliness and whether SSH (port 22) is open on 192.168.1.100 ...
#   <- ops-agent: Gateway health endpoint: UP, HTTP 200 in 18 ms. Port 22 on 192.168.1.100: open ...
#   -> writer-agent: Please turn these findings into a short, clear status update ...
#   <- writer-agent: Quick check-in: the gateway is up and responding normally ...
# **Status update: all services operational** ...
"""),
    p('Give it your own goals: &quot;Find out whether Open WebUI on 192.168.1.100:3000 is up and write a one-line note for the team.&quot; While it runs, <code>sudo journalctl -u ops-agent -f</code> in another terminal shows the tool calls happening inside the delegated agent.'),
    h3('See the whole chain'),
    code(r"""
curl -s "$GW/spend/logs?start_date=$(date -u +%F)&end_date=$(date -u -d tomorrow +%F)&summarize=false" \
  -H "Authorization: Bearer $MK" \
  | jq -r 'group_by(.metadata.user_api_key_alias)[] | "\(.[0].metadata.user_api_key_alias // "master")\t\(length) requests"'
# coordinator    4 requests
# ops-agent      ...
# writer-agent   ...
"""),
    p('One question to the coordinator turned into requests under three different keys. That&#x27;s the point of putting the gateway in the middle: you can see how much work each agent did, and limit or switch off any one of them.'),
    h3('Notes'),
    ul([
        'To add a specialist, run another agent from the same image (a new <code>.container</code> file with a new name, port and prompt), register it, and grant its ID to the coordinator&#x27;s key. The coordinator&#x27;s code doesn&#x27;t change.',
        'Delegation multiplies requests. A <code>max_steps</code> cap and an <code>rpm_limit</code> on every agent&#x27;s key keep a confused coordinator from flooding the model server.',
        'This coordinator waits for each answer before it continues. Long-running agents should return a task right away and report progress; A2A supports that through task states and streaming.',
    ]),
)

# ---------------------------------------------------------------- lab 10
L10 = lab(10, 'Coding Agents Through the Gateway: opencode and Claude Code', 'any host with the agent installed → 192.168.1.101',
    goal('point a coding agent at the gateway instead of straight at a model server, with its own key, so its usage is logged and limited like every other agent, and give it the <code>lab_tools</code> MCP tools.'),
    h3('1. A key for coding agents'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias": "coding-agent", "models": ["lab-agent"], "rpm_limit": 120, "object_permission": {"mcp_servers": ["lab_tools"]}}' \
  | jq -r .key
"""),
    p('Coding agents send many requests per task, so give them a higher <code>rpm_limit</code> than the other agents.'),
    h3('2. opencode'),
    p('opencode can talk to any OpenAI-compatible server. Add the gateway as a provider in <code>~/.config/opencode/opencode.json</code> (or the <code>config.json</code> you already have; merge these keys into it). <code>{env:LITELLM_KEY}</code> reads the key from an environment variable, so the key isn&#x27;t stored in the file.'),
    code(r"""
{
  "$schema": "https://opencode.ai/config.json",
  "model": "litellm/lab-agent",
  "provider": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LiteLLM gateway",
      "options": {
        "baseURL": "http://192.168.1.101:4000/v1",
        "apiKey": "{env:LITELLM_KEY}"
      },
      "models": {
        "lab-agent": { "name": "lab-agent (via gateway)", "tools": true, "limit": { "context": 98304, "output": 8192 } }
      }
    }
  },
  "mcp": {
    "lab-tools": {
      "type": "remote",
      "url": "http://192.168.1.101:4000/mcp/",
      "headers": { "Authorization": "Bearer {env:LITELLM_KEY}" },
      "enabled": true
    }
  }
}
"""),
    code(r"""
read -rsp 'coding-agent key: ' LITELLM_KEY; echo; export LITELLM_KEY
opencode run "Reply with the single word pong."
opencode run "Use the lab-tools check_port tool to check whether port 22 is open on 192.168.1.101."
"""),
    p('Set <code>limit.context</code> to the context length the model is actually loaded with, so opencode compacts the conversation before it overflows.'),
    h3('3. Claude Code'),
    p('Claude Code speaks Anthropic&#x27;s Messages API. LiteLLM serves that too, at <code>/v1/messages</code>, and translates it for whatever model is behind the alias, including the local one:'),
    code(r"""
curl -s $GW/v1/messages -H "Authorization: Bearer $MK" -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{"model": "lab-agent", "max_tokens": 400, "messages": [{"role": "user", "content": "Say pong."}]}' \
  | jq -r '.content[] | select(.type == "text") | .text'
# pong
"""),
    p('Then set these in the shell where you start Claude Code:'),
    code(r"""
export ANTHROPIC_BASE_URL=http://192.168.1.101:4000
export ANTHROPIC_AUTH_TOKEN=<coding-agent key>     # sent as "Authorization: Bearer"
export ANTHROPIC_MODEL=lab-agent
export ANTHROPIC_DEFAULT_HAIKU_MODEL=lab-agent     # used for small background tasks
claude mcp add --transport http lab-tools http://192.168.1.101:4000/mcp/ \
  --header "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN"
claude
"""),
    h3('Verify'),
    p('Run a small task in either agent, then look in the gateway UI under <strong>Logs</strong>, filtered by key alias <code>coding-agent</code>. Every request the coding agent made is there, including the MCP tool calls.'),
    h3('Notes'),
    ul([
        'Use <code>ANTHROPIC_AUTH_TOKEN</code>, not <code>ANTHROPIC_API_KEY</code>. Claude Code treats the latter as a real Anthropic key.',
        'A local 27B model is fine for trying this out and for small edits. For serious work on a big codebase, put a larger or cloud model behind a separate alias and add it to this key&#x27;s <code>models</code>.',
        'Both agents can run shell commands on the machine they run on. Keep their permission prompts on (<code>&quot;permission&quot;: {&quot;bash&quot;: &quot;ask&quot;}</code> in opencode); the gateway controls model access, not what the agent does locally.',
    ]),
)

# ---------------------------------------------------------------- lab 11
L11 = lab(11, 'Operate It: Reboots, Logs, Usage, Kill Switches, Upgrades', '192.168.1.100 and 192.168.1.101',
    goal('prove everything comes back after a reboot, know where to look when something breaks, see what each app and agent used, and shut one off without touching the rest.'),
    h3('1. Everything you built, as services'),
    table(['Host', 'Service', 'Port', 'Files'], [
        ['.101', '<code>litellm</code> (+ <code>litellm-db</code> from Lab 0)', '4000', '<code>/opt/litellm/</code>, <code>/etc/containers/systemd/litellm*</code>'],
        ['.100', '<code>open-webui</code>', '3000', '<code>/opt/open-webui/</code>, volume <code>open-webui</code>'],
        ['.100', '<code>ops-agent</code>, <code>writer-agent</code>', '8601, 8602', '<code>/opt/agents/</code>, image <code>localhost/lab-agent:1</code>'],
        ['.100', '<code>lab-tools</code>', '8701', '<code>/opt/lab-tools/</code>, image <code>localhost/lab-tools:1</code>'],
        ['.100', 'scripts (not services)', '&ndash;', '<code>~/gw-labs/</code>'],
    ]),
    code(r"""
# on .100
systemctl list-units --no-pager 'open-webui*' 'ops-agent*' 'writer-agent*' 'lab-tools*'
sudo podman ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
"""),
    h3('2. The reboot test'),
    p('This is the real proof. Reboot the agent host, and then the gateway:'),
    code(r"""
sudo systemctl reboot                      # on .100; reconnect after a minute
systemctl is-active open-webui ops-agent writer-agent lab-tools    # all "active"
curl -s http://localhost:8601/.well-known/agent-card.json | jq -r .name

# on .101
sudo systemctl reboot
curl -s http://192.168.1.101:4000/health/readiness | jq '{status, db}'
"""),
    p('If a service isn&#x27;t active, check that its file is in <code>/etc/containers/systemd/</code>, that it has an <code>[Install]</code> section with <code>WantedBy=multi-user.target</code>, and run <code>sudo /usr/libexec/podman/quadlet -dryrun</code> to see Quadlet&#x27;s complaints about any file it couldn&#x27;t convert.'),
    h3('3. Logs'),
    code(r"""
sudo journalctl -u ops-agent -f                 # one service, live
sudo journalctl -u litellm --since '10 min ago' # on .101: gateway errors, model failures
sudo journalctl -b -u 'ops-agent' -u 'lab-tools' --no-pager   # everything since the last boot
"""),
    p('A Quadlet container&#x27;s output goes to the journal, so you use <code>journalctl</code>, not <code>podman logs</code> (which still works too).'),
    h3('4. Who used what'),
    code(r"""
curl -s "$GW/spend/logs?start_date=$(date -u -d '7 days ago' +%F)&end_date=$(date -u -d tomorrow +%F)&summarize=false" \
  -H "Authorization: Bearer $MK" \
  | jq -r 'group_by(.metadata.user_api_key_alias)[]
           | "\(.[0].metadata.user_api_key_alias // "master")\t\(length) requests\t\(map(.total_tokens) | add) tokens"'
"""),
    p('The gateway UI shows the same under <strong>Usage</strong> (charts per key and model) and <strong>Logs</strong> (each request, with its prompt and response).'),
    h3('5. Kill switch'),
    code(r"""
# block one key: every request with it fails right away, and nothing else is affected
curl -s $GW/key/block   -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d "{\"key\": \"$OPS_KEY\"}" | jq '{key_alias, blocked}'
curl -s $GW/key/unblock -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d "{\"key\": \"$OPS_KEY\"}" | jq '{key_alias, blocked}'

# delete a key for good
curl -s $GW/key/delete  -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d "{\"keys\": [\"$CALLER_KEY\"]}"

# stop an agent from being reachable through the gateway
curl -s -X DELETE $GW/v1/agents/<agent_id> -H "Authorization: Bearer $MK"
"""),
    p('Blocking <code>ops-agent</code>&#x27;s key stops that agent from reaching any model, even when someone calls it directly on port 8601. That&#x27;s the advantage of agents having their own keys instead of sharing one.'),
    h3('6. Upgrades'),
    p('<strong>An agent:</strong> edit the code in <code>/opt/agents</code>, rebuild with a new tag, point the Quadlet at it, restart. Keeping the old tag makes rolling back a one-line change.'),
    code(r"""
sudo podman build -t localhost/lab-agent:2 /opt/agents
sudo sed -i 's#localhost/lab-agent:1#localhost/lab-agent:2#' /etc/containers/systemd/{ops,writer}-agent.container
sudo systemctl daemon-reload && sudo systemctl restart ops-agent writer-agent
"""),
    p('<strong>LiteLLM (on .101):</strong> back up the database, change the image tag, restart. Read the release notes for the versions you skip first.'),
    code(r"""
sudo podman exec litellm-db pg_dump -U litellm litellm | sudo tee /opt/litellm/backup-$(date +%F).sql >/dev/null
sudo sed -i 's#litellm:v1.104.0#litellm:v1.105.0#' /etc/containers/systemd/litellm.container
sudo systemctl daemon-reload && sudo systemctl restart litellm      # pulls the new image, then runs migrations
curl -s http://192.168.1.101:4000/openapi.json | jq -r .info.version
"""),
    h3('Clean up the labs'),
    code(r"""
# on .100: stop and remove the services, their files and images
sudo systemctl stop open-webui ops-agent writer-agent lab-tools
sudo rm /etc/containers/systemd/{open-webui.container,open-webui.volume,ops-agent.container,writer-agent.container,lab-tools.container}
sudo systemctl daemon-reload
sudo podman volume rm open-webui
sudo podman rmi localhost/lab-agent:1 localhost/lab-tools:1
sudo rm -rf /opt/agents /opt/lab-tools /opt/open-webui ~/gw-labs
# on .101: remove mcp_servers and the lab- models from config.yaml, restart litellm,
# then delete the lab keys and agents in the admin UI (Virtual Keys, Agents)
"""),
)

labs_html = ''.join([L0, L1, L2, L3, L4, L5, L6, L7, L8, L9, L10, L11])
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
<meta name="description" content="Hands-on labs for running chat apps and AI agents through a LiteLLM gateway with rootful Podman: virtual keys, Open WebUI, tool-using agents, A2A, MCP, multi-agent coordination and coding agents.">
<link rel="icon" href="{favicon}">
{STYLE}
</head>
<body id="top">
<button class="menu" type="button" aria-expanded="false" aria-controls="sidebar">Labs</button>
<div class="layout">
<aside id="sidebar">
  <div class="brand"><strong>LiteLLM Gateway Labs</strong><span>agents .100 &nbsp;/&nbsp; gateway .101:4000</span></div>
  <input class="search" type="search" placeholder="Search labs (e.g. quadlet, mcp)" aria-label="Search labs">
  <div class="progress"><span id="prog">0 of {N} labs done</span><div class="bar"><i id="progbar"></i></div></div>
  <nav aria-label="Labs"><ul>{nav}</ul><p class="empty" id="empty">No lab mentions that.</p></nav>
  <div class="side-links">
    <a href="/"><strong>Cropsey IT</strong> home</a>
    <a href="rhcsa.html"><strong>RHCSA Labs</strong></a>
    <a href="#overview">Overview &amp; Podman basics</a>
    <a href="#lab-11">Operate &amp; clean up</a>
    <button class="theme" type="button" id="theme">Switch to dark</button>
  </div>
</aside>
<main>
{overview}
{labs_html}
</main>
</div>
{script}
</body>
</html>
'''

out = f'{SITE}/litellm.html'
open(out, 'w', encoding='utf-8').write(page)
print(f'wrote {out}: {len(page):,} bytes, {N} labs')
