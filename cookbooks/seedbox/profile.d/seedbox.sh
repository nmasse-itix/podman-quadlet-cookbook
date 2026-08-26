##
## Interactive helpers for the seedbox browser container.
##
## Note that this file is NOT what starts the browser for a `waypipe ssh`
## session: `ssh <host> <command>` runs a non-interactive, non-login shell,
## which does not source /etc/profile.d. The entry point in that case is
## /etc/quadlets/seedbox/seedbox-waypipe.sh, passed to waypipe with
## --remote-bin. These helpers are for when you are logged in and want to
## inspect or drive the same container by hand.
##

if [ -r /etc/quadlets/seedbox/browser.conf ]; then
    . /etc/quadlets/seedbox/browser.conf
    export BROWSER_IMAGE BROWSER_PROFILE_DIR BROWSER_DOWNLOAD_DIR
fi

# Run the browser container. Takes the same arguments as the waypipe binary, so
# it can stand in for a manual `waypipe --socket ... server -- librewolf`; with
# no arguments, it opens a shell in the image.
seedbox-browser() {
    sudo -n /etc/quadlets/seedbox/seedbox-waypipe.sh "$@"
}

# Rebuild the image now instead of waiting for tonight's timer.
seedbox-browser-rebuild() {
    sudo -n systemctl start librewolf-build.service &&
        sudo -n journalctl -u librewolf-build.service -n 20 --no-pager
}

# Print the command line to run on the *client* to get a browser on screen.
seedbox-browser-command() {
    printf 'waypipe --remote-bin /etc/quadlets/seedbox/seedbox-waypipe.sh \\\n'
    printf '        --remote-socket /run/seedbox/waypipe/wp \\\n'
    printf '        --no-gpu ssh %s@%s librewolf\n' "${USER:-nicolas}" "$(hostname -f 2>/dev/null || hostname)"
}
