# import os
import sys
import time
import logging

from bd_scan_yocto import global_values
from bd_scan_yocto import config
from bd_scan_yocto import process
from bd_scan_yocto import utils
from bd_scan_yocto import bd_scan_process


def main():

    config.check_args()

    config.get_bitbake_env()

    config.find_yocto_files()

    logging.debug(global_values)

    # if not config.args.cve_check_only and not config.args.nowizard:
    #     config.do_wizard()

    if global_values.target == "":
        logging.error("Yocto target not specified - EXITING")
        sys.exit(2)

    bd = config.connect()
    if bd is None:
        logging.error(f"Cannot connect to specified BD server {global_values.bd_url}")
        sys.exit(3)
    global_values.bd = bd

    if not config.args.cve_check_only:
        logging.info('----------------------------------   PHASE 1  ----------------------------------')
        if not global_values.skip_detect_for_bitbake:
            bd_scan_process.run_detect_for_bitbake()
        else:
            logging.info('Skipping Detect BITBAKE scan ...')

        process.proc_yocto_project(global_values.manifest_file)

    logging.info('----------------------------------   PHASE 7  ----------------------------------')
    if global_values.cve_check_file != "" and not config.args.no_cve_check:

        logging.info("\nProcessing CVEs ...")

        # if not config.args.cve_check_only:
        #     print("Waiting for Black Duck server scan completion before continuing ...")
        #     # Need to wait for scan to process into queue - sleep 15
        #     time.sleep(0)

        try:
            logging.info("- Reading Black Duck project ...")
            proj, ver = utils.get_projver(bd, config.args)
            count = 1
            while ver is None:
                time.sleep(10)
                proj, ver = utils.get_projver(bd, config.args)
                count += 1
                if count > 20:
                    logging.error(f"Unable to locate project {proj} and version '{ver}' - terminating")
                    sys.exit(1)

        except Exception as e:
            logging.error("Unable to get project version from API\n" + str(e))
            sys.exit(3)

        logging.info("- Loading CVEs from cve_check log ...")

        try:
            cvefile = open(global_values.cve_check_file, "r")
            cvelines = cvefile.readlines()
            cvefile.close()
        except Exception as e:
            logging.error("Unable to open CVE check output file\n" + str(e))
            sys.exit(3)

        patched_vulns = []
        pkgvuln = {}
        cves_in_bm = 0
        for line in cvelines:
            arr = line.split(":")
            if len(arr) > 1:
                key = arr[0]
                value = arr[1].strip()
                if key == "PACKAGE NAME":
                    pkgvuln['package'] = value
                elif key == "PACKAGE VERSION":
                    pkgvuln['version'] = value
                elif key == "CVE":
                    pkgvuln['CVE'] = value
                elif key == "CVE STATUS":
                    pkgvuln['status'] = value
                    if pkgvuln['status'] == "Patched":
                        patched_vulns.append(pkgvuln['CVE'])
                        if pkgvuln['package'] in global_values.packages_list:
                            cves_in_bm += 1
                    pkgvuln = {}

        logging.info(f"      {len(patched_vulns)} total patched CVEs identified")
        if not config.args.cve_check_only:
            logging.info(
                f'''      {cves_in_bm} Patched CVEs within packages in build manifest (including potentially mismatched 
            CVEs which should be ignored)''')
        if len(patched_vulns) > 0:
            process.process_patched_cves(bd, ver, patched_vulns)
    else:
        logging.info('Skipping CVE processing')
    logging.info("\nDone")


if __name__ == "__main__":
    main()
