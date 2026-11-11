# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ouvrir une adresse web (PayPal, formulaire de contact, nouveautes) dans le navigateur de
l'utilisateur - partage par les outils omega (D-016, 2026-11-09 ; memoire « module a reprendre
dans la suite »).

Repris tel quel d'omega-log (infrastructure/desktop/browser_opener.py), lui-meme porte
d'omega-fire (valide en reel 6.5, 2026-10-28) : si l'interface tourne en root (sudo), le
navigateur est lance AU NOM de SUDO_USER, avec les variables de sa session graphique relevees
dans /proc/<pid>/environ (repli /run/user/<uid>, /tmp/.X11-unix) ; NAVIGATEUR WEB par defaut
(xdg-settings + gio launch), repli xdg-open ; sorties vers /dev/null, jamais un tube (SIGPIPE
tuait Firefox). Une adresse web, jamais un fichier. Sans session graphique (SSH, serveur), rien
n'est lance : l'appelant affiche l'adresse a la place."""
from __future__ import annotations

import os
import pwd
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_SESSION_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR",
                 "XDG_DATA_DIRS", "XDG_DATA_HOME", "XDG_CONFIG_DIRS",
                 "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE", "DESKTOP_SESSION")
_WAIT_SECONDS = 4.0


@dataclass(frozen=True)
class OpenResult:
    ok: bool
    reason: str = ""          # "no_session", "no_xdg_open", "failed"
    detail: str = ""
    opened_path: str = ""


@dataclass(frozen=True)
class _Target:
    name: str
    uid: int
    gid: int
    home: str


def _target_user() -> _Target | None:
    """Utilisateur au nom duquel ouvrir : SUDO_USER si on est root via sudo, sinon soi."""
    if os.geteuid() == 0:
        name = os.environ.get("SUDO_USER") or ""
        if not name or name == "root":
            return None
        try:
            entry = pwd.getpwnam(name)
        except KeyError:
            return None
    else:
        entry = pwd.getpwuid(os.geteuid())
    return _Target(entry.pw_name, entry.pw_uid, entry.pw_gid, entry.pw_dir)


def _environ_of(environ_file: Path) -> dict[str, str]:
    """Format /proc/<pid>/environ : KEY=VALUE separes par des octets nuls."""
    try:
        raw = environ_file.read_bytes()
    except OSError:
        return {}
    env: dict[str, str] = {}
    for item in raw.split(b"\0"):
        key, sep, value = item.partition(b"=")
        if sep:
            env[key.decode(errors="ignore")] = value.decode(errors="ignore")
    return env


def session_environment(uid: int, current: dict[str, str] | None = None,
                        proc_dir: Path = Path("/proc"), run_dir: Path = Path("/run/user"),
                        x11_dir: Path = Path("/tmp/.X11-unix")) -> dict[str, str]:
    """Variables de la session graphique de `uid`. Vide si aucune session trouvee."""
    current = current if current is not None else dict(os.environ)
    session = {key: current[key] for key in _SESSION_KEYS if current.get(key)}
    if (session.get("DISPLAY") or session.get("WAYLAND_DISPLAY")) and session.get("DBUS_SESSION_BUS_ADDRESS"):
        return session
    # Un processus de l'utilisateur qui porte la session (navigateur, bureau, terminal).
    try:
        pids = [entry.name for entry in proc_dir.iterdir() if entry.name.isdigit()]
    except OSError:
        pids = []
    for pid in pids:
        try:
            if (proc_dir / pid).stat().st_uid != uid:
                continue
        except OSError:
            continue
        env = _environ_of(proc_dir / pid / "environ")
        if (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY")) and env.get("DBUS_SESSION_BUS_ADDRESS"):
            return {key: env[key] for key in _SESSION_KEYS if env.get(key)}
    # Repli : sockets connus.
    runtime = run_dir / str(uid)
    if runtime.is_dir():
        session.setdefault("XDG_RUNTIME_DIR", str(runtime))
        if (runtime / "bus").exists():
            session.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime / 'bus'}")
        if not session.get("WAYLAND_DISPLAY"):
            wayland = sorted(p.name for p in runtime.glob("wayland-*") if not p.name.endswith(".lock"))
            if wayland:
                session["WAYLAND_DISPLAY"] = wayland[0]
    if not session.get("DISPLAY"):
        sockets = sorted(x11_dir.glob("X*")) if x11_dir.is_dir() else []
        if sockets:
            session["DISPLAY"] = ":" + sockets[0].name[1:]
    if not (session.get("DISPLAY") or session.get("WAYLAND_DISPLAY")):
        return {}
    return session


