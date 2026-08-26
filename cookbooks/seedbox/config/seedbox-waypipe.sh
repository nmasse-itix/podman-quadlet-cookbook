#!/bin/bash
#
# waypipe "remote binary" shim for the seedbox browser.
#
# `waypipe ssh` does not run the browser directly. It runs a waypipe *server* on
# the remote side, which connects back to the local waypipe client through an
# SSH-forwarded Unix socket, creates a Wayland socket of its own, and starts the
# program under it. That server has to share a mount namespace with the browser,
# so here it runs *inside* the container -- which is what keeps waypipe and the
# browser off the immutable Fedora CoreOS host entirely.
#
# waypipe calls this script exactly the way it would call the waypipe binary:
#
#     seedbox-waypipe.sh --socket <path> server -- librewolf
#
# so the arguments are handed to the in-container waypipe untouched. Wire it in
# from the client with --remote-bin; see the cookbook README for the full
# client-side command line.
#
# Called with no arguments, it opens an interactive shell in the image instead,
# which is handy to inspect what the nightly rebuild produced.
#
set -Eeuo pipefail

CONFIG_FILE=/etc/quadlets/seedbox/browser.conf

##
## The containers of this cookbook are started by root and drop to the seedbox
## user themselves (--user below), but ssh logs us in as an unprivileged
## account, so re-exec through sudo first.
##
## sudo scrubs the environment, so any BROWSER_* override the caller set is
## carried across explicitly. That does let the caller influence a podman
## command line that runs as root: only grant sudo on this script to accounts
## that already have full root anyway (on Fedora CoreOS, the wheel group).
##
if [ "$(id -u)" -ne 0 ]; then
    overrides=()
    while IFS= read -r name; do
        overrides+=("${name}=${!name}")
    done < <(compgen -v | grep "^BROWSER_" || true)

    exec sudo -n -- /usr/bin/env ${overrides[@]+"${overrides[@]}"} "$0" "$@"
fi

# Defaults live in browser.conf, which uses the ${VAR:-default} form so that the
# environment still wins; these are the fallbacks if the file is missing.
# shellcheck source=/dev/null
[ -r "$CONFIG_FILE" ] && . "$CONFIG_FILE"

BROWSER_IMAGE="${BROWSER_IMAGE:-localhost/librewolf:latest}"
BROWSER_UID="${BROWSER_UID:-10017}"
BROWSER_GID="${BROWSER_GID:-10000}"
BROWSER_PROFILE_DIR="${BROWSER_PROFILE_DIR:-/var/lib/quadlets/seedbox/librewolf}"
BROWSER_DOWNLOAD_DIR="${BROWSER_DOWNLOAD_DIR:-/var/lib/quadlets/seedbox/downloads}"
BROWSER_SHM_SIZE="${BROWSER_SHM_SIZE:-1g}"
BROWSER_WAYPIPE_OPTS="${BROWSER_WAYPIPE_OPTS:---no-gpu}"
BROWSER_PODMAN_OPTS="${BROWSER_PODMAN_OPTS:-}"

##
## Locate the --socket argument waypipe passed us.
##
## Parsing stops at the sub-command: everything after "server" belongs to the
## program being run and may legitimately carry a --socket of its own.
##
socket=""
previous=""
leading_arguments=()
for argument in "$@"; do
    case "$argument" in
        server|client|ssh|bench)
            break
            ;;
        --socket=*)
            socket="${argument#--socket=}"
            ;;
    esac
    case "$previous" in
        -s|--socket)
            socket="$argument"
            ;;
    esac
    leading_arguments+=("$argument")
    previous="$argument"
done

##
## Work out which of our own waypipe options still need to be added.
##
## "waypipe ssh" forwards several of its options to the server side (--no-gpu
## and --threads at least), and the argument parser rejects a repeated flag
## outright:
##
##   error: the argument '--no-gpu' cannot be used multiple times
##
## so anything already on the command line has to be left alone.
##
option_matches() {
    case "$1:$2" in
        "--no-gpu:-n"|"-n:--no-gpu") return 0 ;;
    esac
    [ "$1" = "$2" ]
}

waypipe_options=()
for option in ${BROWSER_WAYPIPE_OPTS}; do
    already_given=false
    for argument in ${leading_arguments[@]+"${leading_arguments[@]}"}; do
        if option_matches "$option" "$argument"; then
            already_given=true
            break
        fi
    done
    "$already_given" || waypipe_options+=("$option")
done

