"""Tests for sv_shared dataset loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from datasets import Dataset

from sv_shared.dataset_loader import (
    DEFAULT_E1_HF_REPO,
    DEFAULT_E2_HF_REPO,
    HF_DATASET_MAP,
    _get_hf_repo,
    _has_hf_credentials,
    _load_from_hub,
    _load_local_jsonl,
    _local_dataset_exists,
    load_dataset_with_fallback,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_hf_repo_default_e1(self) -> None:
        """Test getting default E1 HF repo."""
        with patch.dict(os.environ, {}, clear=True):
            assert _get_hf_repo("e1") == DEFAULT_E1_HF_REPO

    def test_get_hf_repo_default_e2(self) -> None:
        """Test getting default E2 HF repo."""
        with patch.dict(os.environ, {}, clear=True):
            assert _get_hf_repo("e2") == DEFAULT_E2_HF_REPO

    def test_get_hf_repo_custom_e1(self) -> None:
        """Test getting custom E1 HF repo from environment."""
        with patch.dict(os.environ, {"E1_HF_REPO": "custom/e1-repo"}):
            assert _get_hf_repo("e1") == "custom/e1-repo"

    def test_get_hf_repo_custom_e2(self) -> None:
        """Test getting custom E2 HF repo from environment."""
        with patch.dict(os.environ, {"E2_HF_REPO": "custom/e2-repo"}):
            assert _get_hf_repo("e2") == "custom/e2-repo"

    def test_get_hf_repo_invalid_env(self) -> None:
        """Test getting HF repo for invalid environment raises ValueError."""
        with pytest.raises(ValueError, match="Unknown environment"):
            _get_hf_repo("invalid")

    def test_has_hf_credentials_true(self) -> None:
        """Test HF credentials check when token is set."""
        with patch.dict(os.environ, {"HF_TOKEN": "hf_test_token"}):
            assert _has_hf_credentials() is True

    def test_has_hf_credentials_false(self) -> None:
        """Test HF credentials check when token is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _has_hf_credentials() is False

    def test_local_dataset_exists_true(self, tmp_path: Path) -> None:
        """Test local dataset existence check for existing file."""
        dataset_file = tmp_path / "dataset.jsonl"
        dataset_file.write_text('{"example": 1}\n')
        assert _local_dataset_exists(dataset_file) is True

    def test_local_dataset_exists_false(self, tmp_path: Path) -> None:
        """Test local dataset existence check for non-existing file."""
        dataset_file = tmp_path / "nonexistent.jsonl"
        assert _local_dataset_exists(dataset_file) is False

    def test_local_dataset_exists_directory(self, tmp_path: Path) -> None:
        """Test local dataset existence check for directory returns False."""
        assert _local_dataset_exists(tmp_path) is False


class TestLoadLocalJsonl:
    """Tests for _load_local_jsonl function."""

    def test_load_basic(self, tmp_path: Path) -> None:
        """Test loading basic JSONL file."""
        dataset_file = tmp_path / "test.jsonl"
        data = [
            {"prompt": "Q1", "answer": "A1"},
            {"prompt": "Q2", "answer": "A2"},
        ]
        dataset_file.write_text("\n".join(json.dumps(d) for d in data))

        dataset = _load_local_jsonl(dataset_file)
        assert len(dataset) == 2
        assert dataset[0]["prompt"] == "Q1"
        assert dataset[1]["answer"] == "A2"

    def test_load_with_max_examples(self, tmp_path: Path) -> None:
        """Test loading with max_examples limit."""
        dataset_file = tmp_path / "test.jsonl"
        data = [{"id": i} for i in range(10)]
        dataset_file.write_text("\n".join(json.dumps(d) for d in data))

        dataset = _load_local_jsonl(dataset_file, max_examples=5)
        assert len(dataset) == 5
        assert dataset[4]["id"] == 4

    def test_load_with_field_mapping(self, tmp_path: Path) -> None:
        """Test loading with field mapping."""
        dataset_file = tmp_path / "test.jsonl"
        data = [{"old_field": "value1"}, {"old_field": "value2"}]
        dataset_file.write_text("\n".join(json.dumps(d) for d in data))

        dataset = _load_local_jsonl(dataset_file, field_mapping={"old_field": "new_field"})
        assert "new_field" in dataset[0]
        assert dataset[0]["new_field"] == "value1"
        # Original field should still exist
        assert dataset[0]["old_field"] == "value1"

    def test_load_skips_empty_lines(self, tmp_path: Path) -> None:
        """Test loading skips empty lines."""
        dataset_file = tmp_path / "test.jsonl"
        dataset_file.write_text('{"id": 1}\n\n{"id": 2}\n\n\n{"id": 3}\n')

        dataset = _load_local_jsonl(dataset_file)
        assert len(dataset) == 3


