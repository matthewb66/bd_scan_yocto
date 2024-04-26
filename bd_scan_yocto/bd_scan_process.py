import requests
import os
# import subprocess
import sys
import logging

from pathlib import Path

from bd_scan_yocto import global_values
# from bd_scan_yocto import utils
# from bd_scan_yocto import config


def get_detect():
    cmd = ''
    if global_values.detect_jar == '':
        tdir = os.path.join(str(Path.home()), "synopsys-detect")
        if not os.path.isdir(tdir):
            os.mkdir(tdir)
        tdir = os.path.join(tdir, "download")
        if not os.path.isdir(tdir):
            os.mkdir(tdir)
        if not os.path.isdir(tdir):
            logging.error("Cannot create synopsys-detect folder in $HOME")
            sys.exit(2)
        shpath = os.path.join(tdir, 'detect9.sh')

        j = requests.get("https://detect.synopsys.com/detect9.sh")
        if j.ok:
            open(shpath, 'wb').write(j.content)
            if not os.path.isfile(shpath):
                logging.error("Cannot download Synopsys Detect shell script -"
                              " download manually and use --detect-jar-path option")
                sys.exit(2)

            cmd = "/bin/bash " + shpath + " "
    else:
        cmd = "java " + global_values.detect_jar

    return cmd


def run_detect_sigscan(tdir, proj, ver, trust):
    import shutil

    cmd = get_detect()

    detect_cmd = cmd
    detect_cmd += f" --detect.source.path='{tdir}' --detect.project.name='{proj}' " + \
                  f"--detect.project.version.name='{ver}' "
    detect_cmd += f"--blackduck.url={global_values.bd_url} "
    detect_cmd += f"--blackduck.api.token={global_values.bd_api} "
    if trust:
        detect_cmd += "--blackduck.trust.cert=true "
    detect_cmd += "--detect.wait.for.results=true "
    if global_values.snippets:
        detect_cmd += "--detect.blackduck.signature.scanner.snippet.matching=SNIPPET_MATCHING "
    if not 'detect.timeout' in global_values.detect_opts:
        detect_cmd += "--detect.timeout=1200 "

    if global_values.binary_scan:
        detect_cmd += f"--detect.binary.scan.file.name.patterns='{global_values.binary_scan_exts}' "

    if global_values.detect_opts != '':
        detect_cmd += global_values.detect_opts

    # logging.info("\nRunning Detect on identified packages ...")
    logging.debug(f"Detect Sigscan cmd '{detect_cmd}'")
    # output = subprocess.check_output(detect_cmd, stderr=subprocess.STDOUT)
    # mystr = output.decode("utf-8").strip()
    # lines = mystr.splitlines()
    retval = os.system(detect_cmd)
    if not global_values.testmode:
        shutil.rmtree(tdir)

    if retval != 0:
        logging.error("Unable to run Detect Signature scan on package files")
        sys.exit(2)
    else:
        logging.info("Detect scan for Bitbake dependencies completed successfully")

    return


def run_detect_for_bitbake():
    cmd = get_detect()

    detect_cmd = cmd
    detect_cmd += f" --detect.project.name='{global_values.bd_project}' " + \
                  f"--detect.project.version.name='{global_values.bd_version}' "
    detect_cmd += f"--blackduck.url={global_values.bd_url} "
    detect_cmd += f"--blackduck.api.token={global_values.bd_api} "
    detect_cmd += f"--detect.bitbake.build.env.name='{global_values.oe_build_env}' "
    detect_cmd += f"--detect.source.path='{global_values.oe_build_envpath}' "
    if global_values.bd_trustcert:
        detect_cmd += "--blackduck.trust.cert=true "
    detect_cmd += "--detect.wait.for.results=true "
    detect_cmd += "--detect.tools=DETECTOR "
    if global_values.unmap:
        detect_cmd += "--detect.project.codelocation.unmap=true "
    detect_cmd += f"--detect.bitbake.package.names='{global_values.target}' "
    if global_values.build_dir != '':
        detect_cmd += f"--detect.bitbake.source.arguments='{global_values.build_dir}' "

    if not global_values.detect_fix:
        detect_cmd += "--detect.bitbake.dependency.types.excluded=BUILD "
    if global_values.detect_opts != '':
        detect_cmd += global_values.detect_opts

    logging.info("RUNNING DETECT ON BITBAKE PROJECT ...")
    logging.debug(f"Detect Bitbake cmd '{detect_cmd}'")

    # output = subprocess.check_output(detect_cmd, stderr=subprocess.STDOUT)
    # mystr = output.decode("utf-8").strip()
    # lines = mystr.splitlines()
    retval = os.system(detect_cmd)
    if retval != 0:
        logging.error("Unable to run Detect Bitbake scan")
        sys.exit(2)
    else:
        logging.info("Detect scan for Bitbake dependencies completed successfully")
