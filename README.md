# Synopsys Scan Yocto Script - bd_scan_yocto.py - BETA v1.0.18

# PROVISION OF THIS SCRIPT
This script is provided under the Apache v2 OSS license (see LICENSE file).

It does not represent any extension of licensed functionality of Synopsys software itself and is provided as-is, without warranty or liability.

If you have comments or issues, please raise a GitHub issue here. Synopsys support is not able to respond to support tickets for this OSS utility. Users of this pilot project commit to engage properly with the authors to address any identified issues.

# INTRODUCTION
### OVERVIEW OF BD_SCAN_YOCTO

This `bd_scan_yocto.py` script is a utility intended to scan Yocto projects in Synopsys Black Duck. It examines the Yocto project and environment and then uses Synopsys Detect to perform multiple scans, with additional actions to optimise the scan result to produce a more comprehensive scan than previous methods.

Synopsys Detect is the default scan utility for Black Duck and includes support for Yocto projects. However, Synopsys Detect Yocto scans will only identify standard recipes obtained from Openembedded.org, and will not cover modified or custom recipes, recipes moved to new layers or where package versions or revisions have been changed. Copyright and deep license data is also not supported for Synopsys Detect Yocto scans, as well as snippet or other scanning of code within custom recipes. 

This script combines Synopsys Detect default Yocto project scanning with Black Duck Signature scanning of downloaded sources and packages to create a more complete list of original, modified OSS and OSS embedded within custom packages. It also optionally supports snippet and copyright/license scanning of recipes in specific layers, and deep license data for identified components.

`Bd_scan_yocto` can also optionally identify the list of locally patched CVEs within a Yocto build which can then be marked as patched in the Black Duck project.

### SCANNING YOCTO IN BLACK DUCK USING SYNOPSYS DETECT

