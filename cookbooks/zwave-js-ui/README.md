# Podman Quadlet: Z-Wave JS UI

## Overview

[Z-Wave JS UI](https://zwave-js.github.io/zwave-js-ui/) drives a Z-Wave controller
plugged into the host and exposes it twice: a web control panel on port 8091, and the
**Z-Wave JS Server** websocket on port 3000, which is what the Home Assistant `zwave_js`
integration connects to.

This cookbook:

- Runs Z-Wave JS UI as a non-root container (UID 10035) with the controller as its only
  device.
- Takes the controller under the stable name **`/dev/zwave`**, never a
  `/dev/serial/by-id/...` path: which USB stick is the Z-Wave one is a site value, and it
  belongs in a udev rule of the site, not in this cookbook.
- Keeps the **security keys, the Z-Wave JS Server settings and the log level out of the web
  interface**, in an operator-provided file that the container mounts read-only. Z-Wave JS UI
  marks those settings "managed externally" and refuses to edit them.
- Enables **authentication on the web interface from the first boot**, and disables the MQTT
  gateway: Home Assistant is served by the websocket, not by MQTT.
- Stores the node names, the associations, the NVM backups of the controller and the users
  of the web interface on the virtiofs precious-data mount
  (`/var/lib/virtiofs/data/zwave-js-ui/`), so the host's ZFS snapshots and backups pick
  them up.
- Logs to stdout, so `journalctl` is the single place to look.
- Supports automatic container image updates via Podman auto-update.

The image is `ghcr.io/zwave-js/zwave-js-ui:11`, a multi-architecture manifest (amd64 +
arm64, verified 2026-09-26, version 11.24.1). It is pulled by `zwave-js-ui.image`, which the
container **wants** rather than requires — see the deviations below, and the reason is boot
resilience, not taste.

## What this cookbook does NOT do

- **It does not carry the Z-Wave network.** The network lives in the NVM of the controller:
  its home ID, its node list and its routes are on the stick, not here. Wiping this
  cookbook's store loses the node names and the associations, not the network.
- **It does not back the NVM up on its own.** Z-Wave JS UI can dump the controller NVM into
  its store (`backups/nvm/`) from the web interface or on a schedule set there; nothing in
  this cookbook turns that on.
- **It does not publish anything.** No Traefik dependency, no TLS: the two ports are served
  in clear text on the LAN. A radio head is a LAN appliance; if it must be reachable from
  outside, that is a reverse proxy in front, and a decision of the site.
- **It does not include or exclude devices.** Pairing a device is a physical act plus a
  click in the web interface.

## Prerequisites

- The virtiofs data mount `/var/lib/virtiofs/data` must be present (provided by the
  `fcos-with-virtiofs` template / the `base` cookbook). On a physical machine with no
  hypervisor the mount unit's condition simply does not hold, the unit is skipped, and the
  store is a plain directory of `/var` — which is what a radio head wants anyway, as long as
  `/var` survives a reinstallation.
- **A Z-Wave controller reachable as `/dev/zwave`**, whose device node is readable and
  writable by GID 10000. See below.
- The operator must provide the security keys and the session secret. Until both files
  exist, the container is intentionally **not** started (`ConditionPathExists` guards on
  `/etc/quadlets/zwave-js-ui/external-settings.json` and
  `/etc/quadlets/zwave-js-ui/zwave-js-ui.env`).

### `/dev/zwave`, and why

`AddDevice=/dev/zwave` in the container, `ZWAVE_PORT=/dev/zwave` in its environment. The
site provides that name with a udev rule matching *its* controller, for instance:

```
# /etc/udev/rules.d/99-zwave.rules -- Home Assistant Connect ZWA-2
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", ATTRS{idProduct}=="4001", \
  SYMLINK+="zwave", GROUP="itix-svc", MODE="0660"
```

Two things that rule has to do, and the reason for each:

- **`SYMLINK+="zwave"`** — the container and its unit name one path, so a second radio stick
  on the same host (a Zigbee coordinator, say) cannot be handed to the Z-Wave driver by a
  renumbered `/dev/ttyACM*`. Matching on `ATTRS{serial}` as well is what distinguishes two
  sticks that share a USB identifier, which is common: the CP210x bridge is the same chip in
  half the controllers on the market.
- **`GROUP="itix-svc", MODE="0660"`** — the container runs as 10035:10000 and opens the
  device as that user. The kernel default is `root:dialout 0660`, which it cannot read.
  Setting the group on the device node is preferred over adding the host's `dialout` GID to
  the container, because that GID is a distribution constant that does not match the group
  file inside the image.

Reload the rules and replug the controller (or `udevadm trigger`) after writing the file,
then check that the symlink is there:

```sh
ls -l /dev/zwave
```

## Files the operator must provide

Both are provided by the operator (e.g. an Ansible overlay out of a vault) and are **not**
part of the package. Working development examples ship under `config/examples/`.

| Path                                                  | Mode | Owner         | Purpose                                     |
|-------------------------------------------------------|------|---------------|---------------------------------------------|
| `/etc/quadlets/zwave-js-ui/external-settings.json`    | 0400 | `10035:10000` | Security keys + Z-Wave JS Server settings   |
| `/etc/quadlets/zwave-js-ui/zwave-js-ui.env`           | 0600 | `root:root`   | Session secret, initial admin credentials   |

### `external-settings.json`

Z-Wave JS UI reads it through `ZWAVE_EXTERNAL_SETTINGS`. Only `zwave.*` settings are
accepted there, and every key present becomes read-only in the web interface. The shipped
example is a complete, working file; the keys in it are obviously not secrets.

**The four classic keys are the identity of the network.** A device included in S0 or S2
holds a key derived from them: lose them and the device answers nobody, and the only way
back is to exclude and re-include it by hand. They belong in a vault before the first
inclusion, not after.

Generate six independent 16-byte keys:

```sh
for k in S0_Legacy S2_Unauthenticated S2_Authenticated S2_AccessControl \
         LR_S2_Authenticated LR_S2_AccessControl; do
  printf '%s = %s\n' "$k" "$(openssl rand -hex 16)"
done
```

`securityKeysLongRange` is only used by Z-Wave Long Range devices, and only on an 800-series
controller in an LR region. Providing the two keys costs nothing and spares a migration the
day such a device is included.

Settings worth knowing about:

| Key                              | Effect                                                              |
|----------------------------------|---------------------------------------------------------------------|
| `serverEnabled`, `serverPort`    | The Z-Wave JS Server websocket Home Assistant connects to           |
| `serverServiceDiscoveryDisabled` | `false` announces the server over mDNS, so Home Assistant finds it  |
| `rf.region`                      | **Writes the RF region to the controller.** Absent, the controller keeps its own (0 = Europe, 9 = USA LR, 11 = Europe LR, 255 = default EU) |
| `enableSoftReset`                | Lets the driver restart the controller in software rather than ask an operator to replug it |
| `logLevel`, `logEnabled`         | `info` is readable; `debug` is what an inclusion that fails needs    |

`rf.region` is deliberately **absent from the shipped example**: a controller is sold for a
band, an operator who copies an example must not have its region rewritten by surprise.

### `zwave-js-ui.env`

```
SESSION_SECRET=<openssl rand -hex 32>
DEFAULT_USERNAME=admin
DEFAULT_PASSWORD=<a real password>
```

`SESSION_SECRET` signs the session cookies and the API tokens. Absent, Z-Wave JS UI
generates one and persists it in the store — which works, but then the secret is a piece of
state nobody chose and nobody can restore. `DEFAULT_USERNAME` and `DEFAULT_PASSWORD` create
the administrator account **on the first start only**: once `store/users.json` exists,
changing them does nothing and the password is changed from the web interface.

## Ports

| Port | Bind | Purpose                                                          |
|------|------|------------------------------------------------------------------|
| 8091 | all  | Web control panel (authenticated)                                |
| 3000 | all  | Z-Wave JS Server websocket — `ws://<host>:3000` for Home Assistant |

Both are above 1024, so the non-root container binds them without any capability. Host
networking is what lets the mDNS announcement of the websocket server reach the LAN.

## UID and GID

- User: `zwave-js-ui`, UID **10035**
- Group: `itix-svc`, GID **10000**

## Health check

`wget -q -O /dev/null --header="Accept: text/plain" http://127.0.0.1:8091/health`. That
endpoint returns 200 only when the driver is connected to the controller **and** the MQTT
client is either connected or explicitly disabled — which is why the packaged
`initial-settings.json` carries `mqtt.disabled`: with no `mqtt` section at all, Z-Wave JS UI
builds no MQTT client and `/health` answers 500 forever.

**The `Accept` header is load-bearing.** A request that accepts HTML — which includes a
request with no `Accept` header at all, so `curl` and `wget` as they come — is taken by the
single-page-application fallback: 301 to `/health/`, then the web interface, 200, whatever
the driver is doing. A probe written without it passes forever and reports nothing.

A failing probe marks the container unhealthy and nothing more: no restart action is set.
The driver reconnects on its own, and a controller that has been unplugged is not a problem
a restart loop fixes.

## Deviations from the repository conventions

- **The store is seeded once, by `zwave-js-ui-init.service`.** Z-Wave JS UI owns
  `store/settings.json` — everything the web interface changes is written back to it — so the
  two settings this cookbook decides (`gateway.authEnabled`, `mqtt.disabled`) cannot be
  shipped as configuration. They are copied into the store on first boot only, following the
  same pattern as the `home-assistant` cookbook. Z-Wave JS UI merges that file with its own
  defaults at each start, so seeding a partial file loses nothing.
- **Two settings files, on purpose.** `external-settings.json` in `/etc/quadlets` is
  read-only and authoritative for the keys and the websocket server;
  `store/settings.json` is the application's own, and the operator's copy of it is the seed.
  Z-Wave JS UI merges the two at each start and **persists the result, security keys included,
  into `store/settings.json`** (0600, owned by this cookbook's user). So the store holds a copy
  of the keys whether or not they were seeded there, and a store backup is a secret-bearing
  artifact. What the external file buys is not secrecy: it is that the authoritative copy lives
  outside the application, is restorable from a vault, and cannot be edited from the web
  interface.
- **The container wants the `.image` unit, it does not require it — and it names the image
  reference, not the unit.** This is the deviation, and it is the one this cookbook has already
  paid for.

  A `.image` unit runs `podman image pull`, which contacts the registry even when the image is
  already in local storage. A machine that boots before its network does — a PoE port whose
  switch takes a minute to forward, an uplink that comes back after the machine — fails that
  pull with `Temporary failure in name resolution`. Naming the unit in `Image=` is what makes
  quadlet generate a `Requires=` on it, and **a failed dependency is never retried**:
  `Restart=` only ever applies to a unit that started at least once, so the container stays down
  until a human notices. On the radio head that was fifty-five minutes, with the image sitting
  in local storage the whole time.

  What does *not* fix it, measured rather than assumed: `Restart=on-failure` on the `.image`
  unit. The pull converges, and the container stays `inactive` for good, because its job died
  at the first failure. (`Upholds=` on the pull unit does pick the container up, at the price of
  a container that can no longer be stopped on its own — and it still leaves the container down
  for as long as the registry is unreachable, even though the image is right there.)

  So the pull keeps its own unit — it can be long, and its duration has no business inside the
  container's start time — the container keeps `After=` on it so the pull still runs first when
  it can, and the dependency is `Wants=`. Podman then resolves the image at container start with
  its default `--pull=missing`: the local image starts with no registry involved, and a genuinely
  missing image fails the container, which `Restart=` retries. Auto-update is unaffected, it
  reads the container's label.

  The pull unit also carries `Restart=on-failure` with `StartLimitIntervalSec=0`, so a machine
  that boots without a network still ends up with the image rather than with a stale one, and
  `PartOf=zwave-js-ui.target`, so stopping the target leaves nothing retrying behind.

  **The image reference appears in both files on purpose**, and the two must be changed together.
  A divergence is not silent — the pull unit fetches one tag and the container runs the other,
  which both journals say out loud — but it is a divergence. The alternative, a drop-in that
  resets the generated `Requires=`, has to restate the other requirements of the container, and
  silently drops any that a later edit adds. That trap is worse than this one.
- **Only `external-settings.json` is mounted into the container, never the configuration
  directory.** `:Z` relabels what it mounts to `container_file_t`, recursively and on disk, and
  `init.sh` lives in that directory. Mounting the directory therefore leaves a script systemd
  can no longer execute: `zwave-js-ui-init.service` fails with `203/EXEC` at every boot *after
  the first start of the container*, and the container's `Requires=` on it keeps the container
  down too. A machine that survived its installation stops surviving a reboot, which is the
  worst shape a fault can take. The `mosquitto` cookbook mounts its whole directory and is fine
  because it keeps no script there; this one does.
- **No Traefik and no TLS.** See "What this cookbook does NOT do".

## Clearing the store

The seed is a **first-boot** mechanism: `init.sh` writes `store/settings.json` only when it is
absent, because Z-Wave JS UI owns that file afterwards. Two consequences for an operator who
wipes the store, or who deletes `settings.json` to force the settings of
`external-settings.json` back in — after rotating the security keys, for instance, since
Z-Wave JS UI keeps its own copy of the old ones:

- **Delete the file with the container stopped, then restart the init service explicitly**, in
  this order. `systemctl restart zwave-js-ui.target` is not enough: the init service is
  `RemainAfterExit=yes` and already active, so it does not run again, and Z-Wave JS UI then
  writes a `settings.json` that holds the external settings and **not** the seeded ones.
- The symptom of getting it wrong is a container that is `unhealthy` forever with a driver that
  is perfectly happy: no `mqtt` section means no MQTT client, and `/health` answers 500. And,
  more quietly, `gateway.authEnabled` is gone with it, so the web interface stops asking for a
  password.

```sh
systemctl stop zwave-js-ui.service
rm /var/lib/virtiofs/data/zwave-js-ui/settings.json
systemctl restart zwave-js-ui-init.service     # seeds it again
systemctl start zwave-js-ui.service
```

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Z-Wave JS UI.

```sh
sudo make clean install
```

Without a Z-Wave controller there is nothing to drive, and the container unit is skipped
(`ConditionPathExists=/dev/zwave`). To exercise the rest of the cookbook on a machine that
has none, point `/dev/zwave` at any serial device — the driver fails to talk to it and says
so, which is exactly what it should do:

```sh
ln -sf /dev/ttyS0 /dev/zwave
sudo systemctl start zwave-js-ui.target
```

Note that `AddDevice` names the container path explicitly (`/dev/zwave:/dev/zwave`): a udev
`SYMLINK` is a symbolic link, and a device passed without a container path arrives under its
resolved name (`/dev/ttyACM0`), which is not the name `ZWAVE_PORT` asks for.

With a real controller, the driver comes up and the two ports answer (note the `Accept`
header — see [Health check](#health-check)):

```sh
curl -sS -H 'Accept: text/plain' http://127.0.0.1:8091/health   # -> Ok
ss -ltnp | grep -E ':(8091|3000)'                               # 8091 AND 3000
journalctl -u zwave-js-ui.service | grep -E 'Driver ready|server listening'
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make I_KNOW_WHAT_I_AM_DOING=yes uninstall clean
```
