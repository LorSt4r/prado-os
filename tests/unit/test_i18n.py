"""
Unit and integration tests for i18n support in PradoOS.
Verifies translations, language normalization, and fallback mechanisms for ('es', 'en', 'it', 'fr').
"""

import pytest

from prado.config import PradoConfig
from prado.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    normalize_language,
    t,
)


def test_supported_languages_list():
    assert "es" in SUPPORTED_LANGUAGES
    assert "en" in SUPPORTED_LANGUAGES
    assert "it" in SUPPORTED_LANGUAGES
    assert "fr" in SUPPORTED_LANGUAGES


def test_normalize_language_variants():
    assert normalize_language("es") == "es"
    assert normalize_language("Español") == "es"
    assert normalize_language("SPANISH") == "es"

    assert normalize_language("en") == "en"
    assert normalize_language("English") == "en"
    assert normalize_language("eng") == "en"

    assert normalize_language("it") == "it"
    assert normalize_language("Italiano") == "it"
    assert normalize_language("ita") == "it"

    assert normalize_language("fr") == "fr"
    assert normalize_language("Français") == "fr"
    assert normalize_language("francais") == "fr"
    assert normalize_language("fra") == "fr"

    # Default fallback
    assert normalize_language("de") == DEFAULT_LANGUAGE
    assert normalize_language(None) == DEFAULT_LANGUAGE
    assert normalize_language("") == DEFAULT_LANGUAGE


def test_translations_coverage_all_four_languages():
    sample_keys = [
        "menu_header",
        "menu_opt_1",
        "menu_opt_2",
        "menu_opt_3",
        "menu_opt_8",
        "wizard_welcome_banner",
        "wizard_q1_lang",
        "wizard_q1_folder",
        "star_prompt",
        "mail_title",
        "sync_completed",
        "doctor_healthy",
    ]

    for key in sample_keys:
        for lang in ("es", "en", "it", "fr"):
            translated = t(key, lang=lang)
            assert translated != key, f"Missing translation for key '{key}' in lang '{lang}'"
            assert len(translated) > 0


def test_translation_formatting_args():
    msg_es = t("mail_filter_active", lang="es", filter_name="DECSAI")
    assert "DECSAI" in msg_es
    assert "Filtro activo:" in msg_es

    msg_it = t("mail_filter_active", lang="it", filter_name="DECSAI")
    assert "DECSAI" in msg_it
    assert "Filtro attivo:" in msg_it

    msg_fr = t("mail_filter_active", lang="fr", filter_name="DECSAI")
    assert "DECSAI" in msg_fr
    assert "Filtre actif" in msg_fr


def test_prado_config_supports_four_languages():
    for lang in ("es", "en", "it", "fr"):
        cfg = PradoConfig.from_dict({"language": lang})
        assert cfg.language == lang
        as_dict = cfg.to_dict()
        assert as_dict["language"] == lang

    # Unsupported falls back to 'es'
    cfg_unknown = PradoConfig.from_dict({"language": "xx"})
    assert cfg_unknown.language == "es"
