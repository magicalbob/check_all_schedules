#!/usr/bin/env python3
import os
import time
import requests
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load configuration from config.json
with open("config.json") as config_file:
    config = json.load(config_file)

# Extract configuration values
GITLAB_API_BASE = config.get("gitlab_api_base", "https://gitlab.ellisbs.co.uk/api/v4")
TOKEN_ENV_VAR = config.get("token", "SELF_GITLAB_TOKEN")
PORT = config.get("port", 8000)

# Retrieve the actual token from the specified environment variable
TOKEN = os.getenv(TOKEN_ENV_VAR)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            metrics = get_all_schedules_metrics()
            self.wfile.write(metrics.encode("utf-8"))

    def do_HEAD(self):
        # Respond to HEAD requests with status 200 and appropriate headers
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
        else:
            self.send_error(404, "Not Found")

def get_all_schedules_metrics():
    headers = {"PRIVATE-TOKEN": TOKEN}
    project_metrics = ""

    # Get all projects
    projects = requests.get(f"{GITLAB_API_BASE}/projects?per_page=100", headers=headers).json()
    for project in projects:
        project_id = project['id']
        project_path = project['path_with_namespace']

        # Get pipeline schedules for the project
        schedules = requests.get(f"{GITLAB_API_BASE}/projects/{project_id}/pipeline_schedules", headers=headers).json()

        for schedule in schedules:
            schedule_id = schedule['id']
            description = schedule['description']

            # Get pipelines for the schedule
            pipelines = requests.get(f"{GITLAB_API_BASE}/projects/{project_id}/pipeline_schedules/{schedule_id}/pipelines?per_page=100", headers=headers).json()
            total = len(pipelines)

            if total > 0:
                success = sum(1 for p in pipelines if p['status'] == 'success')
                success_rate = (success / total) * 100
                color = "green" if success_rate >= 80 else "amber" if success_rate >= 50 else "red"

                # Format each metric for Prometheus
                metric_name = f'gitlab_pipeline_schedule_success_rate{{project="{project_path}", schedule="{description}", color="{color}"}}'
                project_metrics += f"{metric_name} {success_rate}\n"
            else:
                project_metrics += f'gitlab_pipeline_schedule_success_rate{{project="{project_path}", schedule="{description}", color="no_data"}} 0\n'

    return project_metrics

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MetricsHandler)
    print(f"Serving metrics on port {PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    # Check if TOKEN is set
    if not TOKEN:
        raise EnvironmentError(f"The environment variable '{TOKEN_ENV_VAR}' is not set.")
    run_server()
