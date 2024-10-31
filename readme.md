# Garmin to SQLite

This project provides a docker image to sync Garmin activity to a sqlite
database.

Status:
- [x] Fetch weight data
- [ ] Fetch activity data

For example:

```bash
# Fetch the last 10 days of weight data
docker run 
    -e GARMIN_EMAIL=XXXX 
    -e GARMIN_PASSWORD=XXXXX 
    -it 
    -v path/to/sqlite-folder:/app/data 
    garmin-sync 
    python /app/entrypoint.py --sync-type=recent --days=10

# Fetch all weight data
docker run 
    -e GARMIN_EMAIL=XXXX 
    -e GARMIN_PASSWORD=XXXXX 
    -it 
    -v path/to/sqlite-folder:/app/data 
    garmin-sync 
    python /app/entrypoint.py --sync-type=all

# Run a scheduled sync (runs every day at 09:00)
docker run 
    -e GARMIN_EMAIL=XXXX 
    -e GARMIN_PASSWORD=XXXXX 
    -it 
    -v path/to/sqlite-folder:/app/data 
    garmin-sync 
    python /app/entrypoint.py --sync-type=schedule
```


## Meta
This project is created as an experiment to see the limits of AI autogeneration, so there could be some fun warts. I'm currently trying Cursor and a 'pair programming' style of interaction to see how far I can get.