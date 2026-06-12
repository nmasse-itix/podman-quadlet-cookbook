# Podman Quadlet Developer's Guide

This guide provides instructions for developers and system engineers who packages and deploy software using Podman Quadlets.
It covers the development workflow, testing, and best practices for maintaining Quadlet packages.

## Architecture guidelines

The cookbooks in this repository follow a set of architectural guidelines to ensure security, maintainability, and composability:

- **Development takes place in a dedicated Fedora virtual machine.**
  The reason for this is that the Makefiles are run as root in order to be able to use rootful Podman and systemd features, and thus we want to isolate the development environment from the host system to avoid any potential issues.

- **Cookbooks target immutable operating systems, with a strong focus on Fedora CoreOS.**
  In Fedora CoreOS, the filesystem is mostly read-only and all the applications run in containers.
  The operating system updates itself automatically, which is possible because there are no custom packages installed on the system, all the applications are running in containers.
  The containers can be updated independently from the operating system, which allows for a more flexible and modular system.
  Last but not least, Fedora CoreOS has a strong focus on security, with SELinux enabled by default and a minimal attack surface.

  While it is possible to install Fedora CoreOS on bare metal, the cookbooks in this repository expect to be run on a virtual machine.

  How to deploy the cookbooks on a Fedora CoreOS system if it is immutable? Well, just re-create the VM with its new ignition file produced by the `make package` command! To ensure that the data is preserved during the re-creation of the VM, `/var` is mounted as a separate volume that you have to keep between re-creations of the VM.

  Additionally, the precious data of the cookbooks are stored in a virtiofs mount (`/var/lib/virtiofs/data/$(PROJECT_NAME)`) that is shared between the host and the VM, so that the data is preserved even if the VM is destroyed and re-created.
  Those precious data can be read from the host which is an advantage if the host filesystem is ZFS.
  In case of data corruption, you know which file of the virtiofs mount is corrupted and you can restore it individually from a backup, rather than restoring the whole VM.

- **Cookbooks use four types of data: configuration, transient data, persistent data, and precious data.**
  Configuration is stored in `/etc/quadlets/$(PROJECT_NAME)`, persistent data is stored in `/var/lib/quadlets/$(PROJECT_NAME)` and precious data is stored in `/var/lib/virtiofs/data/$(PROJECT_NAME)`.
  
  The rules are :

  - Treat the configuration under `/etc/quadlets` as read-only data, it should not be modified by the cookbooks, it should only be provided by the user.

  - All the data created by the cookbooks MUST be stored under either `/var/lib/quadlets` or `/var/lib/virtiofs`. NEVER store data outside of those directories.

  - If the data is not precious, it MUST be stored under `/var/lib/quadlets`. This is the case for data that can be re-created or re-downloaded without any issue, such as caches, temporary files, etc.

  - If the data is precious, it MUST be stored under `/var/lib/virtiofs`. This is the case for data that cannot be re-created or re-downloaded without any issue, such as databases, user files, etc.

  - Transient data (lost at each reboot) can be stored in `/run/quadlets/$(PROJECT_NAME)`.

- **Cookbooks are designed to be composable.**
  If you need to deploy a software that needs PostgreSQL as database and a reverse proxy in front, just add the `postgresql` and `traefik` cookbooks as dependencies!
  Want to serve files with Samba? Just add the `samba` cookbook as a dependency!

  Composability goes beyond just declaring dependencies in the Makefile, it also means that you can inject configuration into your dependencies using the hook mechanism.
  
  For instance, if your cookbook depends on `postgresql` and needs to create a database and a user for its application, you can create a file named `other/postgresql/mycookbook.sql` with the SQL commands to create the database and the user, and it will be automatically executed by the `postgresql` cookbook when it is installed.

- **Each Systemd unit or Podman Quadlet perform only one task.**
  Especially, the one-off initialization procedures, upgrade processes, etc. are run as separate units.
  For instance, if your application needs to run a database migration before starting the main service, you can create a `myapp-migration.container` unit that runs the migration command and is executed before the `myapp.container` unit that runs the main service.
  That way, if the service it taking too long to start, you know that the issue is either in the migration or in the main service, and you can check the logs of each unit separately to diagnose the issue.
  It also means that you can adjust the health checks, restart policies, timeouts, etc. of each unit independently, which is not possible if you have a single unit that runs both the migration and the main service.

