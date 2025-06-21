# def solve_captcha(image_url):
#     # Download image
#     img_data = requests.get(image_url).content
#     encoded_image = base64.b64encode(img_data).decode()

#     # Submit to AntiCaptcha
#     task = {
#         "clientKey": ANTI_CAPTCHA_KEY,
#         "task": {
#             "type": "ImageToTextTask",
#             "body": encoded_image
#         }
#     }
#     print("[*] Sending captcha request to anti-captcha...")

#     task_response = requests.post("https://api.anti-captcha.com/createTask", json=task).json()
#     task_id = task_response["taskId"]
#     print(f"[*] Anti-captcha response: {task_response}")

#     # Poll for result
#     while True:
#         time.sleep(5)
#         res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
#             "clientKey": ANTI_CAPTCHA_KEY,
#             "taskId": task_id
#         }).json()
#         if res["status"] == "ready":
#             print(f"[*] Captcha solved: {res}")
#             return res["solution"]["text"]
#         print(f"[*] Polling for captcha solution: {res['status']}")


# def solve_recaptcha(site_key, page_url):
# 	print("[*] Sending captcha request to anti-captcha...")
# 	# Step 1: Send captcha request
# 	task_payload = {
# 		"clientKey": ANTI_CAPTCHA_KEY,
# 		"task": {
# 			"type": "NoCaptchaTaskProxyless",
# 			"websiteURL": page_url,
# 			"websiteKey": site_key
# 		}
# 	}
# 	response = requests.post("https://api.anti-captcha.com/createTask", json=task_payload).json()
# 	print(f"[*] Anti-captcha response: {response}")
# 	task_id = response["taskId"]

# 	# Step 2: Poll for solution
# 	print("[*] Polling for captcha solution...")
# 	for i in range(40):  # ~80 seconds
# 		time.sleep(2)
# 		result = requests.post("https://api.anti-captcha.com/getTaskResult", json={
# 			"clientKey": ANTI_CAPTCHA_KEY,
# 			"taskId": task_id
# 		}).json()
# 		print(f"    Poll {i+1}: status={result['status']}")
# 		if result["status"] == "ready":
# 			print("[*] Captcha solved!")
# 			return result["solution"]["gRecaptchaResponse"]
# 	raise TimeoutError("AntiCaptcha took too long")
