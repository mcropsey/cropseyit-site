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
STYLE = re.search(r'<style>.*?</style>', rh, re.S).group(0).replace('</style>', '''
code.tool { white-space: nowrap; overflow-wrap: normal; }
.explain { margin: -8px 0 18px; padding: 10px 16px 12px; border: 1px solid var(--rule); border-top: 0; border-radius: 0 0 8px 8px; font-size: .9rem; }
.explain > p { margin: 0 0 8px; font-size: .75rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; color: var(--teal); }
.explain dl { margin: 0; display: grid; grid-template-columns: minmax(0, 18em) minmax(0, 1fr); gap: 8px 18px; }
.explain dt, .explain dd { margin: 0; min-width: 0; }
@media (max-width: 640px) { .explain dl { grid-template-columns: minmax(0, 1fr); gap: 2px; } .explain dd { margin-bottom: 8px; } }
</style>''')
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


def explain(*rows):
    """A 'what these commands do' box under a code block, from (command, explanation) pairs.
    A command given as plain text is escaped and shown as code; one starting with '<' is used as is."""
    items = ''.join(f'<dt>{c if c.startswith("<") else f"<code>{e(c)}</code>"}</dt><dd>{t}</dd>'
                    for c, t in rows)
    return f'<div class="explain"><p>What these commands do</p><dl>{items}</dl></div>'


