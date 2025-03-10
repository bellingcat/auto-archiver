import traceback
import requests
import time
from loguru import logger

from auto_archiver.core import Enricher
from auto_archiver.core import Metadata, Media


class WhisperEnricher(Enricher):
    """
    Connects with a Whisper API service to get texts out of audio
    whisper API repository: https://github.com/bellingcat/whisperbox-transcribe/
    Only works if an S3 compatible storage is used
    """

    def setup(self) -> None:
        self.stores = self.config["steps"]["storages"]
        self.s3 = self.module_factory.get_module("s3_storage", self.config)
        if "s3_storage" not in self.stores:
            logger.error(
                "WhisperEnricher: To use the WhisperEnricher you need to use S3Storage so files are accessible publicly to the whisper service being called."
            )
            return

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"WHISPER[{self.action}]: iterating media items for {url=}.")

        job_results = {}
        for i, m in enumerate(to_enrich.media):
            if m.is_video() or m.is_audio():
                # Only storing S3, the rest will get added later in the usual order (?)
                m.store(url=url, metadata=to_enrich, storages=[self.s3])
                try:
                    job_id = self.submit_job(m)
                    job_results[job_id] = False
                    logger.debug(f"JOB SUBMITTED: {job_id=} for {m.key=}")
                    to_enrich.media[i].set("whisper_model", {"job_id": job_id})
                except Exception as e:
                    logger.error(
                        f"Failed to submit whisper job for {m.filename=} with error {e}\n{traceback.format_exc()}"
                    )

        job_results = self.check_jobs(job_results)

        for i, m in enumerate(to_enrich.media):
            if m.is_video() or m.is_audio():
                job_id = to_enrich.media[i].get("whisper_model", {}).get("job_id")
                if not job_id:
                    continue
                to_enrich.media[i].set(
                    "whisper_model",
                    {
                        "job_id": job_id,
                        "job_status_check": f"{self.api_endpoint}/jobs/{job_id}",
                        "job_artifacts_check": f"{self.api_endpoint}/jobs/{job_id}/artifacts",
                        **(job_results[job_id] if job_results[job_id] else {"result": "incomplete or failed job"}),
                    },
                )
                # append the extracted text to the content of the post so it gets written to the DBs like gsheets text column
                if job_results[job_id]:
                    for k, v in job_results[job_id].items():
                        if "_text" in k and len(v):
                            to_enrich.set_content(f"\n[automatic video transcript]: {v}")

    def submit_job(self, media: Media):
        s3_url = self.s3.get_cdn_url(media)
        assert s3_url in media.urls, f"Could not find S3 url ({s3_url}) in list of stored media urls "
        payload = {
            "url": s3_url,
            "type": self.action,
            # "language": "string" # may be a config
        }
        logger.debug(f"calling API with {payload=}")
        response = requests.post(
            f"{self.api_endpoint}/jobs", json=payload, headers={"Authorization": f"Bearer {self.api_key}"}
        )
        assert response.status_code == 201, (
            f"calling the whisper api {self.api_endpoint} returned a non-success code: {response.status_code}"
        )
        logger.debug(response.json())
        return response.json()["id"]

    def check_jobs(self, job_results: dict):
        start_time = time.time()
        all_completed = False
        while not all_completed and (time.time() - start_time) <= self.timeout:
            all_completed = True
            for job_id in job_results:
                if job_results[job_id] is not False:
                    continue
                all_completed = False  # at least one not ready
                try:
                    job_results[job_id] = self.check_job(job_id)
                except Exception as e:
                    logger.error(f"Failed to check {job_id=} with error {e}\n{traceback.format_exc()}")
            if not all_completed:
                time.sleep(3)
        return job_results

    def check_job(self, job_id):
        r = requests.get(f"{self.api_endpoint}/jobs/{job_id}", headers={"Authorization": f"Bearer {self.api_key}"})
        assert r.status_code == 200, f"Job status did not respond with 200, instead with: {r.status_code}"
        j = r.json()
        logger.debug(f"Checked job {job_id=} with status='{j['status']}'")
        if j["status"] == "processing":
            return False
        elif j["status"] == "error":
            return f"Error: {j['meta']['error']}"
        elif j["status"] == "success":
            r_res = requests.get(
                f"{self.api_endpoint}/jobs/{job_id}/artifacts", headers={"Authorization": f"Bearer {self.api_key}"}
            )
            assert r_res.status_code == 200, (
                f"Job artifacts did not respond with 200, instead with: {r_res.status_code}"
            )
            logger.success(r_res.json())
            result = {}
            for art_id, artifact in enumerate(r_res.json()):
                subtitle = []
                full_text = []
                for i, d in enumerate(artifact.get("data")):
                    subtitle.append(f"{i + 1}\n{d.get('start')} --> {d.get('end')}\n{d.get('text').strip()}")
                    full_text.append(d.get("text").strip())
                if not len(subtitle):
                    continue
                if self.include_srt:
                    result[f"artifact_{art_id}_subtitle"] = "\n".join(subtitle)
                result[f"artifact_{art_id}_text"] = "\n".join(full_text)
            # call /delete endpoint on timely success
            r_del = requests.delete(
                f"{self.api_endpoint}/jobs/{job_id}", headers={"Authorization": f"Bearer {self.api_key}"}
            )
            logger.debug(f"DELETE whisper {job_id=} result: {r_del.status_code}")
            return result
        return False
