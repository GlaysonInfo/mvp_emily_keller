from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


SITE_ROOT = Path(__file__).resolve().parents[1] / "site"
PUBLIC_PAGES = {
    "/",
    "/monitoramento-de-equipamentos/",
    "/sistema-de-lubrificacao/",
    "/inteligencia-operacional/",
    "/eficiencia-industrial/",
    "/como-funciona/",
    "/demonstracao/",
    "/contato/",
    "/privacidade/",
    "/cookies/",
    "/termos/",
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []
        self.meta = []

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        if tag == "a" and "href" in attr_map:
            self.links.append(attr_map["href"])
        if tag == "link" and attr_map.get("rel") == "stylesheet":
            self.links.append(attr_map["href"])
        if tag == "img":
            self.images.append(attr_map)
        if tag == "meta":
            self.meta.append(attr_map)


def _html_files():
    return sorted(SITE_ROOT.glob("**/*.html"))


def _target_exists(path):
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc or path.startswith("mailto:") or path.startswith("#"):
        return True
    clean_path = parsed.path
    if clean_path == "/":
        return (SITE_ROOT / "index.html").exists()
    if clean_path.endswith("/"):
        return (SITE_ROOT / clean_path.strip("/") / "index.html").exists()
    return (SITE_ROOT / clean_path.lstrip("/")).exists()


def test_site_internal_links_resolve():
    broken = []
    for html_file in _html_files():
        parser = LinkParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        for link in parser.links:
            if not _target_exists(link):
                broken.append((html_file.relative_to(SITE_ROOT).as_posix(), link))

    assert broken == []


def test_public_pages_are_in_sitemap():
    sitemap = ET.parse(SITE_ROOT / "sitemap.xml")
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {
        urlparse(loc.text).path
        for loc in sitemap.findall(".//sm:loc", namespace)
        if loc.text
    }

    assert PUBLIC_PAGES.issubset(urls)
    assert "/acesso/" not in urls


def test_access_page_is_noindex():
    access_html = (SITE_ROOT / "acesso" / "index.html").read_text(encoding="utf-8")
    assert 'name="robots"' in access_html
    assert "noindex" in access_html


def test_access_page_exposes_local_profile_previews():
    access_html = (SITE_ROOT / "acesso" / "index.html").read_text(encoding="utf-8")

    assert "Entrar no Sistema" in access_html
    assert "Operador" in access_html
    assert "Tecnico" in access_html
    assert "Cliente Admin" in access_html
    assert "Admin do Sistema" in access_html
    assert "http://127.0.0.1:8502/" in access_html
    assert "http://127.0.0.1:8503/" in access_html
    assert "http://127.0.0.1:8505/" in access_html
    assert "http://127.0.0.1:8504/" in access_html
    assert 'data-local-target="http://127.0.0.1:8502/"' in access_html
    assert "local-auth-preview" in access_html


def test_access_page_starts_login_on_app_subdomain():
    access_html = (SITE_ROOT / "acesso" / "index.html").read_text(encoding="utf-8")

    assert "https://app.sentinelaindustrial.com.br/oauth2/start?rd=%2F" in access_html
    assert 'link.href = "https://app.sentinelaindustrial.com.br/oauth2/start?rd=%2F";' in access_html
    assert "Entrar como Operador" not in access_html
    assert "Entrar como Admin" not in access_html


def test_home_positions_operational_intelligence_and_efficiency():
    home_html = (SITE_ROOT / "index.html").read_text(encoding="utf-8")

    assert "Monitoramento da planta + lubrificação eficiente = inteligência operacional" in home_html
    assert "/monitoramento-de-equipamentos/" in home_html
    assert "/inteligencia-operacional/" in home_html
    assert "/eficiencia-industrial/" in home_html
    assert "hero-sentinela-inteligencia-operacional.png" in home_html


def test_home_uses_market_ready_commercial_copy():
    home_html = (SITE_ROOT / "index.html").read_text(encoding="utf-8").lower()

    forbidden_copy = {
        "cereja do bolo",
        "o que o cliente vê na prática",
        "a plataforma foi pensada para clientes",
        "a vitrine agora separa",
    }

    assert all(text not in home_html for text in forbidden_copy)
    assert "correlação de dados para decisões de manutenção" in home_html
    assert "soluções para confiabilidade e eficiência industrial" in home_html
    assert '"email": "suporte@meuprompt.net"' in home_html
    assert '"telephone": "+55-31-98267-3012"' in home_html


def test_commercial_contact_channels_are_configured():
    demo_html = (SITE_ROOT / "demonstracao" / "index.html").read_text(encoding="utf-8")
    contact_html = (SITE_ROOT / "contato" / "index.html").read_text(encoding="utf-8")
    contact_script = (SITE_ROOT / "assets" / "contact.js").read_text(encoding="utf-8")

    for page_html in (demo_html, contact_html):
        assert "suporte@meuprompt.net" in page_html
        assert "https://wa.me/5531982673012" in page_html
        assert "+55 31 98267-3012" in page_html
        assert "data-contact-form" in page_html
        assert "/assets/contact.js" in page_html
        assert "Configure o endpoint do CRM/webhook" not in page_html

    assert 'CONTACT_ENDPOINT = "/contact/submit"' in contact_script
    assert "fetch(CONTACT_ENDPOINT" in contact_script
    assert "mailto:" not in contact_script


def test_indexed_pages_expose_descriptive_images():
    missing = []
    for html_file in _html_files():
        if "acesso" in html_file.parts:
            continue
        parser = LinkParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        for image in parser.images:
            src = image.get("src", "")
            alt = image.get("alt", "")
            if not src or not _target_exists(src) or len(alt.strip()) < 24:
                missing.append((html_file.relative_to(SITE_ROOT).as_posix(), src, alt))

    assert missing == []