socket_options=()
if [ -n "$socket" ]; then
    if [ ! -S "$socket" ]; then
        echo "$0: '$socket' is not a socket: is the SSH remote forwarding set up?" >&2
        exit 1
    fi

    # sshd creates the forwarded socket owned by the login user with mode 0600
    # (StreamLocalBindMask 0177), so the unprivileged browser user can neither
    # connect() to it nor, on shutdown, remove it:
    #
    #   Error: "src/main.rs:1505: Failed to unlink socket: EACCES: Permission denied"
    #
    # Handing the socket over outright covers both: it keeps mode 0600, so no
    # other account can hijack the Wayland connection, and the sticky bit on the
    # parent directory then lets its new owner -- and only its new owner --
    # unlink it. An ACL would grant the connect but not the unlink, since
    # deleting a file is governed by the directory and the file's ownership.
    chown "${BROWSER_UID}:${BROWSER_GID}" "$socket"

    # The *directory* is mounted, not the socket alone. Bind-mounting the
    # socket by itself makes podman synthesize a parent directory inside the
    # container -- root:root, mode 0755 -- and the host's permissions on the
    # real directory become irrelevant: the browser's uid cannot write to that
    # synthetic parent, so waypipe cannot remove its own socket on shutdown:
    #
    #   Error: "src/main.rs:1505: Failed to unlink socket: EACCES: Permission denied"
    #
    # Mounting the directory gives the container the real one, sticky bit and
    # all. Concurrent sessions become visible to each other by name, but their
    # sockets stay 0600 and owned by their own uid, so they can be neither
    # connected to nor deleted.
    socket_directory=$(dirname "$socket")
    socket_options+=(--volume "${socket_directory}:${socket_directory}")
fi

##
## Run the browser.
##
## --userns=host is not decorative: it is what makes the in-container uid the
## same as the host uid, without which the ACL set on the socket above would
## not apply to the browser process.
##
podman_options=(
    --rm
    --interactive
    # Without an init, waypipe is PID 1 and inherits every orphaned browser
    # process, logging each one it reaps as an error:
    #   ERR waypipe-server(1) main.rs:260] Received SIGCHLD for unexpected child
    --init
    --user "${BROWSER_UID}:${BROWSER_GID}"
    --userns=host
    --cap-drop=ALL
    # Firefox's own content sandbox chroots itself, and cannot get the
    # capability back from an empty bounding set: without this, every content
    # process dies with "Sandbox: chroot: EPERM" followed by SIGSEGV. This is
    # the only capability it needs -- SYS_ADMIN is not required.
    #
    # podman also puts it in the ambient set, which breaks the *other* sandbox
    # in this image (bubblewrap, used by the SVG image loader). The image's
    # entrypoint drops the ambient set again; see the Containerfile.
    --cap-add=SYS_CHROOT
    --security-opt no-new-privileges
    # SELinux checks connect() on a Unix socket with "connectto" against the
    # *listening process*, not against the socket file, so relabelling the
    # socket does not help:
    #
    #   avc: denied { connectto } comm="waypipe"
    #        path="/run/seedbox/waypipe/....sock"
    #        scontext=...:container_t:s0:c266,c919
    #        tcontext=...:unconfined_t:s0-s0:c0.c1023
    #        tclass=unix_stream_socket
    #
    # The listener is the SSH session (an unconfined user), and no label this
    # container could carry is allowed to connect to it. The alternative to
    # disabling the label here is a system-wide policy module granting
    # "allow container_t unconfined_t:unix_stream_socket connectto", which
    # opens that hole for *every* container on the host rather than this one.
    # See the README for the trade-off. The container still runs unprivileged
    # (--user, --cap-drop=ALL, no-new-privileges) and is thrown away on exit.
    --security-opt label=disable
    --shm-size "${BROWSER_SHM_SIZE}"
    --env "XDG_RUNTIME_DIR=/run/user/${BROWSER_UID}"
    --env "HOME=/home/browser"
    --env "MOZ_ENABLE_WAYLAND=1"
    --volume "${BROWSER_PROFILE_DIR}:/home/browser:z"
    --volume "${BROWSER_DOWNLOAD_DIR}:/downloads:z"
)

if [ "$#" -eq 0 ]; then
    # No arguments: interactive shell in the image, for troubleshooting.
    exec podman run --tty "${podman_options[@]}" ${BROWSER_PODMAN_OPTS} "${BROWSER_IMAGE}" /bin/bash
fi

status=0
# shellcheck disable=SC2086 # BROWSER_PODMAN_OPTS and BROWSER_WAYPIPE_OPTS are word-split on purpose
podman run "${podman_options[@]}" "${socket_options[@]}" ${BROWSER_PODMAN_OPTS} \
    "${BROWSER_IMAGE}" \
    waypipe ${waypipe_options[@]+"${waypipe_options[@]}"} "$@" || status=$?

##
## waypipe unlinks the forwarded socket itself on a clean shutdown (see the
## chown above), and sshd does not (StreamLocalBindUnlink defaults to no). This
## is the safety net for the cases where waypipe never gets that far -- a crash,
## a killed session -- so that the directory does not fill with dead sockets.
##
if [ -n "$socket" ]; then
    rm -f "$socket"
fi

exit "$status"
