import aiohttp
import asyncio
# import platform
import logging

from bd_scan_yocto import global_values


async def async_main(comps, token):
    async with aiohttp.ClientSession(trust_env=True) as session:
        data_tasks = []
        file_tasks = []

        count = 0
        for url, comp in comps.items():
            count += 1

            file_task = asyncio.ensure_future(async_get_files(session, comp, token))
            file_tasks.append(file_task)

        await asyncio.gather(*data_tasks)
        all_files = dict(await asyncio.gather(*file_tasks))

        await asyncio.sleep(0.250)
        # print(f'- {count} components ')
        #
        # print(all_files)

    return all_files


async def async_get_files(session, comp, token):
    if not global_values.bd_trustcert:
        ssl = False
    else:
        ssl = None

    # retfile = "NOASSERTION"
    hrefs = comp['_meta']['links']

    link = next((item for item in hrefs if item["rel"] == "matched-files"), None)
    if link:
        thishref = link['href'] + '?limit=1000'
        headers = {
            'Authorization': f'Bearer {token}',
            'accept': "application/vnd.blackducksoftware.bill-of-materials-6+json",
        }

        archive_ignore = False
        async with session.get(thishref, headers=headers, ssl=ssl) as resp:
            result_data = await resp.json()
            # cfile = result_data['items']
            # if len(cfile) > 0:
            #     rfile = cfile[0]['filePath']['path']
            #     for ext in ['.jar', '.ear', '.war', '.zip', '.gz', '.tar', '.xz', '.lz', '.bz2', '.7z',
            #                 '.rar', '.rar', '.cpio', '.Z', '.lz4', '.lha', '.arj', '.rpm', '.deb', '.dmg',
            #                 '.gz', '.whl']:
            #         if rfile.endswith(ext):
            #             retfile = rfile
            for item in result_data['items']:
                # if item['filePath']['path'] == item['filePath']['fileName']:
                # print(item['filePath']['path'] + ':' + item['filePath']['archiveContext'])
                if item['filePath']['compositePathContext'] != item['filePath']['path'] + '#':
                    archive_ignore = True
                    break

    return comp['componentVersion'], archive_ignore
