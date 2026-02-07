# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in OmoiOS, please report it responsibly. **Do not open a public GitHub issue.**

### How to Report

Email **security@omoios.dev** with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

### What to Expect

- **Acknowledgment** within 48 hours
- **Assessment** within 5 business days
- **Fix or mitigation** timeline communicated after assessment
- **Credit** in the release notes (unless you prefer to remain anonymous)

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Security Practices

### For Contributors

- **Never commit secrets** — API keys, tokens, passwords, and credentials belong in `.env` files (which are gitignored), not in source code or config files
- **Use `.env.example`** as a template — it contains only placeholder values
- **Run credential checks** before committing: `git diff --staged | grep -iE "(api_key|secret|password|token).*=.*[a-zA-Z0-9]{10,}"`
- **Environment variables** are the only mechanism for providing secrets in production

### For Deployers

- Rotate all secrets before deploying a fork to production
- Use unique JWT signing keys (`openssl rand -hex 32`)
- Configure HTTPS for all public-facing endpoints
- Review `backend/config/production.yaml` and override values via environment variables

## Scope

This security policy applies to the OmoiOS repository and its official deployments. Third-party forks and deployments are the responsibility of their maintainers.
