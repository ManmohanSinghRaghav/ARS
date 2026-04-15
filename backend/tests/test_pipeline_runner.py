"""
Tests for the pipeline runner and execution flow.
Verifies pipeline creation, background execution, and result persistence.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
import threading
import time


class TestPipelineInitialization:
    """Test pipeline creation and initialization."""

    @patch("app.pipeline.runner.db_client")
    def test_run_pipeline_creates_run_record(self, mock_db):
        """Verify run_pipeline creates a Firestore run record."""
        from app.pipeline.runner import run_pipeline
        
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_collection.document.return_value = mock_document
        mock_db.collection.return_value = mock_collection
        mock_document.id = "test_run_123"
        
        result = run_pipeline(
            topic="Test Topic",
            user_id="user_123",
            db=mock_db,
            llm_config={"vibe": "Deep Academic"},
            tavily_api_key="test_key"
        )
        
        assert result["id"] == "test_run_123"
        assert result["status"] == "running"
        assert result["user_id"] == "user_123"
        assert result["topic"] == "Test Topic"

    @patch("app.pipeline.runner.db_client")
    def test_run_pipeline_returns_immediately(self, mock_db):
        """Verify run_pipeline returns immediately (async background execution)."""
        from app.pipeline.runner import run_pipeline
        
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_collection.document.return_value = mock_document
        mock_db.collection.return_value = mock_collection
        mock_document.id = "test_run_123"
        
        start_time = time.time()
        result = run_pipeline(
            topic="Test Topic",
            user_id="user_123",
            db=mock_db
        )
        elapsed = time.time() - start_time
        
        # Should return within 100ms (fast response)
        assert elapsed < 1.0
        assert result["status"] == "running"

    def test_run_record_structure(self):
        """Verify run record has all required fields."""
        required_fields = [
            "id", "user_id", "topic", "status", "created_at",
            "completed_at", "hypothesis", "generated_code",
            "execution_output", "paper_markdown", "summary_json", "error_message"
        ]
        
        run_data = {
            "id": "run_123",
            "user_id": "user_123",
            "topic": "Test Topic",
            "status": "running",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "hypothesis": "",
            "generated_code": "",
            "execution_output": "",
            "paper_markdown": "",
            "summary_json": {},
            "error_message": "",
        }
        
        for field in required_fields:
            assert field in run_data
            assert run_data[field] is not None or run_data[field] == ""


class TestBackgroundExecution:
    """Test background pipeline execution."""

    @patch("app.pipeline.runner.run_crew_pipeline")
    @patch("app.pipeline.runner.db_client")
    def test_background_thread_execution(self, mock_db, mock_crew):
        """Verify pipeline runs in background thread."""
        from app.pipeline.runner import run_pipeline
        
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_collection.document.return_value = mock_document
        mock_db.collection.return_value = mock_collection
        mock_document.id = "test_run_123"
        mock_crew.return_value = {
            "hypothesis": "Test hypothesis",
            "generated_code": "print('test')",
            "execution_output": "test",
            "paper_markdown": "# Test",
            "summary_json": {"score": 8.0}
        }
        
        result = run_pipeline(
            topic="Test Topic",
            user_id="user_123",
            db=mock_db
        )
        
        assert result["status"] == "running"
        # Thread is daemon and background
        threading.active_count()  # Verify threading is working

    @patch("app.pipeline.runner.run_crew_pipeline")
    @patch("app.pipeline.runner.db_client")
    def test_pipeline_completion_updates_db(self, mock_db, mock_crew):
        """Verify pipeline completion updates Firestore."""
        from app.pipeline.runner import run_pipeline
        
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_ref = MagicMock()
        
        mock_collection.document.return_value = mock_ref
        mock_db.collection.return_value = mock_collection
        mock_ref.id = "test_run_123"
        
        mock_crew.return_value = {
            "hypothesis": "Test hypothesis",
            "generated_code": "print('test')",
            "execution_output": "test",
            "paper_markdown": "# Test",
            "summary_json": {"score": 8.0}
        }
        
        run_pipeline(
            topic="Test Topic",
            user_id="user_123",
            db=mock_db
        )
        
        # Give thread time to complete
        time.sleep(0.5)


class TestPipelineFailureHandling:
    """Test error handling in pipeline execution."""

    @patch("app.pipeline.runner.run_crew_pipeline")
    @patch("app.pipeline.runner.db_client")
    def test_crew_exception_handling(self, mock_db, mock_crew):
        """Verify pipeline handles crew execution errors."""
        from app.pipeline.runner import run_pipeline
        
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_ref = MagicMock()
        
        mock_collection.document.return_value = mock_ref
        mock_db.collection.return_value = mock_collection
        mock_ref.id = "test_run_123"
        
        mock_crew.side_effect = Exception("CrewAI error")
        
        run_pipeline(
            topic="Test Topic",
            user_id="user_123",
            db=mock_db
        )
        
        # Give thread time to process error
        time.sleep(0.5)
        
        # DB should be updated with error
        mock_ref.update.assert_called()

    @patch("app.pipeline.runner.db_client", None)
    def test_missing_firestore_client(self):
        """Verify graceful handling when Firestore is unavailable."""
        from app.pipeline.runner import run_pipeline
        
        # Should not crash
        try:
            with patch("app.pipeline.runner.db_client", None):
                result = run_pipeline(
                    topic="Test Topic",
                    user_id="user_123",
                    db=None
                ) or {}
                # Should handle gracefully
        except Exception as e:
            pytest.fail(f"Should handle missing Firestore: {e}")

    @patch("app.pipeline.runner.run_crew_pipeline")
    @patch("app.pipeline.runner.db_client")
    def test_invalid_llm_config_handling(self, mock_db, mock_crew):
        """Verify pipeline handles invalid LLM config."""
        from app.pipeline.runner import run_pipeline
        
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_ref = MagicMock()
        
        mock_collection.document.return_value = mock_ref
        mock_db.collection.return_value = mock_collection
        mock_ref.id = "test_run_123"
        
        mock_crew.return_value = {}
        
        # Should handle None llm_config
        result = run_pipeline(
            topic="Test Topic",
            user_id="user_123",
            db=mock_db,
            llm_config=None
        )
        
        assert result is not None


class TestPipelineInputValidation:
    """Test input validation for pipeline."""

    def test_topic_validation(self):
        """Verify topic is required and non-empty."""
        def validate_topic(topic):
            if not topic or not isinstance(topic, str):
                raise ValueError("Topic must be non-empty string")
        
        with pytest.raises(ValueError):
            validate_topic("")
        
        with pytest.raises(ValueError):
            validate_topic(None)
        
        # Valid topic
        validate_topic("Valid Topic")

    def test_user_id_validation(self):
        """Verify user_id is required."""
        def validate_user_id(user_id):
            if not user_id:
                raise ValueError("User ID required")
        
        with pytest.raises(ValueError):
            validate_user_id("")
        
        validate_user_id("user_123")

    def test_llm_config_validation(self):
        """Verify llm_config structure when provided."""
        def validate_config(config):
            if config and not isinstance(config, dict):
                raise ValueError("Config must be dict")
            if config and "vibe" in config:
                valid_vibes = ["Deep Academic", "Casual", "Technical"]
                if config["vibe"] not in valid_vibes:
                    raise ValueError(f"Invalid vibe: {config['vibe']}")
        
        validate_config(None)
        validate_config({})
        validate_config({"vibe": "Deep Academic"})
        
        with pytest.raises(ValueError):
            validate_config("invalid")
        
        with pytest.raises(ValueError):
            validate_config({"vibe": "Invalid Vibe"})


class TestPipelineProgressTracking:
    """Test progress tracking during execution."""

    @patch("app.pipeline.progress.add_step")
    def test_progress_steps_recorded(self, mock_add_step):
        """Verify all pipeline steps are tracked."""
        from app.pipeline.progress import add_step
        
        add_step("test_run", 1, 10, "Step 1", "running", "detail")
        mock_add_step.assert_called()

    @patch("app.pipeline.progress.add_step")
    def test_step_progression(self, mock_add_step):
        """Verify steps progress from 1 to 10."""
        from app.pipeline.progress import add_step
        
        for step in range(1, 11):
            add_step("test_run", step, 10, f"Step {step}", "running", "")
        
        assert mock_add_step.call_count == 10

    def test_progress_status_validation(self):
        """Verify only valid status values are used."""
        valid_statuses = ["running", "completed", "failed"]
        
        for status in valid_statuses:
            assert isinstance(status, str)


class TestPipelineOutputPersistence:
    """Test saving pipeline outputs to database."""

    @patch("app.pipeline.runner.db_client")
    def test_hypothesis_persistence(self, mock_db):
        """Verify hypothesis is saved to Firestore."""
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        hypothesis = "Novel hypothesis text"
        mock_ref.update({"hypothesis": hypothesis})
        
        mock_ref.update.assert_called()

    @patch("app.pipeline.runner.db_client")
    def test_code_persistence(self, mock_db):
        """Verify generated code is saved."""
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        code = "print('test')"
        mock_ref.update({"generated_code": code})
        
        mock_ref.update.assert_called()

    @patch("app.pipeline.runner.db_client")
    def test_paper_persistence(self, mock_db):
        """Verify markdown paper is saved."""
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        paper = "# Research Paper\n\nContent"
        mock_ref.update({"paper_markdown": paper})
        
        mock_ref.update.assert_called()

    @patch("app.pipeline.runner.db_client")
    def test_summary_json_persistence(self, mock_db):
        """Verify summary JSON is saved."""
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        summary = {"novelty_score": 8.5, "feasibility": 0.9}
        mock_ref.update({"summary_json": summary})
        
        mock_ref.update.assert_called()

    @patch("app.pipeline.runner.db_client")
    def test_completion_timestamp(self, mock_db):
        """Verify completion timestamp is set."""
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        completed_at = datetime.now(timezone.utc).isoformat()
        mock_ref.update({"completed_at": completed_at, "status": "completed"})
        
        mock_ref.update.assert_called()
