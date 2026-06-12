# Backend HTTPS cutover (droplet)

The backend currently serves plain HTTP on `http://137.184.16.45` via
`docker-compose.backend-full.yml` (backend published directly on :80).
`docker-compose.backend-tls.yml` puts Caddy in front with automatic
Let's Encrypt certificates.

## Prerequisites (owner action)

1. Pick a hostname, e.g. `api.profmatch.example`.
2. Create a DNS A record pointing it at the droplet IP (137.184.16.45).
3. Wait for DNS to propagate (`dig +short api.profmatch.example`).

## Cutover steps (on the droplet, /opt/profmatch)

```bash
echo 'DOMAIN=api.profmatch.example' >> .env
docker compose -f docker-compose.backend-full.yml down
docker compose -f docker-compose.backend-tls.yml up -d --build
curl -fsS https://api.profmatch.example/health
```

Then in Vercel, set `BACKEND_URL=https://api.profmatch.example` and redeploy
the frontend. Also add the Vercel hostname to `ALLOWED_ORIGINS` in the
droplet `.env` if it is not already there.

Update `.github/workflows/deploy-droplet-backend.yml` to use
`docker-compose.backend-tls.yml` once the cutover is verified, and set the
`BACKEND_HEALTH_URL` repository variable to the HTTPS health URL so the
uptime workflow watches the right endpoint.

## Rollback

```bash
docker compose -f docker-compose.backend-tls.yml down
docker compose -f docker-compose.backend-full.yml up -d
```

and point `BACKEND_URL` back at the IP.
