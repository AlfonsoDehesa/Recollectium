# Security Policy

## Recollectium v1 security model

Recollectium is local-first software. It is designed for agents and clients running on the same machine as Recollectium Core.

In v1, Recollectium services are not hardened as public network services:

- The API service has no built-in authentication.
- The MCP service has no built-in authentication.
- Recollectium does not provide API keys, user accounts, ACLs, or built-in TLS termination in v1.
- Health, version, and capability checks confirm service compatibility. They are not authentication or authorization controls.

Do not expose Recollectium directly to the public internet.

## Local-first deployment

The recommended v1 deployment is to run Recollectium on the same machine as the agent or client and keep services bound to localhost, usually `127.0.0.1`.

The default local service endpoint is:

```text
http://127.0.0.1:8765
```

This default keeps the service reachable only from the local machine under ordinary host networking rules.

## Running services

Recollectium can run managed API and MCP services:

```bash
recollectium service start api
recollectium service start mcp
```

It can also run the API service in the foreground for development and debugging:

```bash
recollectium serve --host 127.0.0.1 --port 8765
```

Binding to a non-local interface, such as `0.0.0.0`, a LAN address, a VPN address, a container bridge, or a public interface, can expose unauthenticated memory operations to anyone who can reach that interface.

## Memory database and local filesystem access

The SQLite memory database is not encrypted by Recollectium.

Any user, process, or network client with sufficient access to the Recollectium data directory, database file, or unauthenticated service endpoint can read, modify, or delete memories. Because memories influence what agents recall, unauthorized memory changes can also influence agent behavior.

Protect the Recollectium data directory and database file like other sensitive local application data. Host-level protections such as operating-system permissions, encrypted home directories, full-disk encryption, encrypted volumes, backups, and endpoint security remain the user's responsibility.

## Recommended deployment patterns

Recommended for v1:

- Run Recollectium on the same machine as the agent or client.
- Keep API and MCP services bound to `127.0.0.1` unless there is a deliberate private-network deployment.
- Use local service discovery for same-machine adapters.
- Keep the database and config directories protected by normal OS account permissions.

If the agent and Recollectium must run on different machines, expose Recollectium only over private networking with external access controls.

For most users who need split-machine access, a private overlay network such as Tailscale is the recommended path. Equivalent private-network approaches can also work, including WireGuard, SSH tunneling, firewall allowlists, or other VPN/overlay networking.

## Risky or unsupported deployment patterns

Avoid these v1 deployment patterns unless you have added external protections and understand the risk:

- Binding Recollectium to `0.0.0.0` on an untrusted network.
- Exposing Recollectium on a public IP address.
- Publishing Recollectium through a public reverse proxy. Public reverse-proxy exposure is unsupported for v1 unless an advanced user fully supplies and owns external authentication, TLS, and access controls.
- Tunneling Recollectium through a public tunnel without restricting who can connect.
- Assuming Docker, container networking, or a VM boundary alone makes an unauthenticated service safe.

Direct public exposure is unsupported for v1.

## If you must connect from another machine

Use a private network path and restrict which clients can reach Recollectium:

1. Prefer a private overlay network such as Tailscale for split-machine access.
2. Keep Recollectium bound to a private or localhost-only interface where practical.
3. Restrict access with ACLs, firewall rules, SSH tunnel configuration, or equivalent controls.
4. Validate the Recollectium service with health, version, and capability checks before enabling tools.
5. Remember that compatibility validation is not authentication. It does not protect the endpoint from other clients that can reach it.

## Reporting security issues

Please do not publish sensitive vulnerability details in a public GitHub issue.

Use GitHub private vulnerability reporting for this repository if it is enabled. If private vulnerability reporting is unavailable, open a public GitHub issue that asks for a private reporting channel but does not include vulnerability details, proof-of-concept code, private data, or exploit steps.
