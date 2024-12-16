# check_all_schedules

## Description
`check_all_schedules` is a Python-based application designed to interface with GitLab's API and retrieve metrics about pipeline schedules for projects. The application exposes a simple HTTP server which provides Prometheus-style metrics that can be used for monitoring the success rates of your GitLab CI/CD pipeline schedules.

## Features
- Fetches all projects from the specified GitLab API.
- Retrieves pipeline schedules for each project and their corresponding pipeline run statuses.
- Calculates success rates for the pipelines and formats them for Prometheus consumption.
- Exposes a /metrics endpoint that can be scraped by Prometheus or similar monitoring tools.

## Getting Started

### Prerequisites
- Python 3.6 or higher
- `requests` library (install it via pip if not available)

### Installation
1. Clone the repository to your local machine:

   ```bash
   git clone http://192.168.0.124/ian/check_all_schedules.git
   cd check_all_schedules
   ```

2. Install the required Python libraries:

   ```bash
   pip install requests
   ```

3. Create a `config.json` file in the root directory of the project. Use the provided `config.json` as a template:

   ```json
   {
     "gitlab_api_base": "https://gitlab.ellisbs.co.uk/api/v4",
     "token": "SELF_GITLAB_TOKEN",
     "port": 9100
   }
   ```

   Replace `SELF_GITLAB_TOKEN` with the actual token that has access to the GitLab API.

### Usage
To run the application, use the following command:

```bash
python check_all_schedules.py
```

The server will start, and you can access the metrics at `http://<your_host>:9100/metrics`.

### Accessing Metrics
Once the server is running, you can scrape the metrics by integrating your Prometheus server configuration with the endpoint:

```
scrape_configs:
  - job_name: 'gitlab_pipeline_schedules'
    static_configs:
      - targets: ['<your_host>:9100']
    metrics_path: '/metrics'
    scheme: http
    honor_labels: true
```

### Docker

A `Dockerfile` is provided to run the project as a cotainer.

Build it like this:

```
docker build -t docker.ellisbs.co.uk:7070/check_all_schedules:2024.11.24.14.46 .
```

then push it and run it like this:

```
docker run -de "SELF_GITLAB_TOKEN=$SELF_GITLAB_TOKEN" \
           -p 9100:9100 \
	   --name check_all_schedules \
           docker.ellisbs.co.uk:5190/check_all_schedules:2024.11.24.14.46 
```

## Support
If you encounter any issues or have questions, please feel free to open an issue on the repository.

## Contributing
Contributions are welcome! If you want to improve the project, please fork the repository and submit a pull request with your changes.

## Authors and Acknowledgment
This project has been developed by [Your Name/Organization]. Special thanks to the contributors who provided feedback and improvements.

## License
This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for more details.

## Project Status
This project is actively maintained, and contributions are encouraged. Feel free to reach out for any issues you might encounter.
