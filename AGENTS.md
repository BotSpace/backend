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

## Internal config API (dinamik config'ni yangilash)

Dinamik config'lar `OptionsModel` (settings/key/value) da, admin panel /settings da boshqariladi.
Avtomatlashtirib yangilash uchun `X-Internal-Token` bilan himoyalangan endpoint bor (admin login shart emas):

```bash
# .env dagi qiymatlar: BOTSPACE_API_BASE, INTERNAL_API_TOKEN (prod token, botmother-secret dan)
source .env   # yoki qiymatlarni o'qish

# O'qish:
curl -s -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$BOTSPACE_API_BASE/api/v1/shared/config/internal/options/?settings_key=engine&option_key=version"

# Yangilash (upsert):
curl -s -X POST -H "X-Internal-Token: $INTERNAL_API_TOKEN" -H "Content-Type: application/json" \
  -d '{"settings_key":"engine","option_key":"version","value":["3.5.122-prod"]}' \
  "$BOTSPACE_API_BASE/api/v1/shared/config/internal/options/set/"
```

- `value` list bo'ladi (yoki bare string yuborsang `[str]` ga o'raydi). `engine_version()` `value[0]` ni oladi.
- Engine'ni bump qilish = `settings_key=engine, option_key=version, value=["<yangi-tag>"]`. Bu FAQAT yangi/qayta release'larga ta'sir qiladi (release qilingan botlar o'z versiyasiga qotirilgan → buzilgan botni QAYTA release qilish kerak).
- Endpoint: `core/apps/shared/views/config.py` (`internal_options`, `internal_options_set`), permission `IsInternalTokenOnly`.
- Token qiymati `.env` da (gitignored) — hech qachon git'ga commit qilma. Prod'da `botmother-secret/INTERNAL_API_TOKEN`.
