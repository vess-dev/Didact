"""The HTTP side of `didact serve`: a threading stdlib server, a small router, and its guards.

- The Host header must name this server (localhost, 127.0.0.1, [::1] or the bound address,
  with the right port), which defeats DNS rebinding.
- Every POST must come from this site (Origin, Sec-Fetch-Site) and carry the CSRF token: a
  random per-server secret sent in each form and checked against a SameSite=Strict,
  HttpOnly cookie.
- Static files are served by exact name from the package's own folder; responses forbid
  framing and MIME sniffing, and send no CORS headers.
"""

import contextlib
import hmac
import ipaddress
import socket
import socketserver
import sys
import traceback
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from didact.core import i18n
from didact.core.errors import UsageError
from didact.core.i18n import _
from didact.web.app import App, Request, Response
from didact.web.layout import LANGUAGE_COOKIE
from didact.web.pages import ROUTES, not_found
from didact.web.static import assets, version

MAX_BODY = 4_000_000
LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})
WILDCARDS = frozenset({"0.0.0.0", "::", ""})
POLICY = (
    "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)
SECURITY_HEADERS = (
    ("Content-Security-Policy", POLICY),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "same-origin"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
)


# ---------------------------------------------------------------------------- guards


def split_host(value: str) -> tuple[str, int | None] | None:
    """`localhost:8765` → ("localhost", 8765), `[::1]:80` → ("::1", 80); None if garbled."""
    text = value.strip().lower()
    if text.startswith("["):
        end = text.find("]")
        if end < 0:
            return None
        name, rest = text[1:end], text[end + 1 :]
    elif text.count(":") == 1:
        name, _, port = text.partition(":")
        rest = f":{port}"
    elif ":" in text:
        return None  # an IPv6 address must be in brackets
    else:
        name, rest = text, ""
    if not rest:
        return name, None
    if not rest.startswith(":") or not rest[1:].isdigit():
        return None
    return name, int(rest[1:])


def host_allowed(value: str | None, bound: str, port: int) -> bool:
    """Is this Host header one of ours? Loopback names or the bound address, right port.

    Bound to every address (0.0.0.0 or ::), any IP address is fine too: DNS rebinding needs
    a domain name, and other machines reach the app by address.
    """
    parts = split_host(value or "")
    if parts is None or not parts[0]:
        return False
    name, given = parts
    if given != port and not (given is None and port == 80):
        return False
    bound_name = bound.strip("[]").lower()
    if name in LOOPBACK_NAMES or name == bound_name:
        return True
    if bound_name in WILDCARDS:
        with contextlib.suppress(ValueError):
            ipaddress.ip_address(name)
            return True
    return False


def same_site(headers: dict[str, str], bound: str, port: int) -> bool:
    """A POST must come from our own pages (browsers say where a request comes from)."""
    site = headers.get("sec-fetch-site")
    if site is not None and site not in ("same-origin", "none"):
        return False
    origin = headers.get("origin")
    if origin is None:
        return True  # an older browser or a tool: the CSRF token still has to match
    parts = urlsplit(origin)
    return parts.scheme == "http" and host_allowed(parts.netloc, bound, port)


def token_ok(sent: str, cookie: str | None, secret: str) -> bool:
    if not sent or not cookie:
        return False
    return hmac.compare_digest(sent, secret) and hmac.compare_digest(cookie, secret)


def is_loopback(host: str) -> bool:
    name = host.strip("[]").lower()
    if name == "localhost":
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


# ---------------------------------------------------------------------------- the server


class WebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, app: App, host: str, port: int) -> None:
        self.app = app
        self.host = host.strip("[]") or "0.0.0.0"
        self.address_family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        super().__init__((self.host, port), Handler)

    def handle_error(self, request: object, client_address: object) -> None:
        if isinstance(sys.exception(), ConnectionError | TimeoutError):
            return  # the browser went away or kept a connection open too long: nothing wrong
        self.app.report(traceback.format_exc())

    def server_bind(self) -> None:
        # HTTPServer would look the host's name up (slow on some machines, and unused).
        socketserver.TCPServer.server_bind(self)
        address = self.socket.getsockname()
        self.server_name = self.host
        self.server_port = int(address[1])
        self.app.port = self.server_port

    @property
    def url(self) -> str:
        name = "127.0.0.1" if self.host in WILDCARDS else self.host
        return f"http://{f'[{name}]' if ':' in name else name}:{self.app.port}/"


