------ AA + API



2024-03-05 11:57:12.910 | ERROR    | auto_archiver.core.orchestrator:archive:116 - ERROR enricher wacz_archiver_enricher: 'WaczArchiverEnricher' object has no attri bute 'browsertrix_home_host': Traceback (most recent call last):
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/auto_archiver/core/orchestrator.py", line 114, in archive
    try: e.enrich(result)
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/auto_archiver/enrichers/wacz_enricher.py", line 70, in enrich
    browsertrix_home_host = self.browsertrix_home_host or os.path.abspath(ArchivingContext.get_tmp_dir())
AttributeError: 'WaczArchiverEnricher' object has no attribute 'browsertrix_home_host'



-------- API


2024-02-29 17:12:06.078 | WARNING  | worker:task_failure_notifier:100 - 😅 From task_failure_notifier ==> Task failed successfully! 
2024-02-29 17:12:06.078 | ERROR    | worker:task_failure_notifier:101 - list index out of range
2024-02-29 17:12:06.078 | ERROR    | worker:task_failure_notifier:102 - <traceback object at 0x7f3db75446c0>
2024-02-29 17:12:06.079 | ERROR    | worker:task_failure_notifier:103 -   File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/celery/app/trace.py", line 412, in trace_task
    R = retval = fun(*args, **kwargs)

  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/celery/app/trace.py", line 704, in __protected_call__
    return self.run(*args, **kwargs)

  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/celery/app/autoretry.py", line 50, in run
    raise task.retry(exc=exc, **retry_kwargs)

  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/celery/app/task.py", line 706, in retry
    raise_with_context(exc)

  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/celery/app/autoretry.py", line 35, in run
    return task._orig_run(*args, **kwargs)

  File "/app/worker.py", line 35, in create_archive_task
    invalid = is_group_invalid_for_user(archive.public, archive.group_id, archive.author_id)

  File "/app/worker.py", line 160, in is_group_invalid_for_user
    if not crud.is_user_in_group(session, group_id, author_id):

  File "/app/db/crud.py", line 93, in is_user_in_group
    return len(group_name) and len(email) and group_name in get_user_groups(db, email)

  File "/app/db/crud.py", line 103, in get_user_groups
    domain_level_groups = DOMAIN_GROUPS.get(email.split('@')[1], [])

------------------ API

