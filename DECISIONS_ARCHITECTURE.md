# Journal des decisions d'architecture — OMEGA-SUITE

Journal centralise (format ADR-lite) des decisions qui affectent la coherence entre plusieurs outils de la suite (omega-scan, omega-stress, omega-check, omega-deep, omega-fold, omega-track, omega-suite/omega-lib). Objectif : quand une contrainte oblige a devier du plan de dev d'un outil pour rester coherent avec l'avenir de la suite, la deviation est ecrite ici plutot qu'improvisee silencieusement — comme demande explicitement lors de la session du 2026-08-28.

Chaque entree : date, outil(s) concerne(s), contexte, decision, alternative ecartee, impact sur les autres outils.

---

## D-000 — Architecture Clean 9-couches pour CHECK/DEEP/FOLD/SUITE

**Date** : 2026-08-28
**Outils concernes** : CHECK, DEEP, FOLD, SUITE (retroactivement : SCAN, STRESS deja conformes)

**Contexte** : les 4 documents de planification (CHECK/DEEP/FOLD/SUITE) decrivaient initialement une structure plate (`core/probes/storage/export/cli.py`), incoherente avec la Clean Architecture a 9 packages (`app/application/core/domain/infrastructure/interfaces/plugins/ports/shared`) reellement utilisee et validee sur omega-scan et omega-stress (Dependency Rule via import-linter).

**Decision** : CHECK/DEEP/FOLD/SUITE adoptent des le depart la meme structure a 9 couches que scan/stress, avec la meme Dependency Rule et les memes contrats import-linter. Les 4 `ARBORESCENCE.md` ont ete reecrits en consequence.