class Handler(BaseHTTPRequestHandler):
    server: WebServer
    timeout = 60  # an idle keep-alive connection lets its thread go after this long
    protocol_version = "HTTP/1.1"
    server_version = "Didact"
    sys_version = ""

    def do_GET(self) -> None:
        self._handle("GET")

    def do_HEAD(self) -> None:
        self._handle("HEAD")

    def do_POST(self) -> None:
        self._handle("POST")

    def log_message(self, format: str, *args: object) -> None:
        return  # quiet: the terminal shows the URL and errors only

    def _handle(self, method: str) -> None:
        with i18n.use(self._language()):
            try:
                response = self._respond(method)
            except Exception:
                self.server.app.report(traceback.format_exc())
                response = Response.text(
                    _("Something went wrong: see the terminal running didact."), 500
                )
        self._send(response, head=method == "HEAD")

    def _respond(self, method: str) -> Response:
        app = self.server.app
        headers = {k.lower(): v for k, v in self.headers.items()}
        form: dict[str, list[str]] = {}
        if method == "POST":
            body = self._body()
            if body is None:
                return Response.text(_("That request is too large."), 413)
            ctype = headers.get("content-type", "").partition(";")[0].strip().lower()
            if ctype not in ("application/x-www-form-urlencoded", ""):
                return Response.text(_("Forms only."), 415)
            form = parse_qs(body, keep_blank_values=True, max_num_fields=2000)
        if not host_allowed(headers.get("host"), self.server.host, app.port):
            return Response.text(_("Unknown host: open this app at its own address."), 403)
        cookies = _cookies(headers.get("cookie", ""))
        if method == "POST":
            if not same_site(headers, self.server.host, app.port):
                return Response.text(_("Refused: that form didn't come from this app."), 403)
            sent = (form.get("csrf") or [""])[0]
            if not token_ok(sent, cookies.get(app.csrf_cookie), app.secret):
                return Response.text(
                    _("The form is out of date: reload the page and try again."), 403
                )
        parts = urlsplit(self.path)
        if parts.path.startswith("/static/"):
            return _static(parts.path.removeprefix("/static/"), parse_qs(parts.query))
        query = parse_qs(parts.query, keep_blank_values=True, max_num_fields=200)
        want = "GET" if method == "HEAD" else method
        allowed = False
        for route in ROUTES:
            match = route.pattern.fullmatch(parts.path)
            if match is None:
                continue
            if route.method != want:
                allowed = True
                continue
            params = {k: unquote(v) for k, v in match.groupdict().items()}
            return route.handler(Request(app, method, parts.path, query, form, cookies, params))
        if allowed:
            refused = Response.text(_("That page can't do that."), 405)
            refused.headers.append(("Allow", "GET, HEAD, POST"))
            return refused
        return not_found(Request(app, method, parts.path, query, form, cookies))

    def _language(self) -> str:
        """The language chosen in Settings (a cookie), else the browser's."""
        chosen = _cookies(self.headers.get("Cookie") or "").get(LANGUAGE_COOKIE, "")
        if chosen in i18n.LANGUAGES:
            return chosen
        return i18n.negotiate(self.headers.get("Accept-Language") or "")

    def _body(self) -> str | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self.close_connection = True
            return None
        return self.rfile.read(length).decode("utf-8", errors="replace") if length else ""

    def _send(self, response: Response, *, head: bool) -> None:
        app = self.server.app
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        own = {name for name, _ in response.headers}  # a page may set its own policy
        for name, value in SECURITY_HEADERS:
            if name not in own:
                self.send_header(name, value)
        if not any(name == "Cache-Control" for name, _value in response.headers):
            self.send_header("Cache-Control", "no-store")
        for name, value in response.headers:
            self.send_header(name, value)
        if response.content_type.startswith("text/html"):
            self.send_header(
                "Set-Cookie", f"{app.csrf_cookie}={app.secret}; Path=/; HttpOnly; SameSite=Strict"
            )
        self.end_headers()
        if not head:
            self.wfile.write(response.body)


def _cookies(header: str) -> dict[str, str]:
    """Cookies by name (read plainly: other apps on localhost may set odd ones)."""
    found: dict[str, str] = {}
    for part in header.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name:
            found.setdefault(name, value.strip().strip('"'))
    return found


def _static(name: str, query: dict[str, list[str]]) -> Response:
    asset = assets().get(unquote(name))
    if asset is None:
        return Response.text(_("No such file."), 404)
    fresh = query.get("v") == [version()]
    cache = "public, max-age=31536000, immutable" if fresh else "no-cache"
    return Response(asset.body, 200, asset.content_type, [("Cache-Control", cache)])


# ---------------------------------------------------------------------------- serve


def startup_lines(url: str, host: str) -> list[str]:
    lines = [_("Didact is open at {url}", url=url)]
    if not is_loopback(host):
        lines.append(
            _(
                "warning: listening on {host}: other machines on the network can reach this app "
                "and change your library. Use it only on a network you trust.",
                host=host or "0.0.0.0",
            )
        )
    lines.append(_("Ctrl-C stops it."))
    return lines


def serve(
    *,
    home: str | None = None,
    world: str | None = None,
    campaign: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
    gm: bool = False,
    say: Callable[[str], None],
    report: Callable[[str], None] | None = None,
) -> None:
    """Serve the library until Ctrl-C. `say` gets the address, `report` any errors."""
    app = App(home=home, world=world, campaign=campaign, gm=gm, report=report or say)
    try:
        server = WebServer(app, host, port)
    except OSError as exc:
        raise UsageError(
            _(
                "can't listen on {host}:{port}: {error}",
                host=host,
                port=port,
                error=exc.strerror or exc,
            ),
            hint=_("another program may be using that port: try `didact serve --port 8766`"),
        ) from exc
    for line in startup_lines(server.url, host):
        say(line)
    if open_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
