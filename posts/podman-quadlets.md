title: Run Containers as systemd Services with Podman Quadlets
date: 2026-10-19
description: Turn a podman run command into a service that starts at boot, restarts when it crashes and logs to the journal, using a short Quadlet file instead of Docker's daemon.
---

You have a container working with `podman run`. Now you want it to start when the server boots, come back if it crashes, write its logs where the rest of your logs go, and start after the things it depends on. Docker does this with a daemon and `--restart=always`. Podman has no daemon, so the job goes to the service manager that's already running everything else on the box: **systemd**.

**Quadlet** is how you describe a container to systemd. You write a short file that looks like a systemd unit, and Podman turns it into a real service. If you've seen `podman generate systemd`, that command is deprecated; Quadlet replaces it.

> Everything below was run on Rocky Linux 9.8 with Podman 5.8.2. It works the same on RHEL 9 and 10, Rocky 10, and Fedora. Quadlet first shipped in Podman 4.4.

## How it works

1. You write a file such as `hello.container` in `/etc/containers/systemd/`.
2. You run `systemctl daemon-reload`. That runs Podman's Quadlet *generator*, which reads your file and writes a full service, `hello.service`, into `/run/systemd/generator/`.
3. You manage `hello.service` like any other service: `start`, `stop`, `status`, `journalctl`.

The generated service lives in `/run`, which is in memory. It's rebuilt at every boot and every `daemon-reload`, so you never edit it. Your `.container` file is the only thing you maintain, and it's short enough to keep in Git.

| Who runs the container | Put Quadlet files in | Manage with |
|---|---|---|
| root (rootful) | `/etc/containers/systemd/` | `sudo systemctl ...` |
| your own user (rootless) | `~/.config/containers/systemd/` | `systemctl --user ...` |

Rootful is simpler, so we'll start there and cover rootless later.

## Your first Quadlet: a small web server

Make a folder with a web page in it:

```bash
sudo mkdir -p /srv/hello
echo "Hello from a Quadlet" | sudo tee /srv/hello/index.html
```

Then write the Quadlet file. This uses `tee` with a heredoc so you can paste it in one go:

```bash
sudo tee /etc/containers/systemd/hello.container <<'EOF'
[Unit]
Description=Hello web server

[Container]
Image=docker.io/library/nginx:1.29-alpine
ContainerName=hello
PublishPort=8080:80
Volume=/srv/hello:/usr/share/nginx/html:ro,Z

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

Each line does one job:

| Line | What it does |
|---|---|
| `[Unit]` `Description=` | Ordinary systemd. This text shows up in `systemctl status`. |
| `[Container]` | The Quadlet part. Each key here becomes an option on the `podman run` command that systemd will run. |
| `Image=` | The image to run. Use the full name (`docker.io/library/...`), not just `nginx`, so nothing has to guess which registry you meant. |
| `ContainerName=hello` | Names the container `hello`. Without it, Quadlet names it `systemd-hello`. |
| `PublishPort=8080:80` | Port 8080 on the host goes to port 80 in the container. Same as `-p 8080:80`. |
| `Volume=/srv/hello:...:ro,Z` | Mounts the host folder into the container, read-only (`ro`). The `Z` relabels the folder for SELinux so the container is allowed to read it. Leave it off and nginx gets "permission denied". |
| `[Service]` `Restart=always` | Ordinary systemd: if the container stops for any reason other than you stopping it, start it again. |
| `[Install]` `WantedBy=multi-user.target` | Start it at boot, along with the server's other services. |

Now have systemd pick it up and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl start hello
systemctl status hello --no-pager
curl http://localhost:8080
```

`status` shows it running, and `generated` tells you Quadlet made it:

```text
● hello.service - Hello web server
     Loaded: loaded (/etc/containers/systemd/hello.container; generated)
     Active: active (running) since Mon 2026-10-19 09:22:17 CDT; 3s ago
```

`curl` prints `Hello from a Quadlet`. To reach it from another machine, open the port in the firewall:

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

## Don't run `systemctl enable`

Habit says to run `systemctl enable hello` next. It fails:

```text
Failed to enable unit: Unit /run/systemd/generator/hello.service is transient or generated.
```

That's expected. `enable` works by creating links next to a unit file, and a generated unit is rebuilt from scratch every time. In a Quadlet, the `[Install]` section does that job instead: the generator reads `WantedBy=multi-user.target` and creates the boot link itself. `systemctl is-enabled hello` answers `generated`, and the container starts at the next boot.

To stop a Quadlet from starting at boot, remove or comment out the `[Install]` section and run `daemon-reload`.

## See what Quadlet built

You don't have to take the generator's work on trust. Two ways to look:

```bash
systemctl cat hello
sudo /usr/libexec/podman/quadlet -dryrun
```

`systemctl cat` shows the unit systemd is using. `quadlet -dryrun` runs the generator without changing anything and prints every unit it would make, along with any errors in your files. Use `-dryrun -user` for rootless files. If a Quadlet doesn't show up after `daemon-reload`, this is the first thing to run, because a typo in a key name stops the unit from being generated at all.

