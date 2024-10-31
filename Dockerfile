FROM python:3.9-slim

RUN pip install garminconnect schedule

COPY src/garmin_sync.py /app/garmin_sync.py
COPY src/entrypoint.py /app/entrypoint.py

# Set up the environment
ENV GARMIN_EMAIL=
ENV GARMIN_PASSWORD=

# Create the SQLite database directory
RUN mkdir -p /app/data

# Create the fixture data directory
RUN mkdir -p /app/fixture-data


# Start the scheduled script
CMD ["python", "/app/entrypoint.py", "--sync-type=schedule"]
