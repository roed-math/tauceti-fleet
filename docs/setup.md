# Setting up a fleet host

This is written for Ubuntu 26.04, the host the fleet has run on longest. The per-user half applies to
every account that runs a fleet. A note on macOS is at the end.

## Ground rules

- **The fleet acts as its own GitHub account, and only that account's credentials go on the host.**
  Automated activity at a fleet's volume is exactly what GitHub's abuse detection looks for, and an
  account can be suspended for it. Keep your personal account out of reach: no personal token, no
  personal SSH key, no second `gh` login on the fleet user.
- **Workers use HTTPS for git.** The gate admits pushes through the HTTPS credential helper; an SSH
  remote would be a push path the gate never sees. Pick HTTPS at `gh auth login`.
- **One GitHub account, one budget.** Every fleet acting as the same account must share one set of
  gate budgets. See "Several fleets on one host" below.

## 1. Host tools (once, as a sudoer)

```bash
sudo apt update && sudo apt install -y git curl build-essential python3 python3-venv nodejs npm util-linux-extra
```

`gh` from GitHub's own apt repository (the archive's is too old for the worker):

```bash
sudo mkdir -p -m 755 /etc/apt/keyrings && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
```

```bash
sudo apt update && sudo apt install -y gh
```

Claude Code and Codex, system-wide. A root-owned install cannot update itself, so turn its updater
off and upgrade by re-running the install line:

```bash
sudo npm install -g @anthropic-ai/claude-code @openai/codex
```

```bash
echo 'DISABLE_AUTOUPDATER=1' | sudo tee -a /etc/environment
```

Incus 7 from the Zabbly stable repository (bubble needs Incus 7; the archive ships older). Follow
the Incus install guide for the repository, then:

```bash
sudo apt install -y incus qemu-system && sudo incus admin init --minimal
```

```bash
sudo ufw allow in on incusbr0 && sudo ufw route allow in on incusbr0 && sudo ufw route allow out on incusbr0
```

## 2. A fleet user (once per user, as a sudoer)

```bash
sudo adduser fleetuser
```

```bash
sudo adduser fleetuser incus-admin
```

```bash
sudo loginctl enable-linger fleetuser
```

`incus-admin` is equivalent to root on the host, so give it only to fleet accounts. Lingering keeps
the user's systemd manager, which runs bubble's daemons, alive with nobody logged in.

## 3. The user's own setup (as the fleet user)

A `sudo -iu` shell has no systemd session variables. Add this to `~/.profile`, where it does nothing
under a real login:

```bash
if [ -z "${XDG_RUNTIME_DIR:-}" ] && [ -d "/run/user/$(id -u)" ]; then export XDG_RUNTIME_DIR="/run/user/$(id -u)"; fi
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "${XDG_RUNTIME_DIR:-/nonexistent}/bus" ]; then export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"; fi
```

Check with `systemctl --user status --no-pager | head -3`, which must show the user manager.

Tools under the user's home:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
curl -sS https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
```

bubble, from the branch that carries the fixes the fleet needs (see the README's Requirements), and
a local key it uses to reach its containers:

```bash
uv tool install git+https://github.com/roed-math/bubble.git@fleet
```

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "$USER bubble"
```

```bash
bubble doctor
```

The worker, a roadmap checkout, and this repository:

```bash
git clone -b feat/roadmap-targets-v2 https://github.com/roed-math/TauCetiWorker.git ~/TauCetiWorker-v2
```

```bash
git clone https://github.com/TauCetiProject/TauCetiRoadmap.git ~/TauCetiRoadmap
```

```bash
git clone https://github.com/roed-math/tauceti-fleet.git ~/tauceti-fleet
```

```bash
uv tool install git+https://github.com/kim-em/TauCetiWorker.git
```

```bash
ln -sf ~/tauceti-fleet/bin/tauceti-fleet ~/.local/bin/tauceti-fleet
```

The `uv tool install` of the upstream worker is only there to give the tool an interpreter with
`rich` for the live view; the fleet always runs the checkout in `~/TauCetiWorker-v2`.

Logins, once each, at the keyboard. `gh` as the fleet's GitHub account, over HTTPS, with the
`workflow` scope:

```bash
gh auth login -h github.com -s workflow -p https
```

```bash
codex login
```

Claude signs in once per login chain, after `init`: `tauceti-fleet logins` prints the lines.

If the curator should push the target list it edits, give the clone of this repository a commit
identity and a remote the fleet's account can push to:

```bash
git -C ~/tauceti-fleet config user.name "Fleet Bot" && git -C ~/tauceti-fleet config user.email bot@example.org
```

## 4. Create the fleet

```bash
tauceti-fleet init --name NAME --targets ~/tauceti-fleet/targets/YOUR_LIST.md --github-login YOUR-BOT
```

```bash
tauceti-fleet logins
```

Run each printed `CLAUDE_CONFIG_DIR=… claude auth login` line and sign in with the subscription the
workers spend. Six chains cover every shape; the pool is described in
[operating.md](operating.md#the-claude-login-pool).

Before the fleet, check the pieces offline, then run one supervised round:

```bash
bash ~/TauCetiWorker-v2/tests/run-all
```

```bash
tauceti-fleet up --dry-run
```

```bash
tauceti-fleet round
```

`round` ends with the gate report: every request accounted for, no halts, nothing parked. Read the
round's log and any pull request it opened as you would a colleague's. Then `tauceti-fleet up`.

## Several fleets on one host

Each fleet user needs everything in sections 2 to 4, and three things must differ between fleets.

- **The fleet name.** Worker ids, and the Incus containers named after them, are prefixed with
  `fleet.name`, so two fleets with different names never touch each other's containers.
- **bubble's ports.** Each user's bubble runs an auth proxy (port 7654) and an artifact cache (port
  7655) on the host. A second user must move both, in `~/.bubble/config.toml`:

  ```toml
  [auth_proxy]
  port = 7664

  [artifact_cache]
  port = 7665
  ```

- **The GitHub budget, if both fleets use the same GitHub account.** Each fleet counts its own
  requests, so two fleets as one account spend twice the budget you meant to allow. Either give each
  fleet half (`gate.mutations_per_hour`, `gate.reads_per_hour`), or give each fleet its own account.

Two fleets on one host have not been run side by side yet; watch the first rounds of the second.

Each user should sign in its own Claude login pool. Two fleets can spend the same Claude
subscription, but they share its usage window.

## macOS

The tool runs on macOS too, with `up.sandbox = "host"` (bubble needs Incus). Claude credentials live
in the Keychain there, one item per login chain, and an expiring token is renewed by a short `claude`
run rather than by rewriting a file. New checkouts are APFS clones of an existing built checkout, so
a new worker costs seconds rather than a 12 GB Mathlib unpack. Host mode leaves the gate as a
convention rather than a control: the agent could reach GitHub around it. Prefer a Linux host with
bubble for anything unattended.
