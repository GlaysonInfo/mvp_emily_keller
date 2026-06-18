from html.parser import HTMLParser
import json
from pathlib import Path
import re
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


def test_sitemap_uses_current_lastmod_for_public_pages():
    sitemap = ET.parse(SITE_ROOT / "sitemap.xml")
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    entries = {
        urlparse(item.find("sm:loc", namespace).text).path: item.find("sm:lastmod", namespace).text
        for item in sitemap.findall("sm:url", namespace)
    }

    assert all(entries[path] == "2026-06-18" for path in PUBLIC_PAGES)


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

    assert "Comunicação industrial = inteligência operacional" in home_html
    assert "pressão, vazão, temperatura, nível e vibração" in home_html
    assert "paradas não programadas" in home_html
    assert "/monitoramento-de-equipamentos/" in home_html
    assert "/inteligencia-operacional/" in home_html
    assert "/eficiencia-industrial/" in home_html
    assert "hero-sentinela-inteligencia-operacional.png" in home_html


def test_public_pages_expose_search_metadata():
    failures = []

    for page in PUBLIC_PAGES:
        html_file = SITE_ROOT / "index.html" if page == "/" else SITE_ROOT / page.strip("/") / "index.html"
        html = html_file.read_text(encoding="utf-8")
        canonical = f"https://sentinelaindustrial.com.br{page}"

        checks = {
            "title": bool(re.search(r"<title>[^<]{12,}</title>", html)),
            "description": 'meta name="description"' in html,
            "canonical": f'rel="canonical" href="{canonical}"' in html,
            "index": 'meta name="robots" content="index, follow"' in html,
            "favicon": 'rel="icon" href="/favicon.svg"' in html,
            "h1": bool(re.search(r"<h1>[^<]{3,}</h1>", html)),
        }
        failures.extend((page, name) for name, passed in checks.items() if not passed)

    assert failures == []


def test_primary_solution_pages_expose_social_metadata():
    primary_pages = {
        "/",
        "/monitoramento-de-equipamentos/",
        "/sistema-de-lubrificacao/",
        "/inteligencia-operacional/",
        "/eficiencia-industrial/",
        "/como-funciona/",
        "/demonstracao/",
        "/contato/",
    }
    failures = []

    for page in primary_pages:
        html_file = SITE_ROOT / "index.html" if page == "/" else SITE_ROOT / page.strip("/") / "index.html"
        html = html_file.read_text(encoding="utf-8")
        for marker in ('property="og:title"', 'property="og:description"', 'property="og:image"', 'name="twitter:card"'):
            if marker not in html:
                failures.append((page, marker))

    assert failures == []


def test_home_structured_data_exposes_brand_identity():
    home_html = (SITE_ROOT / "index.html").read_text(encoding="utf-8")

    assert '"logo": "https://sentinelaindustrial.com.br/favicon.svg"' in home_html
    assert '"alternateName": "Sentinela"' in home_html
    assert '"@type": "Organization"' in home_html
    assert '"@type": "WebSite"' in home_html


def test_structured_data_blocks_are_valid_json():
    failures = []

    for html_file in _html_files():
        html = html_file.read_text(encoding="utf-8")
        blocks = re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            html,
            flags=re.DOTALL,
        )
        for index, block in enumerate(blocks):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                failures.append((html_file.relative_to(SITE_ROOT).as_posix(), index, str(exc)))

    assert failures == []


def test_home_uses_market_ready_commercial_copy():
    home_html = (SITE_ROOT / "index.html").read_text(encoding="utf-8").lower()

    forbidden_copy = {
        "cereja do bolo",
        "o que o cliente vê na prática",
        "a plataforma foi pensada para clientes",
        "a vitrine agora separa",
    }

    assert all(text not in home_html for text in forbidden_copy)
    assert "comunicação industrial = inteligência operacional" in home_html
    assert "histórico operacional" in home_html
    assert "sinais industriais" in home_html
    assert '"email": "suporte@meuprompt.net"' in home_html
    assert '"telephone": "+55-31-98267-3012"' in home_html


def test_industrial_communication_docs_cover_client_https_and_bluetooth():
    client_manual = Path("docs/manual_cliente_envio_https_sentinela.md").read_text(encoding="utf-8")
    gateway_doc = Path("docs/configuracao_gateway_equipamentos.md").read_text(encoding="utf-8")
    ingest_doc = Path("docs/especificacao_endpoint_condition_ingest.md").read_text(encoding="utf-8")
    field_config = Path("config/field_condition_config.example.json").read_text(encoding="utf-8")

    assert "https://www.raspberrypi.com/documentation/computers/getting-started.html" in client_manual
    assert "https://www.raspberrypi.com/documentation/computers/configuration.html" in client_manual
    assert "/condition/ingest" in client_manual
    assert "CONDITION_INGEST_TOKEN" in client_manual
    assert "Raspberry Pi" in client_manual

    assert "Bluetooth LE (configuração local)" in gateway_doc
    assert "Bluetooth fabricante (configuração local)" in gateway_doc

    for metric in ("pressure_bar", "flow_rate_l_min", "level_percent", "level_m"):
        assert metric in ingest_doc

    for metric in ("pressure_bar", "flow_rate_l_min", "level_percent"):
        assert metric in field_config


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
    assert "data?.ok !== true" in contact_script
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


def test_favicon_is_square_and_crawlable():
    favicon = (SITE_ROOT / "favicon.svg").read_text(encoding="utf-8")

    assert 'viewBox="0 0 512 512"' in favicon
    assert "<svg" in favicon


def test_styles_do_not_block_rendering_with_external_font_imports():
    styles = (SITE_ROOT / "assets" / "styles.css").read_text(encoding="utf-8")

    assert "fonts.googleapis.com" not in styles
    assert "@import url(" not in styles
