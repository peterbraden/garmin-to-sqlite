FROM python:3.9-slim

RUN pip install garminconnect schedule

COPY garmin_sync.py /app/garmin_sync.py
COPY run_daily.py /app/run_daily.py

# Set up the environment
ENV GARMIN_EMAIL=
ENV GARMIN_PASSWORD=

# Create the SQLite database directory
RUN mkdir -p /app/data
RUN mkdir -p /app/fixture-data


# Start the scheduled script
CMD ["python", "/app/run_daily.py"]
