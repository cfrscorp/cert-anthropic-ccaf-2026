---
name: terraform
description: Conventions for Terraform infrastructure code.
paths:
  - "terraform/**/*"
---

# Terraform conventions

Loaded only when editing files under `terraform/`.

- One resource per logical file; group with `main.tf`, `variables.tf`,
  `outputs.tf` inside each module.
- Every variable declares a `type` and a `description`; no bare `variable {}`.
- Pin provider versions in `required_providers`; never float on `latest`.
- Name resources `<provider>_<type>.<purpose>` in snake_case.
- Never hardcode secrets — reference `var.*` or a secrets manager data source.
- Run `terraform fmt` and `terraform validate` before committing.
