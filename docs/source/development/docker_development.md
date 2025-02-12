## Docker development
working with docker locally:
  * `docker compose up` to build the first time and run a local image with the settings in `secrets/orchestration.yaml`
  * To modify/pass additional command line args, use `docker compose run auto-archiver --config secrets/orchestration.yaml [OTHER ARGUMENTS]`
  * To rebuild after code changes, just pass the `--build` flag, e.g. `docker compose up --build`