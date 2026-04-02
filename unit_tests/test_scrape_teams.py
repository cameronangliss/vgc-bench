"""Unit tests for vgc_bench.scrape_teams string processing (no network calls)."""

from vgc_bench.scrape_teams import (
    all_pokemon_have_evs,
    get_regulation_sheets,
    has_duplicate_items,
    normalize_team_text,
)


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
        text = (
            "Ogerpon-Wellspring (F) @ Wellspring Mask\n"
            "Ability: Water Absorb\nTera Type: Grass\n"
        )
        result = normalize_team_text(text)
        assert "Tera Type: Water" in result

    def test_fixes_urshifu_form(self):
        text = "Urshifu @ Focus Sash\nAbility: Unseen Fist\n- Surging Strikes\n"
        result = normalize_team_text(text)
        assert "Urshifu-Rapid-Strike" in result

    def test_removes_raging_bolt_shiny(self):
        text = (
            "Raging Bolt @ Booster Energy\n"
            "Ability: Protosynthesis\nShiny: Yes\nAdamant Nature\n"
        )
        result = normalize_team_text(text)
        assert "Shiny" not in result

    def test_fixes_raging_bolt_atk_iv(self):
        text = (
            "Raging Bolt @ Booster Energy\n"
            "Ability: Protosynthesis\nModest Nature\nIVs: 0 Atk\n"
        )
        result = normalize_team_text(text)
        assert "20 Atk" in result


class TestGetRegulationSheets:
    def test_finds_featured_and_regular(self):
        sheets = [
            "Reg G Featured Teams",
            "Reg H Featured Teams",
            "SV Regulation G",
            "SV Regulation H",
        ]
        featured, regular = get_regulation_sheets(sheets, "G")
        assert "Reg G Featured Teams" in featured
        assert "Reg H Featured Teams" not in featured
        assert "SV Regulation G" in regular
        assert "SV Regulation H" not in regular

    def test_excludes_presentable(self):
        sheets = ["Reg G Featured Teams Presentable", "Reg G Featured Teams"]
        featured, _regular = get_regulation_sheets(sheets, "G")
        assert len(featured) == 1
        assert "Presentable" not in featured[0]

    def test_fallback(self):
        featured, regular = get_regulation_sheets([], "G")
        assert featured == []
        assert regular == ["SV Regulation G"]
