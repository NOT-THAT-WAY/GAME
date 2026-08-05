# ADR 0002 — Transports réseau par étapes

**Statut : accepté — 2026-08-04**

FishNet `4.7.2` est le framework réseau. Tugboat est le transport local et LAN obligatoire ; il permet de développer sans Steam et de lancer plusieurs clients localement.

FishyFacepunch n'est pas retenu car le dépôt est archivé. Après validation LAN, le profil Steam utilisera Steamworks.NET `2025.164.1` avec FishySteamworks `4.1.1`. Multipass ne sera ajouté que si une build doit exposer plusieurs transports en même temps.

Le gameplay ne manipule jamais directement une adresse Tugboat, un lobby Steam ou un transport concret. Une abstraction `ConnectionTarget` résout aujourd'hui adresse/port et pourra résoudre plus tard un lobby. Des profils de build Tugboat et Steam séparés restent valides ; Multipass n'est requis que si les deux transports doivent cohabiter dans le même exécutable. Cette frontière complète [l'ADR 0004](0004-authoritative-topology-and-ticks.md).
