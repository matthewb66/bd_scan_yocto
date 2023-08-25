import requests
import os
# import subprocess
import sys
import logging

from pathlib import Path

from bd_scan_yocto import global_values
# from bd_scan_yocto import utils
# from bd_scan_yocto import config

if global_values.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


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
        shpath = os.path.join(tdir, 'detect8.sh')

        j = requests.get("https://detect.synopsys.com/detect8.sh")
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
    detect_cmd += f"--detect.source.path={tdir} --detect.project.name={proj} " + \
                  f"--detect.project.version.name={ver} "
    detect_cmd += f"--blackduck.url={global_values.bd_url} "
    detect_cmd += f"--blackduck.api.token={global_values.bd_api} "
    if trust:
        detect_cmd += "--blackduck.trust.cert=true "
    detect_cmd += "--detect.wait.for.results=true "
    if global_values.snippets:
        detect_cmd += "--detect.blackduck.signature.scanner.snippet.matching=SNIPPET_MATCHING "
    detect_cmd += "--detect.timeout=1200"

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

    return


def run_detect_for_bitbake():
    cmd = get_detect()

    detect_cmd = cmd
    detect_cmd += f"--detect.project.name={global_values.bd_project} " + \
                  f"--detect.project.version.name={global_values.bd_version} "
    detect_cmd += f"--blackduck.url={global_values.bd_url} "
    detect_cmd += f"--blackduck.api.token={global_values.bd_api} "
    detect_cmd += f"--detect.bitbake.build.env.name={global_values.oe_build_env} "
    if global_values.bd_trustcert:
        detect_cmd += "--blackduck.trust.cert=true "
    detect_cmd += "--detect.wait.for.results=true "
    detect_cmd += "--detect.tools=DETECTOR "
    detect_cmd += "--detect.project.codelocation.unmap=true "
    detect_cmd += f"--detect.bitbake.package.names={global_values.target} "
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