- **Assume SELinux is enabled by default.**
  As this repository targets Fedora CoreOS, which has SELinux enabled by default, the cookbooks are designed to work with SELinux in enforcing mode.
  
  - This means that volumes mounts have the ":Z" or ":z" options to set the appropriate SELinux labels on the host directories. `:Z` is used for private volumes, while `:z` is used for shared volumes.
  - Mounted filesystems have the default SELinux context `system_u:object_r:container_file_t:s0` to be accessible from the containers.
  - It also means that some files of the host are forbidden to be mounted in the containers (e.g. `/etc/shadow`).

- **Avoid containers processes running as root.**
  Whenever possible, run your containers as a non-root user to minimize the impact of a potential security breach. To do so, you can use the "User Namespaces" and "UID/GID mapping" features of Podman, or simply use the `--user` option to run the container as a specific user.
  There are some cases where it is not possible to avoid running the container as root.
  Some applications such as `samba` or `vsftpd` rely heavily on root privileges to start and then drop their privileges as soon as possible.
  In those cases, the reason is documented in the cookbook's README file.
  And if your application just need to bind to a privileged port, you can use the `CAP_NET_BIND_SERVICE` capability to allow it to bind to the privileged port without running as root!

- **Each cookbook runs as a dedicated Linux user.**
  This is a good practice to isolate the cookbooks from each other and from the host system, and to minimize the impact of a potential security breach.
  
  You can create a dedicated user for your cookbook and run the container with the `--user` option to run it as that user.
  If you are using User Namespaces and UID/GID mapping, you can map the user of your cookbook to a non-root user on the host system, which adds an extra layer of security.
  The `PROJECT_UID` and `PROJECT_GID` variables in the Makefile will take care of the file permissions for you.
  
  Also, to avoid conflicts between cookbooks, it is recommended to use a UID/GID above 10000 for the users of the cookbooks, as the UIDs/GIDs below 10000 are reserved for system users and groups.

  - Any UID > 10000 that is not already used in this repository is fair game for your cookbook, and you can document the UID/GID you chose in the README file of your cookbook to avoid conflicts with other cookbooks.
  - UID 10000 can be used freely as an equivalent of the `nobody` user for applications that do not need a dedicated user.
  - GID 10000 is the main group for all the users of the cookbooks, so that you can use it to share files between cookbooks if needed.

## Development environment setup

> [!NOTE]
> In this guide, you will be setting up two different VMs:
> - A Fedora Server VM for development, where you will edit the files and run the Makefiles to build and deploy the cookbooks. This VM is created with `scripts/create-dev-vm.sh`.
> - Several Fedora CoreOS VMs for testing the cookbooks in a clean environment. These VMs are created with `make fcos-vm console` or `pytest` commands.

1. **Set up your development Virtual Machine**:
   Create a Fedora Virtual Machine (VM) using your preferred virtualization tool (e.g., VirtualBox, KVM, or VMWare).
   A helper script is provided for convenience (`scripts/create-dev-vm.sh`), which automates the VM creation process.
   If you prefer to create the VM by yourself, a cloud-init script (`scripts/cloud-init.dev.yaml`) is maintained with the necessary configuration for the development environment.

   You can create a Fedora Virtual Machine with the following command:

   ```sh
   sudo ./scripts/create-dev-vm.sh
   ```

   Then, retrieve the IP address of your VM with the following command:

   ```sh
   sudo virsh domifaddr quadlets
   ```

