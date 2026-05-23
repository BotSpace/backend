## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## CI/CD & Deploy

Avtomatik deploy — `main` branchga push qilsang, GitHub Actions ishga tushadi:

1. Docker image build bo'lib `registry.iprogrammer.uz/botspace/botmother:<commit-sha>` ga push bo'ladi
2. `helm/values.yaml` dagi `image.tag` avtomatik yangilanadi (commit SHA bilan)
3. ArgoCD o'zgarishni ko'rib (~3 min) klasterga deploy qiladi

**Tag yaratish shart emas** — `git push origin main` yetarli.

- Workflow: `.github/workflows/deploy.yml`
- Helm values: `helm/values.yaml`
- ArgoCD Application: `k8s` reposida `helm/argocd/apps/web.yaml`
- `helm/` papkasidagi o'zgarishlar workflow ni qayta trigger qilmaydi (`paths-ignore`)
- Secretlar klasterdagi Kubernetes Secret larda saqlanadi, gitda emas
