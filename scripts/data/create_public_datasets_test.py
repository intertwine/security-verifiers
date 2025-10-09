#!/usr/bin/env python3
"""Unit tests for create_public_datasets.py"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import functions from create_public_datasets
sys.path.insert(0, str(Path(__file__).parent))
from create_public_datasets import (
    create_e1_model_card,
    create_e2_model_card,
    upload_public_dataset,
)


class TestModelCards:
    """Tests for model card generation"""

    def test_e1_model_card_structure(self):
        """Test E1 model card has required sections"""
        card = create_e1_model_card()

        # Check for key sections
        assert "# 🔒 Security Verifiers E1" in card
        assert "Why Private Datasets?" in card
        assert "Training contamination" in card
        assert "Dataset Composition" in card
        assert "Requesting Access" in card
        assert "GitHub Issues" in card
        assert "license: mit" in card
        assert "metadata-only" in card

    def test_e1_model_card_has_datasets(self):
        """Test E1 model card lists all datasets"""
        card = create_e1_model_card()

        assert "IoT-23" in card
        assert "CIC-IDS-2017" in card
        assert "UNSW-NB15" in card
        assert "1,800" in card  # Sample count
        assert "600" in card  # OOD sample counts

    def test_e1_model_card_has_rewards(self):
        """Test E1 model card describes reward components"""
        card = create_e1_model_card()

        assert "Accuracy" in card
        assert "Calibration" in card
        assert "Abstention" in card
        assert "Asymmetric" in card

    def test_e2_model_card_structure(self):
        """Test E2 model card has required sections"""
        card = create_e2_model_card()

        # Check for key sections
        assert "# 🔒 Security Verifiers E2" in card
        assert "Why Private Datasets?" in card
        assert "Training contamination" in card
        assert "Dataset Composition" in card
        assert "Requesting Access" in card
        assert "GitHub Issues" in card
        assert "license: mit" in card
        assert "metadata-only" in card

    def test_e2_model_card_has_tools(self):
        """Test E2 model card lists all tools"""
        card = create_e2_model_card()

        assert "KubeLinter" in card
        assert "Semgrep" in card
        assert "OPA" in card
        assert "Rego" in card

    def test_e2_model_card_has_configs(self):
        """Test E2 model card lists config types"""
        card = create_e2_model_card()

        assert "Kubernetes" in card
        assert "Terraform" in card
        assert "manifests" in card or "YAML" in card

    def test_e2_model_card_has_performance(self):
        """Test E2 model card mentions multi-turn performance"""
        card = create_e2_model_card()

        assert "0.93" in card or "93%" in card
        assert "0.62" in card or "62%" in card
        assert "tool" in card.lower()

    def test_model_cards_have_citation(self):
        """Test both model cards have citation sections"""
        e1_card = create_e1_model_card()
        e2_card = create_e2_model_card()

        for card in [e1_card, e2_card]:
            assert "@misc{security-verifiers" in card
            assert "bibtex" in card
            assert "2025" in card

    def test_model_cards_have_links(self):
        """Test both model cards have important links"""
        e1_card = create_e1_model_card()
        e2_card = create_e2_model_card()

        for card in [e1_card, e2_card]:
            assert "github.com/intertwine/security-verifiers" in card
            assert "issues" in card.lower()
            assert "Prime Intellect" in card or "Verifiers" in card


class TestUploadPublicDataset:
    """Tests for upload_public_dataset function"""

    @patch("create_public_datasets.HfApi")
    @patch("create_public_datasets.create_repo")
    def test_creates_public_repo(self, mock_create_repo, mock_hf_api):
        """Test that repo is created as PUBLIC"""
        mock_api = Mock()
        # Mock repo_info to raise exception (repo doesn't exist)
        mock_api.repo_info.side_effect = Exception("Not found")
        mock_hf_api.return_value = mock_api

        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "sampling.json"
            metadata_file.write_text('{"test": "metadata"}')

            metadata_files = {"sampling": metadata_file}

            upload_public_dataset(
                dataset_name="test-dataset-metadata",
                hf_org="test-org",
                metadata_files=metadata_files,
                card_content="# Test Card",
                token="fake-token",
            )

            # Verify create_repo was called with private=False
            mock_create_repo.assert_called_once()
            call_kwargs = mock_create_repo.call_args[1]
            assert call_kwargs["private"] is False
            assert call_kwargs["repo_type"] == "dataset"

    @patch("create_public_datasets.HfApi")
    @patch("create_public_datasets.create_repo")
    def test_uploads_metadata_files(self, mock_create_repo, mock_hf_api):
        """Test that metadata files are uploaded"""
        mock_api = Mock()
        # Mock repo_info to simulate existing repo
        mock_api.repo_info.return_value = {"id": "test-org/test-dataset-metadata"}
        mock_hf_api.return_value = mock_api

        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "sampling.json"
            metadata_file.write_text('{"test": "metadata"}')

            metadata_files = {"sampling": metadata_file}

            upload_public_dataset(
                dataset_name="test-dataset-metadata",
                hf_org="test-org",
                metadata_files=metadata_files,
                card_content="# Test Card",
                token="fake-token",
            )

            # Verify files were uploaded (metadata + README)
            assert mock_api.upload_file.call_count == 2

    @patch("create_public_datasets.HfApi")
    @patch("create_public_datasets.create_repo")
    def test_handles_missing_metadata(self, mock_create_repo, mock_hf_api):
        """Test that missing metadata files are skipped gracefully"""
        mock_api = Mock()
        mock_api.repo_info.return_value = {"id": "test-org/test-dataset-metadata"}
        mock_hf_api.return_value = mock_api

        metadata_files = {"missing": Path("/nonexistent/file.json")}

        upload_public_dataset(
            dataset_name="test-dataset-metadata",
            hf_org="test-org",
            metadata_files=metadata_files,
            card_content="# Test Card",
            token="fake-token",
        )

        # Should only upload README (not missing metadata)
        assert mock_api.upload_file.call_count == 1

    @patch("create_public_datasets.HfApi")
    @patch("create_public_datasets.create_repo")
    def test_uploads_readme(self, mock_create_repo, mock_hf_api):
        """Test that README is uploaded with card content"""
        mock_api = Mock()
        mock_api.repo_info.return_value = {"id": "test-org/test-dataset-metadata"}
        mock_hf_api.return_value = mock_api

        card_content = "# Test Model Card\nThis is a test."

        upload_public_dataset(
            dataset_name="test-dataset-metadata",
            hf_org="test-org",
            metadata_files={},
            card_content=card_content,
            token="fake-token",
        )

        # Verify README was uploaded
        assert mock_api.upload_file.call_count == 1
        # Check that README.md was uploaded
        call_args = mock_api.upload_file.call_args[1]
        assert call_args["path_in_repo"] == "README.md"

    @patch("create_public_datasets.HfApi")
    @patch("create_public_datasets.create_repo")
    def test_returns_correct_url(self, mock_create_repo, mock_hf_api):
        """Test that correct HuggingFace URL is returned"""
        mock_api = Mock()
        mock_api.repo_info.return_value = {"id": "test-org/test-dataset-metadata"}
        mock_hf_api.return_value = mock_api

        url = upload_public_dataset(
            dataset_name="test-dataset-metadata",
            hf_org="test-org",
            metadata_files={},
            card_content="# Test",
            token="fake-token",
        )

        assert url == "https://huggingface.co/datasets/test-org/test-dataset-metadata"


class TestMainFunction:
    """Tests for main function logic"""

    @patch("create_public_datasets.load_dotenv")
    @patch.dict("os.environ", {}, clear=True)
    def test_requires_hf_token(self, mock_load_dotenv):
        """Test that script exits when HF_TOKEN is missing"""
        with patch("sys.argv", ["create_public_datasets.py", "--hf-org", "test"]):
            with pytest.raises(SystemExit) as exc_info:
                from create_public_datasets import main

                main()

            assert exc_info.value.code == 1
            mock_load_dotenv.assert_called_once()

    @patch("create_public_datasets.load_dotenv")
    @patch.dict("os.environ", {"HF_TOKEN": "fake-token"}, clear=True)
    def test_detects_missing_metadata_files(self, mock_load_dotenv, capsys):
        """Test that script warns about missing metadata files"""
        with patch("sys.argv", ["create_public_datasets.py", "--hf-org", "test", "--e1-only"]):
            with patch("create_public_datasets.Path") as mock_path:
                # Mock metadata files as not existing
                mock_file = Mock()
                mock_file.exists.return_value = False
                mock_path.return_value = mock_file

                with pytest.raises(SystemExit):
                    from create_public_datasets import main

                    main()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