[parameters: (('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/b0c88017bb047ff43fc49907/3811d9d0c74541929f4a72d0.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'profile_picture'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/ff30ece740738d060229c5da/e43172422e274c2a8f9529ff.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'post 3308982791113602520'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/23f218c518e2d5a17fe856bd/bad85f53a8e54c26991cdff9.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'image 3308982790987757405'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/2ffc8c65d6bfec7ef5402bda/520a10e7a7e14028be1cc1c8.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'image 3308982790970975889'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/da0486669cbb102e6221d94c/65b151ee59114ea5b61cfe96.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'image 3308982790979533474'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/d8c4db3247780324b6fa6d4a/df195ff24b104182bf255610.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'image 3308982790979331432'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/715432d8038abe50c8c89994/f49554bf621848e5881388ee.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'image 3308982791122025152'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/f143ce41b1eb329a0c404448/6b3d604f676c4ef583b54ff3.jpg', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'image 3308982790987824546')  ... displaying 10 of 253 total bound parameter sets ...  ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/385ac59684e1148643c762de/0d72d23e6652474a977fe1d6', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', 'timestamp_authority_filesno-dups/385ac59684e1148643c762de/0d72d23e6652474a977fe1d6_3.0'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/261cb9cefe3c373ad5f7f305/545253c297124d31bbf817c9.html', '314b2eb3-98a4-4a4b-be01-7f4d3ea1c4c2', '_final_media'))]


2024-02-25 15:43:13.142 | DEBUG    | worker:convert_if_media:200 - error parsing {'pk': '2045172809601551458', 'id': '2045172809601551458_178884643', 'code': 'Bxh6dWkloxi', 'taken_at': '2019-05-16T16:20:16Z', 'media_type': 1, 'product_type': 'story', 'thumbnail_url': 'https://scontent-sjc3-1.cdninstagram.com/v/t51.12442-15/58604296_289070981969290_2714055836620897014_n.jpg?stp=dst-jpg_e35&efg=eyJ2ZW5jb2RlX3RhZyI6ImltYWdlX3VybGdlbi4xMDI0eDE4MjAuc2RyIn0&_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=110&_nc_ohc=ri2YWjVH4dkAX9TFQox&edm=ANmP7GQBAAAA&ccb=7-5&ig_cache_key=MjA0NTE3MjgwOTYwMTU1MTQ1OA%3D%3D.2-ccb7-5&oh=00_AfCIxHr9jkUmeq9NgbmTpWtURV_eu5JGMRbrsc0WwyO59g&oe=65DD0180&_nc_sid=982cc7', 'user': {'pk': '178884643'}, 'locations': [{'location': {'pk': 218723854, 'name': 'Montañita, Ecuador', 'lng': -80.751982661304, 'lat': -1.829127033905}}]} : 'filename'
2024-02-25 15:43:13.224 | WARNING  | worker:create_sheet_task:84 - cached result detected: (sqlite3.IntegrityError) UNIQUE constraint failed: archive_urls.url, archive_urls.archive_id
[SQL: INSERT INTO archive_urls (url, archive_id, "key") VALUES (?, ?, ?)]
[parameters: (('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/3caafdcb057000f8c70610fe/e45ec0b09b854333afa22c1c.jpg', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'profile_picture'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/58f0b188e55ef64b96d04b35/94cd9b3d2d5c4deebb9ccd13.jpg', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'story 3310558716812786504_178884643'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/9225487f1a559da4060dcf8e/fe55f26616114856a35cc357.jpg', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'post 3301802228841572226'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/e26b8bc09aa4febc53d4a42d/50330faff71d4dc28078d5e6.jpg', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'image 3301802228850013597'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/bec948c1bf5b87f1f0923e1d/e4c3ddef88ad487ab0305402.jpg', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'image 3301802228917101263'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/38c66be1f1898ea7e0d20d9d/9143edba90184ea387fc856d.jpg', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'image 3301802228916961531'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/89f16b246931dc98792d570c/859ea90fd5a84d3cbf1a7b46.mp4', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'video 3301801735390140959'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/7ee6f00d8a05e22996307c20/5f5faa30541d406e9f0ea1f2.mp4', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'video 3301801735750883968')  ... displaying 10 of 587 total bound parameter sets ...  ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/ef3bc69b89e40504cd936e8a/f4a13bf448c04af0b8c3aeae', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', 'timestamp_authority_filesno-dups/ef3bc69b89e40504cd936e8a/f4a13bf448c04af0b8c3aeae_3.0'), ('https://bellingcat-archive.nyc3.cdn.digitaloceanspaces.com/no-dups/561ea3dc87c229eb239266f2/8c292219a03445e396001026.html', '51fe261b-ad32-4c8a-96cd-801ccfa472fa', '_final_media'))]



2024-02-27 13:03:04.585 | ERROR    | auto_archiver.core.orchestrator:archive:128 - ERROR database gsheet_db: {'code': 400, 'message': 'Invalid data[4]: Your input contains more than the maximum of 50000 characters in a single cell.', 'status': 'INVALID_ARGUMENT'}: Traceback (most recent call last):
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/auto_archiver/core/orchestrator.py", line 126, in archive
    try: d.done(result)
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/auto_archiver/databases/gsheet_db.py", line 94, in done
    gw.batch_set_cell(cell_updates)
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/auto_archiver/utils/gworksheet.py", line 104, in batch_set_cell
    self.wks.batch_update(cell_updates, value_input_option='USER_ENTERED')
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/gspread/worksheet.py", line 1361, in batch_update
    response = self.client.values_batch_update(self.spreadsheet_id, body=body)
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/gspread/http_client.py", line 263, in values_batch_update
    r = self.request("post", url, json=body)
  File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.10/site-packages/gspread/http_client.py", line 123, in request
    raise APIError(response)
gspread.exceptions.APIError: {'code': 400, 'message': 'Invalid data[4]: Your input contains more than the maximum of 50000 characters in a single cell.', 'status': 'INVALID_ARGUMENT'}
