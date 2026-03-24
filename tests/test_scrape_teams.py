"""Tests for vgc_bench.scrape_teams (offline-only, no network calls)."""

from vgc_bench.scrape_teams import (
    all_pokemon_have_evs,
    event_slug,
    extract_year,
    get_regulation_sheets,
    has_duplicate_items,
    is_valid_placement,
    normalize_event_name,
    normalize_team_text,
    placement_to_filename,
    slugify,
)


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World!") == "hello_world"

    def test_unicode(self):
        assert slugify("São Paulo") == "sao_paulo"

    def test_empty(self):
        assert slugify("") == ""

    def test_special_chars(self):
        assert slugify("a---b___c") == "a_b_c"


class TestNormalizeEventName:
    def test_strips_regional_championships(self):
        assert "Regional Championships" not in normalize_event_name(
            "Atlanta Regional Championships"
        )

    def test_strips_regionals(self):
        assert "Regionals" not in normalize_event_name("Atlanta Regionals 2024")

    def test_preserves_other_text(self):
        assert "Atlanta" in normalize_event_name("Atlanta Regional Championships")


class TestExtractYear:
    def test_from_event_name(self):
        assert extract_year("Atlanta 2024", "") == "2024"

    def test_from_date_string(self):
        assert extract_year("Atlanta", "15 Jan 2024") == "2024"

    def test_no_year(self):
        assert extract_year("Atlanta", "unknown") is None

    def test_date_with_sept_abbreviation(self):
        assert extract_year("Event", "15 Sept 2023") == "2023"


class TestEventSlug:
    def test_basic(self):
        slug = event_slug("Atlanta 2024", "15 Jan 2024")
        assert "atlanta" in slug
        assert "2024" in slug

    def test_removes_year_from_name(self):
        slug = event_slug("Atlanta 2024", "")
        assert slug.count("2024") == 1


class TestPlacementToFilename:
    def test_champion(self):
        assert placement_to_filename("Champion") == "1st"

    def test_winner(self):
        assert placement_to_filename("Winner") == "1st"

    def test_runner_up(self):
        assert placement_to_filename("Runner Up") == "2nd"

    def test_numeric(self):
        assert placement_to_filename("3rd") == "3rd"


class TestHasDuplicateItems:
    def test_no_duplicates(self, sample_team_text):
        assert has_duplicate_items(sample_team_text) is False

    def test_with_duplicates(self):
        text = "Mon1 @ Focus Sash\n\nMon2 @ Focus Sash\n"
        assert has_duplicate_items(text) is True


class TestAllPokemonHaveEvs:
    def test_valid_team(self, sample_team_text):
        assert all_pokemon_have_evs(sample_team_text) is True

    def test_missing_evs(self):
        text = "Mon1 @ Item\nAbility: Blaze\n\nMon2 @ Item\nAbility: Blaze\n"
        assert all_pokemon_have_evs(text) is False


class TestIsValidPlacement:
    def test_valid(self):
        assert is_valid_placement("1st") is True
        assert is_valid_placement("Champion") is True

    def test_juniors(self):
        assert is_valid_placement("1st Juniors") is False

    def test_seniors(self):
        assert is_valid_placement("1st Seniors") is False


class TestNormalizeTeamText:
    def test_strips_nicknames(self):
        text = "MyNick (Pikachu) @ Light Ball\nAbility: Static\n"
        result = normalize_team_text(text)
        assert "MyNick" not in result
        assert "Pikachu" in result

    def test_fixes_level(self):
        text = "Pikachu @ Light Ball\nAbility: Static\nLevel: 100\n"
        result = normalize_team_text(text)
        assert "Level: 50" in result

    def test_adds_level_when_missing(self):
        text = "Pikachu @ Light Ball\nAbility: Static\n"
        result = normalize_team_text(text)
        assert "Level: 50" in result

    def test_fixes_ogerpon_tera_type(self):
        text = "Ogerpon-Wellspring (F) @ Wellspring Mask\nAbility: Water Absorb\nTera Type: Grass\n"
        result = normalize_team_text(text)
        assert "Tera Type: Water" in result

    def test_fixes_urshifu_form(self):
        text = "Urshifu @ Focus Sash\nAbility: Unseen Fist\n- Surging Strikes\n"
        result = normalize_team_text(text)
        assert "Urshifu-Rapid-Strike" in result

    def test_removes_raging_bolt_shiny(self):
        text = "Raging Bolt @ Booster Energy\nAbility: Protosynthesis\nShiny: Yes\nAdamant Nature\n"
        result = normalize_team_text(text)
        assert "Shiny" not in result

    def test_fixes_raging_bolt_atk_iv(self):
        text = "Raging Bolt @ Booster Energy\nAbility: Protosynthesis\nModest Nature\nIVs: 0 Atk\n"
        result = normalize_team_text(text)
        assert "20 Atk" in result


class TestGetRegulationSheets:
    def test_finds_featured(self):
        sheets = ["Reg G Featured Teams", "Reg H Featured Teams", "Other Sheet"]
        result = get_regulation_sheets(sheets, "G")
        assert "Reg G Featured Teams" in result
        assert "Reg H Featured Teams" not in result

    def test_excludes_presentable(self):
        sheets = ["Reg G Featured Teams Presentable", "Reg G Featured Teams"]
        result = get_regulation_sheets(sheets, "G")
        assert len(result) == 1
        assert "Presentable" not in result[0]

    def test_fallback(self):
        result = get_regulation_sheets([], "G")
        assert len(result) == 1
