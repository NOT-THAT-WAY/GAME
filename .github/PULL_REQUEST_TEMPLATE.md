## Résultat

Décrire ce qui est maintenant testable.

## Fichiers Unity / Wwise / données sensibles

Lister scènes, prefabs, ProjectSettings, Work Units, fichiers LFS, pointeurs DVC et éventuelle migration de données.

## Vérification

- [ ] nom de branche et titre de PR utilisent le même type (`feat`, `fix`, `art`, `audio`, `data`, `docs` ou `chore`)
- [ ] diagnostic local exécuté
- [ ] Play Mode ou test pertinent exécuté
- [ ] test par un second membre
- [ ] autre OS testé si nécessaire
- [ ] aucun cache, secret ou SoundBank intermédiaire ; les banques runtime approuvées utilisent Git LFS
- [ ] `dvc push` terminé avant `git push` si un pointeur DVC change
- [ ] aucun master éditable ou donnée personnelle ajouté à Git
- [ ] registre des assets / ADR mis à jour si nécessaire
