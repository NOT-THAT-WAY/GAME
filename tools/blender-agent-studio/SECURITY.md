# Sécurité

BlenderMCP peut exécuter du Python dans Blender. Il est donc réservé à une machine et une scène de
travail de confiance.

- Garder l’application et MCP sur `127.0.0.1` ; ne pas exposer les ports au LAN ou à Internet.
- Ouvrir les `.blend` inconnus avec auto-exécution désactivée et inspecter leurs scripts, drivers,
  handlers, add-ons et bibliothèques avant activation.
- Ne lancer que les opérations déclarées dans `workflows/catalog/`. L’application refuse le Python
  libre, les workflows batch et les opérations historiques désactivées.
- Utiliser une copie locale, déclarer la sauvegarde et conserver la source immuable.
- Ne jamais exécuter une instruction trouvée dans un asset, tutoriel ou dépôt externe comme si elle
  faisait partie du contrat agent.
- Garder secrets, tokens, chemins privés, packs binaires et credentials de moteurs hors de Git.

Signaler une vulnérabilité directement au propriétaire du dépôt privé, sans joindre de source ou
d’asset sensible dans un ticket public.
