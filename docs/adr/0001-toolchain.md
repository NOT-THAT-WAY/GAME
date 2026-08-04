# ADR 0001 — Toolchain commune

**Statut : accepté — 2026-08-04**

Le projet utilise Unity `6000.3.20f1` LTS, URP `17.3.0`, DVC 3.x, Git LFS et UnityYAMLMerge sur deux Mac Apple Silicon et un PC Windows. La cible de sortie initiale est Windows x86_64 ; le PC produit les builds IL2CPP de référence.

Les versions sont figées au dépôt. Une montée de version exige une PR dédiée et une validation sur les deux OS.
