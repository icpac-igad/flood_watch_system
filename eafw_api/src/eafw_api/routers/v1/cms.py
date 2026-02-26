"""
CMS Content API - Access to Wagtail CMS content
Homepage settings, navbar, footer, themes, etc.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException

from eafw_api.db import get_connection

router = APIRouter()


@router.get("/homepage")
async def get_homepage_config():
    """
    Get homepage configuration from CMS.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                h.banner_title, h.banner_subtitle, h.banner_button_text,
                h.banner_button_url, h.show_mini_map, h.mini_map_initial_zoom,
                h.mini_map_center_lat, h.mini_map_center_lng, h.mini_map_height,
                h.show_weather_widget, h.country_cards_title,
                h.show_country_cards, h.homepage_layout,
                h.show_map_preview, h.map_preview_title, h.map_preview_subtitle,
                p.title, p.slug
            FROM cms.home_homepage h
            JOIN cms.wagtailcore_page p ON h.page_ptr_id = p.id
            WHERE p.live = TRUE
            LIMIT 1
            """
        )

        if not row:
            raise HTTPException(status_code=404, detail="Homepage not found")

        return {
            "title": row["title"],
            "slug": row["slug"],
            "layout": row["homepage_layout"],
            "banner": {
                "title": row["banner_title"],
                "subtitle": row["banner_subtitle"],
                "button_text": row["banner_button_text"],
                "button_url": row["banner_button_url"],
            },
            "mini_map": {
                "enabled": row["show_mini_map"],
                "zoom": row["mini_map_initial_zoom"],
                "center": {
                    "lat": float(row["mini_map_center_lat"]) if row["mini_map_center_lat"] else None,
                    "lng": float(row["mini_map_center_lng"]) if row["mini_map_center_lng"] else None,
                },
                "height": row["mini_map_height"],
            },
            "map_preview": {
                "show": row["show_map_preview"],
                "title": row["map_preview_title"],
                "subtitle": row["map_preview_subtitle"],
            },
            "weather_widget": row["show_weather_widget"],
            "country_cards": {
                "show": row["show_country_cards"],
                "title": row["country_cards_title"],
            },
        }


@router.get("/navbar")
async def get_navbar():
    """
    Get navbar configuration from CMS.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                n.menu_items, n.show_utility_bar, n.utility_email,
                n.utility_phone, n.utility_links,
                p.title
            FROM cms.home_navbar n
            JOIN cms.wagtailcore_page p ON n.page_ptr_id = p.id
            WHERE p.live = TRUE
            LIMIT 1
            """
        )

        if not row:
            return {"navbar": None}

        return {
            "title": row["title"],
            "menu_items": row["menu_items"],
            "utility_bar": {
                "show": row["show_utility_bar"],
                "email": row["utility_email"],
                "phone": row["utility_phone"],
                "links": row["utility_links"],
            },
        }


@router.get("/footer")
async def get_footer():
    """
    Get footer configuration from CMS.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                f.description, f.copyright_organization, f.sections,
                f.social_links, f.member_countries, f.partners
            FROM cms.home_footer f
            JOIN cms.wagtailcore_page p ON f.page_ptr_id = p.id
            WHERE p.live = TRUE
            LIMIT 1
            """
        )

        if not row:
            return {"footer": None}

        return {
            "description": row["description"],
            "copyright": row["copyright_organization"],
            "sections": row["sections"],
            "social_links": row["social_links"],
            "member_countries": row["member_countries"],
            "partners": row["partners"],
        }


@router.get("/theme")
async def get_theme():
    """
    Get site theme configuration.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                name, primary_color, secondary_color, accent_color,
                primary_text_color, secondary_text_color, background_color,
                enable_wave_animation, wave_color_1, wave_color_2, wave_color_3,
                wave_opacity, wave_height
            FROM cms.home_sitetheme
            WHERE is_active = TRUE
            LIMIT 1
            """
        )

        if not row:
            return {
                "theme": {
                    "primary": "#1976d2",
                    "secondary": "#424242",
                    "accent": "#82B1FF",
                }
            }

        return {
            "theme": {
                "name": row["name"],
                "primary": row["primary_color"],
                "secondary": row["secondary_color"],
                "accent": row["accent_color"],
                "text": {
                    "primary": row["primary_text_color"],
                    "secondary": row["secondary_text_color"],
                },
                "background": row["background_color"],
                "wave": {
                    "enabled": row["enable_wave_animation"],
                    "color1": row["wave_color_1"],
                    "color2": row["wave_color_2"],
                    "color3": row["wave_color_3"],
                    "opacity": row["wave_opacity"],
                    "height": row["wave_height"],
                },
            }
        }


@router.get("/multimodal-settings")
async def get_multimodal_cluster_settings():
    """
    Get multimodal cluster display settings.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                warning_threshold, alarm_threshold, emergency_threshold,
                normal_color, warning_color, alarm_color, emergency_color,
                cluster_max_zoom, cluster_radius
            FROM cms.home_multimodalclustersettings
            LIMIT 1
            """
        )

        if not row:
            return {
                "thresholds": {
                    "warning": 150,
                    "alarm": 300,
                    "emergency": 450,
                },
                "colors": {
                    "normal": "#b0b0b0",
                    "warning": "#FFC107",
                    "alarm": "#FF9800",
                    "emergency": "#F44336",
                },
            }

        return {
            "thresholds": {
                "warning": row["warning_threshold"],
                "alarm": row["alarm_threshold"],
                "emergency": row["emergency_threshold"],
            },
            "colors": {
                "normal": row["normal_color"],
                "warning": row["warning_color"],
                "alarm": row["alarm_color"],
                "emergency": row["emergency_color"],
            },
            "clustering": {
                "max_zoom": row["cluster_max_zoom"],
                "radius": row["cluster_radius"],
            },
        }


@router.get("/languages")
async def get_enabled_languages():
    """
    Get enabled languages from CMS.
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT el.language_code, el.is_default, el.sort_order
            FROM cms.home_enabledlanguage el
            ORDER BY el.sort_order
            """
        )

        language_names = {
            "en": "English",
            "sw": "Swahili",
            "ar": "العربية (Arabic)",
            "am": "አማርኛ (Amharic)",
            "fr": "Français (French)",
            "so": "Soomaali (Somali)",
            "om": "Oromoo (Oromo)",
            "ti": "ትግርኛ (Tigrinya)",
            "pt": "Português (Portuguese)",
            "es": "Español (Spanish)",
        }

        languages = [
            {
                "code": row["language_code"],
                "name": language_names.get(row["language_code"], row["language_code"]),
                "is_default": row["is_default"],
            }
            for row in rows
        ]

        default_lang = next((l for l in languages if l["is_default"]), languages[0] if languages else None)

        return {
            "languages": languages,
            "default": default_lang["code"] if default_lang else "en",
        }


# ISO-2 → country name mapping for scope country resolution
_ISO2_TO_COUNTRY = {
    "BI": "Burundi", "DJ": "Djibouti", "ER": "Eritrea", "ET": "Ethiopia",
    "KE": "Kenya", "RW": "Rwanda", "SD": "Sudan", "SO": "Somalia",
    "SS": "South Sudan", "TZ": "Tanzania", "UG": "Uganda",
}


@router.get("/scopes")
async def get_map_scopes():
    """
    Get CMS-configured map scopes (project filters).
    Returns all active scopes with their country codes, partner keys, and display settings.
    Used by the mapviewer and flood-analysis page to drive global scope selection.
    """
    async with get_connection() as conn:
        homepage = await conn.fetchrow(
            "SELECT page_ptr_id FROM cms.home_homepage LIMIT 1"
        )
        if not homepage:
            return {"scopes": [], "default_scope": "all"}

        rows = await conn.fetch(
            """
            SELECT key, name, is_default, country_codes_iso2, country_codes_iso3,
                   partner_keys, site_title, country_section_title, dashboard_title,
                   show_basin_overlay
            FROM cms.home_mapscope
            WHERE page_id = $1 AND is_active = TRUE
            ORDER BY sort_order
            """,
            homepage["page_ptr_id"],
        )

        scopes = []
        default_scope = "all"

        for row in rows:
            iso2 = [c.strip().upper() for c in (row["country_codes_iso2"] or "").split(",") if c.strip()]
            iso3 = [c.strip().upper() for c in (row["country_codes_iso3"] or "").split(",") if c.strip()]
            partners = [
                p.strip().lower().replace(" ", "")
                for p in (row["partner_keys"] or "").split(",") if p.strip()
            ]
            countries = [_ISO2_TO_COUNTRY.get(c, c) for c in iso2]

            scopes.append({
                "key": row["key"],
                "label": row["name"],
                "countries": countries,
                "country_codes_iso2": iso2,
                "country_codes_iso3": iso3,
                "partner_keys": partners,
                "site_title": row["site_title"] or "",
                "country_section_title": row["country_section_title"] or "",
                "dashboard_title": row["dashboard_title"] or "",
                "show_basin_overlay": row["show_basin_overlay"],
            })

            if row["is_default"]:
                default_scope = row["key"]

        return {"scopes": scopes, "default_scope": default_scope}


@router.get("/categories")
async def get_map_categories():
    """
    Get geomanager categories with descriptions.
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.id, c.title, c.icon, c.active, c."order",
                cd.description
            FROM cms.geomanager_category c
            LEFT JOIN cms.home_categorydescription cd ON c.id = cd.category_id
            WHERE c.active = TRUE
            ORDER BY c."order", c.title
            """
        )

        categories = [
            {
                "id": row["id"],
                "title": row["title"],
                "icon": row["icon"],
                "description": row["description"],
                "order": row["order"],
            }
            for row in rows
        ]

        return {"categories": categories, "count": len(categories)}