class TestLoadFromHub:
    """Tests for _load_from_hub function."""

    def test_load_without_credentials(self) -> None:
        """Test loading from Hub without HF_TOKEN raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="HF_TOKEN not found"):
                _load_from_hub("iot23-train-dev-test-v1.jsonl")

    def test_load_unknown_dataset(self) -> None:
        """Test loading unknown dataset raises ValueError."""
        with patch.dict(os.environ, {"HF_TOKEN": "test_token"}):
            with pytest.raises(ValueError, match="Unknown dataset"):
                _load_from_hub("nonexistent.jsonl")

    @patch("datasets.load_dataset")
    def test_load_e1_dataset(self, mock_load_dataset: MagicMock) -> None:
        """Test loading E1 dataset from Hub."""
        mock_dataset = MagicMock(spec=Dataset)
        mock_dataset.__len__ = MagicMock(return_value=100)
        mock_load_dataset.return_value = mock_dataset

        with patch.dict(os.environ, {"HF_TOKEN": "test_token"}):
            result = _load_from_hub("iot23-train-dev-test-v1.jsonl")

        assert result is mock_dataset
        mock_load_dataset.assert_called_once_with(
            DEFAULT_E1_HF_REPO,
            split="train",
            token="test_token",
        )

    @patch("datasets.load_dataset")
    def test_load_e2_dataset(self, mock_load_dataset: MagicMock) -> None:
        """Test loading E2 dataset from Hub."""
        mock_dataset = MagicMock(spec=Dataset)
        mock_dataset.__len__ = MagicMock(return_value=444)
        mock_load_dataset.return_value = mock_dataset

        with patch.dict(os.environ, {"HF_TOKEN": "test_token"}):
            result = _load_from_hub("k8s-labeled-v1.jsonl")

        assert result is mock_dataset
        mock_load_dataset.assert_called_once_with(
            DEFAULT_E2_HF_REPO,
            split="k8s",
            token="test_token",
        )

    @patch("datasets.load_dataset")
    def test_load_with_max_examples(self, mock_load_dataset: MagicMock) -> None:
        """Test loading with max_examples limit."""
        mock_dataset = MagicMock(spec=Dataset)
        mock_dataset.__len__ = MagicMock(return_value=1800)
        mock_select = MagicMock(return_value=mock_dataset)
        mock_dataset.select = mock_select
        mock_load_dataset.return_value = mock_dataset

        with patch.dict(os.environ, {"HF_TOKEN": "test_token"}):
            _load_from_hub("iot23-train-dev-test-v1.jsonl", max_examples=10)

        mock_select.assert_called_once()


class TestLoadDatasetWithFallback:
    """Tests for load_dataset_with_fallback function."""

    def test_explicit_synthetic_request(self) -> None:
        """Test explicit synthetic dataset request."""

        def mock_generator() -> Dataset:
            return Dataset.from_list([{"id": 1}, {"id": 2}])

        dataset, name = load_dataset_with_fallback(
            dataset_name="synthetic",
            env_root=Path("/tmp"),
            dataset_source="synthetic",
            synthetic_generator=mock_generator,
        )
        assert len(dataset) == 2
        assert "synthetic" in name

    def test_synthetic_without_generator_raises(self) -> None:
        """Test synthetic request without generator raises ValueError."""
        with pytest.raises(ValueError, match="no generator provided"):
            load_dataset_with_fallback(
                dataset_name="synthetic",
                env_root=Path("/tmp"),
                dataset_source="synthetic",
            )

    def test_auto_loads_local_first(self, tmp_path: Path) -> None:
        """Test auto mode loads local dataset when available."""
        dataset_file = tmp_path / "data" / "test.jsonl"
        dataset_file.parent.mkdir()
        dataset_file.write_text('{"id": 1}\n{"id": 2}\n')

        dataset, name = load_dataset_with_fallback(
            dataset_name="test.jsonl",
            env_root=tmp_path,
            dataset_source="auto",
        )
        assert len(dataset) == 2
        assert name == "test.jsonl"

    def test_auto_falls_back_to_synthetic(self, tmp_path: Path) -> None:
        """Test auto mode falls back to synthetic when local not found."""

        def mock_generator() -> Dataset:
            return Dataset.from_list([{"id": 99}])

        with patch.dict(os.environ, {}, clear=True):
            dataset, name = load_dataset_with_fallback(
                dataset_name="nonexistent.jsonl",
                env_root=tmp_path,
                dataset_source="auto",
                synthetic_generator=mock_generator,
            )
        assert len(dataset) == 1
        assert "synthetic" in name

    def test_auto_no_fallback_raises(self, tmp_path: Path) -> None:
        """Test auto mode raises when no fallback available."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(FileNotFoundError, match="Dataset .* not found"):
                load_dataset_with_fallback(
                    dataset_name="nonexistent.jsonl",
                    env_root=tmp_path,
                    dataset_source="auto",
                )

    def test_local_mode_requires_file(self, tmp_path: Path) -> None:
        """Test local mode raises when file not found."""
        with pytest.raises(FileNotFoundError, match="Local dataset not found"):
            load_dataset_with_fallback(
                dataset_name="nonexistent.jsonl",
                env_root=tmp_path,
                dataset_source="local",
            )

    def test_hub_mode_requires_credentials(self, tmp_path: Path) -> None:
        """Test hub mode raises when credentials not available."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="HF_TOKEN not found"):
                load_dataset_with_fallback(
                    dataset_name="iot23-train-dev-test-v1.jsonl",
                    env_root=tmp_path,
                    dataset_source="hub",
                )

    def test_invalid_source_raises(self, tmp_path: Path) -> None:
        """Test invalid dataset_source raises ValueError."""
        with pytest.raises(ValueError, match="Unknown dataset_source"):
            load_dataset_with_fallback(
                dataset_name="test.jsonl",
                env_root=tmp_path,
                dataset_source="invalid",  # type: ignore
            )

    def test_absolute_path_loading(self, tmp_path: Path) -> None:
        """Test loading dataset from absolute path."""
        dataset_file = tmp_path / "test.jsonl"
        dataset_file.write_text('{"id": 1}\n')

        dataset, name = load_dataset_with_fallback(
            dataset_name=str(dataset_file),
            env_root=Path("/different/path"),
            dataset_source="auto",
        )
        assert len(dataset) == 1
        assert dataset[0]["id"] == 1


class TestHFDatasetMap:
    """Tests for HF_DATASET_MAP configuration."""

    def test_map_contains_e1_datasets(self) -> None:
        """Test dataset map contains E1 datasets."""
        assert "iot23-train-dev-test-v1.jsonl" in HF_DATASET_MAP
        assert "cic-ids-2017-ood-v1.jsonl" in HF_DATASET_MAP
        assert "unsw-nb15-ood-v1.jsonl" in HF_DATASET_MAP

    def test_map_contains_e2_datasets(self) -> None:
        """Test dataset map contains E2 datasets."""
        assert "k8s-labeled-v1.jsonl" in HF_DATASET_MAP
        assert "terraform-labeled-v1.jsonl" in HF_DATASET_MAP
        assert "combined" in HF_DATASET_MAP

    def test_map_entries_have_required_fields(self) -> None:
        """Test all map entries have required fields."""
        for name, metadata in HF_DATASET_MAP.items():
            assert "split" in metadata, f"{name} missing 'split'"
            assert "env" in metadata, f"{name} missing 'env'"
            assert "description" in metadata, f"{name} missing 'description'"

    def test_map_entries_have_valid_env(self) -> None:
        """Test all map entries have valid env values."""
        valid_envs = {"e1", "e2"}
        for name, metadata in HF_DATASET_MAP.items():
            assert metadata["env"] in valid_envs, f"{name} has invalid env: {metadata['env']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
