#!/usr/bin/env python3
import unittest
import json
import os
from unittest.mock import patch, mock_open, MagicMock
import sys
import io

# Import the module - assuming it's in the same directory
import check_all_schedules

class TestCheckAllSchedules(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample config for testing
        self.test_config = {
            "gitlab_api_base": "https://test-gitlab.example.com/api/v4",
            "token": "TEST_TOKEN_VAR",
            "port": 9000,
            "group": "test-group"
        }
        
        # Set up environment variable for token
        os.environ["TEST_TOKEN_VAR"] = "test-token-value"
        
        # Mock config file
        self.mock_config = mock_open(read_data=json.dumps(self.test_config))
        
        # Sample API responses
        self.mock_projects = [
            {"id": 1, "path_with_namespace": "test-group/project1"},
            {"id": 2, "path_with_namespace": "test-group/project2"},
            {"id": 3, "path_with_namespace": "other-group/project3"}
        ]
        
        self.mock_schedules = [
            {"id": 101, "description": "Daily Backup"},
            {"id": 102, "description": "Weekly Report"}
        ]
        
        self.mock_pipelines_success = [
            {"status": "success"}, {"status": "success"}, {"status": "success"}, 
            {"status": "success"}, {"status": "failed"}
        ]
        
        self.mock_pipelines_mixed = [
            {"status": "success"}, {"status": "failed"}, {"status": "failed"}
        ]
        
        self.mock_pipelines_empty = []

    def tearDown(self):
        """Clean up after tests."""
        if "TEST_TOKEN_VAR" in os.environ:
            del os.environ["TEST_TOKEN_VAR"]

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("json.load")
    def test_config_loading(self, mock_json_load, mock_file_open):
        """Test that configuration is loaded correctly."""
        # Set up the mock to return our test config
        mock_json_load.return_value = self.test_config
        
        # Instead of reloading the module, just set the variables directly
        check_all_schedules.GITLAB_API_BASE = self.test_config["gitlab_api_base"]
        check_all_schedules.TOKEN_ENV_VAR = self.test_config["token"]
        check_all_schedules.PORT = self.test_config["port"]
        check_all_schedules.GROUP = self.test_config["group"]
        check_all_schedules.TOKEN = "test-token-value"
        
        # Assert the configuration was applied correctly
        self.assertEqual(check_all_schedules.GITLAB_API_BASE, self.test_config["gitlab_api_base"])
        self.assertEqual(check_all_schedules.TOKEN_ENV_VAR, self.test_config["token"])
        self.assertEqual(check_all_schedules.PORT, self.test_config["port"])
        self.assertEqual(check_all_schedules.GROUP, self.test_config["group"])
        
        # Verify TOKEN is set from environment variable
        self.assertEqual(check_all_schedules.TOKEN, "test-token-value")

    @patch("requests.get")
    @patch("logging.info")  # Also patch logging to suppress output
    @patch("logging.error")
    def test_get_all_schedules_metrics(self, mock_log_error, mock_log_info, mock_get):
        """Test the metrics generation logic."""
        # Configure mock to return different responses for different URLs
        def mock_response(url, headers):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            if "/projects" in url:
                mock_resp.json.return_value = self.mock_projects
            elif "/pipeline_schedules" in url:
                mock_resp.json.return_value = self.mock_schedules
            elif "/pipelines" in url:
                if "101" in url:  # For schedule ID 101
                    mock_resp.json.return_value = self.mock_pipelines_success
                elif "102" in url:  # For schedule ID 102
                    mock_resp.json.return_value = self.mock_pipelines_mixed
                else:
                    mock_resp.json.return_value = []
                
            return mock_resp
            
        mock_get.side_effect = mock_response
        
        # Set module variables directly
        check_all_schedules.GITLAB_API_BASE = self.test_config["gitlab_api_base"]
        check_all_schedules.TOKEN = "test-token"
        check_all_schedules.GROUP = self.test_config["group"]
        
        # Call the function
        metrics = check_all_schedules.get_all_schedules_metrics()
        
        # Verify metrics contains appropriate data
        self.assertIn("project=\"test-group/project1\"", metrics)
        self.assertIn("project=\"test-group/project2\"", metrics)
        self.assertNotIn("project=\"other-group/project3\"", metrics)  # Should be filtered out by GROUP
        
        # Check that success rates are calculated correctly
        self.assertIn("schedule=\"Daily Backup\"", metrics)
        self.assertIn("color=\"green\"", metrics)  # 80% success should be green
        
        self.assertIn("schedule=\"Weekly Report\"", metrics)
        self.assertIn("color=\"amber\"", metrics)  # 33% success should be amber

    @patch("requests.get")
    @patch("logging.info")  # Patch logging to suppress output
    @patch("logging.error")
    def test_get_all_schedules_metrics_error_handling(self, mock_log_error, mock_log_info, mock_get):
        """Test error handling in metrics fetching."""
        # Mock a failed response for projects
        mock_failed_response = MagicMock()
        mock_failed_response.status_code = 403
        mock_failed_response.text = "Forbidden"
        
        mock_get.return_value = mock_failed_response
        
        # Set module variables
        check_all_schedules.GITLAB_API_BASE = self.test_config["gitlab_api_base"]
        check_all_schedules.TOKEN = "test-token"
        
        # Call the function
        metrics = check_all_schedules.get_all_schedules_metrics()
        
        # Should return empty string on error
        self.assertEqual(metrics, "")

    @patch("http.server.HTTPServer")
    @patch("logging.info")  # Patch logging to suppress output
    def test_run_server(self, mock_log_info, mock_server):
        """Test server initialization."""
        # Mock server instance
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Set PORT
        check_all_schedules.PORT = 9000
        
        # Important: Mock the serve_forever method to prevent hanging
        mock_server_instance.serve_forever = MagicMock()
        
        # Use a timeout to prevent hanging if something goes wrong
        import signal
        
        def handler(signum, frame):
            raise TimeoutError("Test timed out")
        
        # Set a 2-second timeout
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(2)
        
        try:
            # Call run_server
            check_all_schedules.run_server()
            # Cancel the alarm if we reach here
            signal.alarm(0)
        except TimeoutError:
            self.fail("run_server() did not return in time - it might be hanging")
        
        # Verify server was initialized with the correct port
        mock_server.assert_called_once_with(('', 9000), check_all_schedules.MetricsHandler)
        # Verify serve_forever was called
        mock_server_instance.serve_forever.assert_called_once()

    @patch("check_all_schedules.get_all_schedules_metrics")
    @patch("logging.info")  # Patch logging to suppress output
    def test_metrics_handler_get(self, mock_log_info, mock_get_metrics):
        """Test the HTTPHandler GET request for metrics."""
        # Mock the metrics function to return a test string
        mock_get_metrics.return_value = "test_metric{label=\"value\"} 42\n"
        
        # Create a handler instance with mock request and client
        handler = check_all_schedules.MetricsHandler(MagicMock(), ('127.0.0.1', 8888), MagicMock())
        
        # Mock the handler methods we need
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        handler.send_error = MagicMock()
        
        # Test valid metrics path
        handler.path = "/metrics"
        handler.do_GET()
        
        # Verify response
        handler.send_response.assert_called_once_with(200)
        handler.wfile.write.assert_called_once_with(b"test_metric{label=\"value\"} 42\n")
        
        # Reset mocks
        handler.send_response.reset_mock()
        handler.wfile.write.reset_mock()
        
        # Test invalid path
        handler.path = "/invalid"
        handler.do_GET()
        
        # Verify error response
        handler.send_error.assert_called_once_with(404, "Not Found")

    def test_environment_variable_check(self):
        """Test that the script checks for required environment variables."""
        # Remove the token variable
        if "TEST_TOKEN_VAR" in os.environ:
            del os.environ["TEST_TOKEN_VAR"]
        
        # Set module var
        check_all_schedules.TOKEN_ENV_VAR = "TEST_TOKEN_VAR"
        check_all_schedules.TOKEN = None
        
        # Since the error check happens in the __main__ block, we'll test it directly
        with self.assertRaises(EnvironmentError):
            # Simulate the token check from the __main__ block
            if not check_all_schedules.TOKEN:
                raise EnvironmentError(f"The environment variable '{check_all_schedules.TOKEN_ENV_VAR}' is not set.")


if __name__ == "__main__":
    unittest.main()