def write_file(path, name, sudo=False):
    """A code block that saves one of the tested programs to PATH with a heredoc."""
    cmd = f"sudo tee {path} >/dev/null <<'EOF'" if sudo else f"cat > {path} <<'EOF'"
    how = (f'<code>sudo tee</code> writes everything between this line and the final <code>EOF</code> line into <code>{path}</code>. '
           'It runs as root because <code>/opt</code> belongs to root.' if sudo else
           f'<code>cat &gt;</code> writes everything between this line and the final <code>EOF</code> line into <code>{path}</code>.')
    return code(f"{cmd}\n{src(name)}\nEOF") + explain(
        (cmd, how + ' The quotes around <code>&#x27;EOF&#x27;</code> save the program exactly as typed, so the shell doesn&#x27;t touch any <code>$</code> in it. '
              'Paste the whole block at once, or open the file in an editor and paste just the program.'))


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
      ['<strong>gateway</strong> 192.168.1.101', 'The LiteLLM gateway, port 4000', 'LiteLLM and its Postgres database. <strong>Assumed to be running already.</strong> Lab 0 is the reference for installing or fixing it.'],
      ['<strong>agent host</strong> 192.168.1.100', 'Everything you build, and where you type the commands', 'Open WebUI (3000), ops-agent (8601), writer-agent (8602), the lab-tools MCP server (8701), and your Python scripts'],
      ['<strong>model server</strong> 192.168.1.194', 'Where the model actually runs', 'LM Studio on port 1234 serving <code>qwen/qwen3.8-27b</code>. Any OpenAI-compatible server, or a cloud provider, works the same way.'],
  ])}
  <p>Nothing talks to the model server directly. The chat UI, the agents and the coding agent all send their requests to the gateway, and the gateway checks the key and forwards the request to the model. That&#x27;s what lets you swap models, limit an app, or see what an agent did, in one place.</p>

  <h2>Podman and Quadlet</h2>
  <p>Every container in these labs runs under <strong>rootful Podman</strong> (<code>sudo podman</code>); there&#x27;s no Docker anywhere. A container started with plain <code>podman run</code> stops when the host reboots and stays stopped, because there&#x27;s no always-running daemon to bring it back, as there is with Docker. So every lab uses <strong>Quadlet</strong> instead: you write a small <code>.container</code> file in <code>/etc/containers/systemd/</code>, and Podman turns it into a normal systemd service. <code>systemctl start</code>, <code>status</code>, <code>restart</code> and <code>journalctl</code> all work, and it starts at boot. This is the Red Hat-recommended way on Podman 4.4 and newer (Rocky 9 and 10 have Podman 5).</p>
  <p>A Quadlet file has three sections: <code>[Unit]</code> (a description and what it depends on), <code>[Container]</code> (everything you&#x27;d otherwise type after <code>podman run</code>: image, ports, volumes, environment), and <code>[Service]</code>/<code>[Install]</code> (systemd&#x27;s restart policy and &quot;start at boot&quot;). After adding or changing one, run <code>sudo systemctl daemon-reload</code> so systemd regenerates the service. You don&#x27;t run <code>systemctl enable</code> on Quadlet services; the <code>[Install]</code> section takes care of that.</p>

  <h2>Before you start</h2>
  <ul>
    <li>SSH with sudo on 192.168.1.100 and 192.168.1.101, both Rocky Linux 9 or 10 with Podman 5.</li>
    <li>LiteLLM running on .101 with a <strong>master key</strong> and a <strong>database</strong> (virtual keys, used from Lab 3 on, need it). Lab 0 covers whatever is missing.</li>
    <li>A model that can call tools. These labs use <code>qwen/qwen3.8-27b</code> in LM Studio. In LM Studio, set its default <strong>context length to at least 32k</strong> (gear icon on the model, then Context Length). LM Studio loads models on demand with that setting, and a small default leaves a &quot;thinking&quot; model no room to answer.</li>
    <li>The labs were tested with LiteLLM <strong>v1.104.0</strong>, Podman 5.8, Python 3.12, <code>openai</code> 3.24, <code>mcp</code> 2.3 and <code>a2a-sdk</code> 1.2.</li>
  </ul>

  <h2 id="reading">How to read the commands</h2>
  <p>The labs are mostly shell commands, and the same handful of tools comes up again and again. Each command block has a <strong>What these commands do</strong> box under it that goes through it line by line. This section explains the tools once, so the boxes can stay short.</p>
  {table(['Tool', 'What it&#x27;s for here', 'What you&#x27;ll see'], [
      ['<code class="tool">curl</code>', 'Sends an HTTP request from the command line. The gateway is a web API, so <code>curl</code> is how you talk to it without writing a program.', '<code>-s</code> silent (no progress bar); <code>-H &#x27;Name: value&#x27;</code> adds a header; <code>-d &#x27;...&#x27;</code> sends a request body and makes it a POST; <code>-d @file</code> sends a file&#x27;s contents as the body; <code>-X DELETE</code> picks a different HTTP method; <code>-N</code> shows streamed output as it arrives'],
      ['<code class="tool">jq</code>', 'Reads the JSON the gateway sends back and pretty-prints or picks out parts of it. Without it you get one long unreadable line.', '<code>jq</code> on its own pretty-prints everything; <code>jq .info.version</code> picks one field; <code>jq &#x27;{a, b}&#x27;</code> keeps only fields <code>a</code> and <code>b</code>; <code>-r</code> prints text without quotes; <code>.[]</code> goes through each item of a list; <code>select(...)</code> keeps only the items that match'],
      ['<code class="tool">sudo tee FILE</code>', 'Writes its input into a file as root. You can&#x27;t use <code>sudo echo ... &gt; FILE</code>, because the <code>&gt;</code> is handled by <em>your</em> shell, which isn&#x27;t root.', '<code>&gt;/dev/null</code> after it throws away the copy <code>tee</code> also prints to the screen'],
      ['<code class="tool">&lt;&lt;&#x27;EOF&#x27;</code> &hellip; <code class="tool">EOF</code>', 'A <strong>heredoc</strong>: the lines up to the <code>EOF</code> line are fed to the command as its input. It&#x27;s how the labs write config files and JSON without opening an editor.', 'With quotes (<code>&lt;&lt;&#x27;EOF&#x27;</code>) the text is saved exactly as typed. Without quotes (<code>&lt;&lt;EOF</code>) the shell first replaces variables like <code>$OPS_ID</code> with their values, which is how a key or ID gets into a file'],
      ['<code class="tool">systemctl</code>', 'Starts, stops and checks services. Every container in the labs is a systemd service, thanks to Quadlet.', '<code>daemon-reload</code> re-reads unit files after you change them; <code>start</code>, <code>restart</code>, <code>status</code>; <code>is-active</code> prints just <code>active</code> or <code>inactive</code>'],
      ['<code class="tool">journalctl</code>', 'Shows a service&#x27;s log, which for a container is everything the program printed.', '<code>-u NAME</code> picks the service; <code>-f</code> keeps following new lines until Ctrl-C; <code>-n 30</code> shows the last 30 lines'],
      ['<code class="tool">podman</code>', 'Builds and inspects containers. You rarely start containers with it directly; systemd does that.', '<code>build -t NAME DIR</code> builds an image from the <code>Containerfile</code> in <code>DIR</code>; <code>inspect</code> shows how a container was set up; <code>exec NAME CMD</code> runs a command inside a running container'],
      ['<code class="tool">firewall-cmd</code>', 'Opens a port in the host firewall so other machines can reach a service.', '<code>--permanent --add-port=3000/tcp</code> saves the rule, and <code>--reload</code> applies it. Skip it if <code>systemctl is-active firewalld</code> says <code>inactive</code>'],
  ])}
  <h3>Shell basics the labs rely on</h3>
  <ul>
    <li><strong>Variables.</strong> <code>export GW=http://...</code> stores a value; <code>$GW</code> uses it. The labs keep the gateway address in <code>$GW</code> and keys in variables like <code>$MK</code>, so you never paste a key into a command. Variables only last as long as the shell. From Lab 3 on, every key you create is also saved in <code>~/gw-labs/keys.env</code>, so after you log in again, <code>. ~/gw-labs/keys.env</code> brings them all back; only <code>$GW</code> and the master key need setting again.</li>
    <li><strong>Reading a secret.</strong> <code>read -rsp &#x27;Prompt: &#x27; MK</code> asks you to paste a value and stores it in <code>MK</code>. <code>-s</code> hides what you type, <code>-p</code> shows the prompt, <code>-r</code> keeps backslashes as they are. The <code>echo</code> after it just moves to a new line, since the hidden input doesn&#x27;t.</li>
    <li><strong><code>$(...)</code></strong> runs the command inside and drops its output in place. <code>$(date +%F)</code> becomes today&#x27;s date, such as <code>2026-10-06</code>, which the labs use to name backup files.</li>
    <li><strong>Quotes.</strong> Inside <code>&#x27;single quotes&#x27;</code> the shell changes nothing, which is why JSON is written that way. Inside <code>&quot;double quotes&quot;</code> it still replaces <code>$VARIABLES</code>, which is why the <code>Authorization</code> header uses them.</li>
    <li><strong>Long lines.</strong> A <code>\\</code> at the end of a line means the command carries on to the next line. <code>|</code> sends one command&#x27;s output into the next, as in <code>curl ... | jq</code>.</li>
    <li><strong>Grey text after <code>#</code></strong> is a comment. The shell ignores it, so you can paste whole blocks. Comment lines that show output tell you what to expect, not what to type.</li>
  </ul>
  <p>A typical gateway call, taken apart:</p>
  {code(r"""
curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[].id'
""")}
  {explain(
      ('curl -s $GW/v1/models', 'Send a GET request to <code>/v1/models</code> on the gateway, without the progress bar.'),
      ('-H "Authorization: Bearer $MK"', 'Prove who you are. Every gateway call except the health checks needs a key in this header; <code>$MK</code> is replaced with your key before <code>curl</code> runs.'),
      ("| jq -r '.data[].id'", 'The answer is <code>{&quot;data&quot;: [{&quot;id&quot;: &quot;qwen3.8-27b&quot;, ...}, ...]}</code>. This goes into <code>data</code>, takes each item&#x27;s <code>id</code>, and prints them one per line.'),
  )}
  <p>Calls that send data add <code>-H &#x27;Content-Type: application/json&#x27;</code>, which tells the gateway the body is JSON, and <code>-d</code> with the body. When the body contains a key or ID from a variable, the labs first write it to a small <code>.json</code> file with an unquoted heredoc and then send it with <code>-d @file</code>. You can <code>cat</code> the file to see exactly what&#x27;s being sent.</p>

  <h2>Lab order</h2>
  {table(['Lab', 'What you build', 'Needs'], [
      ['0', 'Reference, not a lab: installing LiteLLM, converting it to a Quadlet, giving it its own Postgres, upgrades', 'only if your gateway is missing something'],
      ['1', 'Get the master key, connect to the gateway, and add the two model names the labs use', 'a running gateway'],
      ['2&ndash;4', 'Chat: curl and Python, virtual keys, a chat web UI', '1'],
      ['5&ndash;9', 'Agents: first agent, agents as services, A2A through the gateway, MCP tools, a coordinator', '1, 3'],
      ['10', 'A coding agent (opencode or Claude Code) through the gateway', '1, 3 (8 for MCP)'],
      ['11', 'Operate it: reboot test, logs, usage per agent, kill switch, upgrades', 'any'],
  ])}
</section>
'''

# ---------------------------------------------------------------- lab 0
L0 = lab(0, 'Reference: Setting Up LiteLLM (only if you need to)', '192.168.1.101',
    goal('everything about installing and running the gateway itself, in one place. The labs assume LiteLLM is already running; come here only for the parts your gateway is missing.'),
    p('The rest of the labs never install or reconfigure LiteLLM. They talk to it through its API, as any app would. Use this table to find which parts of this lab, if any, you need:'),
    table(['Your situation', 'Do'], [
        ['No LiteLLM yet', '<a href="#l0-podman">Part 1</a>, <a href="#l0-install">Part 2</a>'],
        ['LiteLLM was started by hand with <code>podman run</code>, so it isn&#x27;t a systemd service', '<a href="#l0-quadlet">Part 3</a>'],
        ['LiteLLM has no database, or uses a database inside another app&#x27;s Postgres', '<a href="#l0-db">Part 4</a>'],
        ['Upgrades, backups and other ways to run it', '<a href="#l0-options">Part 5</a>'],
    ]),

    '<h3 id="l0-podman">Part 1: Podman</h3>',
    p('Rocky Linux and RHEL ship Podman in the base repositories. Quadlet, the feature that turns container files into systemd services (see the overview), is built into Podman 4.4 and newer.'),
    code(r"""
sudo dnf -y install podman jq
podman --version                           # 5.x on Rocky 9.6+ and 10
ls /usr/libexec/podman/quadlet             # present = Quadlet is available
"""),
    explain(
        ('sudo dnf -y install podman jq', 'Install Podman (runs containers) and jq (reads JSON, see <a href="#reading">How to read the commands</a>). <code>-y</code> answers yes to the confirmation prompt.'),
        ('podman --version', 'Check the version. Quadlet needs 4.4 or newer.'),
        ('ls /usr/libexec/podman/quadlet', 'Quadlet is a small program shipped with Podman that systemd runs at boot and on <code>daemon-reload</code>. If <code>ls</code> finds it, you have it.'),
    ),
    p('Everything here runs as root (<code>sudo podman</code>). Root containers and their Quadlet files live in <code>/etc/containers/systemd/</code>; rootless ones would live in <code>~/.config/containers/systemd/</code> and need <code>loginctl enable-linger</code> to start at boot, which is why these labs stick to rootful.'),

    '<h3 id="l0-install">Part 2: A fresh install</h3>',
    p('The result is two Quadlet services: <code>litellm-db</code> (Postgres, which stores virtual keys, agents and spend logs) and <code>litellm</code> (the gateway), joined by a private network so the database is never exposed on the LAN.'),
    p('<strong>Secrets.</strong> Two env files, readable by root only. Podman reads them when it creates each container, so no secret appears in a config file or in <code>ps</code> output. The master key must start with <code>sk-</code>.'),
    code(r"""
sudo mkdir -p /opt/litellm
sudo touch /opt/litellm/db.env /opt/litellm/litellm.env
sudo chmod 600 /opt/litellm/db.env /opt/litellm/litellm.env

DBPASS=$(openssl rand -hex 24)
read -rsp 'Admin UI password: ' UIPASS; echo

sudo tee /opt/litellm/db.env >/dev/null <<EOF
POSTGRES_USER=litellm
POSTGRES_PASSWORD=$DBPASS
POSTGRES_DB=litellm
EOF

sudo tee /opt/litellm/litellm.env >/dev/null <<EOF
LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)
LITELLM_SALT_KEY=sk-$(openssl rand -hex 24)
DATABASE_URL=postgresql://litellm:$DBPASS@litellm-db:5432/litellm
UI_USERNAME=admin
UI_PASSWORD=$UIPASS
LMSTUDIO_API_BASE=http://192.168.1.194:1234/v1
EOF

unset DBPASS UIPASS
sudo grep MASTER_KEY /opt/litellm/litellm.env      # your master key: save it in a password manager
"""),
    explain(
        ('sudo mkdir -p /opt/litellm', 'Make the directory for the gateway&#x27;s files. <code>-p</code> means no error if it already exists.'),
        ('sudo touch ... / sudo chmod 600 ...', 'Create the two env files empty and make them readable and writable by root only (<code>600</code>), <em>before</em> any secret goes into them.'),
        ('DBPASS=$(openssl rand -hex 24)', '<code>openssl rand -hex 24</code> prints 48 random hex characters. That becomes the database password, kept in a variable for the next steps. You never need to type it.'),
        ("read -rsp 'Admin UI password: ' UIPASS; echo", 'Ask you for the password you want for the web UI, without showing it on screen.'),
        ('sudo tee /opt/litellm/db.env >/dev/null <<EOF', 'Write the three lines below into <code>db.env</code>. The heredoc is unquoted (<code>&lt;&lt;EOF</code>), so <code>$DBPASS</code> is replaced with the real password. Postgres reads these variables on first start to create its user and database.'),
        ('sudo tee /opt/litellm/litellm.env ...', 'The same for LiteLLM. Each <code>$(openssl rand -hex 24)</code> is replaced with a fresh random value, so the master key and salt key are generated right here. <code>DATABASE_URL</code> tells LiteLLM where Postgres is: user <code>litellm</code>, that password, host <code>litellm-db</code> (the database container&#x27;s name), port 5432.'),
        ('unset DBPASS UIPASS', 'Remove the passwords from your shell now that they&#x27;re saved in the files.'),
        ('sudo grep MASTER_KEY ...', 'Print the line containing the master key, which you&#x27;ll need in Lab 1.'),
    ),
    p('<strong>Config.</strong> <code>model_list</code> is the list of models the gateway serves. <code>model_name</code> is the name clients ask for; <code>model</code> is the real model, where the <code>openai/</code> prefix means &quot;talk to this server with the OpenAI API&quot;, which LM Studio speaks. <code>os.environ/NAME</code> tells LiteLLM to read a value from the environment. Add one entry per model you want to serve.'),
    code(r"""
sudo tee /opt/litellm/config.yaml >/dev/null <<'EOF'
model_list:
  - model_name: qwen3.8-27b
    litellm_params:
      model: openai/qwen/qwen3.8-27b       # the model's id in LM Studio
      api_base: os.environ/LMSTUDIO_API_BASE
      api_key: not-needed                  # LM Studio doesn't check keys

litellm_settings:
  drop_params: true          # ignore request options the model server doesn't support
  request_timeout: 600       # local models can be slow on long prompts

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  store_model_in_db: true    # reload agents and other API-added objects from the database at every start
EOF
"""),
    explain(
        ("sudo tee /opt/litellm/config.yaml >/dev/null <<'EOF'", 'Write the YAML below into <code>config.yaml</code>. The heredoc is quoted, so <code>os.environ/...</code> lines are saved as typed; LiteLLM looks those values up in the env file when it starts. The secrets stay out of this file, so it&#x27;s safe to show people.'),
        ('drop_params / request_timeout', 'Two quality-of-life settings: silently drop request options LM Studio doesn&#x27;t support instead of failing, and wait up to 10 minutes for slow local models.'),
        ('general_settings', 'The master key and database, both read from the environment.'),
        ('store_model_in_db: true', 'Agents you register through the API (Lab 7) are saved in the database, but LiteLLM only loads them back when it starts if this is on. Without it, every restart or reboot empties the gateway&#x27;s agent list, although the rows are still in the database. It also lets you add models from the admin UI.'),
    ),
    p('<strong>Quadlet files.</strong> A network, a volume for the database files, and one <code>.container</code> file per container. <code>Requires=</code> and <code>After=</code> start the database first, and <code>Notify=healthy</code> makes systemd wait until Postgres actually answers before it starts LiteLLM.'),
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
RestartSec=10
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
"""),
    explain(
        ('litellm.network', 'A private container network called <code>litellm</code>. Containers on it reach each other by container name, which is why <code>DATABASE_URL</code> can say <code>litellm-db</code>. Nothing outside the host can reach the database.'),
        ('litellm-db.volume', 'A named volume: storage that Podman manages and that outlives the container, so the database survives restarts and upgrades.'),
        ('Image=', 'Which image to run, with a pinned version tag. Podman downloads it on the first start.'),
        ('Network= / Volume=', 'Join the network and mount the volume above. Quadlet files refer to each other by file name (<code>litellm.network</code>).'),
        ('EnvironmentFile=', 'Load the variables from the env file you made, so secrets don&#x27;t appear in this file.'),
        ('HealthCmd= / Notify=healthy', 'Every 10 seconds, run <code>pg_isready</code> inside the container to check Postgres answers. <code>Notify=healthy</code> tells systemd the service has only started once that check passes.'),
        ('Requires= / After=', 'LiteLLM needs the database: start <code>litellm-db</code> first, and wait for it.'),
        ('PublishPort=4000:4000', 'Make port 4000 inside the container reachable on port 4000 of the host (<code>host:container</code>).'),
        ('Volume=/opt/litellm/config.yaml:/app/config.yaml:ro,Z', 'Show the host&#x27;s config file inside the container at <code>/app/config.yaml</code>, read-only (<code>ro</code>). <code>Z</code> relabels it for SELinux so the container is allowed to read it.'),
        ('Exec=', 'Arguments passed to the program in the image: which config to use and which port to listen on.'),
        ('Restart= / RestartSec= / TimeoutStartSec=', 'Restart it whenever it stops, 10 seconds apart, and allow 5 minutes for the first start, which downloads the image.'),
        ('WantedBy=multi-user.target', 'Start it at boot.'),
    ),
    p('<strong>Start and check it.</strong>'),
    code(r"""
sudo systemctl daemon-reload               # turn the Quadlet files into services
sudo systemctl start litellm               # starts litellm-db first; the first start pulls the images
sudo journalctl -u litellm -f              # Ctrl-C once you see "Uvicorn running on http://0.0.0.0:4000"
sudo firewall-cmd --permanent --add-port=4000/tcp && sudo firewall-cmd --reload   # if firewalld is running

curl -s http://192.168.1.101:4000/health/liveliness; echo     # "I'm alive!"
curl -s http://192.168.1.101:4000/health/readiness             # "db": "connected"
"""),
    explain(
        ('sudo systemctl daemon-reload', 'Make systemd run Quadlet, which reads the files in <code>/etc/containers/systemd/</code> and generates <code>litellm.service</code> and <code>litellm-db.service</code>.'),
        ('sudo systemctl start litellm', 'Start the gateway. Because of <code>Requires=</code>, systemd starts the database first.'),
        ('sudo journalctl -u litellm -f', 'Watch the gateway&#x27;s log as it starts. Ctrl-C stops watching; the service keeps running.'),
        ('sudo firewall-cmd ... && ...', 'Allow port 4000 through the firewall permanently, then apply the change. <code>&amp;&amp;</code> runs the second command only if the first worked.'),
        ('curl -s .../health/liveliness; echo', 'Ask the gateway whether it&#x27;s running. No key is needed. The <code>echo</code> adds the newline the answer lacks.'),
        ('curl -s .../health/readiness', 'Ask whether it&#x27;s ready, which includes a check that the database is reachable.'),
    ),
    note('In LM Studio, give the model a default <strong>context length of 32k or more</strong> (gear icon on the model, then Context Length). LM Studio loads models on demand with that setting, and reasoning (&quot;thinking&quot;) models spend tokens thinking before they answer. With a small context they can use it all up and return an empty reply with <code>finish_reason: &quot;length&quot;</code>.', 'Model server:'),
    p('The admin UI is at <code>http://192.168.1.101:4000/ui</code> (user <code>admin</code>, the password you chose). The first start runs about 185 database migrations and takes a minute or two.'),

    '<h3 id="l0-quadlet">Part 3: Convert a hand-started container into a Quadlet</h3>',
    p('If LiteLLM was started with <code>podman run</code>, it isn&#x27;t a systemd service. With <code>--restart=always</code> and <code>podman-restart.service</code> enabled it does come back after a reboot, but you can&#x27;t manage it with <code>systemctl</code>, its logs aren&#x27;t in the journal, and if the container is removed the only record of how it was created is your memory. Converting fixes all three. First, record exactly how it runs now, and keep a copy for rollback:'),
    code(r"""
sudo podman inspect litellm | jq '.[0] | {
    image:        .Config.Image,
    networks:     (.NetworkSettings.Networks | keys),
    ports:        .HostConfig.PortBindings,
    created_with: (.Config.CreateCommand | join(" "))
  }'
sudo podman inspect litellm | sudo tee /opt/litellm/inspect.bak-$(date +%F).json >/dev/null
sudo chmod 600 /opt/litellm/inspect.bak-*.json         # it contains the env, including the master key
"""),
    explain(
        ('sudo podman inspect litellm', 'Print everything Podman knows about the container, as a large JSON list with one entry.'),
        ("| jq '.[0] | { ... }'", 'Take that one entry (<code>.[0]</code>) and build a small summary of the four things you need: the image, the networks it&#x27;s on (<code>keys</code> lists their names), the published ports, and the full <code>podman run</code> command it was created with (<code>join(&quot; &quot;)</code> turns the list of words back into one line).'),
        ('... | sudo tee /opt/litellm/inspect.bak-$(date +%F).json', 'Save the complete inspect output as a backup, named with today&#x27;s date, so you can recreate the container exactly if you need to roll back.'),
        ('sudo chmod 600 ...', 'Make the backup root-only: it includes the environment, and so the master key.'),
    ),
    p('Translate what you found into a <code>.container</code> file: <code>-p</code> becomes <code>PublishPort=</code>, <code>-v</code> becomes <code>Volume=</code>, <code>--env-file</code> becomes <code>EnvironmentFile=</code>, each network becomes a <code>Network=</code> line, and the arguments after the image name become <code>Exec=</code>. For example, a container created with <code>podman run -d --name litellm --restart=always -p 4000:4000 -v /opt/litellm/config.yaml:/app/config.yaml:ro,Z --env-file /opt/litellm/litellm.env ghcr.io/berriai/litellm:v1.104.0 --config /app/config.yaml --port 4000</code>, and later connected to a network named <code>docker_default</code> where its database lives, becomes:'),
    code(r"""
sudo tee /etc/containers/systemd/litellm.container >/dev/null <<'EOF'
[Unit]
Description=LiteLLM AI gateway

[Container]
ContainerName=litellm
Image=ghcr.io/berriai/litellm:v1.104.0
Network=podman
Network=docker_default
PublishPort=4000:4000
EnvironmentFile=/opt/litellm/litellm.env
Volume=/opt/litellm/config.yaml:/app/config.yaml:ro,Z
Exec=--config /app/config.yaml --port 4000

[Service]
Restart=always
RestartSec=10
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
sudo /usr/libexec/podman/quadlet -dryrun 2>/dev/null | grep ^ExecStart    # the podman run command it will use
"""),
    explain(
        ('Network=podman / Network=docker_default', 'One line per network the container was on. <code>podman</code> is Podman&#x27;s default network; <code>docker_default</code> is the example&#x27;s extra one.'),
        ('quadlet -dryrun', 'Run Quadlet without changing anything and print the services it <em>would</em> generate. <code>2&gt;/dev/null</code> hides its progress messages.'),
        ('| grep ^ExecStart', 'Keep only the lines starting with <code>ExecStart</code>: the exact <code>podman run</code> command systemd will use.'),
    ),
    p('Compare that <code>ExecStart</code> line with the original command. When they match, swap the containers. Config, env file and database are untouched; only the container is recreated, so the gateway is down for 20&ndash;30 seconds:'),
    code(r"""
sudo podman rm -f litellm
sudo systemctl daemon-reload
sudo systemctl start litellm
sudo podman inspect litellm | jq -r '.[0].Config.Labels.PODMAN_SYSTEMD_UNIT'    # litellm.service
curl -s http://192.168.1.101:4000/health/readiness             # empty for ~20 s while it starts; run it again
"""),
    explain(
        ('sudo podman rm -f litellm', 'Stop and delete the hand-started container (<code>-f</code> stops it first). Only the container goes; its config and data are files and volumes outside it.'),
        ('daemon-reload / start litellm', 'Generate the service from your new file and start it. systemd now creates the container.'),
        ("jq -r '.[0].Config.Labels.PODMAN_SYSTEMD_UNIT'", 'Podman labels every container that a systemd service created with the service&#x27;s name. Seeing <code>litellm.service</code> proves the conversion worked.'),
    ),
    p('Rollback: delete the <code>.container</code> file, run <code>sudo systemctl daemon-reload</code>, and rerun the original <code>podman run</code> command from the inspect output (plus <code>podman network connect</code> for any extra network).'),
    warn('Check that the database comes back after a reboot too. If LiteLLM&#x27;s database lives in another app&#x27;s container that has no systemd service and a restart policy of <code>no</code>, LiteLLM will start after a reboot and find no database. <code>RestartSec=10</code> keeps it retrying, but the real fix is Part 4.'),
    note('If converting isn&#x27;t an option right now, at least make sure the existing container restarts at boot: it needs <code>--restart=always</code> (check with <code>sudo podman inspect litellm | jq -r &#x27;.[0].HostConfig.RestartPolicy.Name&#x27;</code>) and <code>sudo systemctl enable --now podman-restart.service</code>.', 'Quick fix:'),

    '<h3 id="l0-db">Part 4: Give LiteLLM its own Postgres</h3>',
    p('LiteLLM works without a database, but then there are no virtual keys, agents, MCP servers stored through the API, or spend logs, so most of these labs won&#x27;t work. A database inside another application&#x27;s Postgres works, but ties the gateway to that application: it shares its admin login and starts and stops with it. This part moves LiteLLM to a Postgres of its own, keeping every key and log.'),
    p('<strong>1. Create the new database.</strong> Create <code>db.env</code>, <code>litellm.network</code>, <code>litellm-db.volume</code> and <code>litellm-db.container</code> exactly as in <a href="#l0-install">Part 2</a> (skip the parts that write <code>litellm.env</code>, <code>config.yaml</code> and <code>litellm.container</code>), then start only the database. The gateway keeps running on the old one meanwhile.'),
    code(r"""
sudo systemctl daemon-reload
sudo systemctl start litellm-db
sudo podman exec litellm-db psql -U litellm -d litellm -c 'select version();'
"""),
    explain(
        ('sudo podman exec litellm-db psql ...', 'Run <code>psql</code>, the Postgres command-line client, inside the new database container: log in as user <code>litellm</code> (<code>-U</code>) to database <code>litellm</code> (<code>-d</code>) and run one SQL command (<code>-c</code>). A version string back means the database is up and the login works.'),
    ),
    p('<strong>2. Copy the data.</strong> Stop LiteLLM so nothing is written during the copy, then dump the old database and load it into the new one. The example assumes the old database is <code>litellm</code> in a container named <code>postgresdb</code> with the admin user <code>admin</code>; check yours with <code>sudo grep DATABASE_URL /opt/litellm/litellm.env</code>. <code>--no-owner --no-privileges</code> leaves out the old server&#x27;s user names, so everything ends up owned by the new <code>litellm</code> user.'),
    code(r"""
sudo systemctl stop litellm                # or: sudo podman stop litellm
sudo podman exec postgresdb pg_dump -U admin -d litellm --no-owner --no-privileges \
  | sudo tee /opt/litellm/litellm-db-$(date +%F).sql >/dev/null
sudo chmod 600 /opt/litellm/litellm-db-*.sql
sudo cat /opt/litellm/litellm-db-$(date +%F).sql \
  | sudo podman exec -i litellm-db psql -q -v ON_ERROR_STOP=1 -U litellm -d litellm >/dev/null && echo restored
"""),
    explain(
        ('sudo systemctl stop litellm', 'Stop the gateway so no new keys or logs are written while you copy.'),
        ('podman exec postgresdb pg_dump ...', '<code>pg_dump</code> runs inside the <em>old</em> database container and prints the whole <code>litellm</code> database as SQL commands that rebuild it.'),
        ('| sudo tee /opt/litellm/litellm-db-$(date +%F).sql', 'Save that SQL to a dated file on the host. It&#x27;s your copy and your backup.'),
        ('sudo cat ... | podman exec -i litellm-db psql ...', 'Feed the file into <code>psql</code> in the <em>new</em> container. <code>-i</code> lets <code>podman exec</code> pass your input into the container. <code>-q</code> is quiet, and <code>ON_ERROR_STOP=1</code> stops at the first error instead of carrying on with half a database.'),
        ('>/dev/null && echo restored', 'Hide psql&#x27;s output and print <code>restored</code> only if it succeeded.'),
    ),
    p('Check that the important tables arrived with the same number of rows (run each line against both databases):'),
    code(r"""
for t in LiteLLM_VerificationToken LiteLLM_SpendLogs LiteLLM_AgentsTable _prisma_migrations; do
  old=$(sudo podman exec postgresdb psql -U admin   -d litellm -Atc "select count(*) from \"$t\"")
  new=$(sudo podman exec litellm-db psql -U litellm -d litellm -Atc "select count(*) from \"$t\"")
  echo "$t  old=$old  new=$new"
done
"""),
    explain(
        ('for t in A B C D; do ... done', 'A shell loop: run the lines inside once for each table name, with the name in <code>$t</code>.'),
        ('old=$(... psql -Atc "select count(*) ...")', 'Count the rows of that table in the old database and store the number in <code>old</code>. <code>-At</code> prints just the number, without headers. The table name is in <code>\\&quot;</code> quotes because LiteLLM&#x27;s table names contain capital letters.'),
        ('new=$(...)', 'The same count in the new database.'),
        ('echo "$t  old=$old  new=$new"', 'Print both counts side by side. They should match on every line.'),
    ),
    p('<strong>3. Point LiteLLM at it.</strong> Change <code>DATABASE_URL</code> in the env file to the new database, using the password from <code>db.env</code>. Then make the Quadlet start after the database and join its network. You can drop the old database&#x27;s network if LiteLLM only used it for the database.'),
    code(r"""
sudo cp -a /opt/litellm/litellm.env /opt/litellm/litellm.env.bak-$(date +%F)
P=$(sudo grep ^POSTGRES_PASSWORD /opt/litellm/db.env | cut -d= -f2)
sudo sed -i "s#^DATABASE_URL=.*#DATABASE_URL=postgresql://litellm:$P@litellm-db:5432/litellm#" /opt/litellm/litellm.env
unset P
sudo vi /etc/containers/systemd/litellm.container
#   under [Unit]:       Requires=litellm-db.service
#                       After=litellm-db.service
#   under [Container]:  Network=litellm.network   (replacing the old database's network)
sudo systemctl daemon-reload
sudo systemctl start litellm
curl -s http://192.168.1.101:4000/health/readiness                # "db": "connected"
"""),
    explain(
        ('sudo cp -a ... litellm.env.bak-$(date +%F)', 'Back up the env file first. <code>-a</code> keeps its permissions, so the copy is root-only too.'),
        ('P=$(sudo grep ^POSTGRES_PASSWORD ... | cut -d= -f2)', 'Read the new database&#x27;s password: <code>grep</code> finds the line starting (<code>^</code>) with <code>POSTGRES_PASSWORD</code>, and <code>cut -d= -f2</code> keeps what comes after the <code>=</code>.'),
        ('sudo sed -i "s#^DATABASE_URL=.*#DATABASE_URL=...#" ...', '<code>sed -i</code> edits the file in place. <code>s#old#new#</code> means substitute: replace the whole <code>DATABASE_URL=</code> line (<code>.*</code> is &quot;everything after&quot;) with the new one. <code>#</code> separates the parts instead of the usual <code>/</code> because the URL is full of slashes.'),
        ('sudo vi ...litellm.container', 'Open the Quadlet file and make the three changes in the grey comments. In <code>vi</code>: <code>i</code> to type, Esc then <code>:wq</code> to save and quit.'),
        ('daemon-reload / start / curl readiness', 'Apply the changed file, start the gateway, and check that it reaches the new database.'),
    ),
    p('Make a request or two, then check that the newest spend log row is in the <em>new</em> database: <code>sudo podman exec litellm-db psql -U litellm -d litellm -Atc &#x27;select max(&quot;startTime&quot;) from &quot;LiteLLM_SpendLogs&quot;&#x27;</code>. Once you&#x27;re satisfied, drop the old copy (<code>sudo podman exec postgresdb dropdb -U admin litellm</code>) and keep the dump file as a backup.'),
    note('An external Postgres (a database server, a managed service) works the same way: create a database and user there, point <code>DATABASE_URL</code> at it, and leave out the <code>litellm-db</code> files and the <code>Requires=</code> line.', 'Other options:'),

    '<h3 id="l0-options">Part 5: Upgrades, backups and options</h3>',
    p('<strong>Which change needs what.</strong>'),
    table(['You changed', 'Run'], [
        ['<code>config.yaml</code> or <code>litellm.env</code>', '<code>sudo systemctl restart litellm</code> (a Quadlet restart creates a fresh container, so env file changes are picked up)'],
        ['A <code>.container</code>, <code>.network</code> or <code>.volume</code> file', '<code>sudo systemctl daemon-reload</code>, then restart the service'],
        ['Keys, agents, MCP servers (through the API or UI)', 'Nothing; they&#x27;re stored in the database and take effect at once'],
    ]),
    p('<strong>Back up the database</strong> before every upgrade, and on a schedule if the spend logs matter to you:'),
    code(r"""
sudo podman exec litellm-db pg_dump -U litellm litellm | sudo tee /opt/litellm/backup-$(date +%F).sql >/dev/null
sudo chmod 600 /opt/litellm/backup-*.sql
"""),
    explain(
        ('podman exec litellm-db pg_dump -U litellm litellm', 'Dump the whole database as SQL, from inside its container.'),
        ('| sudo tee /opt/litellm/backup-$(date +%F).sql', 'Save it to a file named with today&#x27;s date. To restore, feed the file back into <code>psql</code> as in Part 4.'),
        ('sudo chmod 600 ...', 'Root-only: the dump contains the hashed keys and every logged prompt.'),
    ),
    p('<strong>Upgrade LiteLLM</strong> by changing the image tag. Read the release notes for the versions you&#x27;re skipping first; LiteLLM runs its own database migrations at startup.'),
    code(r"""
sudo sed -i 's#litellm:v1.104.0#litellm:v1.105.0#' /etc/containers/systemd/litellm.container
sudo systemctl daemon-reload && sudo systemctl restart litellm      # pulls the new image, then migrates
curl -s http://192.168.1.101:4000/openapi.json | jq -r .info.version
"""),
    explain(
        ("sudo sed -i 's#litellm:v1.104.0#litellm:v1.105.0#' ...", 'Edit the Quadlet file in place, replacing the old image tag with the new one. Opening it in <code>vi</code> and changing the <code>Image=</code> line does the same.'),
        ('daemon-reload && restart litellm', 'Regenerate the service from the changed file, then restart it. The new container uses the new image, which Podman downloads first.'),
        ('curl ... /openapi.json | jq -r .info.version', 'The gateway describes its own API at <code>/openapi.json</code>, including its version number. This prints just the version.'),
    ),
    ul([
        '<strong>Pin the version.</strong> A floating tag such as <code>main-stable</code> or <code>latest</code> means you can&#x27;t tell which build you run, and a pull can silently change it. Compromised LiteLLM releases were published to PyPI in March 2026, so know exactly what you run. For full reproducibility, pin the digest: <code>Image=ghcr.io/berriai/litellm@sha256:...</code> (<code>sudo podman image inspect --format &#x27;{{index .RepoDigests 0}}&#x27; &lt;image&gt;</code> prints it).',
        'Cloud models go in <code>model_list</code> the same way: <code>model: anthropic/claude-haiku-4-5-20251001</code> with <code>api_key: os.environ/ANTHROPIC_API_KEY</code>, or <code>model: openai/gpt-4.1-mini</code> with <code>api_key: os.environ/OPENAI_API_KEY</code>, and the key itself in <code>litellm.env</code>.',
        '<code>LITELLM_SALT_KEY</code> encrypts provider keys you store through the UI. Never change it after that, or LiteLLM can&#x27;t decrypt them. Older installs without one use the master key, which then mustn&#x27;t change either.',
        '<code>:Z</code> on a mount relabels the file for SELinux. Without it the container gets &quot;permission denied&quot; reading <code>config.yaml</code>.',
        'Without Podman: <code>pip install &#x27;litellm[proxy]==1.104.0&#x27;</code> in a Python 3.12 venv runs the same gateway with <code>litellm --config config.yaml --port 4000</code>. You then write your own systemd unit to keep it running.',
        'Production extras these labs don&#x27;t need: Redis (shared rate limits and caching across several LiteLLM instances), and a reverse proxy with TLS in front of port 4000.',
    ]),
)

# ---------------------------------------------------------------- lab 1
L1 = lab(1, 'Connect to the Gateway and Add the Lab Model Names', '192.168.1.100 → 192.168.1.101',
    goal('get the master key, set up your shell on the agent host, then give the gateway two new model names, <code>lab-chat</code> and <code>lab-agent</code>, that every later lab uses.'),
    h3('1. The master key and your shell'),
    p('First, get the <strong>master key</strong>, LiteLLM&#x27;s admin password. It lives on the gateway in <code>/opt/litellm/litellm.env</code>, readable by root only. Read it on .101:'),
    code(r"""
ssh 192.168.1.101
sudo grep '^LITELLM_MASTER_KEY=' /opt/litellm/litellm.env   # the key is everything after the =
exit
"""),
    explain(
        ('ssh 192.168.1.101', 'Log in to the gateway host.'),
        ("sudo grep '^LITELLM_MASTER_KEY=' /opt/litellm/litellm.env", 'Print the line of the env file that sets the master key. <code>sudo</code> is needed because the file is root-only (<code>600</code>). <code>^</code> means &quot;at the start of the line&quot;, so only that one line matches. The key is the part after <code>=</code>, starting with <code>sk-</code>; copy it.'),
        ('exit', 'Log out of .101 again.'),
    ),
    p('Now set up your shell. You type every command from here on on <strong>192.168.1.100</strong> unless a step says otherwise. Two shell variables hold the gateway address and the master key. <code>read -rsp</code> reads the key without echoing it or saving it in your shell history.'),
    code(r"""
ssh 192.168.1.100
sudo dnf -y install jq                     # pretty-prints and filters JSON answers
export GW=http://192.168.1.101:4000
read -rsp 'LiteLLM master key: ' MK; echo; export MK
curl -s $GW/health/readiness | jq '{status, db}'   # quick check: "healthy" and "connected"
"""),
    explain(
        ('ssh 192.168.1.100', 'Log in to the agent host.'),
        ('sudo dnf -y install jq', 'Install jq, which every lab uses to read the gateway&#x27;s JSON answers.'),
        ('export GW=http://192.168.1.101:4000', 'Store the gateway&#x27;s address in <code>GW</code>, so later commands can say <code>$GW/v1/models</code> instead of the full address. <code>export</code> also passes it to programs you run, such as the Python scripts.'),
        ("read -rsp 'LiteLLM master key: ' MK; echo; export MK", 'Paste the master key when asked. It goes into <code>MK</code> without appearing on screen or in your shell history, and <code>export</code> makes it available to programs too. The labs use it as <code>$MK</code>.'),
        ("curl -s $GW/health/readiness | jq '{status, db}'", 'A quick check that you can reach the gateway and that its database is connected. No key needed. The answer has many fields; <code>jq &#x27;{status, db}&#x27;</code> keeps just those two.'),
    ),
    note('Put the <code>export GW=...</code> line in <code>~/.bashrc</code> so new shells have it. Don&#x27;t do that with the master key; re-enter it when you need it.', 'Tip:'),
    h3('2. Add the two lab model names'),
    p('Look at the models the gateway serves now:'),
    code(r"""
curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[].id'
# qwen3.8-27b
# ...
"""),
    explain(
        ('curl -s $GW/v1/models -H "Authorization: Bearer $MK"', 'Ask for the list of models. This needs a key, sent in the <code>Authorization</code> header; the master key can see everything.'),
        ("| jq -r '.data[].id'", 'The list is in <code>data</code>; print each entry&#x27;s <code>id</code>, the name clients ask for, one per line. This call is taken apart in <a href="#reading">How to read the commands</a>.'),
    ),
    p('Every later lab asks for one of two names: <code>lab-chat</code> (chat apps) or <code>lab-agent</code> (agents, which need a model that can call tools). Neither is a new model. Each is an extra <code>model_list</code> entry, an <strong>alias</strong>, that forwards to a model you already have. Using aliases has two benefits:'),
    ul([
        'The lab commands work unchanged whatever model you run. You map the two names to your model once, here.',
        'It&#x27;s how a gateway is meant to be used. Apps ask for a role, not a specific model, so you can later move <code>lab-agent</code> to a bigger model or a cloud provider by changing one line, and no app or agent has to change.',
    ]),
    p('On <strong>.101</strong>, back up the config and open it:'),
    code(r"""
ssh 192.168.1.101
sudo cp -a /opt/litellm/config.yaml /opt/litellm/config.yaml.bak-$(date +%F)
sudo vi /opt/litellm/config.yaml
"""),
    explain(
        ('sudo cp -a ... config.yaml.bak-$(date +%F)', 'Keep a dated copy of the working config. If your edit breaks it, copy this back and restart.'),
        ('sudo vi /opt/litellm/config.yaml', 'Open the config as root. In <code>vi</code>: move to the end of <code>model_list</code>, press <code>o</code> to open a new line, paste, then Esc and <code>:wq</code> to save and quit. Any editor works (<code>sudo nano</code> if you prefer).'),
    ),
    p('Add these two entries at the end of the existing <code>model_list</code>, indented like the entries already there. Both use the same real model as an existing entry (<code>qwen/qwen3.8-27b</code> here; use your own model&#x27;s id). Only <code>model_name</code> is new:'),
    code(r"""
  - model_name: lab-chat                   # the name chat apps ask for
    litellm_params:
      model: openai/qwen/qwen3.8-27b       # the real model it forwards to
      api_base: os.environ/LMSTUDIO_API_BASE
      api_key: not-needed
  - model_name: lab-agent                  # the name agents ask for
    litellm_params:
      model: openai/qwen/qwen3.8-27b
      api_base: os.environ/LMSTUDIO_API_BASE
      api_key: not-needed
"""),
    p('While the file is open, check that <code>general_settings:</code> has the line <code>store_model_in_db: true</code> (indented two spaces). Agents you register in Lab 7 are saved in the database, and LiteLLM only loads them back after a restart when this is on. If it&#x27;s missing, add it.'),
    p('LiteLLM reads its config only at startup, so restart it. The gateway is down for about 20 seconds:'),
    code(r"""
sudo systemctl restart litellm             # or "sudo podman restart litellm" if it isn't a Quadlet service
sudo journalctl -u litellm -f              # Ctrl-C once you see "Uvicorn running"
"""),
    explain(
        ('sudo systemctl restart litellm', 'Stop the gateway and start it again, so it reads the edited config. With Quadlet a restart also creates a fresh container.'),
        ('sudo journalctl -u litellm -f', 'Follow its log while it starts. A YAML mistake shows up here as an error and the service keeps restarting.'),
    ),
    h3('Verify (back on .100)'),
    code(r"""
curl -s $GW/v1/models -H "Authorization: Bearer $MK" | jq -r '.data[].id' | grep lab-
# lab-chat
# lab-agent

curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model": "lab-agent", "messages": [{"role": "user", "content": "Say hi in five words."}]}' \
  | jq '{model, answer: .choices[0].message.content}'
"""),
    explain(
        ('... | grep lab-', 'List the models again and keep only the lines containing <code>lab-</code>: your two new names.'),
        ('curl -s $GW/v1/chat/completions ...', 'Send a chat request to the new name. Lab 2 takes this request apart piece by piece.'),
        ("jq '{model, answer: .choices[0].message.content}'", 'From the response, show the <code>model</code> field and the reply text, renamed <code>answer</code>. The reply sits at <code>choices[0].message.content</code>: the first (and only) choice&#x27;s message.'),
    ),
    p('The answer comes from qwen3.8-27b, but the response says <code>&quot;model&quot;: &quot;lab-agent&quot;</code>: the client only ever sees the alias.'),
    h3('Notes'),
    ul([
        'Both names point at the same model on purpose. On a single GPU, alternating between two large models makes LM Studio unload one and load the other, and every request waits for the load.',
        'YAML is indentation-sensitive, and each top-level key (<code>model_list:</code>, <code>litellm_settings:</code>) may appear only once. If LiteLLM won&#x27;t start after the edit, <code>sudo journalctl -u litellm -n 50</code> shows the error; copy the backup back and restart to get going again.',
        'If the reply is empty and <code>finish_reason</code> is <code>&quot;length&quot;</code>, the model ran out of context while thinking. In LM Studio, open the model&#x27;s settings (gear icon) and raise Context Length to at least 32k.',
        'Don&#x27;t open <code>/health</code> on its own (without <code>/liveliness</code> or <code>/readiness</code>). It sends a real request to <em>every</em> model the gateway serves, which makes LM Studio load each one in turn and can stall everyone else using it.',
        'The admin UI at <code>http://192.168.1.101:4000/ui</code> shows the same information under <strong>Models</strong> and <strong>Settings</strong>. To log in, get the username and password on .101 with <code>sudo grep &#x27;^UI_&#x27; /opt/litellm/litellm.env</code>: it prints the <code>UI_USERNAME=</code> and <code>UI_PASSWORD=</code> lines, and the value after each <code>=</code> is what you type. Later labs use this UI to look at logs.',
    ]),
)

# ---------------------------------------------------------------- lab 2
L2 = lab(2, 'Chat Through the Gateway: curl and Python', '192.168.1.100 → 192.168.1.101',
    goal('understand a chat request and its response, see why a chat client has to send the whole conversation every time, and build a small streaming chat program in Python.'),
    note('Every command uses <code>$GW</code> and <code>$MK</code> from <a href="#lab-1">Lab 1, step 1</a>. They only last as long as your shell, so if you logged out since, set them again first. <code>echo $GW</code> prints the address if they&#x27;re still set.'),
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
    explain(
        ('curl -s $GW/v1/chat/completions', 'Send the request to <code>/v1/chat/completions</code>, the OpenAI chat API. LiteLLM speaks it whatever provider is behind the alias, so any OpenAI-compatible app or library can use the gateway.'),
        ('-H "Authorization: Bearer $MK"', 'The key. The master key works for now; Lab 3 gives each app its own key.'),
        ("-H 'Content-Type: application/json'", 'Tell the gateway the body is JSON.'),
        ("-d '{...}'", 'The body. Sending one makes this a POST request. The single quotes keep the shell away from the JSON&#x27;s own double quotes.'),
        ('"model": "lab-chat"', 'Which model to use: the alias you added in Lab 1.'),
        ('"messages": [...]', 'The conversation. The <code>system</code> message sets the behaviour; <code>user</code> messages are what you type.'),
        ('| jq', 'Pretty-print the whole response.'),
    ),
    p('In the response, the answer is in <code>choices[0].message.content</code>, <code>usage</code> counts the tokens in and out, and <code>model</code> is the alias you asked for. To print just the answer, replace <code>jq</code> with <code>jq -r &#x27;.choices[0].message.content&#x27;</code>.'),
    h3('2. The API has no memory'),
    p('Ask a follow-up question on its own and the model has no idea what you mean:'),
    code(r"""
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model": "lab-chat", "messages": [{"role": "user", "content": "What did I just ask you?"}]}' \
  | jq -r '.choices[0].message.content'
"""),
    explain(
        ('-d \'{"model": ..., "messages": [...]}\'', 'The same request as before, squeezed onto one line, with no system message and one question.'),
        ("jq -r '.choices[0].message.content'", 'Print only the reply text, as plain text.'),
    ),
    p('Every chat app, including ChatGPT-style web UIs, keeps the conversation itself and sends the whole history with every request, adding the model&#x27;s earlier answers as <code>assistant</code> messages:'),
    code(r"""
curl -s $GW/v1/chat/completions -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"model": "lab-chat", "messages": [
        {"role": "user",      "content": "My favourite distro is Rocky Linux."},
        {"role": "assistant", "content": "Nice choice!"},
        {"role": "user",      "content": "What is my favourite distro?"}
      ]}' | jq -r '.choices[0].message.content'
"""),
    explain(
        ('{"role": "assistant", ...}', 'A message the model &quot;said&quot; earlier. You write it yourself here, the way a chat app replays the history. The model treats the three messages as the conversation so far and answers the last one.'),
    ),
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
    explain(
        ('curl -sN', '<code>-N</code> prints each piece the moment it arrives instead of collecting the whole answer first.'),
        ('"stream": true', 'Ask for a streamed answer: a series of <code>data:</code> lines, each holding a few characters in <code>delta.content</code>, ending with <code>data: [DONE]</code>. No <code>jq</code> here, because the output isn&#x27;t a single JSON document.'),
    ),
    h3('4. A chat program in Python'),
    p('Set up a Python virtual environment in <code>~/gw-labs</code> and install the <code>openai</code> library. It works with any OpenAI-compatible server; pointing <code>base_url</code> at the gateway is all it takes. Later labs add the other libraries they need to the same environment.'),
    code(r"""
sudo dnf -y install python3.12 python3.12-pip
mkdir -p ~/gw-labs && cd ~/gw-labs
python3.12 -m venv .venv
. .venv/bin/activate                       # run this again in every new shell
pip install "openai==3.24.0"
"""),
    explain(
        ('sudo dnf -y install python3.12 python3.12-pip', 'Install Python 3.12 and its package installer, <code>pip</code>, alongside the system Python. If they&#x27;re already there, <code>dnf</code> just says so and changes nothing.'),
        ('mkdir -p ~/gw-labs && cd ~/gw-labs', 'Make a working directory for the lab scripts and move into it.'),
        ('python3.12 -m venv .venv', 'Create a <strong>virtual environment</strong> in <code>.venv</code>: a private copy of Python where you can install libraries without touching the system&#x27;s.'),
        ('. .venv/bin/activate', 'Switch this shell to that environment, so <code>python</code> and <code>pip</code> mean the ones in <code>.venv</code>. Your prompt starts with <code>(.venv)</code> while it&#x27;s active. The leading <code>.</code> means &quot;run this file in the current shell&quot;.'),
        ('pip install "openai==3.24.0"', 'Install the <code>openai</code> library, which talks to chat APIs, at the exact version the labs were tested with (<code>==</code>).'),
    ),
    p('<code>chat.py</code> keeps the history in a list (step 2) and streams each answer (step 3):'),
    write_file('~/gw-labs/chat.py', 'chat.py'),
    explain(
        ('client = OpenAI(base_url=..., api_key=...)', 'A client for the OpenAI API, pointed at the gateway (<code>$GW/v1</code>) instead of OpenAI, with the key from <code>KEY</code>. This line is the only thing that makes it a &quot;gateway&quot; program.'),
        ('MODEL = os.environ.get("MODEL", "lab-chat")', 'Use the model named in <code>MODEL</code>, or <code>lab-chat</code> if it isn&#x27;t set.'),
        ('history = [{"role": "system", ...}]', 'The conversation so far, starting with the system message. This list is the program&#x27;s memory (step 2).'),
        ('input("\\nyou> ")', 'Wait for you to type a line. Ctrl-D raises <code>EOFError</code>, which ends the loop.'),
        ('history.append({"role": "user", ...})', 'Add your question to the conversation.'),
        ('client.chat.completions.create(..., messages=history, stream=True)', 'Send the <em>whole</em> history and ask for a streamed answer (step 3).'),
        ('for chunk in stream: ... print(piece, end="", flush=True)', 'Print each piece as it arrives, without a newline, and collect the pieces into <code>answer</code>.'),
        ('history.append({"role": "assistant", "content": answer})', 'Add the full answer to the conversation, so the next question can refer to it.'),
    ),
    code(r"""
KEY=$MK python chat.py
# you> My name is Pat.
# ai > Hi Pat! How can I help you today?
# you> What is my name?
# ai > Your name is Pat.
"""),
    explain(
        ('KEY=$MK python chat.py', 'Run the program with the variable <code>KEY</code> set to your master key, for this one command only. <code>chat.py</code> reads the key and the gateway address (<code>$GW</code>) from the environment rather than having them written into the code. Ctrl-D quits.'),
    ),
    h3('Notes'),
    ul([
        'Change the model per run with <code>MODEL=lab-agent KEY=$MK python chat.py</code>. The program doesn&#x27;t know or care which real model answers.',
        'The admin UI at <code>http://192.168.1.101:4000/ui</code> (login: <a href="#lab-1">Lab 1</a>, Notes) has a <strong>Playground</strong> page that does the same thing in the browser.',
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
    explain(
        ('curl -s $GW/key/generate -H "Authorization: Bearer $MK"', 'Ask the gateway to create a key. Only the master key may do that.'),
        ('"key_alias": "chat-ui"', 'The key&#x27;s name, which you&#x27;ll see in logs and in the UI. It must be unique.'),
        ('"models": [...]', 'The allow-list: the only models this key may use. Leave it out and the key can use every model.'),
        ('"rpm_limit": 60', 'Requests per minute. Request number 61 inside a minute gets HTTP 429.'),
        ("| jq '{key_alias, key, models, rpm_limit}'", 'The response repeats every setting the key has, most of them defaults. Show only the four that matter here, including the new key itself.'),
    ),
    p('Copy the <code>key</code> value now. LiteLLM stores only a hash of it, so it can never show you the key again. Put it in a variable, and save it in a file only you can read, so it survives logging out:'),
    code(r"""
read -rsp 'chat-ui key: ' UIKEY; echo
touch ~/gw-labs/keys.env && chmod 600 ~/gw-labs/keys.env
echo "UIKEY=$UIKEY" >> ~/gw-labs/keys.env
"""),
    explain(
        ("read -rsp 'chat-ui key: ' UIKEY; echo", 'Paste the <code>sk-...</code> value from the output above. It&#x27;s stored in <code>UIKEY</code>; Labs 4 and 7 use it too.'),
        ('touch ... && chmod 600 ...', 'Create <code>~/gw-labs/keys.env</code> if it doesn&#x27;t exist, and make it readable and writable by you only (<code>600</code>), before any key goes in.'),
        ('echo "UIKEY=$UIKEY" >> ~/gw-labs/keys.env', 'Add the line <code>UIKEY=sk-...</code> to the file. <code>&gt;&gt;</code> appends, so keys from later labs pile up in the same file. The key is filled in from the variable, so it never appears in your shell history.'),
    ),
    note('In a new shell, <code>. ~/gw-labs/keys.env</code> sets <code>UIKEY</code> and every key you save in later labs again. The leading <code>.</code> runs the file in the current shell, so the variables stay set. Every lab that creates a key adds it to this file the same way.', 'Tip:'),
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
    explain(
        ('-H "Authorization: Bearer $UIKEY"', 'The same requests as before, but sent with the new <code>chat-ui</code> key instead of the master key.'),
        ("jq -r '.error.message'", 'When the gateway refuses a request, its answer is <code>{&quot;error&quot;: {&quot;message&quot;: ...}}</code>. This prints just the reason.'),
        ("/key/generate ... -d '{}'", 'Try to create a key (<code>{}</code> means no settings). An app key isn&#x27;t allowed to, so this fails too.'),
    ),
    h3('3. Look a key up and change it'),
    code(r"""
curl -s "$GW/key/info?key=$UIKEY" -H "Authorization: Bearer $MK" | jq '.info | {key_alias, models, rpm_limit, spend}'

# change a limit in place (the key itself stays the same)
cat > ~/gw-labs/chat-ui-update.json <<EOF
{"key": "$UIKEY", "rpm_limit": 30}
EOF
curl -s $GW/key/update -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d @$HOME/gw-labs/chat-ui-update.json | jq '{key_alias, rpm_limit}'

# every key, by alias
curl -s "$GW/key/list?return_full_object=true" -H "Authorization: Bearer $MK" | jq -r '.keys[] | "\(.key_alias)\t\(.models)"'
"""),
    explain(
        ('curl -s "$GW/key/info?key=$UIKEY"', 'Look up one key. The key goes in the URL after <code>?</code>; the URL is in double quotes so the shell doesn&#x27;t treat <code>?</code> as a filename pattern, while still filling in <code>$UIKEY</code>.'),
        ("jq '.info | {...}'", 'The details are under <code>info</code>; show the alias, allowed models, rate limit and spend so far.'),
        ('cat > ~/gw-labs/chat-ui-update.json <<EOF', 'Write the request body to a file. The heredoc is unquoted, so <code>$UIKEY</code> becomes the actual key. Run <code>cat ~/gw-labs/chat-ui-update.json</code> to see what will be sent.'),
        ('-d @$HOME/gw-labs/chat-ui-update.json', 'Send that file as the body. <code>@</code> tells curl to read a file instead of taking the text literally. (<code>$HOME</code>, not <code>~</code>: the shell doesn&#x27;t expand <code>~</code> after <code>@</code>.) The response shows the new limit at once, but the gateway caches keys it has seen recently, so requests made with the key can keep the old limit for up to a minute.'),
        ('/key/list?return_full_object=true', 'List every key with all its details, not just the hashes.'),
        ('jq -r \'.keys[] | "\\(.key_alias)\\t\\(.models)"\'', 'For each key, print a line of text: <code>\\(...)</code> inserts a field&#x27;s value into the string, and <code>\\t</code> is a tab between the two columns.'),
    ),
    h3('Notes'),
    ul([
        'Budgets: add <code>&quot;max_budget&quot;: 5, &quot;budget_duration&quot;: &quot;30d&quot;</code> to cap a key at $5 a month. LiteLLM prices requests from its price list, so this works for cloud models. Local models cost $0, so a budget never trips for them; use <code>rpm_limit</code> instead.',
        'Creating a key whose alias already exists fails with &quot;Key with alias ... already exists&quot;. To start over, delete the old one by name: <code>curl -s $GW/key/delete -H &quot;Authorization: Bearer $MK&quot; -H &#x27;Content-Type: application/json&#x27; -d &#x27;{&quot;key_aliases&quot;: [&quot;chat-ui&quot;]}&#x27;</code>, then remove its line from <code>keys.env</code>.',
        'Everything here is also in the admin UI under <strong>Virtual Keys</strong>, including the one-time display of a new key.',
        'Store app keys the way the next labs do: in a root-only env file (<code>chmod 600</code>) that Podman passes to the container, never in a Quadlet file or a script.',
    ]),
)

# ---------------------------------------------------------------- lab 4
L4 = lab(4, 'A Chat Web UI: Open WebUI on Podman', '192.168.1.100 (Open WebUI) → 192.168.1.101',
    goal('run Open WebUI as a Quadlet on .100, connected to the gateway with the <code>chat-ui</code> key from Lab 3, so you get a ChatGPT-style web page that starts at boot.'),
    h3('1. The key goes in an env file'),
    code(r"""
. ~/gw-labs/keys.env
echo ${UIKEY:0:6}                          # must print sk-...; if it's empty, stop here
sudo mkdir -p /opt/open-webui
sudo touch /opt/open-webui/open-webui.env
sudo chmod 600 /opt/open-webui/open-webui.env
sudo tee /opt/open-webui/open-webui.env >/dev/null <<EOF
OPENAI_API_BASE_URL=http://192.168.1.101:4000/v1
OPENAI_API_KEY=$UIKEY
WEBUI_SECRET_KEY=$(openssl rand -hex 32)
EOF
"""),
    explain(
        ('. ~/gw-labs/keys.env', 'Load your saved keys (Lab 3), so <code>$UIKEY</code> holds the <code>chat-ui</code> key even in a new shell.'),
        ('echo ${UIKEY:0:6}', 'Print just the first six characters of the key, enough to see it&#x27;s set without showing it all. If it prints an empty line, <code>UIKEY</code> isn&#x27;t set, and the env file would get a blank key: Open WebUI would start but show no models, without any error.'),
        ('sudo mkdir -p /opt/open-webui', 'A directory for Open WebUI&#x27;s settings file.'),
        ('sudo touch ... / sudo chmod 600 ...', 'Create the env file empty and root-only before the key goes in.'),
        ('sudo tee ... <<EOF', 'Write the three settings. The heredoc is unquoted, so <code>$UIKEY</code> becomes your <code>chat-ui</code> key and <code>$(openssl rand -hex 32)</code> becomes a random secret. Check with <code>sudo cat /opt/open-webui/open-webui.env</code>.'),
    ),
    p('<code>OPENAI_API_BASE_URL</code> points Open WebUI at the gateway as if it were OpenAI. <code>WEBUI_SECRET_KEY</code> signs login sessions; keeping it fixed means you stay logged in across restarts.'),
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
    explain(
        ("sudo tee /etc/containers/systemd/... <<'EOF'", 'Write each Quadlet file into the directory systemd reads them from. The heredocs are quoted because there&#x27;s nothing for the shell to fill in.'),
        ('open-webui.volume', 'A named volume, <code>open-webui</code>, for the app&#x27;s data.'),
        ('ContainerName=open-webui', 'The name the container gets, so <code>sudo podman ps</code> and <code>podman logs</code> show <code>open-webui</code> instead of a generated name.'),
        ('Image=ghcr.io/open-webui/open-webui:v0.11.4', 'The image to run, pinned to the version the lab was tested with. A tag like <code>:main</code> would change under you; a fixed version only changes when you edit this line.'),
        ('PublishPort=3000:8080', 'Make the container&#x27;s port 8080 reachable as port 3000 on the host.'),
        ('Volume=open-webui.volume:/app/backend/data', 'Mount that volume where Open WebUI keeps its database inside the container.'),
        ('EnvironmentFile= / Environment=', 'Settings from the env file (the gateway URL and key), plus one extra setting written directly, since it isn&#x27;t secret.'),
        ('[Service] / [Install]', '<code>Restart=always</code> restarts the container if it stops. <code>TimeoutStartSec=900</code> allows 15 minutes for the first start. <code>WantedBy=multi-user.target</code> starts it at boot.'),
    ),
    p('<code>ENABLE_OLLAMA_API=false</code> stops it looking for a local Ollama it doesn&#x27;t need. <code>TimeoutStartSec=900</code> gives the first start time to pull the image, which is several GB.'),
    h3('3. Start it'),
    code(r"""
sudo systemctl daemon-reload
sudo systemctl start open-webui            # first start pulls the image: a few minutes
systemctl status open-webui --no-pager
curl -s http://localhost:3000/health; echo                     # {"status":true}

systemctl is-active firewalld              # "inactive": skip the next line
sudo firewall-cmd --permanent --add-port=3000/tcp && sudo firewall-cmd --reload
"""),
    explain(
        ('sudo systemctl daemon-reload', 'Generate <code>open-webui.service</code> from the files you just wrote.'),
        ('sudo systemctl start open-webui', 'Start it. The command waits while the image downloads.'),
        ('systemctl status open-webui --no-pager', 'Show whether it&#x27;s running and its last few log lines. <code>--no-pager</code> prints straight to the screen instead of opening a scrollable view.'),
        ('curl -s http://localhost:3000/health; echo', 'Ask Open WebUI itself whether it&#x27;s up. <code>localhost</code> means this machine.'),
        ('systemctl is-active firewalld', 'Is the host firewall running? If it prints <code>inactive</code>, nothing blocks port 3000, so skip the next line; <code>firewall-cmd</code> would only fail with &quot;FirewallD is not running&quot;.'),
        ('sudo firewall-cmd ...', 'If it printed <code>active</code>: open port 3000 so your browser can reach it from another machine, and apply the change.'),
    ),
    h3('Verify'),
    ol([
        'Open <code>http://192.168.1.100:3000</code> and sign up. <strong>The first account becomes the admin.</strong>',
        'The model menu at the top lists <code>lab-chat</code> and <code>lab-agent</code>, the two models the <code>chat-ui</code> key allows, and nothing else the gateway serves.',
        'Send a message. Then, in the gateway&#x27;s admin UI (<code>http://192.168.1.101:4000/ui</code>, <strong>Logs</strong>; the login is in <a href="#lab-1">Lab 1</a>, Notes), you&#x27;ll see the request under the key alias <code>chat-ui</code>.',
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
echo "OPS_KEY=$OPS_KEY" >> ~/gw-labs/keys.env
"""),
    explain(
        ('curl -s $GW/key/generate ...', 'Create a key named <code>ops-agent</code> that may use only <code>lab-agent</code>, at most 30 requests a minute (Lab 3 explains each setting).'),
        ('| jq -r .key', 'Print only the new key.'),
        ("read -rsp 'ops-agent key: ' OPS_KEY; echo", 'Paste it to store it in <code>OPS_KEY</code>.'),
        ('echo "OPS_KEY=$OPS_KEY" >> ~/gw-labs/keys.env', 'Save it in your key file too, as in Lab 3.'),
    ),
    h3('2. The agent'),
    p('The program needs one more library, <code>httpx</code>, which its <code>check_url</code> tool uses to fetch web pages. Install it into the environment from Lab 2:'),
    code(r"""
cd ~/gw-labs && . .venv/bin/activate
pip install "httpx==0.28.1"
"""),
    explain(
        ('cd ~/gw-labs && . .venv/bin/activate', 'Go to the lab directory and switch to its Python environment (Lab 2).'),
        ('pip install "httpx==0.28.1"', 'Install <code>httpx</code> at the tested version. Only needed once.'),
    ),
    write_file('~/gw-labs/agent.py', 'agent.py'),
    p('What the program does, part by part. The loop at the end is the four steps from the top of this lab:'),
    explain(
        ('client = OpenAI(...) / MODEL = ...', 'A client pointed at the gateway with the agent&#x27;s own key (<code>AGENT_KEY</code>), and the model to ask for: <code>lab-agent</code> unless <code>AGENT_MODEL</code> says otherwise.'),
        ('get_time, check_url, check_port', 'The tools: ordinary Python functions that return a short text result. Nothing about them is AI-specific.'),
        ('TOOLS = {...}', 'Maps each tool&#x27;s name to its function, so the program can look up the function the model asks for by name.'),
        ('call_tool(name, arguments)', 'Runs one tool. The model sends the arguments as a JSON string, so this decodes them first. If the model asks for a tool that doesn&#x27;t exist, or sends arguments that don&#x27;t fit, the error goes back to the model as the tool&#x27;s result instead of crashing the program, and the model usually corrects itself on the next pass. Models do get this wrong sometimes, so every agent needs this.'),
        ('TOOL_SPECS = [...]', 'How the model learns the tools exist: each one&#x27;s name, a <code>description</code> the model reads to decide when to use it, and its parameters as JSON Schema (names, types, which are <code>required</code>). This list is sent with every request.'),
        ('SYSTEM / USE_TOOLS', 'The system prompt, and whether to offer the tools at all. Each reads an environment variable (<code>AGENT_PROMPT</code>, <code>AGENT_TOOLS</code>) and falls back to the ops-agent defaults. Lab 6 runs this same file as a second agent by setting those two variables.'),
        ('messages = [system, user]', 'The conversation starts with the system prompt and your question.'),
        ('reply = client.chat.completions.create(..., tools=TOOL_SPECS)', 'One pass around the loop: an ordinary chat request through the gateway, with the tool list attached.'),
        ('if not msg.tool_calls: return msg.content', 'The model answered in plain text instead of asking for a tool: that&#x27;s the final answer.'),
        ('messages.append(msg.model_dump(...))', 'Otherwise, add the model&#x27;s tool request to the conversation, so on the next pass it remembers what it asked for.'),
        ('for call in msg.tool_calls: ... {"role": "tool", ...}', 'Run each requested tool (the model can ask for several at once), print a <code>[tool]</code> line so you can watch, and add each result as a <code>tool</code> message. <code>tool_call_id</code> tells the model which request the result belongs to.'),
        ('for _ in range(max_steps): ... "Stopped: too many steps."', 'Go round at most 8 times, so a confused model can&#x27;t loop forever.'),
        ('if __name__ == "__main__":', 'When you run the file directly, use the command-line arguments as the question. Lab 6 imports the file instead and calls <code>run()</code> itself.'),
    ),
    h3('3. Run it'),
    code(r"""
cd ~/gw-labs && . .venv/bin/activate
AGENT_KEY=$OPS_KEY python agent.py "Is http://192.168.1.101:4000/health/liveliness answering, is port 22 open on 192.168.1.100, and what time is it?"
#   [tool] check_url({"url":"http://192.168.1.101:4000/health/liveliness"}) -> HTTP 200 in 16 ms
#   [tool] check_port({"host":"192.168.1.100","port":22}) -> 192.168.1.100:22 is open
#   [tool] get_time({}) -> 2026-10-06T00:27:31+00:00
# - 192.168.1.101:4000/health/liveliness: HTTP 200 (16 ms)
# - 192.168.1.100 port 22: open
# - Time: 2026-10-06 00:27 UTC
"""),
    explain(
        ('cd ~/gw-labs && . .venv/bin/activate', 'Go to the lab directory and switch to its Python environment. Needed again in every new shell, along with <code>. ~/gw-labs/keys.env</code> for <code>$OPS_KEY</code>.'),
        ('AGENT_KEY=$OPS_KEY python agent.py "..."', 'Run the agent with its own key, set for this command only, and pass your question as the argument. The quotes keep the question together as one argument.'),
    ),
    p('The <code>[tool]</code> lines are the loop at work: the model chose which tools to call and with what arguments, and the program ran them. Try a question that needs no tools (&quot;What is a TCP port?&quot;) and one about a port that&#x27;s closed.'),
    h3('Verify: what the gateway saw'),
    code(r"""
curl -s "$GW/spend/logs?start_date=$(date -u +%F)&end_date=$(date -u -d tomorrow +%F)&summarize=false" \
  -H "Authorization: Bearer $MK" \
  | jq -r '.[] | select(.metadata.user_api_key_alias == "ops-agent") | "\(.startTime)  \(.model_group)  tokens=\(.total_tokens)"'
"""),
    explain(
        ('"$GW/spend/logs?start_date=...&end_date=...&summarize=false"', 'Ask for the log of every request between two dates, one entry per request (<code>summarize=false</code>). The URL is in double quotes because <code>&amp;</code> would otherwise end the command.'),
        ('$(date -u +%F) / $(date -u -d tomorrow +%F)', 'Today&#x27;s and tomorrow&#x27;s dates in UTC, such as <code>2026-10-06</code>, filled in by the shell. The gateway logs in UTC.'),
        ('jq -r \'.[] | select(...) | "..."\'', 'Go through each logged request, keep only those made with the <code>ops-agent</code> key (<code>select</code>), and print its time, model and token count on one line.'),
    ),
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
    explain(
        ('sudo mkdir -p /opt/agents', 'A directory for everything that goes into the agent image.'),
        ('sudo cp ~/gw-labs/agent.py /opt/agents/', 'Copy your Lab 5 agent there, unchanged.'),
    ),
    write_file('/opt/agents/a2a_server.py', 'a2a_server.py', sudo=True),
    p('What the program does, part by part. Most of it is the <code>a2a-sdk</code> library doing the protocol work; your own code is the one line that calls <code>agent.run()</code>.'),
    explain(
        ('import agent', 'Load your Lab 5 program as a module, so this file can call its <code>run()</code> function. Importing it sets up its gateway client, which is why the container needs <code>GW</code> and <code>AGENT_KEY</code>; the part that takes a question from the command line (<code>__main__</code>) only runs when the file is started directly, so it&#x27;s skipped.'),
        ('NAME / DESCRIPTION / PORT / PUBLIC_URL', 'Settings read from environment variables, which the Quadlet files in step 4 set differently for each agent. <code>PUBLIC_URL</code> has no default: the program stops with an error if it&#x27;s missing, rather than advertising a wrong address.'),
        ('class Executor(AgentExecutor): execute(...)', 'What happens when a message arrives. The library calls <code>execute()</code> with the message (<code>context</code>) and a queue (<code>event_queue</code>) for sending updates back to the caller.'),
        ('task = ... new_task_from_user_message(...)', 'In A2A every piece of work is a <strong>task</strong> with an ID and a state. Create one for this message (or continue the existing one), and send it to the caller.'),
        ('updater.update_status(... TASK_STATE_WORKING ...)', 'Mark the task as &quot;working&quot;. A caller that streams or polls sees this while the agent thinks.'),
        ('await asyncio.to_thread(agent.run, get_message_text(...))', 'The one line that does the work: take the text out of the message and pass it to your Lab 5 agent. <code>agent.run()</code> is ordinary blocking code, so <code>to_thread</code> runs it in a background thread and the server can keep answering other requests meanwhile.'),
        ('updater.add_artifact(...) / update_status(... COMPLETED, ...)', 'Attach the answer to the task as an <strong>artifact</strong> (A2A&#x27;s word for a task&#x27;s output), then mark the task completed with the answer as its final message. That&#x27;s the <code>.result.task.status.message</code> you read in Verify.'),
        ('cancel(...): raise NotImplementedError', 'Callers may ask to cancel a task. This agent doesn&#x27;t support that, and says so.'),
        ('card = AgentCard(...)', 'The <strong>agent card</strong>: name, description, version, the input and output types it accepts (plain text), that it doesn&#x27;t stream, the address and protocol to call it on (<code>supported_interfaces</code>), and its skills. A caller reads this to decide whether and how to use the agent.'),
        ('DefaultRequestHandler(..., task_store=InMemoryTaskStore(), ...)', 'Connects the protocol to your <code>Executor</code>. Tasks are kept in memory, so they&#x27;re forgotten when the container restarts; that&#x27;s fine for short questions.'),
        ('app = Starlette(routes=[...])', 'A small web app with two sets of routes: the agent card at <code>/.well-known/agent-card.json</code>, and JSON-RPC messages at <code>/</code>.'),
        ('uvicorn.run(app, host="0.0.0.0", port=PORT)', 'Start the web server on every network interface of the container, on <code>PORT</code>.'),
    ),
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
sudo podman build -t localhost/a2a-agent:1 /opt/agents
"""),
    explain(
        ('FROM docker.io/library/python:3.12.15-slim', 'Start from the official small Python image.'),
        ('RUN pip install ...', 'Run a command while building: install the libraries into the image, at pinned versions.'),
        ('WORKDIR /app / COPY agent.py a2a_server.py ./', 'Use <code>/app</code> as the working directory and copy the two programs from <code>/opt/agents</code> into it.'),
        ('USER 1001 / CMD [...]', 'Run as an ordinary user, and start the A2A server when a container starts from this image.'),
        ('sudo podman build -t localhost/a2a-agent:1 /opt/agents', 'Build the image from the <code>Containerfile</code> in <code>/opt/agents</code> and name it (<code>-t</code>, for tag) <code>localhost/a2a-agent</code>, version <code>1</code>. Check with <code>sudo podman images</code>.'),
    ),
    p('<code>USER 1001</code> runs the agent as an unprivileged user inside the container. The <code>localhost/</code> prefix marks an image you built yourself, so Podman never tries to pull it from a registry.'),
    h3('3. A second key, then one env file per agent'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias": "writer-agent", "models": ["lab-agent"], "rpm_limit": 30}' | jq -r .key
read -rsp 'writer-agent key: ' WRITER_KEY; echo
echo "WRITER_KEY=$WRITER_KEY" >> ~/gw-labs/keys.env

. ~/gw-labs/keys.env
echo ${OPS_KEY:0:6} ${WRITER_KEY:0:6}      # must print sk-... sk-...; if either is missing, stop here
sudo touch /opt/agents/ops-agent.env /opt/agents/writer-agent.env
sudo chmod 600 /opt/agents/ops-agent.env /opt/agents/writer-agent.env
echo "AGENT_KEY=$OPS_KEY"    | sudo tee /opt/agents/ops-agent.env >/dev/null
echo "AGENT_KEY=$WRITER_KEY" | sudo tee /opt/agents/writer-agent.env >/dev/null
"""),
    explain(
        ('curl ... / read -rsp ... / echo ... >> keys.env', 'A second key, for <code>writer-agent</code>, stored in <code>WRITER_KEY</code> and saved in your key file. Same steps as for <code>ops-agent</code> in Lab 5.'),
        ('. ~/gw-labs/keys.env / echo ${OPS_KEY:0:6} ...', 'Load your saved keys and print the start of both. If one is missing, its agent would still start and show <code>active</code>, but every message would fail with a 401 from the gateway.'),
        ('sudo touch ... / sudo chmod 600 ...', 'Create one root-only env file per agent.'),
        ('echo "AGENT_KEY=$OPS_KEY" | sudo tee ...', '<code>echo</code> prints the line with your key filled in, and <code>sudo tee</code> writes it into the agent&#x27;s env file. Each agent gets its own key, so the logs tell them apart.'),
    ),
    h3('4. Two Quadlet units, one image'),
    p('The two files differ only in name, port and environment. <code>writer-agent</code> gets no tools and a different system prompt; it turns notes into a readable status update. <code>PUBLIC_URL</code> is the address other hosts use to reach the agent; it goes into the agent card.'),
    code(r"""
sudo tee /etc/containers/systemd/ops-agent.container >/dev/null <<'EOF'
[Unit]
Description=ops-agent (A2A)

[Container]
ContainerName=ops-agent
Image=localhost/a2a-agent:1
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
Image=localhost/a2a-agent:1
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

systemctl is-active firewalld              # "inactive": skip the next line
sudo firewall-cmd --permanent --add-port={8601,8602}/tcp && sudo firewall-cmd --reload
"""),
    explain(
        ('ContainerName= / PublishPort= / [Service] / [Install]', 'The same as in Lab 4: a fixed container name, the port on the host, restart if it stops, start at boot.'),
        ('Image=localhost/a2a-agent:1', 'Both services run the image you just built. What makes them different agents is only their settings.'),
        ('EnvironmentFile=/opt/agents/ops-agent.env', 'Load the agent&#x27;s key (<code>AGENT_KEY</code>) from its root-only file, so the key isn&#x27;t in the Quadlet file.'),
        ('Environment=GW=http://192.168.1.101:4000', 'The gateway&#x27;s address. <code>agent.py</code> sends every model request there, just as when you ran it by hand with <code>$GW</code> set.'),
        ('Environment=AGENT_NAME= / PORT= / PUBLIC_URL=', 'Settings the program reads at startup: its name, the port to listen on, and the address to advertise in its agent card.'),
        ('Environment=AGENT_TOOLS=off / AGENT_PROMPT="..."', '<code>writer-agent</code> only: no tools, and a different system prompt. The double quotes keep a value with spaces together.'),
        ('sudo systemctl start ops-agent writer-agent', 'Start both services with one command.'),
        ('systemctl is-active ops-agent writer-agent', 'Print one word per service: <code>active</code> if it&#x27;s running.'),
        ('systemctl is-active firewalld', 'As in Lab 4: only if this prints <code>active</code> do you need the <code>firewall-cmd</code> line.'),
        ('--add-port={8601,8602}/tcp', 'The shell expands the braces into two arguments, <code>--add-port=8601/tcp --add-port=8602/tcp</code>, opening both ports at once.'),
    ),
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
    explain(
        ('curl -s http://192.168.1.100:8601/.well-known/agent-card.json', 'Fetch the agent card from the agent itself. This is a plain GET; no key is needed.'),
        ("jq '{name, description, url: .supportedInterfaces[0].url}'", 'Show the name, the description, and the first address it says it can be reached at.'),
        ("cat > ~/gw-labs/ask.json <<'EOF'", 'Save an A2A message to a file: a JSON-RPC call (<code>&quot;jsonrpc&quot;: &quot;2.0&quot;</code>) to the <code>SendMessage</code> method, from the user, with one text part. <code>messageId</code> is any unique ID you choose.'),
        ("curl ... -H 'A2A-Version: 1.0' -d @$HOME/gw-labs/ask.json", 'POST that file to the agent. The <code>A2A-Version</code> header says which version of the protocol you&#x27;re speaking.'),
        ("jq -r '.result.task.status.message.parts[0].text'", 'Dig the answer text out of the reply: the result is a task, whose status holds a message, whose first part is the text.'),
        ('sudo journalctl -u ops-agent -n 5 --no-pager', 'The last five lines of the agent&#x27;s log, where you can see which tools it called to answer.'),
    ),
    p('The reply is an A2A <strong>task</strong>: it has a state (<code>TASK_STATE_COMPLETED</code>) and the answer as a message. Long-running agents use the same structure to report progress.'),
    h3('Notes'),
    ul([
        'Changed <code>agent.py</code>? Copy it, rebuild the image and restart both agents: <code>sudo cp ~/gw-labs/agent.py /opt/agents/ &amp;&amp; sudo podman build -t localhost/a2a-agent:1 /opt/agents &amp;&amp; sudo systemctl restart ops-agent writer-agent</code>. (For <code>a2a_server.py</code>, edit it in <code>/opt/agents</code> with <code>sudo vi</code> and run just the last two.) A restart creates a fresh container from the new image.',
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
    p('Registration is an agent card plus a name for the gateway. Each agent already serves its own card (Lab 6), but you type it out here because LiteLLM takes the card in an older, flat layout with a single top-level <code>url</code>: the address it forwards calls to. The agents&#x27; own cards list their address under <code>supportedInterfaces</code> instead.'),
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
    -d @$HOME/gw-labs/$a.json | jq '{agent_name, agent_id, detail}'
done
"""),
    explain(
        ("cat > ~/gw-labs/ops-agent.json <<'EOF'", 'Save each registration to a file. The heredoc is quoted, since there&#x27;s nothing for the shell to fill in.'),
        ('"agent_name"', 'The name in the gateway&#x27;s URL: <code>/a2a/ops-agent</code>. It must be unique on the gateway.'),
        ('"agent_card_params": {...}', 'The agent card the gateway shows callers who ask what agents exist.'),
        ('"protocolVersion": "1.0"', 'The A2A version the agent speaks, so the gateway knows how to talk to it.'),
        ('"url": "http://192.168.1.100:8601/"', 'Where the gateway forwards calls: the agent service from Lab 6.'),
        ('"name" / "description" / "version"', 'What callers see. Other agents read <code>description</code> to decide whether this agent can help them, much as a model reads a tool&#x27;s description.'),
        ('"defaultInputModes" / "defaultOutputModes"', 'The kinds of content it takes and returns: plain text only.'),
        ('"capabilities": {"streaming": false}', 'It answers in one piece rather than streaming progress.'),
        ('"skills": [...]', 'A list of the specific things the agent can do, each with an ID, a name, a description and search tags. One skill per agent is enough here.'),
        ('for a in ops-agent writer-agent; do ... done', 'Run the <code>curl</code> once per agent, with the name in <code>$a</code>, so <code>@$HOME/gw-labs/$a.json</code> sends <code>ops-agent.json</code> and then <code>writer-agent.json</code>.'),
        ('curl -s $GW/v1/agents ... -d @...', 'POST the registration to <code>/v1/agents</code>. Registering is an admin job, so it uses the master key.'),
        ("jq '{agent_name, agent_id, detail}'", 'Show the name and the ID the gateway gave the agent. <code>detail</code> is <code>null</code> on success. If you run this again, the gateway refuses to register the same name twice: you get <code>null</code> for the name and ID and &quot;Agent with name ops-agent already exists&quot; in <code>detail</code>. That&#x27;s harmless; the first registration is still there.'),
    ),
    p('Each agent gets an <code>agent_id</code>. You&#x27;ll use the IDs to grant access. List them again any time with:'),
    code(r"""
curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r '.[] | "\(.agent_id)  \(.agent_name)"'
"""),
    explain(
        ('curl -s $GW/v1/agents ...', 'A GET to the same address lists the registered agents.'),
        ('jq -r \'.[] | "\\(.agent_id)  \\(.agent_name)"\'', 'For each agent in the list, print its ID and name on one line.'),
    ),
    h3('2. Call an agent through the gateway'),
    p('With the master key first, to prove the route works. It&#x27;s the same <code>ask.json</code> from Lab 6, sent to the gateway instead of to the agent:'),
    code(r"""
curl -s $GW/a2a/ops-agent -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d @$HOME/gw-labs/ask.json | jq -r '.result.task.status.message.parts[0].text'
"""),
    explain(
        ('curl -s $GW/a2a/ops-agent ...', 'The same A2A call as in Lab 6, word for word, except for two things: it goes to the gateway&#x27;s <code>/a2a/ops-agent</code> address, and it carries a key. The gateway checks the key, forwards the message to <code>http://192.168.1.100:8601/</code>, and passes the answer back.'),
    ),
    h3('3. A caller key that may use ops-agent only'),
    p('Virtual keys can&#x27;t see <em>any</em> agent until you grant one. The grant goes in <code>object_permission.agents</code> and takes agent <strong>IDs</strong>, not names:'),
    code(r"""
OPS_ID=$(curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r '.[] | select(.agent_name=="ops-agent") | .agent_id')
echo "$OPS_ID"

cat > ~/gw-labs/ops-caller.json <<EOF
{
  "key_alias": "ops-caller",
  "models": ["lab-agent"],
  "object_permission": {"agents": ["$OPS_ID"]}
}
EOF
cat ~/gw-labs/ops-caller.json               # check the ID was filled in

curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d @$HOME/gw-labs/ops-caller.json | jq -r .key
read -rsp 'ops-caller key: ' CALLER_KEY; echo
echo "CALLER_KEY=$CALLER_KEY" >> ~/gw-labs/keys.env
"""),
    explain(
        ('OPS_ID=$(curl ... | jq -r \'... select(.agent_name=="ops-agent") | .agent_id\')', 'List the agents, keep the one named <code>ops-agent</code>, print its ID, and store that in <code>OPS_ID</code> (<code>$(...)</code> captures the output). <code>echo</code> shows it so you can see it worked.'),
        ('cat > ~/gw-labs/ops-caller.json <<EOF', 'Write the new key&#x27;s settings to a file. The heredoc is unquoted, so <code>$OPS_ID</code> is replaced with the real ID. <code>object_permission.agents</code> is the list of agents this key may reach.'),
        ('curl ... -d @$HOME/gw-labs/ops-caller.json | jq -r .key', 'Create the key from that file and print it, then paste it into <code>CALLER_KEY</code> and save it in your key file.'),
    ),
    h3('Verify'),
    code(r"""
. ~/gw-labs/keys.env                       # UIKEY from Lab 3, CALLER_KEY from step 3

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
    explain(
        ('. ~/gw-labs/keys.env', 'Load your saved keys. Without it, in a new shell <code>$UIKEY</code> is empty, and the last check gets an error instead of <code>0</code>.'),
        ("... -H \"Authorization: Bearer $CALLER_KEY\" | jq -r '.[].agent_name'", 'List agents as the new key sees them: only the names it was granted.'),
        ('curl -s $GW/a2a/ops-agent ... $CALLER_KEY', 'The same call as step 2, now with the limited key.'),
        ('... $UIKEY | jq length', '<code>length</code> counts the items in the list. The <code>chat-ui</code> key sees zero agents.'),
    ),
    h3('Notes'),
    ul([
        'There are two keys in every gateway call to an agent. The <strong>caller&#x27;s</strong> key decides whether it may reach the agent. The <strong>agent&#x27;s own</strong> key (in its env file) is what the agent uses for its model calls. The logs show both, so you can tell who asked and what the agent spent answering.',
        'LiteLLM also accepts older A2A v0.3 clients (<code>&quot;method&quot;: &quot;message/send&quot;</code>, parts with <code>&quot;kind&quot;: &quot;text&quot;</code>) and translates them for these 1.0 agents.',
        'The admin UI&#x27;s <strong>Agents</strong> page shows the same registrations, and can add or delete them.',
        'Registrations are kept in the database. They survive a gateway restart only if the config has <code>store_model_in_db: true</code> (<a href="#lab-1">Lab 1</a>, step 2). If <code>/v1/agents</code> comes back empty after a restart, that setting is missing.',
        'To change where an agent lives, delete its registration (<code>curl -s -X DELETE $GW/v1/agents/$OPS_ID -H &quot;Authorization: Bearer $MK&quot;</code>), edit <code>url</code> in its JSON file and run the registration again. It gets a <strong>new ID</strong>, and keys granted the old ID silently lose access. Re-grant them: set <code>OPS_ID</code> again as in step 3, write <code>{&quot;key&quot;: &quot;$CALLER_KEY&quot;, &quot;object_permission&quot;: {&quot;agents&quot;: [&quot;$OPS_ID&quot;]}}</code> to a file with an unquoted heredoc, and send it to <code>$GW/key/update</code> with <code>-d @file</code>, as in Lab 3. The gateway caches keys, so a key that was used recently can take up to a minute to see the change.',
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
    explain(('sudo mkdir -p /opt/lab-tools', 'A directory for the MCP server&#x27;s program and <code>Containerfile</code>, like <code>/opt/agents</code> in Lab 6.')),
    write_file('/opt/lab-tools/lab_tools.py', 'lab_tools.py', sudo=True),
    explain(
        ('mcp = MCPServer("lab-tools")', 'Create an MCP server named <code>lab-tools</code>. The library handles the protocol: listing tools, checking arguments, returning results.'),
        ('@mcp.tool()', 'Put above a function, this registers it as a tool. The function&#x27;s name becomes the tool&#x27;s name, its docstring becomes the description the model reads, and its type hints (<code>host: str, port: int</code>) become the parameter schema, so you don&#x27;t write <code>TOOL_SPECS</code> by hand as in Lab 5.'),
        ('check_url / check_port / dns_lookup', 'The same kind of plain Python functions as in Lab 5, plus a DNS lookup. If a caller sends a missing or wrong-type argument, the library refuses the call with an error message before the function runs.'),
        ('mcp.run(transport="streamable-http", host="0.0.0.0", port=8701)', 'Serve the tools over HTTP on port 8701, at the path <code>/mcp</code>. &quot;Streamable HTTP&quot; is MCP&#x27;s network transport; the other common one, stdio, only works for a program started on the same machine.'),
    ),
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

systemctl is-active firewalld              # "inactive": skip the next line
sudo firewall-cmd --permanent --add-port=8701/tcp && sudo firewall-cmd --reload
"""),
    explain(
        ('Containerfile', 'The same recipe as the agent image in Lab 6, with the <code>mcp</code> library and one program. <code>EXPOSE 8701</code> documents the port it listens on.'),
        ('sudo podman build -t localhost/lab-tools:1 /opt/lab-tools', 'Build the image and name it <code>localhost/lab-tools</code>, version <code>1</code>.'),
        ('lab-tools.container', 'A Quadlet service for it, publishing port 8701. It has no env file: the tools need no key, because the MCP server never calls the gateway.'),
        ('daemon-reload / start / is-active', 'Generate the service, start it, and check it&#x27;s running.'),
        ('systemctl is-active firewalld / firewall-cmd ...', 'As in Lab 4: open port 8701 only if the firewall is <code>active</code>.'),
    ),
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
ssh 192.168.1.101
sudo cp -a /opt/litellm/config.yaml /opt/litellm/config.yaml.bak-$(date +%F)
sudo vi /opt/litellm/config.yaml             # paste the block above at the end, starting in column 1
sudo systemctl restart litellm
sudo journalctl -u litellm -f                # Ctrl-C once you see "Uvicorn running"
exit                                         # back to .100
"""),
    explain(
        ('ssh 192.168.1.101', 'Log in to the gateway host. The config file is there, not on .100.'),
        ('mcp_servers: / lab_tools: / url: / transport: http', 'A new top-level section of the config, not indented. It names the server <code>lab_tools</code> and tells the gateway where it is and that it speaks MCP over plain HTTP.'),
        ('sudo cp -a ... / sudo vi ...', 'Back up the config, then open it to paste the block, as in Lab 1.'),
        ('sudo systemctl restart litellm / journalctl -f', 'Restart so the gateway reads the change, and watch it start.'),
        ('exit', 'Log out of .101, back to your shell on .100.'),
    ),
    p('Back on .100, check that LiteLLM sees the tools:'),
    code(r"""
curl -s $GW/mcp-rest/tools/list -H "Authorization: Bearer $MK" | jq -r '.tools[].name'
# check_url
# check_port
# dns_lookup
"""),
    explain(
        ('curl -s $GW/mcp-rest/tools/list ...', 'Ask the gateway which MCP tools it can reach. <code>/mcp-rest/</code> is a plain-HTTP view of MCP that&#x27;s easy to try with curl; agents use the real MCP endpoint, <code>/mcp/</code>.'),
        ("jq -r '.tools[].name'", 'Print each tool&#x27;s name.'),
    ),
    h3('3. A key that may use lab_tools'),
    p('As with agents, a virtual key sees no MCP servers until you grant them, in <code>object_permission.mcp_servers</code>. Server names work here.'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias": "mcp-agent", "models": ["lab-agent"], "object_permission": {"mcp_servers": ["lab_tools"]}}' \
  | jq -r .key
read -rsp 'mcp-agent key: ' MCP_KEY; echo
echo "MCP_KEY=$MCP_KEY" >> ~/gw-labs/keys.env
"""),
    explain(
        ('"object_permission": {"mcp_servers": ["lab_tools"]}', 'Grant this key the <code>lab_tools</code> server. Because a name works here, no variable is needed and the JSON can stay in single quotes.'),
        ("read -rsp ... / echo ... >> keys.env", 'Paste the key into <code>MCP_KEY</code> and save it in your key file.'),
    ),
    h3('4. An agent with no tools of its own'),
    p('<code>mcp_agent.py</code> connects to the gateway&#x27;s MCP endpoint, asks which tools its key may use, hands them to the model, and sends each tool call back through the gateway. Compare it to <code>agent.py</code>: the loop is the same, and the tool code is gone.'),
    write_file('~/gw-labs/mcp_agent.py', 'mcp_agent.py'),
    p('What the program does, part by part:'),
    explain(
        ('import httpx2', 'The HTTP library the <code>mcp</code> client uses. It isn&#x27;t installed separately: it comes with <code>mcp</code>.'),
        ('llm = OpenAI(...)', 'The same gateway client as in Lab 5, for model requests.'),
        ('call_tool(mcp, name, arguments)', 'Runs one tool through the gateway, like <code>call_tool</code> in Lab 5. Unknown tools and bad arguments already come back from the MCP server as error text; this also catches broken JSON from the model and errors from the gateway, and hands them to the model instead of crashing.'),
        ('httpx2.AsyncClient(headers={"Authorization": ...})', 'An HTTP client that sends the agent&#x27;s key with every request. The gateway uses it to decide which MCP servers this agent may see.'),
        ('Client(streamable_http_client(GW + "/mcp/", ...))', 'Connect to the gateway&#x27;s MCP endpoint, which looks like one MCP server that holds every tool the key may use. <code>async with</code> closes the connection when the block ends.'),
        ('tools = (await mcp.list_tools()).tools', 'Ask which tools exist. This replaces the tool functions and <code>TOOLS</code> table from Lab 5: the agent learns its tools at startup.'),
        ('specs = [...]', 'Turn each MCP tool description into the format the chat API expects, the same shape as <code>TOOL_SPECS</code> in Lab 5. <code>input_schema</code> is the JSON Schema the MCP server built from the type hints.'),
        ('for _ in range(8): ...', 'The same agent loop as Lab 5: ask the model; if it wants tools, run each one (here through <code>call_tool</code>, which goes to the gateway, which goes to the MCP server) and add the results as <code>tool</code> messages; stop when it answers in text, or after 8 passes.'),
        ('asyncio.run(main(...))', 'The <code>mcp</code> library is asynchronous (<code>async</code>/<code>await</code>), so the program runs inside <code>asyncio</code>. The logic is the same as in <code>agent.py</code>.'),
    ),
    h3('Verify'),
    code(r"""
cd ~/gw-labs && . .venv/bin/activate
pip install "mcp==2.3.0"
AGENT_KEY=$MCP_KEY python mcp_agent.py "Resolve github.com, check whether port 4000 is open on 192.168.1.101, and fetch http://192.168.1.101:4000/health/liveliness."
# tools from the gateway: ['lab_tools-check_url', 'lab_tools-check_port', 'lab_tools-dns_lookup']
#   [mcp] lab_tools-dns_lookup({"name":"github.com"}) -> 140.82.112.3
#   [mcp] lab_tools-check_port({"host":"192.168.1.101","port":4000}) -> 192.168.1.101:4000 is open
#   [mcp] lab_tools-check_url({"url":"http://192.168.1.101:4000/health/liveliness"}) -> HTTP 200 in 18 ms
# All three checks done: ...
"""),
    explain(
        ('cd ~/gw-labs && . .venv/bin/activate', 'Go to the lab directory and switch to its Python environment.'),
        ('pip install "mcp==2.3.0"', 'Install the <code>mcp</code> library, which <code>mcp_agent.py</code> uses to talk to the gateway&#x27;s MCP endpoint. Only needed once.'),
        ('AGENT_KEY=$MCP_KEY python mcp_agent.py "..."', 'Run the MCP agent with the <code>mcp-agent</code> key. The first line it prints is the tool list it got from the gateway; each <code>[mcp]</code> line is a tool call the gateway passed on to the MCP server.'),
    ),
    p('A key that was never granted <code>lab_tools</code> can&#x27;t even connect. Try the <code>ops-agent</code> key:'),
    code(r"""
. ~/gw-labs/keys.env                       # OPS_KEY from Lab 5
curl -s $GW/mcp-rest/tools/list -H "Authorization: Bearer $OPS_KEY" | jq -r .message
# ... The key is not allowed to access any MCP servers.
"""),
    explain(
        ('. ~/gw-labs/keys.env', 'Load your saved keys, so <code>$OPS_KEY</code> is set even in a new shell.'),
        ('... $OPS_KEY | jq -r .message', 'The same tool list request with a key that wasn&#x27;t granted the server. This endpoint reports refusals in a <code>message</code> field.'),
    ),
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
echo "$IDS"                                 # ["...","..."]: two agent IDs

cat > ~/gw-labs/coordinator-key.json <<EOF
{
  "key_alias": "coordinator",
  "models": ["lab-agent"],
  "object_permission": {"agents": $IDS}
}
EOF
cat ~/gw-labs/coordinator-key.json

curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d @$HOME/gw-labs/coordinator-key.json | jq -r .key
read -rsp 'coordinator key: ' COORD_KEY; echo
echo "COORD_KEY=$COORD_KEY" >> ~/gw-labs/keys.env
"""),
    explain(
        ('jq -c \'[.[] | select(... or ...) | .agent_id]\'', 'Keep the two agents by name, take their IDs, and collect them into a JSON list (the outer <code>[ ]</code>). <code>-c</code> prints it compactly on one line, ready to drop into the key&#x27;s settings.'),
        ('IDS=$(...)', 'Store that list in <code>IDS</code>.'),
        ('cat > ~/gw-labs/coordinator-key.json <<EOF', 'Write the key&#x27;s settings, with <code>$IDS</code> replaced by the list. It already has its brackets and quotes, so it goes in without any.'),
        ('curl ... -d @$HOME/gw-labs/coordinator-key.json', 'Create the key, paste it into <code>COORD_KEY</code>, and save it in your key file.'),
    ),
    h3('2. The coordinator'),
    write_file('~/gw-labs/coordinator.py', 'coordinator.py'),
    p('What the program does, part by part:'),
    explain(
        ('llm = OpenAI(...) / auth = {...}', 'The gateway client for model requests, as in Lab 5, and the <code>Authorization</code> header for the plain HTTP calls below. Both use the coordinator&#x27;s key.'),
        ('list_agents()', 'GET <code>/v1/agents</code> with the coordinator&#x27;s key, the same call as in Lab 7. The gateway returns only the agents this key was granted, and the function turns that into <code>{name: description}</code>.'),
        ('ask_agent(agent, message)', 'Build the same A2A message as <code>ask.json</code> in Lab 6 (with a fresh <code>messageId</code> each time, from <code>uuid4()</code>) and POST it to <code>/a2a/&lt;agent&gt;</code> on the gateway. It returns the reply text from the task, as your <code>jq</code> filter did in Lab 6.'),
        ('except ... return f"error from {agent}: ..."', 'Anything that goes wrong (the agent is too slow, its service is down, the gateway sends back an error or something unexpected) becomes a text answer instead of a crash. The model reads it and can try again, try another agent, or report the problem.'),
        ('roster = ...', 'One line per agent, <code>- name: description</code>, added to the system prompt. That&#x27;s how the model knows which agent does what.'),
        ('tools = [ask_agent ...]', 'The coordinator&#x27;s only tool. <code>&quot;enum&quot;: list(agents)</code> limits <code>agent</code> to names that actually exist, so the model can&#x27;t invent one.'),
        ('"You cannot check anything yourself..."', 'The system prompt. Telling it that it can&#x27;t do the work itself stops it guessing an answer instead of delegating.'),
        ('for _ in range(8): ...', 'The agent loop from Lab 5 with one tool. Each tool call is decoded; if the arguments don&#x27;t fit, the model is told so (the <code>!!</code> line). Otherwise it prints <code>-&gt;</code>, asks the agent, prints <code>&lt;-</code> and adds the answer as a <code>tool</code> message. After 8 passes it stops.'),
    ),
    h3('Verify'),
    code(r"""
cd ~/gw-labs && . .venv/bin/activate && . ./keys.env
START=$(date -u +%FT%T)                    # remember when this run started, for the next step
AGENT_KEY=$COORD_KEY python coordinator.py
# agents on the gateway: ['ops-agent', 'writer-agent']
#   -> ops-agent: Check http://192.168.1.101:4000/health/liveliness and whether SSH (port 22) is open on 192.168.1.100 ...
#   <- ops-agent: Gateway health endpoint: UP, HTTP 200 in 18 ms. Port 22 on 192.168.1.100: open ...
#   -> writer-agent: Please turn these findings into a short, clear status update ...
#   <- writer-agent: Quick check-in: the gateway is up and responding normally ...
# **Status update: all services operational** ...
"""),
    explain(
        ('cd ~/gw-labs && . .venv/bin/activate && . ./keys.env', 'Go to the lab directory, switch to its Python environment and load your saved keys, so <code>$COORD_KEY</code> is set even in a new shell.'),
        ('START=$(date -u +%FT%T)', 'Save the current time in UTC, such as <code>2026-10-06T14:05:09</code>. The next step uses it to count only the requests this run caused.'),
        ('AGENT_KEY=$COORD_KEY python coordinator.py', 'Run the coordinator with its key. With no question given, it uses a built-in example. <code>-&gt;</code> lines are messages it sends to an agent, <code>&lt;-</code> lines are the answers.'),
    ),
    p('Give it your own goals: &quot;Find out whether Open WebUI on 192.168.1.100:3000 is up and write a one-line note for the team.&quot; While it runs, <code>sudo journalctl -u ops-agent -f</code> in another terminal shows the tool calls happening inside the delegated agent.'),
    h3('See the whole chain'),
    code(r"""
curl -s "$GW/spend/logs?start_date=$(date -u +%F)&end_date=$(date -u -d tomorrow +%F)&summarize=false" \
  -H "Authorization: Bearer $MK" \
  | jq -r --arg start "$START" '[.[] | select(.startTime >= $start)]
      | group_by(.metadata.user_api_key_alias)[] | "\(.[0].metadata.user_api_key_alias // "master")\t\(length) requests"'
# coordinator    4 requests
# ops-agent      ...
# writer-agent   ...
"""),
    explain(
        ('curl -s "$GW/spend/logs?..."', 'Today&#x27;s request log, as in Lab 5.'),
        ('--arg start "$START"', 'Pass the shell&#x27;s <code>$START</code> into <code>jq</code>, where it&#x27;s called <code>$start</code>.'),
        ('[.[] | select(.startTime >= $start)]', 'Keep only the requests made since the coordinator run began. The log has every request from today, including the earlier labs&#x27;, which would hide what this one question caused. Times in the log look like <code>2026-10-06T14:05:12.303000Z</code>, so comparing them as text works.'),
        ("group_by(.metadata.user_api_key_alias)[]", 'Sort the requests into groups, one per key alias, and go through each group.'),
        ('"\\(.[0].metadata.user_api_key_alias // \"master\")\\t\\(length) requests"', 'For each group, print the alias (taken from its first request) and how many requests it holds. <code>//</code> means &quot;or, if empty&quot;: requests made with the master key have no alias.'),
    ),
    p('Spend logs are written in batches, so wait a minute after the run before you look. One question to the coordinator turned into requests under three different keys. That&#x27;s the point of putting the gateway in the middle: you can see how much work each agent did, and limit or switch off any one of them.'),
    h3('Notes'),
    ul([
        'To add a specialist, run another agent from the same image (a new <code>.container</code> file with a new name, port and prompt), register it, and grant its ID to the coordinator&#x27;s key. The coordinator&#x27;s code doesn&#x27;t change.',
        'Delegation multiplies requests. A <code>max_steps</code> cap and an <code>rpm_limit</code> on every agent&#x27;s key keep a confused coordinator from flooding the model server.',
        'This coordinator waits for each answer before it continues. Long-running agents should return a task right away and report progress; A2A supports that through task states and streaming.',
    ]),
)

# ---------------------------------------------------------------- lab 10
L10 = lab(10, 'Coding Agents Through the Gateway: opencode and Claude Code', '192.168.1.100 → 192.168.1.101',
    goal('point a coding agent at the gateway instead of straight at a model server, with its own key, so its usage is logged and limited like every other agent, and give it the <code>lab_tools</code> MCP tools.'),
    p('Both opencode and Claude Code are assumed to be installed on .100, where your keys are. Neither setup below changes the agents&#x27; normal configuration: opencode gets an extra config file that you name on the command line, and Claude Code gets its settings from environment variables in one shell.'),
    h3('1. A key for coding agents'),
    code(r"""
curl -s $GW/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_alias": "coding-agent", "models": ["lab-agent"], "rpm_limit": 120, "object_permission": {"mcp_servers": ["lab_tools"]}}' \
  | jq -r .key
read -rsp 'coding-agent key: ' CODING_KEY; echo
echo "CODING_KEY=$CODING_KEY" >> ~/gw-labs/keys.env
"""),
    explain(
        ('curl -s $GW/key/generate ... | jq -r .key', 'Create a <code>coding-agent</code> key that may use <code>lab-agent</code>, up to 120 requests a minute, plus the <code>lab_tools</code> MCP server from Lab 8. Coding agents send many requests per task, so the limit is higher than the other agents&#x27;.'),
        ("read -rsp ... / echo ... >> keys.env", 'Paste the key into <code>CODING_KEY</code> and save it in your key file, as in the earlier labs.'),
    ),
    h3('2. opencode'),
    p('opencode can talk to any OpenAI-compatible server. Rather than edit your usual <code>~/.config/opencode/config.json</code>, put the gateway settings in a separate file. When the <code>OPENCODE_CONFIG</code> environment variable names a file, opencode loads it <em>on top of</em> your usual config: it adds the gateway provider and makes <code>lab-agent</code> the default, and your existing providers and MCP servers stay as they are. Without the variable, opencode behaves exactly as before.'),
    code(r"""
cat > ~/gw-labs/opencode-lab.json <<'EOF'
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
EOF
"""),
    explain(
        ("cat > ~/gw-labs/opencode-lab.json <<'EOF'", 'Write the file. The heredoc is quoted, so <code>{env:LITELLM_KEY}</code> is saved as typed: it&#x27;s opencode&#x27;s own syntax for reading an environment variable when it starts, which keeps the key out of the file.'),
        ('"model": "litellm/lab-agent"', 'The default model, written as <code>provider/model</code>: the <code>lab-agent</code> model from the provider defined below.'),
        ('"provider": {"litellm": {...}}', 'A provider named <code>litellm</code>. <code>npm</code> names the client library opencode uses for any OpenAI-compatible server; <code>options</code> gives it the gateway&#x27;s address and the key.'),
        ('"models": {"lab-agent": {...}}', 'Which models to offer from that provider. <code>tools: true</code> says it can call tools; <code>limit</code> tells opencode how much it can send and receive. Set <code>context</code> to the context length the model is actually loaded with, so opencode compacts the conversation before it overflows.'),
        ('"mcp": {"lab-tools": {...}}', 'An MCP server: the gateway&#x27;s <code>/mcp/</code> endpoint, with the same key sent in the <code>Authorization</code> header.'),
    ),
    code(r"""
. ~/gw-labs/keys.env
export LITELLM_KEY=$CODING_KEY
export OPENCODE_CONFIG=~/gw-labs/opencode-lab.json
opencode debug config | jq -r .model                # litellm/lab-agent
opencode run "Reply with the single word pong."
opencode run "Use the lab-tools check_port tool to check whether port 22 is open on 192.168.1.101."
"""),
    explain(
        ('. ~/gw-labs/keys.env / export LITELLM_KEY=$CODING_KEY', 'Load your keys and hand the <code>coding-agent</code> key to opencode under the name the file expects.'),
        ('export OPENCODE_CONFIG=...', 'Tell opencode to load the lab file on top of your usual config, for every opencode command in this shell. Close the shell (or <code>unset OPENCODE_CONFIG LITELLM_KEY</code>) and opencode is back to normal.'),
        ('opencode debug config | jq -r .model', 'Print the configuration opencode actually ended up with, and pick out the default model. <code>litellm/lab-agent</code> means the lab file was loaded.'),
        ('opencode run "..."', 'Run one task without opening opencode&#x27;s full-screen interface. The first proves the model works through the gateway; the second makes it use an MCP tool through the gateway.'),
    ),
    h3('3. Claude Code'),
    p('Claude Code speaks Anthropic&#x27;s Messages API. LiteLLM serves that too, at <code>/v1/messages</code>, and translates it for whatever model is behind the alias, including the local one. Check it with the <code>coding-agent</code> key:'),
    code(r"""
curl -s $GW/v1/messages -H "Authorization: Bearer $CODING_KEY" -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{"model": "lab-agent", "max_tokens": 400, "messages": [{"role": "user", "content": "Say pong."}]}' \
  | jq -r '.content[] | select(.type == "text") | .text'
# pong
"""),
    explain(
        ('curl -s $GW/v1/messages', 'Anthropic&#x27;s API address on the gateway, instead of the OpenAI-style <code>/v1/chat/completions</code>.'),
        ('-H "Authorization: Bearer $CODING_KEY"', 'The key Claude Code will use, so this proves that key works with Anthropic-style requests.'),
        ("-H 'anthropic-version: 2023-06-01'", 'The Anthropic API requires a version header. This is the current one, despite the date.'),
        ('"max_tokens": 400', 'The Anthropic API requires a limit on the length of the answer.'),
        ("jq -r '.content[] | select(.type == \"text\") | .text'", 'Anthropic-style answers are a list of blocks (text, thinking, tool calls). Print only the text blocks.'),
    ),
    p('Then set these in the shell where you start Claude Code. They last only as long as that shell:'),
    code(r"""
cd ~/gw-labs && . ./keys.env
export ANTHROPIC_BASE_URL=http://192.168.1.101:4000
export ANTHROPIC_AUTH_TOKEN=$CODING_KEY            # sent as "Authorization: Bearer"
export ANTHROPIC_MODEL=lab-agent
export ANTHROPIC_DEFAULT_OPUS_MODEL=lab-agent ANTHROPIC_DEFAULT_SONNET_MODEL=lab-agent
export ANTHROPIC_DEFAULT_FABLE_MODEL=lab-agent ANTHROPIC_DEFAULT_HAIKU_MODEL=lab-agent
export CLAUDE_CODE_SUBAGENT_MODEL=lab-agent
claude mcp add --transport http lab-tools http://192.168.1.101:4000/mcp/ \
  --header "Authorization: Bearer $CODING_KEY"
claude
"""),
    explain(
        ('cd ~/gw-labs && . ./keys.env', 'Work in the lab directory, and load your keys.'),
        ('export ANTHROPIC_BASE_URL=...', 'Send Claude Code&#x27;s requests to the gateway instead of to Anthropic.'),
        ('export ANTHROPIC_AUTH_TOKEN=$CODING_KEY', 'The <code>coding-agent</code> key, sent as a Bearer token.'),
        ('export ANTHROPIC_MODEL=lab-agent', 'The model name to ask for in the main conversation.'),
        ('ANTHROPIC_DEFAULT_*_MODEL / CLAUDE_CODE_SUBAGENT_MODEL', 'Claude Code asks for other models too: a small one for background jobs, others when you switch with <code>/model</code>, and one for subagents. The key only allows <code>lab-agent</code>, so map every one of them to it; otherwise those requests are refused.'),
        ('claude mcp add --transport http lab-tools URL --header ...', 'Register the gateway&#x27;s MCP endpoint with Claude Code under the name <code>lab-tools</code>, sending the key with every call. Unlike the variables, this is saved: in <code>~/.claude.json</code>, with the key written out, and only for the current directory (<code>~/gw-labs</code>), which is Claude Code&#x27;s default. Remove it with <code>claude mcp remove lab-tools</code> when you&#x27;re done.'),
        ('claude', 'Start Claude Code. Ask it to use the lab-tools <code>check_port</code> tool, as with opencode.'),
    ),
    h3('Verify'),
    p('Run a small task in either agent, then list what the <code>coding-agent</code> key did today. Spend logs are written in batches, so give it a minute:'),
    code(r"""
curl -s "$GW/spend/logs?start_date=$(date -u +%F)&end_date=$(date -u -d tomorrow +%F)&summarize=false" \
  -H "Authorization: Bearer $MK" \
  | jq -r '.[] | select(.metadata.user_api_key_alias == "coding-agent") | "\(.startTime)  \(.call_type)  tokens=\(.total_tokens)"'
"""),
    explain(
        ('curl -s "$GW/spend/logs?..."', 'Today&#x27;s request log, as in Lab 5.'),
        ('select(.metadata.user_api_key_alias == "coding-agent")', 'Keep only the requests made with the <code>coding-agent</code> key.'),
        ('"\\(.startTime)  \\(.call_type)  tokens=\\(.total_tokens)"', 'Print the time, the kind of call and the tokens used. Chat requests show up as <code>acompletion</code> and MCP tool calls as <code>/mcp/</code>; Claude Code&#x27;s Anthropic-style requests get their own call type. All of them are under the same key.'),
    ),
    p('The admin UI&#x27;s <strong>Logs</strong> page shows the same, filtered by key alias <code>coding-agent</code>, including the MCP tool calls.'),
    h3('Notes'),
    ul([
        'Use <code>ANTHROPIC_AUTH_TOKEN</code>, not <code>ANTHROPIC_API_KEY</code>. Claude Code treats the latter as a real Anthropic key.',
        'A local 27B model is fine for trying this out and for small edits. For serious work on a big codebase, put a larger or cloud model behind a separate alias and add it to this key&#x27;s <code>models</code>.',
        'Both agents can run shell commands on the machine they run on. Keep their permission prompts on (<code>&quot;permission&quot;: {&quot;bash&quot;: &quot;ask&quot;}</code> in opencode); the gateway controls model access, not what the agent does locally.',
    ]),
)

# ---------------------------------------------------------------- lab 11
L11 = lab(11, 'Operate It: Reboots, Logs, Usage, Kill Switches, Upgrades', '192.168.1.100 and 192.168.1.101',
    goal('prove everything you built comes back after a reboot, know where to look when something breaks, see what each app and agent used, and shut one off without touching the rest.'),
    h3('1. Everything you built, as services'),
    table(['Host', 'Service', 'Port', 'Files'], [
        ['.101', '<code>litellm</code>, <code>litellm-db</code> (set up before the labs)', '4000', '<code>/opt/litellm/</code>, <code>/etc/containers/systemd/litellm*</code>'],
        ['.100', '<code>open-webui</code>', '3000', '<code>/opt/open-webui/</code>, volume <code>open-webui</code>'],
        ['.100', '<code>ops-agent</code>, <code>writer-agent</code>', '8601, 8602', '<code>/opt/agents/</code>, image <code>localhost/a2a-agent:1</code>'],
        ['.100', '<code>lab-tools</code>', '8701', '<code>/opt/lab-tools/</code>, image <code>localhost/lab-tools:1</code>'],
        ['.100', 'scripts (not services)', '&ndash;', '<code>~/gw-labs/</code>'],
    ]),
    code(r"""
# on .100
systemctl list-units --no-pager 'open-webui*' 'ops-agent*' 'writer-agent*' 'lab-tools*'
sudo podman ps
"""),
    explain(
        ("systemctl list-units --no-pager 'open-webui*' ...", 'List the lab&#x27;s services and whether each is running. The <code>*</code> patterns are quoted so systemctl sees them, not the shell.'),
        ('sudo podman ps', 'List the running containers, with how long each has been up and its ports.'),
    ),
    h3('2. The reboot test'),
    p('This is the real proof that everything you built comes back on its own. Reboot the agent host; the gateway keeps running:'),
    code(r"""
sudo systemctl reboot                      # on .100; your session drops
ssh 192.168.1.100                          # log in again after a minute
systemctl is-active open-webui ops-agent writer-agent lab-tools    # all "active"
curl -s http://localhost:8601/.well-known/agent-card.json | jq -r .name

export GW=http://192.168.1.101:4000
read -rsp 'LiteLLM master key: ' MK; echo; export MK
. ~/gw-labs/keys.env
curl -s $GW/health/readiness | jq '{status, db}'
"""),
    explain(
        ('sudo systemctl reboot', 'Restart .100. Your SSH session drops.'),
        ('ssh 192.168.1.100', 'Log in again once it&#x27;s back up.'),
        ('systemctl is-active ...', 'One word per service. Every line should be <code>active</code>, without you having started anything.'),
        ('curl ... agent-card.json | jq -r .name', 'Ask <code>ops-agent</code> for its card and print its name: proof that it&#x27;s answering, not just running.'),
        ('export GW=... / read -rsp ... MK / . ~/gw-labs/keys.env', 'A reboot empties every shell variable. Set the gateway address and master key again as in Lab 1, and load your saved app keys. The rest of this lab needs them.'),
        ('curl -s $GW/health/readiness ...', 'Check you can still reach the gateway and its database from .100.'),
    ),
    p('If a service isn&#x27;t active, check that its file is in <code>/etc/containers/systemd/</code>, that it has an <code>[Install]</code> section with <code>WantedBy=multi-user.target</code>, and run <code>sudo /usr/libexec/podman/quadlet -dryrun</code> to see Quadlet&#x27;s complaints about any file it couldn&#x27;t convert.'),
    h3('3. Logs'),
    code(r"""
sudo journalctl -u ops-agent -f                 # one service, live
sudo journalctl -u litellm --since '10 min ago' # on .101: gateway errors, model failures
sudo journalctl -b -u 'ops-agent' -u 'lab-tools' --no-pager   # everything since the last boot
"""),
    explain(
        ('-f', 'Keep following: new lines appear as they&#x27;re written, until Ctrl-C.'),
        ("--since '10 min ago'", 'Only lines from the last ten minutes. It also accepts times such as <code>&#x27;2026-10-06 14:00&#x27;</code>.'),
        ('-b -u ... -u ...', 'Only lines since the last boot (<code>-b</code>), from both services mixed together in time order.'),
    ),
    p('A Quadlet container&#x27;s output goes to the journal, so you use <code>journalctl</code>, not <code>podman logs</code> (which still works too).'),
    h3('4. Who used what'),
    code(r"""
curl -s "$GW/spend/logs?start_date=$(date -u -d '7 days ago' +%F)&end_date=$(date -u -d tomorrow +%F)&summarize=false" \
  -H "Authorization: Bearer $MK" \
  | jq -r 'group_by(.metadata.user_api_key_alias)[]
           | "\(.[0].metadata.user_api_key_alias // "master")\t\(length) requests\t\(map(.total_tokens) | add) tokens"'
"""),
    explain(
        ("$(date -u -d '7 days ago' +%F)", 'The date a week ago, so the log covers the last seven days.'),
        ('group_by(...)[]', 'One group per key alias, as in Lab 9.'),
        ('map(.total_tokens) | add', 'Take every request&#x27;s token count in the group and add them up.'),
    ),
    p('The gateway UI shows the same under <strong>Usage</strong> (charts per key and model) and <strong>Logs</strong> (each request, with its prompt and response).'),
    h3('5. Kill switch'),
    code(r"""
# block one key: every request with it fails right away, and nothing else is affected
cat > ~/gw-labs/ops-key.json <<EOF
{"key": "$OPS_KEY"}
EOF
curl -s $GW/key/block   -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d @$HOME/gw-labs/ops-key.json | jq '{key_alias, blocked}'

# ask ops-agent directly, as in Lab 6: it's running, but can't reach the model now
curl -s http://192.168.1.100:8601/ -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d @$HOME/gw-labs/ask.json | jq
sudo journalctl -u ops-agent -n 5 --no-pager                   # "Key is blocked"

curl -s $GW/key/unblock -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d @$HOME/gw-labs/ops-key.json | jq '{key_alias, blocked}'

# delete a key for good
cat > ~/gw-labs/delete-keys.json <<EOF
{"keys": ["$CALLER_KEY"]}
EOF
curl -s $GW/key/delete  -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d @$HOME/gw-labs/delete-keys.json
sed -i '/^CALLER_KEY=/d' ~/gw-labs/keys.env

# stop an agent from being reachable through the gateway
OPS_ID=$(curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r '.[] | select(.agent_name=="ops-agent") | .agent_id')
curl -s -X DELETE $GW/v1/agents/$OPS_ID -H "Authorization: Bearer $MK"
"""),
    explain(
        ('cat > ~/gw-labs/ops-key.json <<EOF', 'A request body naming the key to act on, with <code>$OPS_KEY</code> filled in. Block and unblock both use it.'),
        ('/key/block', 'Block the key. The answer shows <code>blocked</code> is now <code>true</code>. Unlike other key changes, which can take a minute to apply (Lab 3), a block takes effect on the very next request.'),
        ('curl -s http://192.168.1.100:8601/ ... | jq', 'Ask <code>ops-agent</code> a question directly, skipping the gateway, with the <code>ask.json</code> from Lab 6. The agent still runs, but its own model request is refused, so you get an error back instead of an answer.'),
        ('sudo journalctl -u ops-agent -n 5 --no-pager', 'The agent&#x27;s log shows why: the gateway answered its model request with &quot;Key is blocked&quot;.'),
        ('/key/unblock', 'Unblock it, which also takes effect at once. Ask again and the answer is back.'),
        ('{"keys": ["$CALLER_KEY"]} / /key/delete', 'Delete takes a list, so you can remove several keys at once. A deleted key can&#x27;t be brought back.'),
        ("sed -i '/^CALLER_KEY=/d' ~/gw-labs/keys.env", 'Remove the deleted key&#x27;s line from your key file: <code>sed -i</code> edits the file in place, and <code>/^CALLER_KEY=/d</code> deletes the line that starts with <code>CALLER_KEY=</code>.'),
        ('OPS_ID=$(...) / curl -s -X DELETE $GW/v1/agents/$OPS_ID', 'Look up <code>ops-agent</code>&#x27;s ID by name, as in Lab 7, and remove its registration. <code>-X DELETE</code> sends a DELETE request instead of a GET. The service on .100 keeps running, but the gateway no longer forwards to it, and <code>/a2a/ops-agent</code> answers &quot;not found&quot;.'),
    ),
    p('Blocking <code>ops-agent</code>&#x27;s key stops that agent from reaching any model, even when someone calls it directly on port 8601. That&#x27;s the advantage of agents having their own keys instead of sharing one.'),
    h3('6. Upgrades'),
    p('<strong>An agent:</strong> edit the code in <code>/opt/agents</code>, rebuild with a new tag, point the Quadlet at it, restart. Keeping the old tag makes rolling back a one-line change.'),
    code(r"""
sudo podman build -t localhost/a2a-agent:2 /opt/agents
sudo sed -i 's#localhost/a2a-agent:1#localhost/a2a-agent:2#' /etc/containers/systemd/{ops,writer}-agent.container
sudo systemctl daemon-reload && sudo systemctl restart ops-agent writer-agent
"""),
    explain(
        ('sudo podman build -t localhost/a2a-agent:2 /opt/agents', 'Build the changed code as version <code>2</code>. Version <code>1</code> stays on the machine.'),
        ("sudo sed -i 's#...:1#...:2#' /etc/containers/systemd/{ops,writer}-agent.container", 'In both Quadlet files (the braces expand to the two file names), replace the image version 1 with 2.'),
        ('daemon-reload && restart', 'Apply the changed files and restart both agents on the new image. To roll back, run the same <code>sed</code> the other way round.'),
    ),
    p('Upgrading LiteLLM itself, and backing up its database, are in <a href="#l0-options">Lab 0, Part 5</a>.'),
    h3('Clean up the labs'),
    code(r"""
# on .100: stop and remove the services, their files and images
sudo systemctl stop open-webui ops-agent writer-agent lab-tools open-webui-volume
sudo rm /etc/containers/systemd/{open-webui.container,open-webui.volume,ops-agent.container,writer-agent.container,lab-tools.container}
sudo systemctl daemon-reload
sudo podman volume rm open-webui
sudo podman rmi -i localhost/a2a-agent:1 localhost/a2a-agent:2 localhost/lab-tools:1
sudo rm -rf /opt/agents /opt/lab-tools /opt/open-webui
cd ~/gw-labs && claude mcp remove lab-tools; cd ~   # only if you did the Claude Code part of Lab 10

# on .100 still: delete the lab keys and agent registrations on the gateway
curl -s $GW/key/delete -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d '{"key_aliases": ["chat-ui", "ops-agent", "writer-agent", "ops-caller", "mcp-agent", "coordinator", "coding-agent"]}'
for a in ops-agent writer-agent; do
  ID=$(curl -s $GW/v1/agents -H "Authorization: Bearer $MK" | jq -r --arg n "$a" '.[] | select(.agent_name == $n) | .agent_id')
  [ -n "$ID" ] && curl -s -X DELETE $GW/v1/agents/$ID -H "Authorization: Bearer $MK"; echo
done
rm -rf ~/gw-labs

# on .101: remove the mcp_servers block from Lab 8 (and the lab- models, if you added them
# only for these labs) from /opt/litellm/config.yaml, then: sudo systemctl restart litellm
"""),
    explain(
        ('sudo systemctl stop ...', 'Stop the four services, and <code>open-webui-volume</code>, the small service Quadlet made from the <code>.volume</code> file. Left running, systemd keeps it marked as done after the volume is gone, which can confuse a later redo of Lab 4.'),
        ('sudo rm /etc/containers/systemd/{...}', 'Delete their Quadlet files. After the <code>daemon-reload</code> the services no longer exist.'),
        ('sudo podman volume rm open-webui', 'Delete Open WebUI&#x27;s data: accounts and chats.'),
        ('sudo podman rmi -i ...', 'Delete the images you built, including version 2 of the agent image from the upgrade step. <code>-i</code> skips any that don&#x27;t exist instead of stopping with an error.'),
        ('sudo rm -rf /opt/agents /opt/lab-tools /opt/open-webui', 'Delete the lab directories and everything in them. <code>-r</code> includes their contents and <code>-f</code> skips the prompts, so check the paths before you press Enter.'),
        ('claude mcp remove lab-tools', 'Undo the <code>claude mcp add</code> from Lab 10. It was saved for the <code>~/gw-labs</code> directory, so run it from there.'),
        ('curl -s $GW/key/delete ... "key_aliases": [...]', 'Delete every key the labs created, by name, in one request. Names that are already gone, such as <code>ops-caller</code> from step 5, don&#x27;t cause an error.'),
        ('for a in ops-agent writer-agent; do ... done', 'For each agent, look up its ID by name and delete its registration. <code>[ -n &quot;$ID&quot; ] &amp;&amp;</code> skips the delete if the agent is already gone, like <code>ops-agent</code> after step 5.'),
        ('rm -rf ~/gw-labs', 'Last, delete your lab directory, including <code>keys.env</code>, the scripts and the opencode file. It comes after the gateway clean-up because <code>$MK</code> and the key names are all you need there, and nothing in the directory is used again.'),
    ),
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
    <a href="#lab-0">LiteLLM setup reference</a>
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