2. **Configure VScode Remote Explorer**:
   Use the Remote Explorer extension in Visual Studio Code to connect to your development VM via SSH.
   This allows you to edit files directly on the VM and run commands in the integrated terminal.

   First, on your host, add the following configuration to your `~/.ssh/config` file:

   ```
   Host quadlets
         HostName <IP_ADDRESS_OF_YOUR_VM>
         User root
         ForwardAgent yes
         StrictHostKeyChecking=no
         UserKnownHostsFile=/dev/null
   ```

   Then, install the [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh&ssr=false#overview) extension for Visual Studio Code, and connect to your VM using the "Remote - SSH: Connect to Host..." command.

   If needed, you can also connect to your VM using `ssh root@quadlets` from your terminal or from the libvirt console using `sudo virsh console quadlets` with the login `root` and the password `root`.

3. **Clone the Repository**:
   Clone the [repository](https://github.com/nmasse-itix/podman-quadlet-cookbook.git) onto your development VM.

4. **Install an off-the-shelf Cookbook**:
   Deploy the `miniflux` Cookbook from the `cookbooks/` directory to familiarize yourself with the structure and deployment process.

   ```sh
   cd cookbooks/miniflux
   make install
   curl --resolve miniflux:80:127.0.0.1 http://miniflux/
   make clean uninstall
   ```

  If you want to access the miniflux web interface, you can add an entry in your `/etc/hosts` file to resolve `miniflux` to `127.0.0.1`.

  And then connect to the development VM with the `ssh -L 80:localhost:80` option to forward the port 80 of the VM to your local machine.

## Development Workflow

1. **Create a new directory for your Cookbook**: Inside the `cookbooks/` directory, create a new folder for your Cookbook (e.g., `myapp`).
2. **Write your Cookbook**: The strictly required files for a Cookbook are:

   - `Makefile`: A Makefile to automate the installation, testing, and cleanup of your Cookbook.
   - `myapp.container`: The Podman Quadlet definition file that describes how to run your application.

   The minimal Makefile looks like this:

   ```Makefile
   # Include common Makefile
   include ../../scripts/common.mk
   ```

   The `myapp.container` file should follow the Podman Quadlet specification (`man 5 podman-systemd.unit`), defining the necessary parameters for your application.

> [!TIP]
> If you already have a Docker Compose or Docker run command for your application, you can use the `podlet` tool to convert it into a Podman Quadlet as a starting point for your `myapp.container` file.

   Please read the [Best Practices guide](BEST_PRACTICES.md) for more guidelines on how to write your Cookbook.

3. **Test your Cookbook**: Use the `make install` command to deploy your Cookbook and verify that it works as expected. You can access your application using the appropriate URL or port.
4. **Iterating**: Make changes to your Cookbook files as needed, and use `make I_KNOW_WHAT_I_AM_DOING=yes uninstall clean install` to iterate quickly on a fresh deployment.
   If you want to keep the data between iterations, simply omit the `clean` target.
5. **Troubleshooting**: If you encounter issues, check the logs of your Cookbook using `make tail-logs` to diagnose and fix problems (it tails the journalctl logs for all the units of your Cookbook and also its dependencies).

Iterate on steps 2-5 until your Cookbook is working as expected.

6. **Clean up**: Once you are satisfied with your Cookbook, use `make I_KNOW_WHAT_I_AM_DOING=yes uninstall clean` to remove it from your system.

7. **Extended testing**: You can add a `test` target to your Makefile to automate testing of your Cookbook.
  For instance, the `postgresql` and `nextcloud` Cookbooks have a `test` target that go through an specific upgrade path to ensure that the data is preserved during major version upgrades of the packaged application.

Then, you can test it on a clean VM to ensure that it works in a fresh environment.

8. **Create the `local.bu` butane file**: This file contains the initial username & password for the Fedora CoreOS VM used for testing.
   Run `cp local.bu.template local.bu` and edit the `local.bu` file to set the desired username and password for the VM.
9. **Run the Cookbook in a clean environment**: Run `make fcos-vm console` to create a new VM with Fedora CoreOS and test your Cookbook in a clean environment.
   This step is crucial to ensure that your Cookbook works correctly without any dependencies on your development environment.
10. **Clean-up the VM**: After testing, you can clean up the VM using `make remove-vm` to free up resources.

At this point, you have enough confidence in your Cookbook to know that it works in a clean environment and is ready for deployment.

## Troubleshooting

The `make debug` command prints out the list of all the Makefile variables and their corresponding values, which can be useful for troubleshooting issues with your Cookbook's Makefile.

`make tail-logs` is a very useful command to troubleshoot issues with your Cookbook, as it tails the logs of all the systemd units of your Cookbook and its dependencies.

> [!TIP]
> Run `make tail-logs` in a separate terminal while you are installing or testing your Cookbook to have real-time logs of your application and quickly identify any issues that may arise during the installation or execution of your Cookbook.

If you are lost, `make help` will print out the list of available Makefile targets and their descriptions, along with the main Makefile variables and their values.

`make dryrun` process your Quadlet files (only the Quadlet files, not the systemd unit files) with `podman-system-generator -dryrun` to validate them and print out the resulting systemd units without actually installing them.

During the installation of your Cookbook, the systemd unit files are validated with `systemd-analyze verify` after being installed, so if there is an issue with your systemd unit files, you will see an error message in the output of the `make install` command.

## End-to-End Testing (optional)

End-to-end testing is an essential part of the development process to ensure that your Cookbook works correctly and remains functional as you make changes.
You can use the `make pytest` command to run automated tests for your Cookbook.

Of course, you need to write tests for your Cookbook first. You can use the `tests/` directory to store your test scripts.

The `tests/` directory usually contains Python scripts that use the `pytest` framework to define test cases for your Cookbook.

- `conftest.py`: This file contains fixtures that set up the testing environment.
  Have a look at the `conftest.py` file at the top level of the repository for built-in fixtures that you can use in your tests.
- `helpers.py`: Create a subclass of `test_quadlet.TestQuadlet` in this file to have basic tests for your Cookbook, such as checking if the container is running and if the expected ports are open.
- `test_01_myapp.py`: This file contains the actual test cases for your Cookbook.

You can have a look at the tests for the `traefik` and `postgresql` Cookbooks for examples of how to write tests for your Cookbook.

Have a look at the [Testing Guide](TESTING_GUIDE.md) file for more details on how to write and run tests for your Cookbook.

## Documentation

The `README.md` file in your Cookbook directory should contain documentation for your Cookbook, including:

- A short description of the packaged application.
- Pre-requisites: dependencies, virtiofs mounts, memory, CPU & disk requirements, etc.
- Files to be provided by the user to run the Cookbook (e.g., configuration files, data directories, etc.).
- TCP & UDP ports used by the application.
- UID and GID used by the application.

## Convention over Configuration

This repository follows the principle of "convention over configuration" to simplify the development process and reduce the amount of boilerplate code needed for each Cookbook.

- **Podman Quadlet files** (*.container, *.image, *.network, *.volume, *.pod, *.build, *.image) are expected to be in the same directory as the Makefile of the Cookbook.
  A dry-run is applied before installation to all quadlet files to ensure that they are valid (`podman-system-generator -dryrun` is used for validation).

- **Systemd units** (*.service, *.timer, *.mount, *.target) are expected to be in the same directory as the Makefile of the Cookbook.
  A validation is applied after installation of all systemd unit files to ensure that they are valid (`systemd-analyze verify` is used for validation).

- **Dependencies**: If your Cookbook depends on other Cookbooks, you can specify them in the `DEPENDENCIES` variable in your Makefile.
  The build system will automatically handle the installation and uninstallation of dependencies when you run `make install` or `make uninstall`.

- **Configuration files**: If your Cookbook requires configuration files, they are expected to be in a `config/` directory inside the Cookbook directory.
  
  Those configuration files will land to `/etc/quadlets/<cookbook-name>/` on the target system.
  
  You can use sub-directories inside the `config/` directory to organize your configuration files if needed.
  For instance, `config/foo/bar.conf` will land to `/etc/quadlets/<cookbook-name>/foo/bar.conf` on the target system.

- **Skaffolding with systemd-tmpfiles**: If your Cookbook needs to create files or directories on the target system, you can use systemd's `tmpfiles.d` mechanism.
  You can create a `tmpfiles.d/` directory inside your Cookbook directory and place your systemd-tmpfiles configuration files there.
  Those files will be installed to `/etc/tmpfiles.d/` on the target system.

  If the file `tmpfiles.d/<cookbook-name>.conf` exists, it has a special meaning: it will be applied / purged during the `make install` / `make uninstall` of the Cookbook.

- **Sysctl configuration**: If your Cookbook needs to set **system wide** sysctl parameters, you can create a `sysctl.d/` directory inside your Cookbook directory and place your sysctl configuration files there.
  Those files will be installed to `/etc/sysctl.d/` on the target system.

  If the file `sysctl.d/<cookbook-name>.conf` exists, it has a special meaning: it will be applied to the current system during the `make install` of the Cookbook.

- **Shell profiles**: If your Cookbook needs to set environment variables for the user, you can create a `profile.d/` directory inside your Cookbook directory and place your shell profile configuration files there.
  Those files will be installed to `/etc/profile.d/` on the target system.

- **Systemd and Cookbook drop-ins**: If your project needs to override or extend the configuration of systemd units or Cookbook files of other projects, you can create a `dropins/` directory inside your Cookbook directory and place your drop-in configuration files there.

  The expected structure for drop-ins is as follows:

  ```
  dropins/
    <unit-name>.d/
      <drop-in-file>.conf
  ```

  For instance, if you want to override the `ExecStart` of a systemd unit named `myapp.service`, you can create a file named `dropins/myapp.service.d/override.conf` with the following content:

  ```ini
  [Service]
  ExecStart=
  ExecStart=/usr/bin/myapp --new-argument
  ```

  The same example applies for Quadlet files, if you want to override the `Image` of a Quadlet file named `myapp.container`, you can create a file named `dropins/myapp.container.d/override.conf` with the following content:

  ```ini
  [Container]
  Image=myapp:latest
  ```

- **Examples**: If you want to provide example files for your Cookbook, they are expected to be in an `examples/` directory under the `config`, `tmpfiles.d`, `sysctl.d`, `profile.d` or `dropins` directories inside the Cookbook directory.

  They will land to at the same path as their parent directory.
  For instance `config/examples/foo/bar.conf` will land to `/etc/quadlets/<cookbook-name>/foo/bar.conf` on the target system too.

  Examples are used during the development and testing of your Cookbook to provide your application with a working configuration (not necessarily secure, nor optimized).
  They are not part of the final package, and thus is not deployed to production systems.

## Dependencies and hooks

Dependencies and hooks are useful to compose Cookbooks to build a modular system, just like Lego bricks.
For instance, you can have a `nextcloud` Cookbook that depends on a `postgresql` Cookbook, and the `nextcloud` Cookbook will automatically start the `postgresql` service before starting the `nextcloud` service.
In fact, the `nextcloud` Cookbook in this repository has more dependencies than just `postgresql`, it also depends on the `redis` and `traefik` Cookbooks.

A Cookbook can declare dependencies on other Cookbooks using the `DEPENDENCIES` variable in the Makefile.
When you run `make install`, the build system will automatically install the dependencies before installing your Cookbook.
When you run `make uninstall`, the build system will automatically uninstall your Cookbook before uninstalling the dependencies.

The hook is an adjacent concept to dependencies, it allows you to inject custom configuration to your dependencies' configuration using a pluggable hook mechanism.

For instance, the `nextcloud` Cookbook depends on `postgresql`. It has a file named `other/postgresql/nextcloud.sql` with the following content:

```sql
-- Initialization script for Nextcloud database and user
CREATE USER nextcloud WITH PASSWORD 'nextcloud';
CREATE DATABASE nextcloud OWNER nextcloud;
GRANT ALL PRIVILEGES ON DATABASE nextcloud TO nextcloud;
ALTER ROLE nextcloud SET client_encoding TO 'utf8';
```

This allows PostgreSQL to automatically execute this SQL script when the `postgresql` Cookbook is installed, which creates the necessary database and user for Nextcloud to work.

Unless otherwise specified, the files deployed using the hook mechanism are considered as examples and thus are not part of the final package, and thus is not deployed to production systems.

## The Makefile

The Makefile is the entry point for building, installing, testing, and cleaning your Cookbook.

The minimal Makefile includes the common Makefile from `scripts/common.mk`, which provides a set of predefined targets and variables to simplify the development process.

```Makefile
# Include common Makefile
include ../../scripts/common.mk
```

You can customize your Makefile by adding your own targets and variables as needed.

> [!WARNING]
> Unless otherwise specified, the **variables** have to be declared **BEFORE** including the common Makefile.
> Your **targets** have to be declared **AFTER** including the common Makefile.

### Dependencies

If your Cookbook has dependencies, you can declare them in the `DEPENDENCIES` variable:

```Makefile
# Declare dependencies
DEPENDENCIES = postgresql redis traefik

# Include common Makefile
include ../../scripts/common.mk
```

### UID and GID

To configure the UID and GID of the user that will run the containers of your Cookbook, you can set the `PROJECT_UID` and `PROJECT_GID` variables:

```Makefile
# Configure the UID and GID of the user that will run the containers
PROJECT_UID = 10001
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk
```

To find the already used UIDs in this repository, run this command at the root of the repository:

```sh
sed 's/^PROJECT_UID *= *//; t; d' $(find cookbooks/ -name Makefile) | sort -u
```

By default, the configuration files under `/etc/quadlets/<cookbook_name>/` will have the correct ownership (`PROJECT_UID:PROJECT_GID`) to be readable by the containers of your Cookbook.
The `/var/lib/quadlets/<cookbook_name>/` directory will have the correct permissions to be writable by the containers of your Cookbook too.

The `.env` files under `/etc/quadlets/<cookbook_name>/` are meant to be read by Systemd as environment files, and thus they are owned by root and have the permissions `0600` to be readable only by Systemd.

### Systemd units to enable and start

By default, the `make install` command will enable and start all the Systemd units of type `target`.
If you want to enable and start units of other types (e.g. `service`, `timer`, etc.), you can set the `SYSTEMD_MAIN_UNIT_NAMES` variable in your Makefile:

```Makefile
SYSTEMD_MAIN_UNIT_NAMES += vmagent.service
```

> [!NOTE]
> If you want a disctinction between the units to enable and the ones to start, you can use the `SYSTEMD_ENABLE_UNITS` and `SYSTEMD_START_UNITS` variables instead of `SYSTEMD_MAIN_UNIT_NAMES`.

### Prerequisites

If your Cookbook has development prerequisites, declare them in the `prerequisites` target of your Makefile:

```Makefile
pre-requisites::
	@set -Eeuo pipefail; \
	for tool in tool1 tool2 tool3; do \
		if ! which $$tool &>/dev/null ; then \
			echo "$$tool is not installed. Please install it first." >&2; \
			exit 1; \
		fi ; \
	done
```

The pre-requisites target is run automatically, even when a dependent cookbook calls you.

### Fetching external files

If your Cookbook needs to fetch external files during the installation process, you can adjust your Makefile like this:

```Makefile
TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/nextcloud/collabora-seccomp-profile.json
$(TARGET_CHROOT)/etc/quadlets/nextcloud/collabora-seccomp-profile.json: $(TARGET_CHROOT)/etc/quadlets/nextcloud
	curl -sSfL -o $@ https://raw.githubusercontent.com/CollaboraOnline/online/refs/heads/main/docker/cool-seccomp-profile.json
```

### Installing files outside of the reserved directories

If your Cookbook needs to install files outside of the reserved directories (`/etc/quadlets` and `/var/lib/quadlets`), you can adjust your Makefile like this:

```Makefile
# Additional nftables directories and files
TARGET_FILES += $(TARGET_CHROOT)/etc/sysconfig/nftables.conf
$(TARGET_CHROOT)/etc/sysconfig/nftables.conf: other/nftables.conf
	install -D -o root -g root -m 755 $< $@
```

### Providing a hook for dependant cookbooks

For dependent cookbooks to be able to inject configuration into your cookbook, you can create a file named `hook.mk` in your cookbook directory with the following content:

```Makefile
# Short comment about the purpose of this hook
# For instance: "this hook allows dependent cookbooks to inject SQL scripts and shell scripts to initialize
# the PostgreSQL database for their own needs".

# Define the target files that will be deployed to the target system when the hook is used by a dependent cookbook.
TARGET_POSTGRESQL_FILES = $(patsubst other/postgresql/%, $(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%, $(wildcard other/postgresql/*))

# Inject those files into the example file set (you can also use the "TARGET_FILES" variable instead if you
# want those files to be part of the final package, but usually they are just examples for the dependent
# cookbooks to use and thus they are not part of the final package)
TARGET_EXAMPLE_FILES += $(TARGET_POSTGRESQL_FILES)

# Define the installation rules for the target files
# Here .sql files and .sh files are deployed with different permissions, but you can adjust the rules as 
# needed for your use case. You can also create sub-directories in your hook directory (other/postgresql
# in this example) if you have different kinds of hooks that need to be deployed to different locations 
# on the target system.
$(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%.sql: other/postgresql/%.sql
	install -m 0600 -o 10004 -g 10000 $< $@
$(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%.sh: other/postgresql/%.sh
	install -m 0700 -o 10004 -g 10000 $< $@
```

Note that the `hook.mk` file is a Makefile snippet that will be included in the Makefile **of the dependent cookbook**, so you **CANNOT** use **your Makefile's variables** here.

### Creating empty directories

If your Cookbook needs to create empty directories (for instance, to be filled by dependent cookbooks using the hook mechanism), adjust your Makefile like this:

```Makefile
TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/<cookbook_name>/my-hooks.d

# Include common Makefile
include ../../scripts/common.mk

$(TARGET_CHROOT)/etc/quadlets/<cookbook_name>/my-hooks.d:
	install -d -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) -D $@
```
