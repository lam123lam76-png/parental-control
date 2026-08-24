import time

import requests

api_key = '732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7'
headers = {'Authorization': f'Bearer {api_key}'}
dev_id = 'b6ad42c1-e582-402c-af79-c64b176563f3'

for i in range(18):
    time.sleep(10)
    try:
        r = requests.get(f'https://nguyentruclam.io.vn/api/device/{dev_id}/status', headers=headers, timeout=5)
        is_online = r.json().get('data', {}).get('is_online')
        print(f'Poll {i+1}: is_online = {is_online}')
        if is_online:
            print('DEVICE IS BACK ONLINE! Testing check_version...')
            r2 = requests.post(
                f'https://nguyentruclam.io.vn/api/device/{dev_id}/command',
                headers=headers,
                json={'command': 'check_version'},
                timeout=10
            )
            print('Version check result:', r2.json())
            break
    except Exception as e:
        print(f'Poll {i+1} error: {e}')
