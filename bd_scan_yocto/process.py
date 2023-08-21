import os
# import uuid
# import datetime
import sys
# import re
import subprocess
import logging

import glob

from bd_scan_yocto import global_values
from bd_scan_yocto import utils
from bd_scan_yocto import config
from bd_scan_yocto import bd_scan_process
from bd_scan_yocto import bd_process_bom

if global_values.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


def proc_license_manifest(liclines):
    logging.info("- Working on recipes from license.manifest: ...")
    entries = 0
    ver = ''
    for line in liclines:
        arr = line.split(":")
        if len(arr) > 1:
            key = arr[0]
            value = arr[1].strip()
            if key == "PACKAGE NAME":
                global_values.packages_list.append(value)
            elif key == "PACKAGE VERSION":
                ver = value
            elif key == "RECIPE NAME":
                entries += 1
                if value not in global_values.recipes_dict.keys():
                    global_values.recipes_dict[value] = ver
    if entries == 0:
        return False
    logging.info("	Identified {} recipes from {} packages".format(len(global_values.recipes_dict), entries))
    return True


def proc_layers_in_recipes():

    logging.info("- Identifying layers for recipes ...")
    if global_values.oe_build_env == '':
        output = subprocess.check_output(['bitbake-layers', 'show-recipes'], stderr=subprocess.STDOUT)
    else:
        output = subprocess.check_output(['bash', '-c', 'source ' + global_values.oe_build_env +
                                          ' && bitbake-layers show-recipes'], stderr=subprocess.STDOUT)
    mystr = output.decode("utf-8").strip()
    lines = mystr.splitlines()

    rec = ""
    bstart = False
    for rline in lines:
        if bstart:
            if rline.endswith(":"):
                arr = rline.split(":")
                rec = arr[0]
            elif rec != "":
                arr = rline.split()
                if len(arr) > 1:
                    layer = arr[0]
                    ver = arr[1]
                    # print(ver)
                    # if ver.find(':') >= 0:
                    #     print('found')
                    if rec in global_values.recipes_dict.keys():
                        if global_values.recipes_dict[rec] == ver:
                            global_values.recipe_layer_dict[rec] = layer
                            if layer not in global_values.layers_list:
                                global_values.layers_list.append(layer)
                        elif ver.find(':') >= 0:
                            # version does not match exactly
                            # check for epoch
                            tempver = ver.split(':')[1]
                            if global_values.recipes_dict[rec] == tempver:
                                # version includes epoch:
                                # update version in dict
                                global_values.recipes_dict[rec] = ver
                                global_values.recipe_layer_dict[rec] = layer
                                if layer not in global_values.layers_list:
                                    global_values.layers_list.append(layer)
                                    
                rec = ""
        elif rline.endswith(": ==="):
            bstart = True
    logging.info("	Discovered {} layers".format(len(global_values.layers_list)))


def proc_pkg_files():
    if global_values.download_dir == '':
        logging.error('Download dir empty - cannot continue\n')
        sys.exit(3)
    files_to_copy = []
    files_to_expand = []

    for recipe in global_values.recipes_dict.keys():
        found = False
        ver = global_values.recipes_dict[recipe]
        logging.info(f"- Recipe package {recipe}/{ver}")

        # Try to find package files in download folder
        pattern = "{}/{}[-_]{}*".format(global_values.download_dir, recipe, ver)
        # print(pattern)
        files_list = glob.glob(pattern, recursive=True)
        if len(files_list) > 0:
            for file in files_list:
                if not file.endswith(".done"):
                    if len(global_values.exclude_layers) > 0 and \
                            global_values.recipe_layer_dict[recipe] in global_values.exclude_layers:
                        continue
                    if len(global_values.extended_scan_layers) > 0 and \
                            global_values.recipe_layer_dict[recipe] in global_values.extended_scan_layers:
                        files_to_expand.append(file)
                    else:
                        files_to_copy.append(file)
                    found = True
                    logging.info(' - Located package file:' + file)
            if found:
                continue

        # Try to find pkg files in pkg folder
        if global_values.pkg_dir != '':
            pattern = f"{os.path.join(global_values.pkg_dir, global_values.machine)}/" \
                      f"{recipe}[-_]{ver}-*.{global_values.image_pkgtype}"
            # print(pattern)
            files_list = glob.glob(pattern, recursive=True)
            if len(files_list) > 0:
                files_to_copy.extend(files_list)
                logging.info(' - Located pkg file:' + files_list[0])
                found = True

        if not found:
            logging.info(" - No package file found")

    # print(files_to_copy)
    return files_to_copy, files_to_expand


def copy_pkg_files(pkgs, tmpdir):
    import shutil

    # print(temppkgdir)
    count = 0
    for pkg in pkgs:
        shutil.copy(pkg, tmpdir)
        count += 1

    logging.info(f"\nCOPYING PACKAGE FILES\n- Copied {count} package files ...")
    return count


