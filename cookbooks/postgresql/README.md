# Podman Quadlet: PostgreSQL

## Overview

PostgreSQL is started as a Podman Quadlet and before that, the database is initialized:

- either from a previous backup,
- or from scratch using SQL statements or scripts.

The upgrade process between major versions is handled by a one-off job before the database server startup.

Finally, a Podman Quadlet is provided to perform a backup of the database, including a simple retention policy.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start PostgreSQL.

```sh
sudo make clean install
```

You should see the **postgresql-set-major.service** starting up to set the symlink pointing to the PGDATA directory of the desired major version.
Then, the **postgresql-init.service** should start up and initialize the database from scratch.
Finally, the **postgresql-server.service** is started.

Restart the **postgresql.target** unit.

```sh
sudo systemctl restart postgresql.target
```

You should see in the logs that the **postgresql-init.service** is skipped (because the database is already initialized) and the **postgresql-server.service** unit is started.

Increment the PostgreSQL major version number.

```sh
awk -i inplace -F= '/PG_MAJOR=/ { $2=$2+1; print $1"="$2; next } 1' /etc/quadlets/postgresql/config.env
```

Restart the **postgresql.target** unit.

```sh
sudo systemctl restart postgresql.target
```

In the logs, you should see that the **postgresql-upgrade.service** converts the database files to the new major version.

Make backups of the database.

```sh
for i in $(seq 1 10); do
    sudo systemctl start postgresql-backup.service
    sleep 1
done
```

In the logs, you should see ten runs of the **postgresql-backup.service** unit.
And in the three last runs, the retention policy should be kicked in to clean up old backup files.

Now, stop the database server.

```sh
sudo systemctl stop postgresql.target
```

Remove all the PostgreSQL files (except the backups).

```sh
sudo find /var/lib/quadlets/postgresql/ -maxdepth 1 -mindepth 1 \! -name backup -exec rm -rf '{}' \;
```

Confirm there is no more data in `/var/lib/quadlets/postgresql`.

```
$ sudo ls -l /var/lib/quadlets/postgresql
total 0
drwx------. 1 avahi avahi 38  1 déc.  21:04 backup
```

Start the PostgreSQL database server.

```sh
sudo systemctl start postgresql.target
```

In the logs, you should see the **postgresql-init.service** unit restoring the database from the last backup.

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