As described above, the standard, supported method of scanning a Yocto project into Black Duck is provided by Synopsys Detect (see [Synopsys Detect - scanning Yocto](https://sig-product-docs.synopsys.com/bundle/integrations-detect/page/packagemgrs/bitbake.html)).

To perform a standard Yocto scan using Synopsys Detect:
- Change to the poky folder of a Yocto project
- Run Synopsys Detect adding the options `--detect.tools=DETECTOR --detect.bitbake.package.names=core-image-sato`  (where `core-image-sato` is the package name).
- Synopsys Detect will look for the default OE initialization script (`oe-init-build-env`); you can use the option `--detect.bitbake.build.env=oe-init-script` if you need to specify an alternate init script (`oe-init-script` in this example).
- Detect can optionally inspect the build manifest to remove build dependencies if the option `--detect.bitbake.dependency.types.excluded=BUILD` is used (see [here](https://community.synopsys.com/s/document-item?bundleId=integrations-detect&topicId=properties%2Fdetectors%2Fbitbake.html]) for more information).

However, Synopsys Detect can only identify unmodified, original recipes obtained from [layers.openembedded.org](http://layers.openembedded.org/), meaning that many Yocto recipes which have been modified and custom recipes will not be identified.

Components in the resulting BOM will also not have copyrights or deep license data associated, and it is not possible to use local snippet or license/copyright scanning to supplement license and copyright data.

### WHY BD_SCAN_YOCTO?

This `bd_scan_yocto` script provides a multifactor scan for Yocto projects combining the default Synopsys Detect Bitbake scan with other techniques to produce a more complete Bill of Materials including modified OSS packages and OSS within custom recipes.

It should be considered in the following scenarios:
- Where many standard OpenEmbedded recipes have been moved to new layers (meaning they will not be matched by Synopsys Detect)
- Where OpenEmbedded recipe versions or revisions have been modified from the original
- Where the Yocto project contains modified OSS recipes and custom recipes
- Where copyright or deep license data is required
- Where local license and copyright scanning is required
- Where snippet scanning is required for recipes in specific layers
- Where locally patched CVEs need to be applied to the Black Duck project

The script operates on a built Yocto project, by identifying the build (license) manifest containing __only the recipes which are within the built image__ as opposed to the superset of all recipes used to build the distribution (including build tools etc.).

The script also Signature scans the downloaded origin packages (before they are modified by local patching) to identify modified or custom recipes, with the option to expand archived sources and optionally perform Snippet scans and local copyright/license searches for recipes in specified layers.

This script also optionally supports extracting a list of locally patched CVEs from Bitbake via the `cve_check` class and marking them as patched in the Black Duck project.

The script must be executed on a Linux workstation where Yocto has been installed and after a successful Bitbake build and requires access to a Black Duck server via the API (see Prerequisites below).

### BD_SCAN_YOCTO SCAN BEHAVIOUR

The automatic scan behaviour of `bd_scan_yocto` is described below:
1. Locate the OE initialization script in the invocation folder (bypass if --no_init_script used).
2. Extract information from the Bitbake environment (by running `bitbake -e` and optionally `bitbake-layers show-recipes` if layer specific options are specified)
3. Run Synopsys Detect in Bitbake dependency scan mode to extract the standard OE recipes/dependencies (skipped if `--skip_detect_for_bitbake` option is used) to create the specified Black Duck project & version
4. Locate the software components and rpm/ipk/deb packages downloaded during the build, and copy those matching the recipes in license.manifest to a temporary folder (if the option `--exclude_layers layer1,layer2` is applied then skip recipes within the specified layers)
5. If the option `--extended_scan_layers layer1,layer2` is specified with a list of layers, then expand (decompress) the archives for the recipes in the listed layers. 
6. Run a Signature scan using Synopsys Detect on the copied/expanded and rpm/ipk/deb packages and append to the specified Black Duck project. If `--snippet` is specified then add snippet scanning, adding other Detect scan options with the `--detect_opts` option (for example, local copyright and license scanning with the option `--detect_opts '--detect.blackduck.signature.scanner.license.search=true --detect.blackduck.signature.scanner.copyright.search=true'`)
7. Wait for scan completion, and then post-process the project version BOM to remove identified subcomponents from the unexpanded archives and rpm packages only. This step is required because Signature scanning can sometimes match a complete package, but continue to scan at lower levels to find embedded OSS components which can lead to false-positive matches, although this behaviour is useful for custom recipes (hence why expanded archives are excluded from this process)
8. Optionally identify locally patched CVEs and apply to BD project

### COMPARING BD_SCAN_YOCTO AGAINST IMPORT_YOCTO_BM

An alternate script [import_yocto_bm](https://github.com/blackducksoftware/import_yocto_bm) has been available for some time to address limitations of Synopsys Detect for Yocto, however it requires the list of known OpenEmbedded recipes from the Black Duck KB to be maintained and updated regularly within the project, potentially leading to inaccurate results if the data is out of date.

Furthermore, `import_yocto_bm` does not support scanning non-OpenEmbedded recipes or custom recipes, providing only a partial Bill of Materials and also uses a deprecated method of creating projects.

Components matched from `import_yocto_bm` have no copyright or deep license data, and snippet or local license/copyright scanning is not supported (as there is no package source to scan).

This script should be used in place of `import_yocto_bm`.

# RUNNING BD_SCAN_YOCTO 
### SUPPORTED YOCTO PROJECTS

This script is designed to support Yocto versions 2.0 up to 4.4 (other versions may also be supported).

### PREREQUISITES

1. Script must be run on Linux.

2. Python 3.9 or greater must be installed.

3. A Yocto build environment is required.

4. The Yocto project must have been pre-built with a `license.manifest` file generated by the build and the downloaded original package archives available in the download folder (usually `poky/build/downloads`) and rpm packages in the rpm cache folder.

5. Black Duck server credentials (URL and API token) are required.

6. Ensure that the Bitbake project is valid and commands can be executed including `bitbake -g` and `bitbake-layers show-recipes`.

7. OPTIONAL: For patched CVE remediation in the Black Duck project, you will need to add the `cve_check` bbclass to the Yocto build configuration to generate the CVE check log output. Add the following line to the `build/conf/local.conf` file:

       INHERIT += "cve-check"

   Then rebuild the project (using for example `bitbake core-image-sato`)  to run the CVE check action and generate the required CVE log files without a full rebuild.

### INSTALLATION

Install using `pip3 install bd_scan_yocto`

To upgrade to the latest version use `pip3 install bd_scan_yocto --upgrade`

Alternatively the project can be built locally:
1. Download or clone this repository
2. Create a virtual environment (optional)
3. Run 'python3 setup.py install' to install dependencies
4. Run the script using 'python3 <path_to_library>/main.py OPTIONS'

### USAGE

If installed as a pip package, simply run:

       bd-scan-yocto OPTIONS

If `bd-scan-yocto` is not found on the PATH, note the messages when the package was installed and add the install location for the script to the PATH.

To use the utility, change to the poky folder where the OE initialization script exists.

The minimum data required to run the script is:

- Black Duck server URL
- Black Duck API token with scan permissions
- Black Duck project and project version name to be created
- OE initialization script (for example `oe-init-build-env`)
- Yocto target name

Alternatively, if you wish to run the code directly without pip installation, use python to run the script `bd_scan_yocto/main.py`, for example (where SCRIPT_DIR is the folder where the script has been
installed):

    python3 SCRIPT_DIR/bd_scan_yocto/main.py OPTIONS

### SCAN CONSIDERATIONS

The Black Duck project will probably end up with duplicated components shown in the BOM from the Yocto scan and the Signature scan because they have different origins. All Yocto (OpenEmbedded) components have no origin source code so cannot be matched by Signature scanning. It is therefore possible to compare origins/licenses/vulnerabilities etc. between the similar components matched for each scan type.

Use the option `--exclude_layers layer1,layer2` to skip Signature scan on specific layers if required. You could consider using this for layers where recipes are identified by the Detect Bitbake scan (e.g. the `meta` layer) to remove duplication (same component shown twice).

Use the option `--extended_scan_layers layer1,layer2` to automatically extract the package archives used by recipes within the specified layers before Signature scanning if required. Extracted package archives can also be Snippet scanned (see below), and you could configure additional Signature scan options for these expanded packages if desired.

Add the option `--snippets` to run snippet scans on the downloaded packages, but note that this will slow the scan process considerably so should be used with caution.

Add the option `--no_ignore` to skip ignoring partially matched components from the Signature scan. The ignore process ignores any matches not at the root folder of scanned packages.

Note that the first Synopsys Detect scan for Yocto has the option `--detect.project.codelocation.unmap=true` configured to remove previously mapped scans.

Note also that the script identifies subcomponents within packages, and unless `--extended_scan_layers` is specified, these are ignored in the project. By default, components ignored in 1 project version will also be ignored in the other versions in the same project. It is theoretically possible that a component may be ignored in a project version as it is a subcomponent, but should not be ignored in another version because it is used in a custom recipe for example. In this case, disable `Component Adjustments` under the Project-->Settings page to stop propagating changes across versions.

Note that the Signature scan process can take some time (several minutes) related to the size of the project and the package files to scan.

Black Duck Signature scanning should not be used for an entire Yocto project because it contains a large number of project and configuration files, including the development packages needed to build the image. Furthermore, OSS package code can be modified locally by change/diff files meaning Signature scans of entire Yocto projects will consume large volumes of server resources and produce a Bill of Materials with a lot of additional components which are not deployed in the Yocto image.

### COMMAND LINE OPTIONS
The `bd_scan_yocto` parameters for command line usage are shown below:

     -h, --help            show this help message and exit
     --blackduck_url BLACKDUCK_URL
                           Black Duck server URL (REQUIRED)
     --blackduck_api_token BLACKDUCK_API_TOKEN
                           Black Duck API token (REQUIRED)
     --blackduck_trust_cert
                           Black Duck trust server cert
     --detect-jar-path DETECT_JAR_PATH
                           Synopsys Detect jar path
     -p PROJECT, --project PROJECT
                           Black Duck project to create (REQUIRED)
     -v VERSION, --version VERSION
                           Black Duck project version to create (REQUIRED)
     --oe_build_env OE_BUILD_ENV
                           Yocto build environment config file (default 'oe-init-
                           build-env' - must exist in invocation folder not full PATH)
     -t TARGET, --target TARGET
                           Yocto target (e.g. core-image-sato - REQUIRED)
     -m MANIFEST, --manifest MANIFEST
                           Built license.manifest file
     --build_dir BUILD_DIR
                           Alternative build folder (default is poky/build)
     --machine MACHINE     Machine Architecture (for example 'qemux86-64')
     --skip_detect_for_bitbake
                           Skip running Detect for Bitbake dependencies
     --detect_opts DETECT_OPTS
                           Additional Synopsys Detect options for scanning
     --cve_check_only      Only check for patched CVEs from cve_check and update 
                           existing project (skipping scans)
     --no_cve_check        Skip checking/updating patched CVEs
     --cve_check_file CVE_CHECK_FILE
                           CVE check output file (if not specified will be
                           determined from environment)

     --extended_scan_layers EXTENDED_SCAN_LAYERS
                           Specify a comma-delimited list of layers where
                           packages within recipes will be expanded and Snippet
                           scanned
     --snippets            Run snippet scanning on downloaded package files
     --exclude_layers EXCLUDE_LAYERS
                           Specify a command-delimited list of layers where
                           packages within recipes will not be Signature scanned
     --download_dir DOWNLOAD_DIR
                           Download directory where original software archives are
                           downloaded (usually poky/build/downloads)
     --package_dir PKG_DIR Download directory where packages are downloaded
                           (usually poky/build/tmp/deploy/rpm/<ARCH>)
     --image_package_type rpm|deb|ipk
                           Type of packages installed (rpm, deb or ipk - default 'rpm')
     --no_ignore           Do not ignore partially matched components from Signature scan
     --binary_scan         Run an additional binary (BDBA) scan on the downloaded package files (Requires BDBA license)
     --no_init_script      Bypass using the OE init script, taking environment from current shell
                           (requires --skip_detect_for_bitbake to be specified)
     --detect_fix          Add extra logic to process license_manifest to ignore build dependencies
                           (required where Detect option --detect.bitbake.dependency.types.excluded=BUILD is
                           not operating correctly) - see section 
     --debug               DEBUG mode - add debug messages to the console log
     --logfile LOGFILE     Specify LOGFILE to store logging messages (will also be sent to the console)
     --no_unmap            Do not unmap existing scans from the project on rescan


The script needs to be executed in the Yocto project folder (e.g. `yocto_zeus/poky`) where the OE initialisation script is located (for example `oe-init-build-env`).

The `--project` and `--version` options are required to define the Black Duck project and version names as well as the Black Duck server URL and API key to upload results.

The Yocto target must also be specified using for example `--target core-image-sato`.

The machine (architecture) will be extracted from the Bitbake environment automatically, but the `--machine` option can be used to specify manually.

The most recent Bitbake output manifest file (usually the file `build/tmp/deploy/licenses/<image>-<target>-<datetime>/license.manifest`) will be located automatically. Use the `--manifest` option to specify the manifest file manually.

The most recent cve\_check log file `build/tmp/deploy/images/<arch>/<image>-<target>.cve` will be located automatically if it exists. Use the `--cve_check_file` option to specify the cve\_check log file location manually (for example to use an older copy).

Use the `--cve_check_only` option to skip the scanning and creation of a project, only looking for a CVE check output log file to identify and patch matched CVEs within an existing Black Duck project (which must have been created previously).

Use the `--no_cve_check` option to skip the patched CVE identification and update of CVE status in the Black Duck project if the cve_check output file exists.

### BLACK DUCK CONFIGURATION

You will need to specify the Black Duck server URL, API_TOKEN, project and version using command line options - the minimum set of options is shown below:

      --blackduck_url https://SERVER_URL
      --blackduck_api_token TOKEN
      --blackduck_trust_cert (specify if untrusted CA certificate used for BD server)
      --project PROJECT_NAME
      --version VERSION_NAME
      --target core-image-minimal
      --oe-build-env oe-init-build-env

You can also assign the URL and API Token by setting environment variables:

      export BLACKDUCK_URL=https://SERVER_URL
      export BLACKDUCK_API_TOKEN=TOKEN

Where `SERVER_URL` is the Black Duck server URL and `TOKEN` is the Black Duck API token.

### EXAMPLE USAGE

Use the following command to scan a Yocto project (with default oe-build-env 'oe-init-build-env' and target 'core-image-sato', latest license.manifest file), create Black Duck project `myproject` and version `v1.0`, then update CVE patch status for identified CVEs if cve_patch data available (where SCRIPT_DIR is the location where the script has been installed):

    bd-scan-yocto \
      --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -t core-image-minimal \
      --oe-build-env custom-oe-init \
      -p myproject -v v1.0

To scan a Yocto project with a custom oe-init script, specified target 'core-image-minimal' and a different license manifest as opposed to the most recent one:

    bd-scan-yocto \
      --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -p myproject -v v1.0 \
      --oe-build-env custom-oe-init \
      -t core-image-minimal \
      -m tmp/deploy/licenses/core-image-sato-qemux86-64-20220728105751/package.manifest

To skip the Synopsys Detect Yocto scan and Signature scan the downloaded package archives only with default target and latest license manifest file:

    bd-scan-yocto \
      --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -p myproject -v v1.0 \
      -t core-image-minimal \
      --oe-build-env custom-oe-init \
      --skip_detect_for_bitbake

To perform a CVE check patch analysis ONLY (to update an existing Black Duck project created previously by the script with patched vulnerabilities) use the command:

    bd-scan-yocto \
      --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -p myproject -v v1.0 \
      -t core-image-minimal \
      --oe-build-env custom-oe-init \
      --cve_check_only

### TROUBLESHOOTING

- Check all the prerequisites, and that there is a built Yocto project with a generated license.manifest file.


- Ensure that the Yocto environment is fully defined with the OE init file (`--oe-build-env` option). This script calls Synopsys Detect to extract dependencies which requires that all environment variables are configured within the init file. If necessary, modify the init script to include the additional values, and test with Synopsys Detect standalone first.


- After scan completion, check that there are at least 2 separate code locations in the Source tab in the Black Duck project (one for dependencies and the other for Signature scan).


- Ensure that the Synopsys Detect run has completed successfully, and created entries in the project. Look for items in the project with Match Type of `Direct Dependency`. If none are shown then try running Synopsys Detect standalone to troubleshoot why the dependency scan is not working correctly.


- If the dependency scan exists but shows no components, then examine the console log from the script run, looking for the message `No license.manifest file found for target image core-image-sato; every dependency will be considered a BUILD dependency`. If so, then rerun using the `--detect_fix` option in this script (see section DETECT FIX).


- Examine the `Unmatched Components` from the Synopsys Detect run - these indicate recipes which could not be matched against the Black Duck KB (usually because they have been moved to a new layer, use a new version or revision, or are modified OSS or commercial components). Consider adding manual components to the project to match these components.


- Examine the Signature scan contents within the Source tab to confirm that package files (.rpm, .pki, .tar.gz etc.) were identified and scanned.


- If you are looking for a specific package which appears to be missing from the project, confirm that you are looking for the recipe name not the package name. See the FAQs for an explanation of Yocto recipes versus packages. Check that the package file was included in the Signature scan (within the Source tab).


- If your environment is not set completely within an oe-init script (or you are using another Yocto wrapper such as KAS https://kas.readthedocs.io/), you could try the --no_init_script option (See FAQs below).


### CVE PATCHING

The Yocto `cve_check` class works on the Bitbake dependencies within the dev environment, and produces a list of CVEs identified from the NVD for ALL packages in the development environment.

This script can extract the packages from the build manifest (which will be a subset of those in the full Bitbake dependencies for build environment) and creates a Black Duck project.

The list of CVEs reported by `cve_check` will therefore be considerably larger than seen in the Black Duck project (which is the expected situation).

See the Prerequisites section above for details on how to configure this script to use the `cve_check` data.

# ADDITIONAL SCAN OPTIONS

The Binary scan option (requires separate licensed Binary scan module to be enabled) can be used to run additional scans on the origin package installed in the image.

For a custom C/C++ recipe, or where other languages and package managers are used to build custom recipes, other types of scan could be considered in addition to the techniques used in this script.

For C/C++ recipes, the advanced [blackduck_c_cpp](https://pypi.org/project/blackduck-c-cpp/) utility could be used as part of the build to identify the compiled sources, system includes and operating system dependencies. You would need to modify the build command for the recipe to call the `blackduck-c-cpp` utility as part of a scanning cycle after it had been configured to connect to the Black Duck server.

For recipes where a package manager is used, then a standard Synopsys Detect scan in DETECTOR mode could be utilised to analyse the project dependencies separately.

Multiple scans can be combined into the same Black Duck project (ensure to use the Synopsys Detect option `--detect.project.codelocation.unmap=false` to stop previous scans from being unmapped).

# DETECT FIX OPTION

A recent bug in Synopsys Detect can cause a project to have no dependencies because the option --detect.bitbake.dependency.types.excluded=BUILD cannot locate the license.manifest file when Detect is run on the Bitbake project. To determine whether this option should be used, look for the message `No license.manifest file found for target image core-image-sato; every dependency will be considered a BUILD dependency.` in the Detect log, or a project where no dependencies are reported. Add the option '--detect_fix' to remove the build dependency parameter from the Detect run, and then ignore recipes not found in the license.manifest within this script.

# OUTSTANDING ISSUES

The identification of the Linux Kernel version from the Bitbake recipes and association with the upstream component in the KB has not been completed yet. Until an automatic identification is possible, the required Linux Kernel component can be added manually to the Black Duck project.

# FAQs

1. Why couldn't I just use the license data provided by Yocto in the license.manifest?

   _The licenses reported by Bitbake come straight from the recipe files used to build the project.
   However, the applicable license for each package is the actual declared license reported in the origin repository,
   which may not match the license name in the recipe used to build/install the package. Furthermore, the obligations of
   most OSS licenses require that the full license text is included in the distribution along with any relevant copyrights.
   Another concern is that most OSS packages use or encapsulate other OSS which can have different licenses to the declared
   license in the main package, and in some cases re-licensing is not allowed meaning that the declared license of the main
   is not applicable. Black Duck uses the licenses from the origin packages (not the Yocto recipe), supports full
   license text and copyrights as well as optional deep license analysis to identify embedded licenses within packages._


2. Can this utility be used on a Yocto image without access to the build environment?

   _No - this utility needs access to the Yocto build environment including the cache of downloaded components and rpm packages to perform scans._


3. Why couldn't I simply use the `cve-check` class provided by Yocto to determine unpatched vulnerabilities?

   _The cve-check class processes all recipes in the build and then looks up packages in the NVD to try to associate CVEs. The script reports all packages including build dependencies as opposed to the packages only in the distributed image which is usually not useful.
   The CVE association uses CPE (package enumerators) to match packages, but this uses wildcards which result in a large number of false positive CVEs being reported.
   For example, for a sample Yocto 4.1 minimal build, cve-check reported 160 total unpatched CVEs of which 14 were shown against zlib, however the Black Duck project shows that none of these should be associated with the zlib version in the build (only 3 patched and 0 unpatched vulnerabilities should be shown in the project)._


4. Why couldn't I just use the `create-spdx` class provided by Yocto to export a full SBOM?

   _The Yocto `create-spdx` class produces SPDX JSON files for the packages in the project with the runtime packages also identified,
   including useful data such as the list of files in the image per package with hashes.
   However, many of the SPDX fields are blank (NO-ASSERTION) including license text, copyrights etc.
   The packages are also not identified by PURL so the SBOM cannot be effectively imported into other tools (including Black Duck)._


5. I cannot see a specific package in the Black Duck project.

   _Black Duck reports recipes in the Yocto project not individual packages. Multiple packages can be combined into a single recipe, but these are typically not downloaded separately and are considered to be part of the main component managed by the recipe, not individual OSS components._


6. I cannot see the Linux kernel in the Black Duck project.

   _The kernel cannot be identified due to a custom name format being used in Yocto. See the section OUTSTANDING ISSUES above. Add the required kernel version to the project manually._


7. My environment is not completely set inside the oe-init script (or I am using another Yocto wrapper such as KAS https://kas.readthedocs.io/)

   _Synopsys Detect calls the oe-init script in a sub-shell before running Bitbake, meaning that it is not possible to pass environmental values unless they are in the oe-init script.
   The --no_init_script option allows the bd_scan_yocto script to bypass the use of the oe-init sceript, but you will also need to specify the --skip_detect_for_bitbake option to skip the Detect Bitbake scan_


# UPDATE HISTORY

## V1.0
- Initial version

## V1.0.1
- Modified scan options & config

## V1.0.2
- Added ipk package file support

## V1.0.3
- Bug fixes for detect bitbake scan

## V1.0.4
- Reworked file matching for packages

## V1.0.5
- Fixed issue with Detect Bitbake scan

## V1.0.6
- Added option to skip ignoring partial components after Signature matching

## V1.0.7
- Added logfile option, migrated to Detect9 and fixed issue with oe_build_env being supplied as a path.

## V1.0.8
- Added binary_scan option, added quoting of Detect options with potential spaces. Added --detect_fix option.

## V1.0.9
- Added regex fix.

## V1.0.10
- Fixed CVE file locations, removed default target name, added deb file support.

## V1.0.11
- Added check for target (after wizard) which is now required.

## V1.0.12
- Added --no_init_script option.

## V1.0.13
- Packaged project with pyproject.toml

## V1.0.14
- Removed wizard, added --build_dir option

## V1.0.15
- minor fix to --detect_fix option

## V1.0.16, V1.0.17, V1.0.18
- minor fix to file copying for Sig scan