The most useful line in the output is the command systemd actually runs:

```text
ExecStart=/usr/bin/podman run --name hello --replace --rm --cgroups=split --sdnotify=conmon -d -v /srv/hello:/usr/share/nginx/html:ro,Z --publish 8080:80 docker.io/library/nginx:1.29-alpine
```

Note `--rm` and `--replace`. **The container is thrown away when it stops and created fresh when it starts.** Anything written inside the container and not in a volume is gone after a restart. That's the point: the container stays disposable and your data lives in volumes, which are the next section.

Newer Podman releases also have `podman quadlet list`, which shows every Quadlet and whether it's running:

```text
NAME             UNIT NAME      PATH ON DISK                             STATUS          APPLICATION
hello.container  hello.service  /etc/containers/systemd/hello.container  active/running
```

### It comes back on its own

Kill the container behind systemd's back and watch it return:

```bash
sudo podman kill hello
sleep 4
systemctl show hello -p NRestarts -p ActiveState
```

```text
NRestarts=1
ActiveState=active
```

### Its logs are in the journal

Everything the container prints goes to the journal under the service name, next to the rest of the system's logs:

```bash
sudo journalctl -u hello -f
```

If you ship the journal to Loki or a SIEM, your containers come along with no extra setup.

## Two pieces: a database with its own network, volume and password

Real services have parts. Here's PostgreSQL with a private network, a named volume for its data, and a password kept out of the files. Quadlet has a file type for each part.

First, store the password as a Podman secret, so it never appears in a file you might commit:

```bash
printf 'change-me-to-something-long' | sudo podman secret create demo-db-pass -
```

Then the three Quadlet files. The network and volume files can be empty; defaults are fine.

```bash
sudo tee /etc/containers/systemd/demo.network <<'EOF'
[Network]
EOF

sudo tee /etc/containers/systemd/demo-db.volume <<'EOF'
[Volume]
EOF

sudo tee /etc/containers/systemd/demo-db.container <<'EOF'
[Unit]
Description=Demo PostgreSQL database

[Container]
Image=docker.io/library/postgres:17-alpine
ContainerName=demo-db
Network=demo.network
Volume=demo-db.volume:/var/lib/postgresql/data
Secret=demo-db-pass,type=env,target=POSTGRES_PASSWORD
HealthCmd=pg_isready -U postgres
HealthInterval=10s
Notify=healthy

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start demo-db
```

What's new here:

| Line | What it does |
|---|---|
| `demo.network` | Creates a Podman network. Containers on it can reach each other by container name, and nothing else is on it. |
| `demo-db.volume` | Creates a named volume. It's kept when the container is thrown away and recreated, so the database survives restarts and upgrades. |
| `Network=demo.network` | Joins the network. Naming the *file* (with `.network` on the end) tells Quadlet to make sure the network exists first. |
| `Volume=demo-db.volume:/var/lib/...` | Mounts the named volume where PostgreSQL keeps its data. Again, naming the file adds the dependency. |
| `Secret=demo-db-pass,type=env,target=POSTGRES_PASSWORD` | Hands the secret to the container as the `POSTGRES_PASSWORD` variable. The password is in Podman's secret store, not in this file. |
| `HealthCmd=` `HealthInterval=` | A command Podman runs every 10 seconds to check that the database is actually answering, not just that the process exists. |
| `Notify=healthy` | Tells systemd the service hasn't finished starting until the health check passes. `systemctl start demo-db` waits until PostgreSQL accepts connections, so anything that starts after it can connect straight away. |

Quadlet wired the dependencies up for you. `systemctl cat demo-db` shows:

```text
Requires=demo-network.service
After=demo-network.service
Requires=demo-db-volume.service
After=demo-db-volume.service
```

Note the names, because they trip people up. Each file becomes a service with a suffix, and the Podman object gets a `systemd-` prefix:

| File | systemd unit | Podman object |
|---|---|---|
| `demo.network` | `demo-network.service` | network `systemd-demo` |
| `demo-db.volume` | `demo-db-volume.service` | volume `systemd-demo-db` |
| `demo-db.container` | `demo-db.service` | container `demo-db` (set by `ContainerName=`) |

To prove the network works, run a throwaway client on the same network and connect by name:

```bash
sudo podman run --rm --network systemd-demo -e PGPASSWORD='change-me-to-something-long' \
  docker.io/library/postgres:17-alpine psql -h demo-db -U postgres -c 'select version();'
```

An app container that needs the database joins the same network and adds ordinary systemd ordering, so it starts only once the database is healthy:

```ini
[Unit]
Requires=demo-db.service
After=demo-db.service

[Container]
Network=demo.network
```

## Changing a Quadlet and upgrading the image

Any time you edit a Quadlet file, do both of these, or systemd keeps running the old version:

```bash
sudo systemctl daemon-reload
sudo systemctl restart hello
```

