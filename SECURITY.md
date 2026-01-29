# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please email security@prompted365.com or report it privately through GitHub's security advisory feature.

**Please do not report security vulnerabilities through public GitHub issues.**

### What to Include

- Type of vulnerability
- Full path of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- We will acknowledge your report within 48 hours
- We will provide a detailed response within 7 days
- We will work to release a fix as quickly as possible
- We will credit you in the release notes (unless you prefer to remain anonymous)

## Security Best Practices

### API Keys

- Never commit `.env` files
- Use environment variables for secrets
- Rotate API keys regularly
- Use different keys for development/production

### Docker Deployment

- Don't expose ports unnecessarily
- Use secrets management for production
- Keep images updated
- Use non-root users where possible

### Database

- Use strong passwords
- Enable SSL/TLS in production
- Regular backups
- Limit network access

### Web Crawling

- Validate and sanitize URLs
- Set timeout limits
- Use rate limiting
- Monitor for abuse

## Known Security Considerations

### 1. LLM API Keys

Store LLM API keys (OpenAI, Anthropic, Requesty.ai) securely:
- Use environment variables
- Don't log API keys
- Use separate keys for different environments

### 2. Web Crawling

When crawling external websites:
- Respect robots.txt
- Use rate limiting
- Set User-Agent headers appropriately
- Handle authentication securely

### 3. Vector Database

Milvus collections may contain sensitive data:
- Use authentication in production
- Limit network access
- Regular backups
- Consider encryption at rest

### 4. Task Queue

Celery tasks may process sensitive data:
- Use Redis password authentication
- Encrypt result backend if needed
- Monitor for task queue abuse
- Set resource limits

## Security Updates

Security updates will be published:
- In GitHub Security Advisories
- In CHANGELOG.md
- As GitHub releases
- Via email to security mailing list (if subscribed)

## Bug Bounty

We don't currently have a formal bug bounty program, but we appreciate responsible disclosure and will credit security researchers in our releases.
