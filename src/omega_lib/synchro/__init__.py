# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrats d'interconnexion de la suite omega (D-017, 2026-11-10).

Specification : ~/DEV/CONNECT/SPEC_ETAPE2_CONTRATS_OMEGA_LIB.md (validee par l'auteur le 2026-11-10).

- `constants` : zone neutre, groupe, noms de fichiers, formats et versions ;
- `models` : jeton d'installation, fiche d'instance, evenement de ban, etats de lecture ;
- `codec` : dict <-> modeles, lecture tolerante (jamais d'exception sur un fichier recu) ;
- `policies` : regles pures (identifiant, empreinte machine, adresses, origines, rafraichissement) ;
- `rights` : droits attendus par fichier partage (ce qu'omega-connect verifiera) ;
- `registry` : registre de la zone neutre (contenu fixe a l'etape 3, omega-connect seul ecrivain).

Tout est pur (bibliotheque standard, aucune I/O). Les lectures et ecritures de fichiers sont dans
`omega_lib.infrastructure.synchro`. Aucun contrat ne contient de commande a executer."""
