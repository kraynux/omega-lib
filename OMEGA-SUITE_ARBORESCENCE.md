# OMEGA-SUITE – Arborescence du projet

**Objectif** : `omega-lib` et `omega-suite` structurés pour que la migration soit un déplacement de fichiers, pas une réécriture — rendu possible par le fait que CHECK/DEEP/FOLD (et la remise à niveau de SCAN/STRESS) partagent déjà la même Dependency Rule. Décision actée le 2026-08-28 (voir `DECISIONS_ARCHITECTURE.md`, même dossier).

---

## 1. omega-lib (bibliothèque partagée)

`omega-lib` ne contient QUE ce qui est réellement identique entre plusieurs outils — pas de couche `interfaces/` ni `app/` (ce n'est pas une application, pas de composition root propre).

**Bootstrap anticipé (D-005, 2026-08-28)** : cette structure complète est la cible finale (Phase Suite), mais `omega-lib` est en réalité créé bien plus tôt — dès la Phase 1 de CHECK — avec un périmètre volontairement réduit à `core/confidence.py` + `shared/*` (voir `DECISIONS_ARCHITECTURE.md` D-005). Le reste (probes, ports, storage communs ci-dessous) est ajouté progressivement au fil de CHECK/DEEP/FOLD, pas d'un coup en Phase Suite.

**Extension theme/terminal (D-008, 2026-08-29)** : en construisant le TUI de CHECK, tout le système de thème (`theme/{models,policies,service}.py` — catalogue de 10 thèmes TUI + 5 thèmes d'export, identique à omega-scan/omega-stress) et de détection terminal (`terminal/{models,policies,service}.py`, `infrastructure/terminal/*`, `ports/{terminal_detector,settings_store}.py`) a été rapatrié dans `omega-lib` plutôt que dupliqué une 3e fois — ces modules étaient déjà documentés dans omega-scan comme "identiques à omega-stress", donc déjà mûrs pour la mutualisation dès le 2e/3e outil qui en a besoin (voir D-002/D-005 pour le principe). `omega-lib` a donc maintenant, en plus de `core/`+`shared/` : `theme/`, `terminal/`, `ports/`, `infrastructure/terminal/`.

**État réel à date (D-013, 2026-09-07)** : le contenu **effectivement construit et consommé par tous les outils du périmètre** (CHECK/DEEP/FOLD/FUZZ/STRESS/TRACK/SCAN — omega-fire/omega-serv/omega-waf/omega-log explicitement hors périmètre) se limite à `core/confidence.py`, `shared/{clock,ids,typing}.py`, `theme/{models,policies,service}.py`, `terminal/{models,policies,service}.py`, `ports/{terminal_detector,settings_store}.py`, `infrastructure/terminal/{detector,fallback_resolver,raw_capabilities}.py` — **rien de plus** (`core/exceptions.py`, `core/audit.py`, tout `domain/`, `application/pipeline/`, `infrastructure/network`, `infrastructure/storage`, `infrastructure/exporters` listés ci-dessous restent des cibles Phase Suite non construites, pas décrire l'existant). SCAN était le dernier outil du périmètre à ne pas encore consommer ce noyau (il gardait sa propre copie d'origine) ; migré lors de D-013, clôturant la réserve posée par D-008 — les 7 outils du périmètre partagent désormais ce noyau à l'identique, vérifié par diff direct entre chaque `vendor/omega-lib/` et la source du monorepo.

```
omega-lib/
├── pyproject.toml
├── README.md
│
├── src/omega_lib/
│   ├── __init__.py
│   │
│   ├── core/                        # Vocabulaire transverse commun aux 6 outils (D-012)
│   │   ├── confidence.py            # ConfidenceLevel (modèle révisé — voir SPECIFICATIONS.md §2)
│   │   ├── exceptions.py
│   │   └── audit.py
│   │
│   ├── domain/                      # UNIQUEMENT les bounded contexts réellement partagés
│   │   ├── scans/                   # Scan (champs communs : id, created_at, tool, target, status)
│   │   ├── profiles/                # Profile (check + deep uniquement — pas scan/stress/fold)
│   │   └── html_links/              # NOUVEAU (voir décision D-002) : extraction de liens HTML,
│   │                                #   mutualisé entre omega-deep (discovery) et omega-fold (crawl)
│   │
│   ├── ports/                       # Contrats communs
│   │   ├── http_prober.py           # Réutilisé par scan, check, deep
│   │   ├── tls_prober.py            # Réutilisé par scan, check, deep
│   │   ├── scan_repository.py       # Contrat générique (chaque outil l'implémente pour son schéma)
│   │   └── report_exporter.py
│   │
│   ├── application/
│   │   └── pipeline/
│   │       ├── guards/
│   │       │   └── authorization_guard.py   # Un seul guard d'autorisation pour tous les outils actifs
│   │       └── hooks/
│   │           └── audit_hook.py
│   │
│   ├── infrastructure/
│   │   ├── network/
│   │   │   ├── httpx_http_prober.py
│   │   │   └── httpx_tls_prober.py
│   │   ├── storage/
│   │   │   └── sqlite/
│   │   │       ├── connection.py
│   │   │       └── base_schema.py   # Table `scans` commune (voir §6 Stockage unifié)
│   │   └── exporters/
│   │       ├── json_exporter.py
│   │       ├── text_exporter.py
│   │       ├── html_exporter.py
│   │       └── templates/           # Thèmes communs (base.html, header/footer partagés)
│   │
│   └── shared/
│       ├── clock.py
│       ├── ids.py                   # UUID — voir principes §6.2
│       └── typing.py
│
└── tests/
    ├── unit/
    └── integration/
```

**Ce qui NE va PAS dans omega-lib** (reste dans chaque outil) : tout `domain/` métier réellement spécifique (`domain/services` de check, `domain/architecture` de deep, `domain/tree|stats` de fold, logique de charge de stress, logique de hygiène HTTP de scan), tout `interfaces/` (CLI/TUI propres), tout `app/` (composition root propre à chaque outil — chaque outil reste exécutable seul).

---

## 2. omega-suite (interface unifiée)

```
omega-suite/
├── pyproject.toml                   # Dépend de omega-lib + des 6 outils (D-012)
├── README.md
│
├── src/omega_suite/
│   ├── __init__.py
│   ├── __main__.py
│   │
│   ├── app/
│   │   ├── bootstrap.py             # Assemble les DependencyContainer des 6 outils
│   │   ├── dependency_container.py
│   │   └── lifecycle.py
│   │
│   └── interfaces/
│       ├── cli/
│       │   ├── main.py              # `omega-suite <outil> <commande> ...`
│       │   └── commands/
│       │       ├── scan.py          # Délègue à omega_scan.application
│       │       ├── stress.py
│       │       ├── check.py
│       │       ├── deep.py
│       │       └── fold.py
│       └── tui/
│           ├── app.py
│           └── screens/
│               ├── home.py          # Écran d'accueil, choix de l'outil
│               ├── scan.py
│               ├── stress.py
│               ├── check.py
│               ├── deep.py
│               └── fold.py
│
└── tests/
    └── e2e/                          # Tests bout-en-bout sur la suite complète
```

`omega-suite` importe `omega_scan.application`, `omega_check.application`, etc. directement (chaque outil reste un package installable séparé) — `omega-suite` n'est qu'une couche `interfaces/` + `app/` supplémentaire, il ne réimplémente aucune logique métier.

---

## 3. Chaque outil (scan, stress, check, deep, fold, track) après migration

```
omega-<outil>/
├── src/omega_<outil>/
│   ├── core/           # Ce qui n'a pas pu être remonté dans omega_lib (spécifique à l'outil)
│   ├── domain/         # Bounded contexts spécifiques (voir §1 "ce qui ne va pas dans omega-lib")
│   ├── ports/           # Contrats spécifiques (ceux communs sont importés depuis omega_lib.ports)
│   ├── application/     # Use cases spécifiques
│   ├── infrastructure/  # Adaptateurs spécifiques (ceux communs importés depuis omega_lib.infrastructure)
│   ├── interfaces/       # CLI/TUI propre — reste utilisable en standalone
│   ├── app/              # Composition root propre — reste utilisable en standalone
│   └── shared/           # Peut être entièrement remplacé par un import de omega_lib.shared
```

Chaque outil reste **exécutable de façon autonome** (`omega-check scan ...` fonctionne toujours après migration) — `omega-suite` est une façade additionnelle, pas un remplacement qui casse la rétrocompatibilité, conformément à la note de PLAN_DEV.md.

---

## 4. Fichiers clés à créer en priorité

1. `omega-lib/src/omega_lib/core/confidence.py` (modèle révisé, base de tout le reste).
2. `omega-lib/src/omega_lib/ports/http_prober.py`, `tls_prober.py` (déjà éprouvés dans scan — extraction directe).
3. `omega-lib/src/omega_lib/infrastructure/storage/sqlite/base_schema.py` (table `scans` commune).
4. `omega-suite/src/omega_suite/app/dependency_container.py`.
5. `omega-suite/src/omega_suite/interfaces/cli/main.py`.

---

## 5. Dépendances principales

```toml
# omega-lib/pyproject.toml
[project]
name = "omega-lib"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["httpx>=0.27", "jinja2>=3.1"]

# omega-suite/pyproject.toml
[project]
name = "omega-suite"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "omega-lib>=0.1.0",
    "omega-scan>=2.0.0",
    "omega-stress>=0.1.0",
    "omega-check>=0.1.0",
    "omega-deep>=0.1.0",
    "omega-fold>=0.1.0",
    "textual>=0.60",
]
[project.scripts]
omega-suite = "omega_suite.__main__:main"
```

---

## 6. Stockage unifié (SQLite) — principes anticipés dès aujourd'hui

Décidés maintenant pour que la fusion en un seul `omega.db` (Phase 4) soit une copie de lignes, pas une migration de schéma :

1. **`scan_id` en UUID** (via `shared/ids.py`) plutôt qu'un entier autoincrémenté local à chaque DB — aucune collision possible lors de la fusion de 5 fichiers SQLite.
2. **Colonne `tool`** dès la v1 solo de chaque outil (`tool TEXT NOT NULL DEFAULT 'check'`, etc.), même si elle est mono-valeur aujourd'hui — la fusion devient un `UNION`, pas un `ALTER TABLE`.
3. **`created_at` en ISO8601 UTC** partout (déjà le cas dans scan/stress).
4. **Fichier séparé par outil aujourd'hui** (`~/.local/share/omega-<outil>/<outil>.db`, cohérent avec scan/stress existants) — la fusion Phase 4 copie les lignes vers `omega.db` sans renumérotation.
5. Chaque outil garde un schéma de table spécifique pour ses résultats (`hosts`/`ports`/`services` pour check, `files`/`links` pour fold, etc.) — **pas** de colonne JSON fourre-tout `scan_results`, qui était sous-spécifiée dans la version précédente de ce document. La table `scans` (commune, dans `omega_lib.infrastructure.storage.sqlite.base_schema`) référence ces tables spécifiques par `scan_id`, à la manière d'une clé étrangère inter-DB (ou table réelle une fois fusionné).

---

## 7. Notes

- Toute divergence entre ce document et ce qui est réellement codé (dans n'importe quel outil de la suite) doit être tracée dans `DECISIONS_ARCHITECTURE.md`.
