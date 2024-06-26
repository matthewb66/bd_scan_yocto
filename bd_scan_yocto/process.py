import os
# import uuid
# import datetime
import sys
import re
import subprocess
import logging

import glob

from bd_scan_yocto import global_values
from bd_scan_yocto import utils
from bd_scan_yocto import config
from bd_scan_yocto import bd_scan_process
from bd_scan_yocto import bd_process_bom


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
                ver = value.split('+')[0]
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

    # Get list of all download files
    pattern = f"{global_values.download_dir}/*"
    # print(pattern)
    all_download_paths_list = glob.glob(pattern, recursive=True)
    download_paths_list = []
    download_files_list = []
    for path in all_download_paths_list:
        if not path.endswith(".done"):
            download_paths_list.append(path)
            download_files_list.append(os.path.basename(path))

    # Get list of all package files
    pattern = f"{global_values.pkg_dir}/**/*.{global_values.image_pkgtype}"
    package_paths_list = glob.glob(pattern, recursive=True)
    package_files_list = []
    for path in package_paths_list:
        package_files_list.append(os.path.basename(path))

    for recipe in global_values.recipes_dict.keys():
        found = False
        ver = global_values.recipes_dict[recipe]

        # # Try to find package files in download folder
        # pattern = f"{global_values.download_dir}/{recipe}[_-]{ver}[.-]*"
        # # print(pattern)
        # files_list = glob.glob(pattern, recursive=True)

        # Skip recipes in excluded layers
        if len(global_values.exclude_layers) > 0 and \
                global_values.recipe_layer_dict[recipe] in global_values.exclude_layers:
            continue

        recipe_esc = re.escape(recipe)
        ver_esc = re.escape(ver)
        download_regex = re.compile(f"^{recipe_esc}[_-]v?{ver_esc}[.-].*$")
        pkg_regex = re.compile(f"^(lib)?{recipe_esc}\d*[_-]v?{ver_esc}[+.-].*\.{global_values.image_pkgtype}")

        for path, file in zip(download_paths_list, download_files_list):
            # Check for recipe and version
            download_res = download_regex.match(file)
            if download_res is not None:
                if len(global_values.extended_scan_layers) > 0 and \
                        global_values.recipe_layer_dict[recipe] in global_values.extended_scan_layers:
                    files_to_expand.append(path)
                else:
                    files_to_copy.append(path)
                found = True
                logging.info(f"- Recipe:{recipe}/{ver} - Located package file: {path}")
        if found:
            continue

        for path, file in zip(package_paths_list, package_files_list):
            if global_values.pkg_dir != '':
                # pattern = f"{os.path.join(global_values.pkg_dir, global_values.machine)}/" \
                #           f"{recipe}[-_]{ver}-*.{global_values.image_pkgtype}"
                pkg_res = pkg_regex.match(file)

                if pkg_res is not None:
                    files_to_copy.append(path)
                    logging.info(f"- Recipe:{recipe}/{ver} - Located package file: {path}")
                    found = True

        if not found:
            logging.info(f"- Recipe:{recipe}/{ver} - No package file found")

    # print(files_to_copy)
    return files_to_copy, files_to_expand


def copy_pkg_files(pkgs, tmpdir):
    import shutil

    # print(temppkgdir)
    count = 0
    for pkg in pkgs:
        if os.path.isdir(pkg):
            shutil.copytree(pkg, tmpdir, ignore_dangling_symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy(pkg, tmpdir)
        count += 1

    logging.info(f"Copying recipe package files")
    logging.info(f"- Copied {count} package files ...")
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
    logging.info('----------------------------------   PHASE 2  ----------------------------------')
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

    logging.info("Processing Bitbake project:")
    if not proc_license_manifest(liclines):
        sys.exit(3)

    logging.info('----------------------------------   PHASE 3  ----------------------------------')
    if len(global_values.extended_scan_layers) > 0 or len(global_values.exclude_layers) > 0:
        logging.debug("Processing layers due to extended_scan_layers or excluded_layers specified ")
        proc_layers_in_recipes()
    else:
        logging.info('Skipping layer processing ...')

    # proc_recipe_revisions()
    # if not config.args.no_kb_check:
    #     utils.check_recipes(config.args.kb_recipe_dir)
    # proc_layers()
    # proc_recipes()

    logging.info('----------------------------------   PHASE 4  ----------------------------------')
    logging.info("Processing recipe & package files ...")
    pkg_copy_list, pkg_expand_list = proc_pkg_files()
    temppkgdir = tempfile.mkdtemp(prefix="bd_sig_pkgs")

    processed_files = 0
    if len(pkg_copy_list) > 0:
        processed_files += copy_pkg_files(pkg_copy_list, temppkgdir)
    if len(pkg_expand_list) > 0:
        processed_files += expand_pkg_files(pkg_expand_list, temppkgdir)

    logging.info('----------------------------------   PHASE 5  ----------------------------------')
    logging.info("Running Synopsys Detect on recipes ...")

    bd_scan_process.run_detect_sigscan(temppkgdir, config.args.project, config.args.version,
                                       config.args.blackduck_trust_cert)

    logging.info('----------------------------------   PHASE 6  ----------------------------------')
    bd_process_bom.process_bdproject(config.args.project, config.args.version)


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