For image upgrades you have two choices.

**Pin the tag and upgrade on purpose.** Change `Image=` to the new tag, then `daemon-reload` and `restart`. You decide when it changes, and the file in Git shows exactly what's running. This is what I use for anything with a database behind it.

**Let Podman do it.** Add `AutoUpdate=registry` under `[Container]`, then turn on Podman's daily timer:

```bash
sudo systemctl enable --now podman-auto-update.timer
sudo podman auto-update --dry-run
```

Once a day, Podman checks whether the registry has a newer image for that tag, pulls it and restarts the service. `--dry-run` shows what it would update without doing it. The timer isn't on by default, which is easy to miss. Auto-update needs the full image name (`docker.io/library/nginx:...`), another reason to always write it out.

## Rootless: the same thing as your own user

Running as an ordinary user means a container breakout lands in an unprivileged account instead of root. The file is nearly the same, but goes in your home directory:

```bash
mkdir -p ~/.config/containers/systemd ~/hello-user
echo "Hello from a rootless Quadlet" > ~/hello-user/index.html

cat > ~/.config/containers/systemd/hello-user.container <<'EOF'
[Unit]
Description=Rootless hello web server

[Container]
Image=docker.io/library/nginx:1.29-alpine
PublishPort=8081:80
Volume=%h/hello-user:/usr/share/nginx/html:ro,Z

[Service]
Restart=always

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user start hello-user
```

What's different:

| Difference | Why |
|---|---|
| `systemctl --user`, no `sudo` | It's your own systemd instance, which runs your services. |
| `%h` | systemd's shorthand for your home directory. |
| `WantedBy=default.target` | User services start with `default.target`; there's no `multi-user.target` in a user's systemd. |
| Port 8081, not 80 | Ordinary users can't listen on ports below 1024 by default. |

One more step matters more than all of these. By default, your user's systemd only runs while you're logged in. Log out, and your containers stop; reboot, and they don't start until you log in. Fix that with:

```bash
sudo loginctl enable-linger $USER
```

## Removing a Quadlet cleanly

This is the one that bites. Network and volume services run once and then sit at `active (exited)`. If you delete the files first, those services *stay* active, with nothing on disk behind them:

```text
● demo-network.service
     Loaded: not-found (Reason: Unit demo-network.service not found.)
     Active: active (exited) since Mon 2026-10-19 09:22:34 CDT; 38s ago
```

The network and volume are still there too. Now suppose you clean up with `podman network rm` and later put the files back. systemd still thinks `demo-network.service` is running, so it never runs it again to recreate the network, and the database container fails to start because its network is missing. I hit exactly this rebuilding a lab. Stop everything first, then delete:

```bash
# 1. Stop the containers, then the network and volume services
sudo systemctl stop demo-db
sudo systemctl stop demo-network demo-db-volume

# 2. Remove the files and tell systemd
sudo rm /etc/containers/systemd/demo.network \
        /etc/containers/systemd/demo-db.volume \
        /etc/containers/systemd/demo-db.container
sudo systemctl daemon-reload

# 3. Remove what Podman made. This deletes the database's data.
sudo podman network rm systemd-demo
sudo podman volume rm systemd-demo-db
sudo podman secret rm demo-db-pass
```

Stopping a volume service doesn't delete the volume, so step 3 is a separate, deliberate step. Skip it if you want to keep the data.

## Why I like this from a security point of view

- **No daemon running as root.** Nothing sits listening on a socket with full control of every container.
- **Rootless is easy.** Same file, different folder, plus `enable-linger`.
- **SELinux stays on.** `:Z` labels the files the container needs instead of turning protection off.
- **Secrets stay out of files**, so the unit files can go in Git and be reviewed like any other change.
- **One place for logs and status.** Containers show up in `systemctl` and `journalctl` with every other service, so your existing monitoring already covers them.

Quadlet also has keys for locking a container down further, such as `ReadOnly=true`, `NoNewPrivileges=true` and `DropCapability=`. Add them one at a time and test, since many images expect to write somewhere or need a capability or two.

## Cheat sheet

| Task | Command |
|---|---|
| Pick up new or changed files | `sudo systemctl daemon-reload` |
| Start, stop, restart | `sudo systemctl start NAME` (or `stop`, `restart`) |
| Status and logs | `systemctl status NAME`, `sudo journalctl -u NAME -f` |
| See the generated unit | `systemctl cat NAME` |
| Check files for errors | `sudo /usr/libexec/podman/quadlet -dryrun` |
| List all Quadlets | `sudo podman quadlet list` |
| Start at boot | `[Install]` `WantedBy=multi-user.target` (not `systemctl enable`) |
| Rootless at boot | `WantedBy=default.target` and `sudo loginctl enable-linger $USER` |
| Automatic image updates | `AutoUpdate=registry` and `sudo systemctl enable --now podman-auto-update.timer` |

If you're running containers in production and want a second pair of eyes on how they're isolated, updated and monitored, [get in touch](/#contact).
