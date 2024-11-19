#!/usr/bin/env python3
import os
import json
import logging
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from config.json
with open("config.json") as config_file:
    config = json.load(config_file)

# Extract configuration values
GITLAB_API_BASE = config.get("gitlab_api_base", "https://gitlab.ellisbs.co.uk/api/v4")
TOKEN_ENV_VAR = config.get("token", "SELF_GITLAB_TOKEN")
PORT = config.get("port", 8000)
GROUP = config.get("group", None) # Optional group to search in

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
            logging.info("Metrics requested and served.")
        else:
            self.send_error(404, "Not Found")

    def do_HEAD(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            logging.info("HEAD request for metrics served.")
        else:
            self.send_error(404, "Not Found")

def get_all_schedules_metrics():
    headers = {"PRIVATE-TOKEN": TOKEN}
    project_metrics = ""

    logging.info("Fetching all projects from GitLab API...")

    # Fetch all projects
    projects_response = requests.get(f"{GITLAB_API_BASE}/projects?per_page=100", headers=headers)
    if projects_response.status_code != 200:
        logging.error(f"Failed to fetch projects: {projects_response.status_code} {projects_response.text}")
        return ""
    
    projects = projects_response.json()
    logging.info(f"Total projects retrieved: {len(projects)}")

    for project in projects:
        project_id = project['id']
        project_path = project['path_with_namespace']

        # Check if a group is specified and if the project belongs to that group
        if GROUP and GROUP not in project_path:
            logging.info(f"Skipping project '{project_path}' as it does not belong to specified group '{GROUP}'.")
            continue

        logging.info(f"Fetching pipeline schedules for project '{project_path}' (ID: {project_id})")
        schedules_response = requests.get(f"{GITLAB_API_BASE}/projects/{project_id}/pipeline_schedules", headers=headers)
        
        if schedules_response.status_code != 200:
            logging.error(f"Failed to fetch schedules for project '{project_path}': {schedules_response.status_code} {schedules_response.text}")
            continue

        schedules = schedules_response.json()
        logging.info(f"Schedules retrieved for project '{project_path}': {len(schedules)}")

        for schedule in schedules:
            schedule_id = schedule['id']
            description = schedule['description']

            logging.info(f"Processing schedule '{description}' (ID: {schedule_id})")
            pipelines_response = requests.get(f"{GITLAB_API_BASE}/projects/{project_id}/pipeline_schedules/{schedule_id}/pipelines?per_page=100", headers=headers)
            
            if pipelines_response.status_code != 200:
                logging.error(f"Failed to fetch pipelines for schedule '{description}' in project '{project_path}': {pipelines_response.status_code} {pipelines_response.text}")
                continue

            pipelines = pipelines_response.json()
            total = len(pipelines)
            logging.info(f"Total pipelines found for schedule '{description}': {total}")

            if total > 0:
                success = sum(1 for p in pipelines if p['status'] == 'success')
                success_rate = (success / total) * 100
                color = "green" if success_rate >= 80 else "amber" if success_rate >= 50 else "red"

                metric_name = f'gitlab_pipeline_schedule_success_rate{{project="{project_path}", schedule="{description}", color="{color}"}}'
                project_metrics += f"{metric_name} {success_rate}\n"
                logging.info(f"Success rate for schedule '{description}' in project '{project_path}': {success_rate:.2f}% (Color: {color})")
            else:
                project_metrics += f'gitlab_pipeline_schedule_success_rate{{project="{project_path}", schedule="{description}", color="no_data"}} 0\n'
                logging.info(f"No data for schedule '{description}' in project '{project_path}'")

    logging.info("Completed fetching all metrics.")
    return project_metrics

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MetricsHandler)
    logging.info(f"Serving metrics on port {PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    if not TOKEN:
        raise EnvironmentError(f"The environment variable '{TOKEN_ENV_VAR}' is not set.")
    run_server()
