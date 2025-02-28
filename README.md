# lucos_locations
Location tracking service.

Uses [OwnTracks](https://owntracks.org/) to track locations from a smartphone.

## Dependencies

* docker
* docker compose

## Running

`docker compose up --build`

## Environment Variables
The following environment variables are used:

* **OT_USERNAME** - The username for logging into OwnTracks
* **OT_PASSWORD** - The password for logging into OwnTracks
* **RECORDER_USERNAME** - The username otrecorder uses for connecting to the message queue
* **RECORDER_PASSWORD** - The password otrecorder uses for connecting to the message queue

Environment Variables are stored securely in [lucos_creds](https://github.com/lucas42/lucos_creds)