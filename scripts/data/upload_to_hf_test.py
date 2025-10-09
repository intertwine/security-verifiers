#!/usr/bin/env python3
"""Unit tests for upload_to_hf.py"""

import os

# Import functions from upload_to_hf
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from upload_to_hf import (
    build_e1_datasets,
    build_e2_datasets,
    create_dataset_card,
    run_build_script,
    upload_to_huggingface,
)


class TestRunBuildScript:
    """Tests for run_build_script function"""

    def test_successful_script_execution(self):
        """Test running a script that succeeds"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("#!/usr/bin/env python3\nprint('success')\n")
            script_path = Path(f.name)

        try:
            result = run_build_script(script_path, [])
            assert result == 0
        finally:
            script_path.unlink()

    def test_failing_script_execution(self):
        """Test running a script that fails"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("#!/usr/bin/env python3\nimport sys\nsys.exit(1)\n")
            script_path = Path(f.name)

        try:
            result = run_build_script(script_path, [])
            assert result == 1
        finally:
            script_path.unlink()

    def test_script_with_arguments(self):
        """Test running a script with command-line arguments"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                "#!/usr/bin/env python3\nimport sys\nassert '--test' in sys.argv\nprint('args received')\n"
            )
            script_path = Path(f.name)

        try:
            result = run_build_script(script_path, ["--test"])
            assert result == 0
        finally:
            script_path.unlink()


class TestBuildE1Datasets:
    """Tests for build_e1_datasets function"""

    @patch("upload_to_hf.run_build_script")
    def test_successful_build(self, mock_run_script):
        """Test successful E1 dataset build"""
        mock_run_script.return_value = 0

        # Create temporary data files to simulate existing datasets
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "environments/sv-env-network-logs/data"
            data_dir.mkdir(parents=True, exist_ok=True)

            # Create mock data files
            files = [
                "iot23-train-dev-test-v1.jsonl",
                "cic-ids-2017-ood-v1.jsonl",
                "unsw-nb15-ood-v1.jsonl",
                "sampling-iot23-v1.json",
                "sampling-e1-ood-v1.json",
            ]
            for fname in files:
                (data_dir / fname).write_text("{}")

            # Patch Path to return our temp directory
            with patch("upload_to_hf.Path") as mock_path:
                mock_path.return_value = data_dir
                result = build_e1_datasets()

            # Verify all expected files are returned
            assert len(result) == 5
            assert "iot23-train-dev-test" in result
            assert "cic-ids-2017-ood" in result
            assert "unsw-nb15-ood" in result

    @patch("upload_to_hf.run_build_script")
    def test_iot23_build_failure(self, mock_run_script):
        """Test E1 build fails when IoT-23 build fails"""
        mock_run_script.return_value = 1

        with pytest.raises(RuntimeError, match="Failed to build E1 IoT-23 dataset"):
            build_e1_datasets()

    @patch("upload_to_hf.run_build_script")
    def test_ood_build_failure(self, mock_run_script):
        """Test E1 build fails when OOD build fails"""
        # First call succeeds (IoT-23), second fails (OOD)
        mock_run_script.side_effect = [0, 1]

        with pytest.raises(RuntimeError, match="Failed to build E1 OOD datasets"):
            build_e1_datasets()


class TestBuildE2Datasets:
    """Tests for build_e2_datasets function"""

    @patch("upload_to_hf.run_build_script")
    def test_successful_build(self, mock_run_script):
        """Test successful E2 dataset build"""
        mock_run_script.return_value = 0

        k8s_root = Path("/fake/k8s")
        tf_root = Path("/fake/tf")

        # Create temporary data files
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "environments/sv-env-config-verification/data"
            data_dir.mkdir(parents=True, exist_ok=True)

            files = [
                "k8s-labeled-v1.jsonl",
                "terraform-labeled-v1.jsonl",
                "tools-versions.json",
                "sampling-e2-v1.json",
            ]
            for fname in files:
                (data_dir / fname).write_text("{}")

            with patch("upload_to_hf.Path") as mock_path:
                mock_path.return_value = data_dir
                result = build_e2_datasets(k8s_root, tf_root)

            assert len(result) == 4
            assert "k8s-labeled" in result
            assert "terraform-labeled" in result

    @patch("upload_to_hf.run_build_script")
    def test_build_failure(self, mock_run_script):
        """Test E2 build fails when build script fails"""
        mock_run_script.return_value = 1

        k8s_root = Path("/fake/k8s")
        tf_root = Path("/fake/tf")

        with pytest.raises(RuntimeError, match="Failed to build E2 datasets"):
            build_e2_datasets(k8s_root, tf_root)


class TestCreateDatasetCard:
    """Tests for create_dataset_card function"""

    def test_creates_valid_markdown(self):
        """Test that dataset card is valid markdown with metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {
                "train": Path(tmpdir) / "train.jsonl",
                "test": Path(tmpdir) / "test.jsonl",
            }
            for path in files.values():
                path.write_text('{"example": "data"}\n')

            card = create_dataset_card("test-dataset", "A test dataset", files)

            # Check for key components
            assert "# test-dataset" in card
            assert "A test dataset" in card
            assert "train.jsonl" in card
            assert "test.jsonl" in card
            assert "license: mit" in card
            assert "task_categories:" in card
            assert "from datasets import load_dataset" in card

    def test_handles_missing_files(self):
        """Test that card handles missing files gracefully"""
        files = {
            "missing": Path("/nonexistent/file.jsonl"),
        }

        card = create_dataset_card("test-dataset", "Test", files)

        # Should still create a valid card
        assert "# test-dataset" in card
        # Missing file should not appear in the card
        assert "file.jsonl" not in card

    def test_shows_file_sizes(self):
        """Test that file sizes are included in card"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.jsonl"
            test_file.write_text("x" * 2048)  # 2KB file

            files = {"test": test_file}
            card = create_dataset_card("test-dataset", "Test", files)

            # Should show file size
            assert "KB" in card
            assert "test.jsonl" in card


class TestUploadToHuggingface:
    """Tests for upload_to_huggingface function"""

    @patch("upload_to_hf.HfApi")
    @patch("upload_to_hf.create_repo")
    def test_successful_upload(self, mock_create_repo, mock_hf_api):
        """Test successful upload to HuggingFace"""
        # Mock API
        mock_api = Mock()
        # Mock repo_info to simulate existing repo
        mock_api.repo_info.return_value = {"id": "test-org/test-dataset"}
        mock_hf_api.return_value = mock_api

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.jsonl"
            test_file.write_text('{"test": "data"}\n')

            files = {"test": test_file}

            url = upload_to_huggingface(
                dataset_name="test-dataset",
                hf_org="test-org",
                files=files,
                description="Test dataset",
                token="fake-token",
            )

            # Verify repo_info was called to check if repo exists
            mock_api.repo_info.assert_called_once()

            # Verify file upload
            assert mock_api.upload_file.call_count == 2  # data file + README

            # Verify returned URL
            assert url == "https://huggingface.co/datasets/test-org/test-dataset"

    @patch("upload_to_hf.HfApi")
    @patch("upload_to_hf.create_repo")
    def test_handles_missing_files(self, mock_create_repo, mock_hf_api):
        """Test that upload handles missing files gracefully"""
        mock_api = Mock()
        # Mock repo_info to simulate existing repo
        mock_api.repo_info.return_value = {"id": "test-org/test-dataset"}
        mock_hf_api.return_value = mock_api

        files = {"missing": Path("/nonexistent/file.jsonl")}

        upload_to_huggingface(
            dataset_name="test-dataset",
            hf_org="test-org",
            files=files,
            description="Test dataset",
            token="fake-token",
        )

        # Verify repo_info was called to check if repo exists
        mock_api.repo_info.assert_called_once()

        # Should only upload README (not missing file)
        assert mock_api.upload_file.call_count == 1

    @patch("upload_to_hf.HfApi")
    @patch("upload_to_hf.create_repo")
    def test_handles_permission_error(self, mock_create_repo, mock_hf_api):
        """Test that upload handles permission errors gracefully"""
        mock_api = Mock()
        # Mock repo_info to raise exception (repo doesn't exist)
        mock_api.repo_info.side_effect = Exception("Not found")
        # Mock create_repo to raise 403 error
        mock_create_repo.side_effect = Exception(
            "403 Forbidden: You don't have the rights to create a dataset"
        )
        # Mock whoami for username suggestion
        mock_api.whoami.return_value = {"name": "test-user"}
        mock_hf_api.return_value = mock_api

        files = {"test": Path("/fake/file.jsonl")}

        # Should raise RuntimeError with helpful message
        with pytest.raises(RuntimeError, match="permission denied"):
            upload_to_huggingface(
                dataset_name="test-dataset",
                hf_org="test-org",
                files=files,
                description="Test dataset",
                token="fake-token",
            )

    @patch("upload_to_hf.HfApi")
    @patch("upload_to_hf.create_repo")
    def test_handles_upload_errors(self, mock_create_repo, mock_hf_api):
        """Test that upload handles errors gracefully"""
        mock_api = Mock()
        # Mock repo_info to simulate existing repo
        mock_api.repo_info.return_value = {"id": "test-org/test-dataset"}
        mock_api.upload_file.side_effect = Exception("Upload failed")
        mock_hf_api.return_value = mock_api

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.jsonl"
            test_file.write_text('{"test": "data"}\n')

            files = {"test": test_file}

            # Should not raise, just print errors
            url = upload_to_huggingface(
                dataset_name="test-dataset",
                hf_org="test-org",
                files=files,
                description="Test dataset",
                token="fake-token",
            )

            # Should still return URL even if uploads failed
            assert url == "https://huggingface.co/datasets/test-org/test-dataset"


class TestMainFunction:
    """Tests for main function and environment variable loading"""

    @patch("upload_to_hf.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_hf_token(self, mock_load_dotenv):
        """Test that script exits when HF_TOKEN is missing"""
        with patch("sys.argv", ["upload_to_hf.py", "--e1-only"]):
            with pytest.raises(SystemExit) as exc_info:
                from upload_to_hf import main

                main()

            assert exc_info.value.code == 1
            mock_load_dotenv.assert_called_once()

    @patch("upload_to_hf.load_dotenv")
    @patch.dict(os.environ, {"HF_TOKEN": "fake-token"}, clear=True)
    @patch("upload_to_hf.build_e1_datasets")
    @patch("upload_to_hf.upload_to_huggingface")
    def test_loads_dotenv(self, mock_upload, mock_build_e1, mock_load_dotenv):
        """Test that main function calls load_dotenv"""
        mock_build_e1.return_value = {}
        mock_upload.return_value = "https://example.com"

        with patch("sys.argv", ["upload_to_hf.py", "--e1-only"]):
            try:
                from upload_to_hf import main

                main()
            except SystemExit:
                pass  # Expected when build returns empty dict

        # Verify load_dotenv was called
        mock_load_dotenv.assert_called_once()

    @patch("upload_to_hf.load_dotenv")
    @patch.dict(os.environ, {"HF_TOKEN": "test-token"}, clear=True)
    @patch("upload_to_hf.build_e1_datasets")
    @patch("upload_to_hf.upload_to_huggingface")
    def test_e1_only_flag(self, mock_upload, mock_build_e1, mock_load_dotenv):
        """Test --e1-only flag"""
        mock_build_e1.return_value = {"test": Path("/fake/file.jsonl")}
        mock_upload.return_value = "https://example.com"

        with patch("sys.argv", ["upload_to_hf.py", "--e1-only"]):
            from upload_to_hf import main

            main()

        # Should only build E1
        mock_build_e1.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
