# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Aide -> « Contact et support », partage par les outils omega (D-016, 2026-11-09).

Repris d'omega-serv 2.6.0 / omega-log 1.6.0 (OMEGA-SERV_ETUDE_TELEMETRIE.md §3b) : payer un cafe,
se declarer utilisateur anonyme (UNE SEULE FOIS : aucun de ces outils n'a de service permanent,
decision utilisateur 2026-11-09, comme omega-log), contacter le support, verifier les mises a jour.

- `models` / `policies` / `countries` : purs, aucune I/O ;
- `service` : cas d'usage (declarer, retirer, verifier une mise a jour) ;
- ports dans `omega_lib.ports.declaration`, adaptateurs dans `omega_lib.infrastructure.declaration`,
  ecrans Textual dans `omega_lib.interfaces.tui.contact_support`."""
