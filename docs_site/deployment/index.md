# Deployment

Production deployment guides and operational documentation.

## Deployment Guides

- [Docker Deployment](docker.md) - Container-based deployment
- [Production Setup](production.md) - Production configuration and best practices
- [Security Guide](security.md) - Security hardening and best practices
- [Monitoring & Observability](monitoring.md) - Setting up monitoring stack
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Backup & Recovery](backup-recovery.md) - Data protection strategies

## Quick Deploy

\`\`\`bash
# Using Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Or using the Makefile
make deploy-prod
\`\`\`

See [Production Setup](production.md) for detailed deployment procedures.
