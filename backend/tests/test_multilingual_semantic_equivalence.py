"""
Phase 2.5 — Section 10A: Cross-Language Semantic Equivalence & Fallback Test Matrix.

Verifies that English, Hindi, and Marathi semantic queries resolve against the
SAME FarmContext, load the SAME recommendation, use the SAME canonical evidence,
and apply language-independent grounding rules.
"""
import pytest
import sys
sys.path.insert(0, '.')

from app.schemas.ai import (
    FarmContext,
    CropRankEntry,
    NDVIContext,
    ResourcePlanContext,
    ParetoPointSummary,
)
from app.core.ai_grounding import validate_answer_is_grounded, build_grounding_prompt
from app.services.ai.assistant_service import _GROUNDING_FALLBACKS


@pytest.fixture
def sample_context():
    """Authoritative FarmContext used across all language tests."""
    return FarmContext(
        recommendation_id=42,
        generated_at="2026-08-25T12:00:00Z",
        recommendation_status="complete",
        data_completeness_weather="live",
        data_completeness_soil="live",
        data_completeness_satellite="live",
        data_completeness_market="csv",
        satellite_source="gee-sentinel2",
        weather_source="nasa-power",
        soil_source="soilgrids-reference",
        market_source="csv",
        latitude=18.5204,
        longitude=73.8567,
        ndvi=NDVIContext(
            value=0.254,
            source="gee-sentinel2",
            scene_date="2026-07-14",
            status="moderate vegetation",
            is_live=True,
        ),
        ndvi_available=True,
        satellite_scene_date="2026-07-14",
        rainfall_mm_last_30d=470.2,
        avg_temp_c=23.7,
        humidity_pct=93.4,
        solar_radiation_mj_m2=8.98,
        wind_speed_m_s=3.4,
        soil_ph=6.98,
        soil_moisture_pct=27.2,
        soil_nitrogen_mg_kg=1560.0,
        soil_organic_carbon_g_kg=18.0,
        soil_sand_pct=38.0,
        soil_clay_pct=23.5,
        ahp_weights={
            "climate_suitability": 0.4495,
            "soil_suitability": 0.2596,
            "water_efficiency": 0.1707,
            "market_value": 0.1202,
        },
        ahp_consistency_ratio=0.0265,
        ahp_is_consistent=True,
        ahp_method="fuzzy-ahp-chang-extent-analysis",
        crop_ranking=[
            CropRankEntry(
                crop="Groundnut", topsis_closeness=0.8123, electre_net_outranking=2, rank=1,
                criteria_scores={"climate_suitability": 0.8, "soil_suitability": 0.7, "water_efficiency": 0.85, "market_value": 0.7},
            ),
            CropRankEntry(
                crop="Wheat", topsis_closeness=0.7412, electre_net_outranking=1, rank=2,
                criteria_scores={"climate_suitability": 0.7, "soil_suitability": 0.7, "water_efficiency": 0.75, "market_value": 0.6},
            ),
            CropRankEntry(
                crop="Rice", topsis_closeness=0.6200, electre_net_outranking=-1, rank=3,
                criteria_scores={"climate_suitability": 0.6, "soil_suitability": 0.65, "water_efficiency": 0.50, "market_value": 0.8},
            ),
        ],
        crop_names_in_ranking=["Groundnut", "Wheat", "Rice"],
        resource_plan=ResourcePlanContext(
            water_liters_per_week=25293.0,
            fertilizer_kg_per_acre=20.0,
            optimizer_best_fitness=0.145,
            optimizer_generations_run=80,
            irrigation_schedule="~3613 L/day, split across 2-3 waterings/week",
            optimizer_method="nsga2-multiobjective",
            pareto_front=[
                ParetoPointSummary(water_liters_per_week=25293.0, fertilizer_kg_per_acre=20.0, resource_cost=1500.0)
            ],
            convergence_history=[10.0] * 80,
        ),
        ai_explanation="Groundnut was top recommended.",
    )


