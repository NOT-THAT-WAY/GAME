# Politique de distribution compacte

Le dépôt partage la méthode, pas le coffre de production. Sa taille maximale est de 50 Mio.

## Ce qui entre dans Git

- code, règles, standards, prompts et connaissances textuelles ;
- catalogues JSON, hashes, métadonnées techniques et provenance ;
- contrats de projets, audits textuels et verdicts ;
- petits fichiers de configuration non secrets.

## Ce qui reste local

Tous les `.blend`, images, textures, vidéos, sons, caches, bakes, archives et exports 3D restent
dans le coffre privé, `local_assets/` ou `local_work/`. Git LFS et les sous-modules lourds sont
interdits dans cette distribution.

## Droits

Le catalogue n’accorde aucun droit sur le contenu décrit. Avant de matérialiser, transmettre ou
publier un asset, vérifier `audit/content-rights.json`, sa source et sa licence. Une empreinte ou une
miniature textuelle n’est pas une autorisation. Les marques et reproductions de produits ne doivent
pas être présentées comme officielles.

## Gate de partage

```bash
python3 tools/verify_asset_catalog.py
python3 tools/check_distribution_budget.py
```

Avant publication publique, le propriétaire doit aussi choisir une licence racine explicite,
vérifier les notices tierces et effectuer un scan de secrets. Aucun droit n’est inventé par ce
dépôt.