**Alternative ecartee** : garder la structure plate et remigrer plus tard en Phase Suite (cout paye deux fois — une fois de facon ad-hoc, une fois lors de l'extraction omega-lib).

**Impact** : l'extraction `omega-lib` (Phase Suite) devient un deplacement de fichiers entre couches identiques plutot qu'un re-agencement structurel prealable. Cout initial plus eleve sur CHECK (scaffolding des 9 couches des la Phase 1) mais evite une double depense.

---

## D-001 — Modele ConfidenceLevel revise

**Date** : 2026-08-28
**Outils concernes** : CHECK, DEEP, FOLD (SUITE/omega-lib centralise `core/confidence.py`) ; a appliquer retroactivement a SCAN/STRESS lors de leur migration Phase Suite si leur propre notion de confiance existe sous une autre forme.

**Contexte** : l'ancien modele (`garanti/fiable/modere/incertain/cache`) est un ordinal qui confond "a quel point on y croit" et "pourquoi on y croit" — une valeur auto-declaree par la cible (ex: header `Server`) et une valeur deduite d'un pattern comportemental tombaient toutes deux dans des categories intermediaires ambigues (FIABLE/MODERE) sans distinction claire de la nature de la preuve.

**Decision** : `ConfidenceLevel = VERIFIED | DECLARED | CORROBORATED | INFERRED | UNKNOWN`, ou `DECLARED` marque explicitement "ce que la cible annonce elle-meme, et qu'elle peut falsifier" (le cas du server tag). Valeurs d'enum en anglais/ASCII (au lieu du francais accentue) pour la robustesse du stockage SQLite/JSON inter-outils.

**Alternative ecartee** : garder les valeurs francaises accentuees en s'assurant seulement d'un encodage UTF-8 propre dans le code (les fichiers `.md` de planification etaient corrompus par des entites HTML — probleme purement documentaire, pas un argument suffisant pour changer l'enum, mais la clarification "declare vs verifie" l'est).

**Impact** : les probes documentees dans les SPECIFICATIONS.md de CHECK/DEEP/FOLD utilisent encore ponctuellement l'ancien vocabulaire dans le texte descriptif (non corrige terme a terme, cout jugee disproportionne) — a relire au moment de l'implementation, pas a copier tel quel.

---

## D-002 — Extraction HTML : candidat a mutualisation anticipee

**Date** : 2026-08-28
**Outils concernes** : DEEP (`infrastructure/discovery/html_link_extractor.py`), FOLD (`infrastructure/network/bs4_link_extractor.py`)

**Contexte** : DEEP (decouverte de cibles via liens HTML) et FOLD (crawl distant) resolvent tous deux "extraire des URLs d'une page HTML" independamment, alors que ce sont deux developpements distincts prevus en parallele (FOLD n'a pas de dependance de dev vers DEEP).

**Decision (provisoire)** : dupliquer pour l'instant (developpement independant maintenu), mais flagger explicitement ce point dans les deux ARBORESCENCE.md. Si les deux implementations divergent significativement en pratique (deux logiques de parsing incompatibles), reevaluer une mutualisation anticipee dans `omega_lib.domain.html_links` avant la Phase Suite plutot que d'attendre.

**A trancher** : au moment ou DEEP et FOLD sont tous deux en cours de developpement (probablement pas simultane vu le sequencement — voir D-004), reevaluer si l'un peut reutiliser le travail de l'autre plutot que de dupliquer.

---

## D-003 — Flux `validate_targets` (DEEP) detaille

**Date** : 2026-08-28
**Outils concernes** : DEEP

**Contexte** : la spec initiale de `validate_targets` etait sommaire ("afficher, demander confirmation, permettre selection") alors que c'est le point le plus sensible de DEEP — action sur des cibles non explicitement demandees par l'utilisateur au depart, meme avec garde-fous (subnet, profondeur, nombre max).

**Decision** : machine a etats explicite (PROPOSED -> PRESENTED -> ACCEPTED/REJECTED -> SCANNED), refus implicite par defaut (fail-safe) pour toute cible non explicitement validee, `--auto-validate` deconseille avec avertissement, comportement non-interactif = pas de scan des cibles decouvertes sans validation. Detail dans `OMEGA-DEEP_SPECIFICATIONS.md` §6.2.

**Impact** : aucun sur les autres outils (specifique a DEEP).

---

## D-004 — Calendrier de developpement : hypothese de depart obsolete

**Date** : 2026-08-28
**Outils concernes** : CHECK, DEEP, FOLD, SUITE

**Contexte** : les estimations "X semaines" des PLAN_DEV.md de chaque outil supposaient un codage manuel a l'ancienne, journees completes, sans assistance IA. Ce n'est plus le mode de developpement reel.

**Decision** : les chiffres en semaines restent indicatifs (ordre de grandeur relatif entre phases, pas une duree calendaire engageante) et ne sont plus une reference fiable. Le principe qui reste : developpement **sequentiel**, un outil termine avant de commencer le suivant (CHECK -> DEEP -> FOLD peut chevaucher puisqu'independant -> SUITE), jamais concomitant, tout en gardant les besoins des outils futurs a l'esprit pendant le developpement de l'outil courant. Toute derogation a ce sequencement (ex: commencer FOLD avant que CHECK soit fini) doit etre justifiee ici.

**Impact** : les tableaux "Recapitulatif des phases" des PLAN_DEV.md restent en l'etat a titre indicatif uniquement — voir note ajoutee dans chaque PLAN_DEV.md.

---

## D-005 — Bootstrap minimal de omega-lib des maintenant (pas en Phase Suite)

**Date** : 2026-08-28
**Outils concernes** : CHECK (premier consommateur), DEEP, FOLD ensuite ; SUITE (heritier direct)

**Contexte** : la duplication des probes HTTP/TLS entre CHECK/DEEP (et de la logique HTML entre DEEP/FOLD, voir D-002) a un cout qui croit avec le nombre de copies a reconcilier plus tard. Le refus initial de creer omega-lib avant la Phase Suite reposait sur "omega-lib n'existe pas encore" — mais rien n'empeche de le faire exister des maintenant pour le sous-ensemble de code qui ne varie structurellement pas d'un outil a l'autre.

**Decision** : creer `~/DEV/LIB/omega-lib/` des la Phase 1 de CHECK (pas une "mini-lib" jetable a part, litteralement le futur `omega-lib`, demarre au format reduit) contenant UNIQUEMENT :
- `core/confidence.py` (`ConfidenceLevel`, voir D-001) — primitif stable, quasi zero risque de divergence entre outils.
- `shared/clock.py`, `shared/ids.py` (UUID pour `scan_id`, voir D-006), `shared/typing.py` — utilitaires sans dependance, deja identiques mot pour mot entre scan et stress.

CHECK installe `omega-lib` en dependance editable locale (`pip install -e ../../LIB/omega-lib` ou equivalent `uv`/`hatch`) des le depart plutot que de copier ces 4 fichiers. DEEP et FOLD font de meme.

Restent DUPLIQUES pour l'instant (pas dans ce bootstrap) : les probes HTTP/TLS/SSH/VNC (`ports/*_prober.py` + leurs implementations `infrastructure/network/`), la logique d'extraction HTML (D-002), les modeles `Scan`/`Host`/`Port`/`Service` (trop de champs specifiques par outil pour factoriser sans sur-ingenierie prematuree — a revisiter une fois CHECK et DEEP tous deux codes, cf. D-002 "a trancher").

**Alternative ecartee** : (a) tout dupliquer et n'extraire qu'en Phase Suite (cout de reconciliation x5 a la fin) ; (b) construire omega-lib complet des maintenant en anticipant tous les besoins de DEEP/FOLD/SUITE avant d'avoir code le moindre outil (sur-ingenierie contre laquelle la feedback memorisee sur omega-stress met deja en garde — ne pas re-deriver dans le vide).

**Impact** : `OMEGA-SUITE_ARBORESCENCE.md` §1 (structure de omega-lib) reste la cible finale ; ce bootstrap n'en couvre qu'un sous-ensemble volontairement restreint. Quand la Phase Suite arrive, omega-lib n'est pas cree ex nihilo, il est etendu depuis ce noyau deja en production dans 3 outils.

---

## D-006 — Schema SQLite extensible des la v1 solo de chaque outil

**Date** : 2026-08-28
**Outils concernes** : CHECK, DEEP, FOLD, SUITE

**Contexte** : "un seul SQLite pour tous les outils" avec "JSON ou tables dediees" (spec SUITE initiale) n'etait pas tranche — risque de migration de schema lourde en Phase Suite si chaque outil fige un schema incompatible sans y penser des le depart.

**Decision** : principe formalise dans `OMEGA-SUITE_ARBORESCENCE.md` §6 — (1) `scan_id` en UUID (via `omega_lib.shared.ids`, voir D-005) plutot qu'auto-increment local ; (2) colonne `tool` des la v1 solo de chaque outil, meme mono-valeur aujourd'hui ; (3) `created_at` en ISO8601 UTC partout ; (4) une DB SQLite separee par outil aujourd'hui (`~/.local/share/omega-<outil>/<outil>.db`), fusionnee en Phase Suite par simple copie de lignes vers `omega.db` ; (5) chaque outil garde ses propres tables de resultats specifiques (`hosts`/`ports`/`services` pour check, `files`/`links` pour fold, etc.) plutot qu'une colonne JSON fourre-tout `scan_results`.

**Alternative ecartee** : colonne `results_json` generique pour stocker les resultats specifiques de chaque outil — plus simple a court terme mais rend impossibles les requetes structurees (ex: "tous les ports 443 ouverts, tous scans confondus") sans deserialiser du JSON en Python a chaque fois.

**Impact** : aucun cout supplementaire immediat (c'est la conception naturelle d'un schema `scans` + tables satellites) — juste une discipline a respecter des la Phase 2 de CHECK pour ne pas avoir a la retro-appliquer.

---

## D-007 — Contrats import-linter copies verbatim depuis omega-scan/stress

**Date** : 2026-08-28
**Outils concernes** : CHECK (premier a implementer), puis DEEP, FOLD

**Contexte** : question posee explicitement — partir des contrats import-linter d'omega-scan et les "upgrader" vers une version generique anticipant tous les outils, ou copier verbatim et adapter au cas par cas ? Comparaison faite entre les contrats reels de omega-scan et omega-stress : les deux contrats generiques (`layers` / Dependency Rule, `interfaces` independant de `infrastructure`) sont identiques mot pour mot entre les deux outils deja finis ; seuls les contrats `forbidden` de confinement de techno (ex: `httpx` confine a `infrastructure.network` pour scan, a `infrastructure.runner` pour stress) divergent, parce que chaque outil nomme differemment l'endroit ou vit cette techno.

**Decision** : pour CHECK, copier tel quel le bloc `[tool.importlinter]` + les contrats `layers` et `interfaces-independant-de-infrastructure` (juste `omega_scan.` -> `omega_check.`), puis recreer un contrat `forbidden` par technologie (`textual`, `sqlite3`, `httpx`, `jinja2`) en pointant vers le chemin reel de CHECK (`interfaces.tui`, `infrastructure.storage.sqlite`, `infrastructure.network`, `infrastructure.exporters`). Ne pas tenter de generaliser en amont sans un 2e ou 3e exemple reel.

**Alternative ecartee** : concevoir a l'avance un contrat "universel" parametrable — rejete, ce serait deviner une contrainte hypothetique avant d'avoir les donnees (meme scan et stress, deja finis, n'ont pas cherche a s'aligner artificiellement sur les memes noms de modules).

**Impact** : une fois CHECK et DEEP codes (2 exemples de plus), reevaluer objectivement ce qui converge vraiment entre les 4 implementations et si un gabarit commun merite d'etre codifie (ex: `scripts/generate_importlinter_contracts.py` dans omega-lib, ou un simple snippet documente ici) — pas avant.

---

## D-008 — Theme TUI/export et detection terminal centralises dans omega-lib

**Date** : 2026-08-29
**Outils concernes** : CHECK (premier consommateur), SCAN/STRESS (source, non modifies), DEEP/FOLD/SUITE (futurs consommateurs)

**Contexte** : demande explicite de presentation/esthetique/thematique identique a omega-scan et omega-stress pour le TUI de CHECK. Lecture du code source de omega-scan a confirme que tout le systeme de theme (`domain/theme/{models,policies,service}.py`, catalogue de 10 themes TUI + 5 themes d'export) et de detection terminal (`domain/terminal/*`, `infrastructure/terminal/*`, ports `terminal_detector`/`settings_store`) est deja explicitement documente dans son propre code comme "identique a omega-stress" / "porte depuis omega-stress" — aucune logique specifique a omega-scan n'y figure. Copier ce systeme une 3e fois dans CHECK aurait ete exactement le scenario que D-002/D-005 anticipaient : mutualiser des qu'un vrai 2e/3e point de comparaison confirme qu'un module est reellement partage.

**Decision** : ce systeme est deplace dans `omega-lib` plutot que recopie dans CHECK :
- `omega_lib.theme.{models,policies,service}` — catalogue de themes (`TUI_THEMES`, `EXPORT_PALETTES`), degradation par profil de rendu.
- `omega_lib.terminal.{models,policies,service}` — `RenderProfile`, resolution du profil de rendu.
- `omega_lib.ports.{terminal_detector,settings_store}` — contrats.
- `omega_lib.infrastructure.terminal.{raw_capabilities,fallback_resolver,detector}` — detection reelle du terminal (env vars, taille), 100% independante de l'outil.

CHECK re-exporte les 2 ports sous `omega_check.ports.*` (meme convention que `core/enums.py::ConfidenceLevel`, D-005) et importe le reste directement depuis `omega_lib`. `omega-scan`/`omega-stress` NE SONT PAS retouches (ils gardent leurs propres copies locales identiques) — migrer du code deja fini et valide n'est pas fait sans demande explicite (voir [[git-ownership-dev-projects]] et le principe general de cette session : ne pas toucher aux outils finis en passant).

**Alternative ecartee** : recopier le systeme une 3e fois dans `omega_check/domain/theme` et `omega_check/domain/terminal` en suivant l'organisation d'omega-scan a l'identique. Rejetee : le module lui-meme documente deja qu'il doit rester synchronise entre outils, une 3e copie aurait immediatement re-cree le probleme que D-002 memorise pour l'extraction HTML.

**Impact** : `omega-lib` passe de "core/+shared/ uniquement" (D-005) a un perimetre elargi. `OMEGA-SUITE_ARBORESCENCE.md` §1 devra etre mis a jour pour refleter ce nouveau contenu la prochaine fois qu'il est relu attentivement. Quand omega-deep/omega-fold construiront leur propre TUI, ils consommeront directement `omega_lib.theme`/`omega_lib.terminal` sans avoir a se poser la question.

**Artwork du splash/wordmark** : le logo ASCII dessine lettre par lettre d'omega-scan est explicitement documente comme fourni par l'utilisateur pour CE tool (pas un patron reutilisable) et utilise des glyphes (C, H, K) absents de son propre alphabet dessine — reproduire "OMEGA-CHECK" a l'identique aurait exige d'inventer de nouveaux glyphes a l'aveugle, sans verification visuelle possible dans cet environnement. `widgets/splash_hero.py` et `widgets/home_wordmark.py` de CHECK utilisent donc un texte simple avec le meme mecanisme de jetons de theme reactifs ($accent/$foreground/$secondary) — la mecanique de theming est identique, l'artwork est un placeholder que l'utilisateur peut remplacer.

**Perimetre du TUI de CHECK par rapport a omega-scan, a la livraison initiale (2026-08-29)** — **corrige depuis** par un round de retour utilisateur en conditions reelles le meme jour, les 3 ecarts ci-dessous n'existent plus :
- ~~Pas d'ecran "Cibles"/pinning~~ -> ajoute (`TargetsScreen`, carnet d'adresses simple, sans notion d'autorisation contrairement a omega-scan — CHECK n'a toujours pas ce garde-fou, juste une commodite de saisie).
- ~~Pas de gestion de profils depuis le TUI~~ -> ajoute (`ProfilesScreen`, cree/modifie/supprime des profils utilisateur, epaulé par un profil `CUSTOM` cumulant profil enregistre + saisie libre de ports dans l'ecran Scanner).
- ~~Pas de relai de log en direct pendant le scan~~ -> ajoute (logger `omega_check.scan`, handler relais attache le temps du scan, memes mecanique/raison qu'omega-scan).

Le detail complet de ce round (bugs corriges, ameliorations d'ecran, theme HTML enrichi) vit dans `OMEGA-CHECK_PLAN_DEV-complet.md`, pas ici — cette entree ne gardait qu'un etat perime.

---

## D-009 — TUI de DEEP : oubli de la scission CHECK/DEEP, corrige

**Date** : 2026-08-30
**Outils concernes** : DEEP (correction), CHECK (reference), SUITE (vision d'ensemble, clarifiee)

**Contexte** : CHECK et DEEP etaient a l'origine prevus comme **une seule
application**, scindee plus tard en deux outils distincts (CHECK = scan
fixe mono-cible, DEEP = analyse multi-cibles avec decouverte). Cette
scission n'a jamais ete reportee dans les documents de planification de
DEEP (`OMEGA-DEEP_{SPECIFICATIONS,PLAN_DEV,ARBORESCENCE}.md`,
`ROADMAP_OMEGA-DEEP.md`) ni dans ce journal — resultat : le plan de DEEP
ne mentionnait qu'une CLI (Phase 6.4), sans aucune phase TUI, ce qui
donnait l'impression d'un choix delibere alors que c'etait un oubli de la
scission. Confirme explicitement par l'utilisateur apres la fin de la
Phase 6 de DEEP (CLI complete et fonctionnelle, verifiee en conditions
reelles).

**Decision** : DEEP recoit une phase TUI, au meme titre que CHECK
(reutilisation directe de `omega_lib.theme`/`omega_lib.terminal`, D-008 —
aucune nouvelle question de mutualisation a se poser, deja tranchee).
Perimetre attendu, par analogie avec les ecrans de CHECK : accueil,
formulaire d'analyse (cible + profil + `--max-depth`/`--max-targets`/
`--subnet` en equivalents-champs), ecran de validation des cibles
decouvertes (remplace les prompts `input()` de `analyze_command.py` — le
flux d'etats PROPOSED/PRESENTED/ACCEPTED/REJECTED de D-003 s'y prete
directement), detail d'un scan (avec graphe), historique, reglages.

**Clarification de vision (vue d'ensemble, deja presente dans
`OMEGA-SUITE_SPECIFICATIONS.md`/`ROADMAP_OMEGA-SUITE.md` mais reaffirmee
explicitement par l'utilisateur)** : le but final de la suite est une
application unique ou chaque outil `omega-*` tourne comme un onglet/mode,
pas cinq CLI/TUI durablement separes — chaque outil reste executable en
autonome d'ici la (voir `OMEGA-SUITE_ARBORESCENCE.md`, "facade
additionnelle, pas un remplacement"). Consequence immediate pour DEEP :
son export d'architecture doit produire un **vrai schema/diagramme
exportable au format HTML**, pas seulement un tableau des relations
source/type/cible — `OMEGA-DEEP_SPECIFICATIONS.md` §9 le disait deja
("HTML : ... avec visualisation du graphe"), la premiere implementation
(round Phase 6) n'a livre qu'un tableau, sous-livrant cette exigence.

**Alternative ecartee** : laisser DEEP en CLI seule "puisque son plan ne
demandait pas de TUI" — rejetee des lors que l'origine de cette absence
(oubli de scission, pas choix delibere) est etablie.

**Impact** : `OMEGA-DEEP_PLAN_DEV.md`/`SPECIFICATIONS.md`/`ROADMAP_OMEGA-DEEP.md`
a mettre a jour pour ajouter la phase TUI explicitement. L'export HTML de
DEEP (`infrastructure/exporters/html_exporter.py` + template) a revoir
pour un rendu de graphe reel (ex. SVG genere a la main — le graphe reste
petit, pas besoin d'une dependance de layout de graphe lourde comme
graphviz) plutot que le tableau actuel.

---

## D-010 — FOLD : garde-fous de crawl en domain/, port DistantCrawler rendu async

**Date** : 2026-08-31
**Outils concernes** : FOLD (les deux), DEEP (precedent invoque pour la premiere)

**Contexte 1 (emplacement des garde-fous de crawl)** : `OMEGA-FOLD_ARBORESCENCE.md`
§2 placait les garde-fous de crawl distant (profondeur/nombre de
pages/delai/robots.txt) dans `application/pipeline/guards/crawl_guard.py`
— un sous-package `application/pipeline/` qui n'existe chez aucun autre
outil de la suite (CHECK, DEEP). Au moment d'implementer les Phases 2+3
de FOLD, le precedent direct le plus proche s'est avere etre
`omega_deep.domain.discovery.policies` : memes garde-fous purs (aucune
E/S), meme besoin de les tester sans reseau, deja en production.

**Decision 1** : les garde-fous de crawl de FOLD (`is_depth_allowed`,
`is_page_count_allowed`, `is_same_domain`) vivent dans
`domain/scans/policies.py`, pas `application/pipeline/guards/`. Aucun
`application/pipeline/` n'est cree. `OMEGA-FOLD_ARBORESCENCE.md` a mettre
a jour en consequence.

**Contexte 2 (port DistantCrawler)** : la Phase 1 de FOLD (fondations)
avait pose `ports/distant_crawler.py::DistantCrawler.fetch` comme une
methode synchrone, par erreur — `aiohttp` (impose par
`OMEGA-FOLD_ARBORESCENCE.md` §5 pour le crawl) est fondamentalement
asynchrone, une implementation reelle ne peut pas respecter un contrat
sync sans un bridge artificiel.

**Decision 2** : `DistantCrawler.fetch` devient `async def`, revise avant
meme sa premiere implementation reelle (Phase 3) — meme genre de
revision de port assumee que `save_host` -> `save_hosts` chez DEEP en
cours de Phase 6. `robots.txt` (fetch + parsing) est verifie DANS
l'implementation (`infrastructure/network/aiohttp_crawler.py`), pas par
l'appelant : c'est la meme nature d'E/S que recuperer la page elle-meme,
seule exception au principe "l'appelant orchestre tout" du port.

**Alternative ecartee** : garder `application/pipeline/` pour rester
fidele a `ARBORESCENCE.md` au prix d'un sous-package sans equivalent
ailleurs dans la suite — rejetee, la coherence inter-outils l'emporte sur
un document de planification ecrit avant que le premier outil de la
suite (CHECK) n'ait fixe le gabarit reel a 9 couches.

**Impact** : `OMEGA-FOLD_ARBORESCENCE.md` §2 corrige (retire
`application/pipeline/`, `application/dto/` ; deplace les garde-fous vers
`domain/scans/policies.py` ; signature async de `DistantCrawler.fetch`
et ajout de `read_file` a `LocalFsReader` documentes).

---

## D-011 — FOLD : schema SQLite simplifie (files/links seuls), arbre et stats recalcules a la lecture

**Date** : 2026-08-31
**Outils concernes** : FOLD

**Contexte** : `OMEGA-FOLD_SPECIFICATIONS.md` §7.1 decrit 7 tables SQLite
(`scans`/`files`/`dirs`/`links`/`extension_stats`/`family_stats`/
`top_files`/`external_domains`). Au moment d'implementer Phases 4+5,
`domain/tree/service.py::build_tree` et `domain/stats/service.py::
compute_*` (Phase 2) sont deja des fonctions pures capables de
reconstruire integralement `DirEntry` (l'arbre imbrique) et toutes les
statistiques a partir d'une simple liste `files`+`links` — stocker les
resultats intermediaires en plus des donnees source aurait cree une
duplication avec un risque reel de divergence (un bug de recalcul cote
ecriture ne serait jamais rattrape, les deux versions coexisteraient
silencieusement).

**Decision** : `infrastructure/storage/sqlite/schema.py` ne definit que
3 tables (`scans`/`files`/`links`). `SqliteScanRepository.save_result`
aplatit `ScanResult.root_dir` via `domain/tree/service.py::flatten_files`
avant d'ecrire (delete-then-insert par `scan_id`, meme raisonnement que
`save_hosts` de DEEP — pas de `ON DELETE CASCADE` fiable par defaut).
`get_result` relit `files`+`links` puis rappelle `build_tree`+`compute_*`
a chaque lecture plutot que de stocker leur resultat.

**Alternative ecartee** : suivre le schema §7.1 a la lettre (7 tables) —
rejetee, la duplication stockage/calcul n'apporte aucun gain de
performance mesurable a l'echelle d'un scan FOLD (quelques milliers de
fichiers au plus) et introduit une source de bugs de synchronisation
sans contrepartie.

**Impact** : `OMEGA-FOLD_SPECIFICATIONS.md` §7.1 reste la reference du
modele de donnees "riche" mais n'est plus le schema SQL litteral (meme
tolerance D-001 que le reste des specs deja obsoletes en vocabulaire).
Tout futur outil de la suite face au meme choix (donnees source pures +
fonctions de reconstruction deja pures et testees) devrait envisager la
meme simplification plutot que de stocker un cache derive.

---

## D-012 — OMEGA-TRACK rejoint la suite comme 6e outil

**Date** : 2026-09-06
**Outils concernes** : TRACK (nouveau), SUITE (roadmap/sequencement mis a jour)

**Contexte** : `OMEGA_TRACK_PLAN_DEVELOPPEMENT.md` (`~/DEV/TRACK/`) a ete redige puis corrige pour aligner son architecture sur D-000/D-001/D-005/D-006/D-008 (9 couches dont `shared/`, `ConfidenceLevel` reexporte depuis `omega_lib.core.confidence` plutot que redefini, `omega-lib` installe des sa Phase 1, colonne `tool` sur `track_runs`, raccourcis clavier TUI alignes sur CHECK). Il n'apparaissait cependant dans aucun document `OMEGA-SUITE_*` ni dans le sequencement D-004 (CHECK -> DEEP -> FOLD -> SUITE) — un outil peut difficilement etre "coherent avec l'avenir de la suite" (raison d'etre de ce journal) s'il n'est meme pas mentionne comme faisant partie de cet avenir.

**Decision** : OMEGA-TRACK rejoint la suite comme 6e outil, aux memes conditions que les 5 autres — Clean Architecture 9 couches, dependance `omega-lib` des sa Phase 1, futur onglet `omega-suite track` (vision D-009 : une application unique, chaque outil en onglet, chacun restant executable en autonome d'ici la). Sequencement (D-004 etendu) : TRACK se developpe apres FOLD — le principe "un outil termine avant de commencer le suivant" reste la regle, TRACK n'a pas de raison de le court-circuiter juste parce que son document de planification a ete ecrit/corrige plus tot. TRACK peut chevaucher SUITE de la meme facon que FOLD le peut deja avec DEEP (deux developpements independants l'un de l'autre). Le contenu du plan de dev de TRACK lui-meme reste correct en l'etat — cette entree ne change que sa place dans le calendrier global, pas son contenu technique.

**Alternative ecartee** : garder TRACK en outil satellite hors suite unifiee, au meme titre qu'omega-fire (jamais prevu pour rejoindre l'app unique car il agit sur la machine locale, pas sur une cible distante — decision anterieure documentee dans la memoire de session omega-serv). Ecartee : TRACK observe des cibles distantes (IP/domaine) et complete explicitement CHECK/SCAN/DEEP dans sa propre mission — meme famille que les 5 outils deja dans la suite, pas une exception comme omega-fire.

**Impact** : `ROADMAP_OMEGA-SUITE.md`, `OMEGA-SUITE_SPECIFICATIONS.md`, `OMEGA-SUITE_PLAN_DEV.md`, `OMEGA-SUITE_ARBORESCENCE.md` mis a jour partout ou les 5 outils sont enumeres a titre de vision/cible future — jamais dans une section decrivant une phase deja terminee (ex. Phase 1 SUITE "uniformiser omega-scan et omega-stress", historique, non retouchee : TRACK n'existait pas a ce moment-la et ne peut pas retroactivement en avoir fait partie).

---

## D-013 — OMEGA-SCAN migre sur omega-lib, cloture la reserve de D-008

**Date** : 2026-09-07
**Outils concernes** : SCAN (migre), LIB/omega-lib (aucun changement de code, juste devenu le seul point de verite)

**Contexte** : D-008 avait deja constate que le catalogue de themes/detection
terminal de SCAN et STRESS etait identique a celui extrait dans `omega-lib`,
mais avait explicitement choisi de ne pas y toucher : *"migrer du code deja
fini et valide n'est pas fait sans demande explicite"*. STRESS a ete migre
depuis (constate au code, aucune trace de decision dediee retrouvee) et ne
possede plus aucune copie locale de `domain/theme`/`domain/terminal`. SCAN
restait le seul outil du perimetre (CHECK/DEEP/FOLD/FUZZ/STRESS/TRACK/SCAN,
omega-fire/omega-serv/omega-waf/omega-log explicitement hors perimetre) a
n'avoir aucune dependance `omega-lib` : il portait toujours sa copie
d'origine (`domain/theme/{models,policies,service}.py`,
`domain/terminal/{models,policies,service}.py`,
`infrastructure/terminal/{detector,fallback_resolver,raw_capabilities}.py`,
`ports/{terminal_detector,settings_store}.py` locaux, `RenderProfile`
redefini dans `core/enums.py`). L'utilisateur a formule la demande explicite
qui manquait : plus aucun nouvel outil prevu (omega-serv en pause), et
omega-suite sera le point d'integration final consommant cette bibliotheque
— elle doit etre coherente et identique partout des maintenant.

**Decision** : SCAN migre sur `omega-lib` en reproduisant exactement le
patron deja eprouve par CHECK/TRACK (D-005/D-008) — reexport sous
`omega_scan.ports.{terminal_detector,settings_store}` et
`omega_scan.core.enums.RenderProfile` (meme geste que `ConfidenceLevel`),
import direct d'`omega_lib.theme.*`/`omega_lib.terminal.*`/
`omega_lib.infrastructure.terminal.*` partout ailleurs, suppression pure des
3 dossiers dupliques (contenu verifie identique caractere pour caractere par
diff direct avant suppression, aucune fusion de logique divergente
necessaire). `install.sh`/`pyproject.toml` alignes sur le patron
vendor/omega-lib deja utilise par CHECK/DEEP/FOLD/FUZZ. Suite complete
revalidee apres coup : 166/166 tests (verts des le premier passage, sans
aucune correction de logique — seulement des imports), ruff/mypy/
import-linter propres.

**Alternative ecartee** : ne migrer que la donnee (palette/terminal) et
laisser SCAN garder ses propres Protocols `SettingsStore`/`TerminalDetector`
locaux — ecartee, ces Protocols sont deja dans `omega_lib.ports` avec la
meme forme exacte (D-008 les y avait deja places), les dupliquer aussi
aurait laisse une incoherence partielle au lieu de resoudre le probleme
signale par l'utilisateur ("bibliotheque coherente et iso a date").

**Impact** : `omega-lib` est desormais le point de verite unique du
theme/terminal pour les 7 outils du perimetre (CHECK/DEEP/FOLD/FUZZ/STRESS/
TRACK/SCAN) — plus aucune copie locale nulle part, verifie par recherche
directe dans chaque depot avant cette entree. `~/DEV/SCAN/dist/omega-scan.tar.gz`
existant est desormais perime (code source change, pas de `build-release.sh`
chez SCAN pour le reconstruire automatiquement) — signale a l'utilisateur,
pas reconstruit dans le cadre de cette entree. `OMEGA-SUITE_ARBORESCENCE.md`
§1 mis a jour dans la foulee (voir plus bas) pour refleter le contenu reel
actuel d'omega-lib, comme D-008 l'annonçait deja.

---

## Gabarit pour une nouvelle entree

```
## D-00X — Titre court

**Date** :
**Outils concernes** :

**Contexte** :

**Decision** :

**Alternative ecartee** :

**Impact** :
```
