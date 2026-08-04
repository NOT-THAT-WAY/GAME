# ADR 0002 — Transports réseau par étapes

**Statut : accepté — 2026-08-04**

FishNet `4.7.2` est le framework réseau. Tugboat est le transport local et LAN obligatoire ; il permet de développer sans Steam et de lancer plusieurs clients localement.

FishyFacepunch n'est pas retenu car le dépôt est archivé. Après validation LAN, le profil Steam utilisera Steamworks.NET `2025.164.1` avec FishySteamworks `4.1.1`. Multipass ne sera ajouté que si une build doit exposer plusieurs transports en même temps.
