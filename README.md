# omega-lib

Bibliotheque partagee pour la suite OMEGA (omega-scan, omega-stress, omega-check, omega-deep, omega-fold, omega-suite, omega-fuzz).

**Statut (2026-08-28)** : noyau minimal uniquement — voir `DECISIONS_ARCHITECTURE.md` D-005. Contient pour l'instant :

- `omega_lib.core.confidence.ConfidenceLevel` — modele de confiance commun (D-001).
- `omega_lib.shared.clock` / `shared.ids` / `shared.typing` — utilitaires transverses sans dependance.

Le reste (probes, ports, storage, export communs — voir `OMEGA-SUITE_ARBORESCENCE.md` §1) sera ajoute progressivement au fil du developpement, pas d'un coup.

Installe en dependance editable par chaque outil consommateur :

```bash
pip install -e ../../LIB/omega-lib
```
