# import os
# import json
# import sys
import time
# import requests
import subprocess
import logging

from bd_scan_yocto import global_values
# from bd_scan_yocto import config


def get_projver(bd, pargs):
    params = {
        'q': "name:" + pargs.project,
        'sort': 'name',
    }
    projects = bd.get_resource('projects', params=params, items=False)

    if projects['totalCount'] == 0:
        logging.info(f"Project '{pargs.project}' does not exist yet")
        return None, None

    projects = bd.get_resource('projects', params=params)
    for proj in projects:
        versions = bd.get_resource('versions', parent=proj, params=params)
        for ver in versions:
            if ver['versionName'] == pargs.version:
                return proj, ver
    logging.info(f"Version '{pargs.project}' does not exist in project '{pargs.version}' yet")
    return None, None


def patch_vuln(bd, comp):
    status = "PATCHED"
    comment = "Patched by bitbake recipe"

    try:
        # vuln_name = comp['vulnerabilityWithRemediation']['vulnerabilityName']

        comp['remediationStatus'] = status
        comp['remediationComment'] = comment
        # result = hub.execute_put(comp['_meta']['href'], data=comp)
        href = comp['_meta']['href']
        # href = '/'.join(href.split('/')[3:])
        r = bd.session.put(href, json=comp)
        r.raise_for_status()
        if r.status_code != 202:
            return False

    except Exception as e:
        logging.error("Unable to update vulnerabilities via API\n" + str(e))
        return False

    return True


def wait_for_bom_completion(bd, ver):
    # Check job status
    try:
        links = ver['_meta']['links']
        link = next((item for item in links if item["rel"] == "bom-status"), None)

        href = link['href']
        # headers = {'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
        # resp = hub.execute_get(href, custom_headers=custom_headers)
        loop = 0
        uptodate = False
        while not uptodate and loop < 80:
            # resp = hub.execute_get(href, custom_headers=custom_headers)
            resp = bd.get_json(href)
            if 'status' in resp:
                uptodate = (resp['status'] == 'UP_TO_DATE')
            elif 'upToDate' in resp:
                uptodate = resp['upToDate']
            else:
                logging.error('Unable to determine bom status')
                return False
            if not uptodate:
                time.sleep(15)
            loop += 1

    except Exception as e:
        logging.error(str(e))
        return False

    return uptodate


def wait_for_scans_old(bd, ver):
    links = ver['_meta']['links']
    link = next((item for item in links if item["rel"] == "codelocations"), None)

    href = link['href']

    time.sleep(10)
    wait = True
    loop = 0
    while wait and loop < 20:
        # custom_headers = {'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
        # resp = bd.execute_get(href, custom_headers=custom_headers)
        resp = bd.get_json(href)
        for cl in resp['items']:
            print(cl)
            if 'status' in cl:
                status_list = cl['status']
                for status in status_list:
                    if status['operationNameCode'] == "ServerScanning":
                        if status['status'] == "COMPLETED":
                            wait = False
        if wait:
            # time.sleep(15)
            loop += 1

    return not wait


def run_cmd(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    proc_stdout = proc.communicate()[0].strip()
    return proc_stdout
