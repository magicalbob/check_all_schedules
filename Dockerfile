# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir requests

# Expose the port the app runs on
EXPOSE 9100

# Define environment variable for the GitLab token
ARG SELF_GITLAB_TOKEN="dummy_token"
ENV SELF_GITLAB_TOKEN=$SELF_GITLAB_TOKEN

# Run check_all_schedules.py when the container launches
CMD ["python", "check_all_schedules.py"]
