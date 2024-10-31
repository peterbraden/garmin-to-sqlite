# Garmin to SQLite

This project provides a docker image to sync Garmin activity to a sqlite
database.


For example: (TBD)
```
docker run -e GARMIN_EMAIL=XXXX -e GARMIN_PASSWORD=XXXXX -it -v path/to/sqlite-folder:/app/data garmin-sync python /app/garmin_sync.py
```


## Meta
This project is created as an experiment to see the limits of AI autogeneration, so there could be some fun warts. I'm currently trying Cursor and a 'pair programming' style of interaction to see how far I can get.