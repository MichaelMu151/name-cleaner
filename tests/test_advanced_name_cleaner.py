import pandas as pd
import pytest

from advanced_name_cleaner import AdvancedNameCleaner


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "p_name": [
            "王俊峰", "王俊峰", "王俊峰", "王俊锋",
            "王俊锋", "王俊峰", "李明",
        ],
        "year": [2008, 2009, 2012, 2013, 2014, 2015, 2015],
        "post1": ["副市长"] * 6 + ["局长"],
        "company": ["甲市人民政府"] * 6 + ["乙市财政局"],
    })


def test_find_potential_groups_finds_homophone_variants(sample_df):
    cleaner = AdvancedNameCleaner(threshold=0.85)

    groups = cleaner.find_potential_groups(sample_df, verbose=False)

    assert any(set(group) == {"王俊峰", "王俊锋"} for group in groups)
    assert all("李明" not in group for group in groups)


def test_find_potential_groups_validates_name_column(sample_df):
    cleaner = AdvancedNameCleaner()

    with pytest.raises(ValueError, match="姓名列"):
        cleaner.find_potential_groups(sample_df, name_col="missing", verbose=False)


def test_character_differences_reports_position_and_characters():
    differences = AdvancedNameCleaner.character_differences("王俊峰", "王俊锋")

    assert differences == [{
        "position": 3,
        "reference": "峰",
        "variant": "锋",
    }]


def test_group_evidence_contains_frequency_ratio_and_timeline(sample_df):
    cleaner = AdvancedNameCleaner(aux_columns=["post1", "company", "missing"])

    evidence = cleaner.build_group_evidence(
        sample_df,
        ["王俊峰", "王俊锋"],
        year_col="year",
    )

    assert evidence["suggested_name"] == "王俊峰"
    assert evidence["total_frequency"] == 6
    assert evidence["context_columns"] == ["post1", "company"]
    assert [item["name"] for item in evidence["variants"]] == ["王俊峰", "王俊锋"]
    assert evidence["variants"][0]["frequency"] == 4
    assert evidence["variants"][0]["frequency_ratio"] == pytest.approx(4 / 6)
    assert evidence["variants"][1]["year_min"] == 2013
    assert evidence["variants"][1]["year_max"] == 2014
    assert [row["year"] for row in evidence["timeline"]] == [
        2008, 2009, 2012, 2013, 2014, 2015
    ]
    assert evidence["timeline"][3] == {
        "year": 2013,
        "name": "王俊锋",
        "frequency": 1,
        "post1": "副市长",
        "company": "甲市人民政府",
    }


def test_group_evidence_falls_back_without_valid_year(sample_df):
    cleaner = AdvancedNameCleaner(aux_columns=["post1"])

    evidence = cleaner.build_group_evidence(
        sample_df,
        ["王俊峰", "王俊锋"],
        year_col="missing",
    )

    assert evidence["year_column"] is None
    assert evidence["timeline"] == []
    assert len(evidence["raw_records"]) == 6


def test_apply_corrections_preserves_original_names(sample_df):
    cleaned = AdvancedNameCleaner.apply_corrections(
        sample_df,
        {"王俊锋": "王俊峰"},
    )

    assert "p_name_raw" in cleaned.columns
    assert set(cleaned["p_name"]) == {"王俊峰", "李明"}
    assert set(cleaned["p_name_raw"]) == {"王俊峰", "王俊锋", "李明"}
    assert "p_name_raw" not in sample_df.columns


def test_apply_corrections_does_not_overwrite_existing_raw_column(sample_df):
    source = sample_df.copy()
    source["p_name_raw"] = "最初值"

    cleaned = AdvancedNameCleaner.apply_corrections(
        source,
        {"王俊锋": "王俊峰"},
    )

    assert cleaned["p_name_raw"].eq("最初值").all()
