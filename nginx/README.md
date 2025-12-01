# Podman Quadlet: Nginx

## Overview

Nginx is started as a Podman Quadlet and before that, the content to serve is initialized (`git clone`) or updated (`git pull`) from a GIT repository.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Nginx.

```sh
sudo make clean install
```

You should see the **nginx-init.service** cloning this git repository to fetch the content to serve.
Then, the **nginx-server.service** should start up.

You can check that the content is indeed served on port 80.

```
$ curl http://localhost/
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>
```

Then restart the **nginx.target** unit.

```sh
sudo systemctl restart nginx.target
```

In the logs, you should see the **nginx-update.service** starting up and executing a `git pull` to update the content to serve.
Then, the **nginx-server.service** should start up.

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```
