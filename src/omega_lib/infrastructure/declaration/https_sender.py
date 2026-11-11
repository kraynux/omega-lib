# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Envoi d'une declaration anonyme : un POST HTTPS, bibliotheque standard seulement (urllib) -
repris d'omega-log / omega-serv. Certificat verifie (contexte par defaut), 5 s au plus pour la
connexion et la reponse. Ne leve jamais : tout echec devient un SendOutcome. Appele dans un fil
de travail par l'ecran (l'interface ne se fige jamais)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from omega_lib.declaration.models import RECEPTION_URL
from omega_lib.ports.declaration import SendOutcome

TIMEOUT_SECONDS = 5.0


class HttpsDeclarationSender:
    def __init__(self, software: str, version: str, url: str = RECEPTION_URL,
                 timeout: float = TIMEOUT_SECONDS) -> None:
        self._user_agent = f"{software}/{version}"
        self._url = url
        self._timeout = timeout

    def send(self, payload: dict[str, object]) -> SendOutcome:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self._url, data=body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": self._user_agent},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            return SendOutcome(False, f"http-{error.code}")
        except (urllib.error.URLError, OSError, ValueError):
            return SendOutcome(False, "unreachable")
        if 200 <= status < 300:
            return SendOutcome(True)
        return SendOutcome(False, f"http-{status}")
