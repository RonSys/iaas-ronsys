"""
Tests para Configuración / Branding — sin dependencia de pydantic.

Testean la estructura de datos y defaults.
"""

from dataclasses import dataclass, field, asdict


# ═══════════════════════════════════════════════════════════════
# Réplicas de schemas con dataclasses (stdlib, sin pydantic)
# ═══════════════════════════════════════════════════════════════


@dataclass
class ColorPalette:
    primary: str = "#1a365d"
    secondary: str = "#2b6cb0"
    accent: str = "#e53e3e"
    background: str = "#f7fafc"
    surface: str = "#ffffff"
    text_primary: str = "#1a202c"
    text_secondary: str = "#718096"
    success: str = "#38a169"
    warning: str = "#d69e2e"
    error: str = "#e53e3e"


@dataclass
class CompanySettings:
    palette: ColorPalette = field(default_factory=ColorPalette)
    logo_url: str | None = None
    favicon_url: str | None = None
    date_format: str = "DD/MM/YYYY"
    currency: str = "PEN"
    timezone: str = "America/Lima"


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════


class TestColorPalette:
    def test_default_palette(self):
        p = ColorPalette()
        assert p.primary == "#1a365d"
        assert p.secondary == "#2b6cb0"
        assert p.accent == "#e53e3e"

    def test_custom_palette(self):
        p = ColorPalette(
            primary="#ff6600",
            secondary="#ff9900",
            accent="#00cc66",
            background="#111111",
            surface="#222222",
            text_primary="#ffffff",
            text_secondary="#aaaaaa",
            success="#00ff00",
            warning="#ffaa00",
            error="#ff0000",
        )
        assert p.primary == "#ff6600"
        assert p.background == "#111111"

    def test_palette_serialization(self):
        p = ColorPalette(primary="#ff6600")
        data = asdict(p)
        assert data["primary"] == "#ff6600"
        assert data["secondary"] == "#2b6cb0"  # default

    def test_valid_hex_colors(self):
        """Todas las entradas deben ser hex codes válidos."""
        import re
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        p = ColorPalette()
        for name, value in asdict(p).items():
            assert hex_pattern.match(value), f"Color {name}={value} no es hex válido"


class TestCompanySettings:
    def test_default_settings(self):
        s = CompanySettings()
        assert s.currency == "PEN"
        assert s.timezone == "America/Lima"
        assert s.palette.primary == "#1a365d"

    def test_settings_partial_update(self):
        s = CompanySettings()
        s2 = CompanySettings(
            palette=s.palette,
            currency="USD",
        )
        assert s2.currency == "USD"
        assert s2.palette.primary == "#1a365d"  # No se tocó
        assert s2.timezone == "America/Lima"  # Default

    def test_logo_url_nullable(self):
        s = CompanySettings()
        assert s.logo_url is None
        s2 = CompanySettings(logo_url="https://example.com/logo.png")
        assert s2.logo_url == "https://example.com/logo.png"