def open_in_browser(url: str) -> OpenResult:
    target = _target_user()
    if target is None:
        return OpenResult(False, "no_session", "SUDO_USER")
    xdg_open = shutil.which("xdg-open")
    if xdg_open is None:
        return OpenResult(False, "no_xdg_open")
    session = session_environment(target.uid)
    if not session:
        return OpenResult(False, "no_session")

    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": target.home, "USER": target.name, "LOGNAME": target.name,
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        **session,
    }
    kwargs: dict = {}
    if os.geteuid() != target.uid:
        kwargs.update(user=target.uid, group=target.gid, extra_groups=os.getgrouplist(target.name, target.gid))
    cwd = target.home if os.path.isdir(target.home) else "/"

    # Le NAVIGATEUR WEB par defaut de l'utilisateur (retour utilisateur 2026-10-28, omega-fire).
    # Repli : xdg-open.
    desktop_file = default_browser_desktop_file(env, cwd, kwargs, target.home)
    gio = shutil.which("gio")
    if desktop_file is not None and gio is not None:
        result = _spawn([gio, "launch", str(desktop_file), url], env, cwd, kwargs)
        if result.ok:
            return OpenResult(True, opened_path=url)
    result = _spawn([xdg_open, url], env, cwd, kwargs)
    return OpenResult(result.ok, result.reason, result.detail, url if result.ok else "")


def _desktop_dirs(home: str, environ: dict[str, str]) -> list[Path]:
    data_home = environ.get("XDG_DATA_HOME") or f"{home}/.local/share"
    data_dirs = (environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    roots = [data_home, *data_dirs, f"{home}/.local/share/flatpak/exports/share", "/var/lib/flatpak/exports/share"]
    return [Path(root) / "applications" for root in roots if root]


def find_desktop_file(desktop_id: str, home: str, environ: dict[str, str] | None = None) -> Path | None:
    """Fichier .desktop d'un identifiant (ex. brave-browser.desktop), selon les dossiers XDG."""
    if not desktop_id.endswith(".desktop") or "/" in desktop_id:
        return None
    for folder in _desktop_dirs(home, environ if environ is not None else dict(os.environ)):
        candidate = folder / desktop_id
        if candidate.is_file():
            return candidate
    return None


def default_browser_desktop_file(env: dict[str, str], cwd: str, kwargs: dict, home: str) -> Path | None:
    """`xdg-settings get default-web-browser`, execute au nom de l'utilisateur (son reglage,
    pas celui de root). None si indisponible."""
    xdg_settings = shutil.which("xdg-settings")
    if xdg_settings is None:
        return None
    try:
        # Sortie lue par un tube : xdg-settings rend la main sans laisser de processus fils.
        completed = subprocess.run([xdg_settings, "get", "default-web-browser"], env=env, cwd=cwd,
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=5, check=False,
                                   **kwargs)
    except (OSError, subprocess.SubprocessError):
        return None
    desktop_id = completed.stdout.decode(errors="ignore").strip()
    if completed.returncode != 0 or not desktop_id:
        return None
    return find_desktop_file(desktop_id, home, env)


def _spawn(argv: list[str], env: dict[str, str], cwd: str, kwargs: dict) -> OpenResult:
    try:
        # Sorties vers /dev/null, JAMAIS un tube vers l'outil. Retour utilisateur
        # 2026-10-28 : avec stderr en tube, Firefox se fermait 3 a 5 s apres l'ouverture —
        # xdg-open rend la main, Firefox herite du tube ; au lancement de commande suivant
        # (rafraichissement du tableau de bord), Python libere le processus termine et ferme
        # le tube, et la premiere ecriture de Firefox sur stderr le tue (SIGPIPE).
        process = subprocess.Popen(
            argv, env=env, cwd=cwd,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, **kwargs,
        )
    except OSError as exc:
        return OpenResult(False, "failed", str(exc))
    try:
        returncode = process.wait(timeout=_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        # Le lanceur attend parfois le navigateur : il est lance, on le laisse tourner.
        return OpenResult(True)
    if returncode != 0:
        return OpenResult(False, "failed", str(returncode))  # code de sortie du lanceur
    return OpenResult(True)


def open_url(url: str) -> bool:
    """True si un navigateur a ete lance ; False sans session graphique (l'appelant affiche l'adresse)."""
    return open_in_browser(url).ok