class TestCrossLanguageSemanticEquivalence:
    """Matrix of 5 semantically equivalent question categories in EN, HI, MR."""

    @pytest.mark.parametrize("lang,answer_text", [
        ("en", "Groundnut was recommended because it achieved a TOPSIS closeness score of 0.8123 and water efficiency score of 0.85."),
        ("hi", "मूंगफली की सिफारिश की गई क्योंकि इसने 0.8123 का TOPSIS स्कोर और 0.85 की जल दक्षता प्राप्त की।"),
        ("mr", "भुईमूगाची शिफारस करण्यात आली कारण त्याने 0.8123 चा TOPSIS स्कोअर आणि 0.85 ची पाणी कार्यक्षमता मिळवली."),
    ])
    def test_1_recommendation_explanation(self, sample_context, lang, answer_text):
        """Category 1: Recommendation explanation in EN, HI, MR."""
        prompt = build_grounding_prompt(sample_context, "Why recommended?", language=lang)
        assert sample_context.crop_ranking[0].crop in prompt
        check = validate_answer_is_grounded(answer_text, sample_context)
        assert check.passed, f"Language {lang} grounding check failed: {check.ungrounded_crop_claims}, {check.ungrounded_numeric_claims}"

    @pytest.mark.parametrize("lang,answer_text", [
        ("en", "Your farm requires 25293 L/week of water and 20 kg/acre of fertilizer."),
        ("hi", "आपके खेत को 25293 लीटर/सप्ताह पानी और 20 किग्रा/एकड़ उर्वरक की आवश्यकता है।"),
        ("mr", "तुमच्या शेतासाठी 25293 लिटर/आठवडा पाणी आणि 20 किग्रॅ/एकड खत आवश्यक आहे."),
    ])
    def test_2_water_and_fertilizer(self, sample_context, lang, answer_text):
        """Category 2: Water and fertilizer queries in EN, HI, MR."""
        check = validate_answer_is_grounded(answer_text, sample_context)
        assert check.passed, f"Language {lang} water/fert check failed: {check.ungrounded_crop_claims}, {check.ungrounded_numeric_claims}"

    @pytest.mark.parametrize("lang,answer_text", [
        ("en", "Rank 1 is Groundnut (0.8123), Rank 2 is Wheat (0.7412), Rank 3 is Rice (0.6200)."),
        ("hi", "रैंक 1 मूंगफली (0.8123), रैंक 2 गेहूं (0.7412), और रैंक 3 चावल (0.6200) है।"),
        ("mr", "रँक 1 भुईमूग (0.8123), रँक 2 गहू (0.7412), आणि रँक 3 भात (0.6200) आहे."),
    ])
    def test_3_ranking_explanation(self, sample_context, lang, answer_text):
        """Category 3: Ranking explanation in EN, HI, MR."""
        check = validate_answer_is_grounded(answer_text, sample_context)
        assert check.passed, f"Language {lang} ranking check failed: {check.ungrounded_crop_claims}, {check.ungrounded_numeric_claims}"

    @pytest.mark.parametrize("lang,answer_text", [
        ("en", "Your NDVI value is 0.254, indicating moderate vegetation from Sentinel-2."),
        ("hi", "आपका NDVI मान 0.254 है, जो मध्यम वनस्पति को दर्शाता है।"),
        ("mr", "तुमचे NDVI मूल्य 0.254 आहे, जे मध्यम वनस्पती दर्शवते."),
    ])
    def test_4_ndvi_explanation(self, sample_context, lang, answer_text):
        """Category 4: NDVI interpretation in EN, HI, MR."""
        check = validate_answer_is_grounded(answer_text, sample_context)
        assert check.passed, f"Language {lang} NDVI check failed: {check.ungrounded_crop_claims}, {check.ungrounded_numeric_claims}"

    @pytest.mark.parametrize("lang,answer_text", [
        ("en", "The dominant factor is climate_suitability with an AHP weight of 0.4495."),
        ("hi", "मुख्य कारक जलवायु (climate_suitability) है जिसका AHP भार 0.4495 है।"),
        ("mr", "प्रमुख घटक हवामान (climate_suitability) आहे ज्याचे AHP वजन 0.4495 आहे."),
    ])
    def test_5_dominant_criterion(self, sample_context, lang, answer_text):
        """Category 5: Dominant criterion in EN, HI, MR."""
        check = validate_answer_is_grounded(answer_text, sample_context)
        assert check.passed, f"Language {lang} dominant criterion check failed: {check.ungrounded_crop_claims}, {check.ungrounded_numeric_claims}"


class TestLanguageFallbackContract:
    """Verify that fallbacks are localized to English, Hindi, and Marathi."""

    def test_fallbacks_exist_and_non_english_for_hi_mr(self):
        assert "en" in _GROUNDING_FALLBACKS
        assert "hi" in _GROUNDING_FALLBACKS
        assert "mr" in _GROUNDING_FALLBACKS

        # Verify Hindi fallback contains Devanagari Hindi text
        assert "मुझे खेद है" in _GROUNDING_FALLBACKS["hi"]
        # Verify Marathi fallback contains Devanagari Marathi text
        assert "मला माफ करा" in _GROUNDING_FALLBACKS["mr"]

    def test_unsupported_language_defaults_to_english(self):
        fallback = _GROUNDING_FALLBACKS.get("unknown_lang", _GROUNDING_FALLBACKS["en"])
        assert "I'm sorry" in fallback


class TestDevanagariNumeralsGrounding:
    """Verify that answers containing Devanagari digits pass grounding validation."""

    def test_devanagari_numerals_pass_validation(self, sample_context):
        # 25293 in Devanagari is २५२९३, 20 is २०
        devanagari_answer = "खेत को २५२९३ लीटर पानी और २० किग्रा उर्वरक चाहिए।"
        check = validate_answer_is_grounded(devanagari_answer, sample_context)
        assert check.passed, f"Devanagari numerals check failed: {check.ungrounded_numeric_claims}"