def expand_pkg_files(pkgs, tmpdir):
    # import shutil
    import tarfile

    # print(temppkgdir)
    count = 0
    for pkg_path in pkgs:
        pkg_file = os.path.basename(pkg_path)
        pkg_name = pkg_file.split('.')[0]
        extract_dir = os.path.join(tmpdir, pkg_name)
        if not os.path.isdir(extract_dir):
            os.mkdir(extract_dir)
        tfile = tarfile.open(pkg_path)
        tfile.extractall(extract_dir)
        count += 1

    logging.info(f"- Extracted {count} package files ...")
    return count


def proc_yocto_project(manfile):
    import tempfile
    try:
        i = open(manfile, "r")
    except Exception as e:
        logging.error(f'Unable to open input manifest file {manfile}\n' + str(e))
        sys.exit(3)

    try:
        liclines = i.readlines()
        i.close()
    except Exception as e:
        logging.error(f'Unable to read license.manifest file {manfile} \n' + str(e))
        sys.exit(3)

    logging.info("\nPROCESSING BITBAKE PROJECT:")
    if not proc_license_manifest(liclines):
        sys.exit(3)

    if len(global_values.extended_scan_layers) > 0 or len(global_values.exclude_layers) > 0:
        logging.debug("Processing layers due to extended_scan_layers or excluded_layers specified ")
        proc_layers_in_recipes()

    # proc_recipe_revisions()
    # if not config.args.no_kb_check:
    #     utils.check_recipes(config.args.kb_recipe_dir)
    # proc_layers()
    # proc_recipes()

    logging.info("\nPROCESSING PACKAGE FILES ...")
    pkg_copy_list, pkg_expand_list = proc_pkg_files()
    temppkgdir = tempfile.mkdtemp(prefix="bd_sig_pkgs")

    processed_files = 0
    if len(pkg_copy_list) > 0:
        processed_files += copy_pkg_files(pkg_copy_list, temppkgdir)
    if len(pkg_expand_list) > 0:
        processed_files += expand_pkg_files(pkg_expand_list, temppkgdir)

    logging.info("\nRUNNING SYNOPSYS DETECT ON PACKAGE FILES ...\n")

    bd_scan_process.run_detect_sigscan(temppkgdir, config.args.project, config.args.version,
                                       config.args.blackduck_trust_cert)

    bd_process_bom.process_project(config.args.project, config.args.version)


def process_patched_cves(bd, version, vuln_list):
    try:
        # headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}
        # resp = bd.get_json(version['_meta']['href'] + '/vulnerable-bom-components?limit=5000', headers=headers)
        items = get_vulns(bd, version)

        count = 0

        for comp in items:
            if comp['vulnerabilityWithRemediation']['source'] == "NVD":
                if comp['vulnerabilityWithRemediation']['vulnerabilityName'] in vuln_list:
                    if utils.patch_vuln(bd, comp):
                        print("		Patched {}".format(comp['vulnerabilityWithRemediation']['vulnerabilityName']))
                        count += 1
            elif comp['vulnerabilityWithRemediation']['source'] == "BDSA":
                vuln_url = "/api/vulnerabilities/" + comp['vulnerabilityWithRemediation'][
                    'vulnerabilityName']
                # custom_headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
                # resp = hub.execute_get(vuln_url, custom_headers=custom_headers)
                vuln = bd.get_json(vuln_url)
                # vuln = resp.json()
                # print(json.dumps(vuln, indent=4))
                for x in vuln['_meta']['links']:
                    if x['rel'] == 'related-vulnerability':
                        if x['label'] == 'NVD':
                            cve = x['href'].split("/")[-1]
                            if cve in vuln_list:
                                if utils.patch_vuln(bd, comp):
                                    print("		Patched " + vuln['name'] + ": " + cve)
                                    count += 1
                        break

    except Exception as e:
        logging.error("Unable to get components from project via API\n" + str(e))
        return False

    logging.info(f"- {count} CVEs marked as patched in project "
                 f"'{global_values.bd_project}/{global_values.bd_version}'")
    return True


def get_vulns(bd, version):
    bucket = 1000
    headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}
    compurl = f"{version['_meta']['href']}/vulnerable-bom-components?limit={bucket}"

    try:
        resp = bd.get_json(compurl, headers=headers)
        total = resp['totalCount']
        alldata = resp['items']
        offset = bucket
        while len(alldata) < total:
            resp = bd.get_json(f"{compurl}&offset={offset}", headers=headers)
            alldata += resp['items']
            offset += bucket
    except Exception as e:
        logging.error("Unable to get components from project via API\n" + str(e))
        return None
    return alldata
