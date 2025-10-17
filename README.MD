# JST-DJANGO
[Docs](https://docs.jscorp.uz)

## GitHub Actions CI/CD

This project uses GitHub Actions for continuous integration and deployment to Docker Hub.

### Required Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `DOCKER_USERNAME` - Your Docker Hub username
- `DOCKER_PASSWORD` - Your Docker Hub password or access token

### Workflow

The workflow automatically:
1. Builds Docker image
2. Runs database migrations and tests
3. Pushes to Docker Hub with tags: `latest` and build number
