# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Lecture HTTPS de download/sha.txt du site (verification MANUELLE des mises a jour, repris
d'omega-log / omega-serv 2.6.0) : un GET, bibliotheque standard seulement (urllib). Certificat
verifie, 5 s au plus, 64 Kio lus au plus ; ne leve jamais : tout echec donne None. Rien n'est
envoye d'autre que la requete elle-meme (User-Agent avec la version)."""
from __future__ import annotations

import urllib.error
import urllib.request

from omega_lib.declaration.policies import sha_list_url

TIMEOUT_SECONDS = 5.0
MAX_BYTES = 64 * 1024


class HttpsReleaseSource:
    def __init__(self, software: str, version: str, url: str | None = None,
                 timeout: float = TIMEOUT_SECONDS) -> None:
        self._user_agent = f"{software}/{version}"
        self._url = url if url is not None else sha_list_url(software)
        self._timeout = timeout

    def fetch_sha_list(self) -> str | None:
        request = urllib.request.Request(self._url, headers={"User-Agent": self._user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                if not 200 <= response.status < 300:
                    return None
                body: bytes = response.read(MAX_BYTES)
                return body.decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError, ValueError):
            return None
