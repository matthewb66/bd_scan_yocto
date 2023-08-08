# Synopsys Scan Yocto Script - bd_scan_yocto.py - BETA v1.0

# PROVISION OF THIS SCRIPT
This script is provided under the Apache v2 OSS license (see LICENSE file).

It does not represent any extension of licensed functionality of Synopsys software itself and is provided as-is, without warranty or liability.

If you have comments or issues, please raise a GitHub issue here. Synopsys support is not able to respond to support tickets for this OSS utility. Users of this pilot project commit to engage properly with the authors to address any identified issues.

# INTRODUCTION
### OVERVIEW OF BD_SCAN_YOCTO

This `bd_scan_yocto.py` script is a utility intended to scan Yocto projects in Synopsys Black Duck. It examines the Yocto project and environment and then uses Synopsys Detect to perform multiple scans, with additional actions to optimise the scan result to produce a more comprehensive scan than previous methods.

Synopsys Detect is the default scan utility for Black Duck and includes support for Yocto projects. However, Synopsys Detect Yocto scans will only identify standard recipes obtained from Openembedded.org, and will not cover modified or custom recipes, recipes moved to new layers or where package versions or revisions have been changed. Copyright and deep license data is also not supported for Synopsys Detect Yocto scans, as well as snippet or other scanning of code within custom recipes. 

This script combines Synopsys Detect default Yocto project scanning with Black Duck Signature scanning of downloaded packages to create a more complete list of original, modified OSS and OSS embedded within custom packages. It also optionally supports snippet and copyright/license scanning of recipes in specific layers, and deep license data for identified components.

`Bd_scan_yocto` can also optionally identify the list of locally patched CVEs within a Yocto build which can then be marked as patched in the Black Duck project.

### SCANNING YOCTO IN BLACK DUCK USING SYNOPSYS DETECT

As described above, the standard, supported method of scanning a Yocto project is provided by Synopsys Detect (see [Synopsys Detect - scanning Yocto](https://sig-product-docs.synopsys.com/bundle/integrations-detect/page/packagemgrs/bitbake.html)).

To perform a standard Yocto scan using Synopsys Detect:
- Change to the poky folder of a Yocto project
- Run Synopsys Detect adding the options `--detect.tools=DETECTOR --detect.bitbake.package.names=core-image-sato`  (where `core-image-sato` is the package name).
- Synopsys Detect will look for the default OE initialization script (`oe-init-build-env`); you can use the option `--detect.bitbake.build.env=oe-init-script` if you need to specify an alternate init script (`oe-init-script` in this example).
- Detect can optionally inspect the build manifest to remove build dependencies if the option `--detect.bitbake.dependency.types.excluded=BUILD` is used (see [here](https://community.synopsys.com/s/document-item?bundleId=integrations-detect&topicId=properties%2Fdetectors%2Fbitbake.html] ) for more information).

However, Synopsys Detect can only identify unmodified, original recipes obtained from [layers.openembedded.org](http://layers.openembedded.org/), meaning that many Yocto recipes which have been modified and custom recipes will not be identified.

Components in the resulting BOM will also not have copyrights or deep license data associated, and it is not possible to use local snippet or license/copyright scanning to supplement license and copyright data.

### WHY BD_SCAN_YOCTO?

This `bd_scan_yocto` script provides a multi-factor scan for Yocto projects combining the default Synopsys Detect Bitbake scan with other techniques to produce a more complete Bill of Materials including modified OSS packages and OSS within custom recipes.

It should be considered in the following scenarios:
- Where many standard OpenEmbedded recipes have been moved to new layers (meaning they will not be matched by Synopsys Detect)
- Where OpenEmbedded recipe versions or revisions have been modified from the original
- Where the Yocto project contains modified OSS recipes and custom recipes
- Where copyright or deep license data is required
- Where local license and copyright scanning is required
- Where snippet scanning is required for recipes in specific layers
- Where locally patched CVEs need to be applied to the Black Duck project

The script operates on a built Yocto project, by identifying the build (license) manifest containing __only the recipes which are within the built image__ as opposed to the superset of all recipes used to build the distribution (including build tools etc.).

The script also Signature scans the downloaded origin packages (before they are modified by local patching) to identify modified or custom recipes, with the option to expand archived sources and perform Snippet scans and local copyright/license searches for recipes in specified layers.

This script also optionally supports extracting a list of locally patched CVEs from Bitbake via the `cve_check` class and marking them as patched in the Black Duck project.

The script must be executed on a Linux workstation where Yocto has been installed and after a successful Bitbake build.

The script requires access to a Black Duck server via the API (see Prerequisites below).

### BD_SCAN_YOCTO SCAN BEHAVIOUR

The automatic scan behaviour of `bd_scan_yocto` is described below:
1. Locate the OE initialization script (default `oe-init-build-env`)
2. Extract information from the Bitbake environment (by running `bitbake -e`)
3. Run Synopsys Detect in Bitbake dependency scan mode to extract the standard OE recipes/dependencies (skipped if `--skip_detect_for_bitbake` option is used) to create the specified Black Duck project & version
4. Locate the software components and rpm packages downloaded during the build, and copy those matching the recipes from license.manifest to a temporary folder (if the option `--exclude_layers layer1,layer2` is applied then skip recipes within the specified layers)
5. If the option `--extended_scan_layers layer1,layer2` is specified with a list of layers, then expand (decompress) the archives for the recipes in the listed layers. These expanded archives will also be snippet scanned in 6 below.
6. Run a Signature and Snippet scan using Synopsys Detect on the copied/expanded and rpm packages and append to the specified Black Duck project, adding any other Detect scan options (for example, local copyright and license scanning with the option `--detect_opts '--detect.blackduck.signature.scanner.license.search=true --detect.blackduck.signature.scanner.copyright.search=true'`)
7. Wait for scan completion, and then post-process the project version BOM to remove identified sub-components from the unexpanded archives and rpm packages only. This step is required because Signature scanning can sometimes match a complete package, but continue to scan at lower levels to find embedded OSS components which can lead to false-positive matches, although this behaviour is useful for custom recipes (hence why expanded archives are excluded from this process)
8. Optionally identify locally patched CVEs and apply to BD project

### COMPARING BD_SCAN_YOCTO AGAINST IMPORT_YOCTO_BM

An alternate script [import_yocto_bm](https://github.com/blackducksoftware/import_yocto_bm) has been available for some time to address limitations of Synopsys Detect for Yocto, however it requires the list of known OpenEmbedded recipes from the Black Duck KB to be maintained and updated regularly within the project, potentially leading to inaccurate results if the data is out of date.

Furthermore, `import_yocto_bm` does not support scanning non-OpenEmbedded recipes or custom recipes, providing only a partial Bill of Materials.

Components matched from `import_yocto_bm` have no copyright or deep license data, and snippet, local license/copyright scanning is not supported (as there is no package source to scan).

# RUNNING BD_SCAN_YOCTO 
### SUPPORTED YOCTO PROJECTS

This script is designed to support Yocto versions 2.0 up to 4.2.

### PREREQUISITES

1. Script must be run on Linux.

1. Python 3 must be installed.

1. A Yocto build environment is required.

1. The Yocto project must have been pre-built with a `license.manifest` file generated by the build and the downloaded original package archives available in the download folder (usually `poky/build/downloads`) and rpm packages in the rpm cache folder.

1. Black Duck server credentials (URL and API token) are required.

1. OPTIONAL: For patched CVE remediation in the Black Duck project, you will need to add the `cve_check` bbclass to the Yocto build configuration to generate the CVE check log output. Add the following line to the `build/conf/local.conf` file:

       INHERIT += "cve-check"

   Then rebuild the project (using for example `bitbake core-image-sato`)  to run the CVE check action and generate the required CVE log files without a full rebuild.

### INSTALLATION

1. Download or clone this repository
2. Create a virtual environment (optional)
3. Run 'python3 setup.py install' to install dependencies
4. Run the script using 'python3 <path_to_library>/main.py OPTIONS'

### USAGE

Change to the poky folder where the OE initialization script exists (`oe-init-build-env` by default).

The minimum data required to run the script is:

- Black Duck server URL
- Black Duck API token with scan permissions
- Black Duck project and project version name to be created
- OE initialization script (if not `oe-init-build-env`)
- Yocto target name (default `core-image-sato`)
- Yocto machine name (default `qemux86-64`)

Run the command `bd_scan_yocto` without arguments to invoke the wizard to guide you through the required information and options.

### SCAN CONSIDERATIONS

The Black Duck project will probably end up with duplicated components shown in the BOM from the Yocto scan and the Signature scan because they have different origins. All Yocto (OpenEmbedded) components have no origin source code so cannot be matched by Signature scanning. It is therefore possible to compare origins/licenses/vulnerabilities etc. between the similar components matched for each scan type.

Use the option `--exclude_layers layer1,layer2` to skip Signature scan on specific layers if required. You could consider using this for layers where recipes are identified by the Detect Bitbake scan (e.g. the `meta` layer) to remove duplication (same component shown twice).

Use the option `--extended_scan_layers layer1,layer2` to automatically extract the package archives used by recipes within the sepcified layers before Signature scanning if required. Extracted package archives will also be Snippet scanned by default, and you could configure additional Signature scan options for these packages if desired.

Note that the first Synopsys Detect scan for Yocto has the option `--detect.project.codelocation.unmap=true` configured to remove previously mapped scans.

Note also that the script identifies sub-components within packages, and unless `--extended_scan_layers` is specified, these are ignored in the project. By default, components ignored in 1 project version will also be ignored in the other versions in the same project. It is theoretically possible that a component may be ignored in a project version as it is a sub-component, but should not be ignored in another version because it is used in a custom recipe for example. In this case, disable `Component Adjustments` under the Project-->Settings page to stop propagating changes across versions.

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
                           build-env')
     -t TARGET, --target TARGET
                           Yocto target (default core-image-sato)
     -m MANIFEST, --manifest MANIFEST
                           Built license.manifest file)
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
     --wizard              Start command line wizard (Wizard will run by default
                           if config incomplete)
     --nowizard            Do not use wizard (command line batch only)
     --extended_scan_layers EXTENDED_SCAN_LAYERS
                           Specify a comma-delimited list of layers where
                           packages within recipes will be expanded and Snippet
                           scanned
     --exclude_layers EXCLUDE_LAYERS
                           Specify a command-delimited list of layers where
                           packages within recipes will not be Signature scanned
     --download_dir DOWNLOAD_DIR
                           Download directory where original packages are
                           downloaded (usually poky/build/downloads)
     --rpm_dir RPM_DIR     Download directory where rpm packages are downloaded
                           (usually poky/build/tmp/deploy/rpm/<ARCH>)
     --debug               DEBUG mode - add debug messages to the console log


The script needs to be executed in the Yocto project folder (e.g. `yocto_zeus/poky`) where the OE initialisation script is located (`oe-init-build-env` by default).

The `--project` and `--version` options are required to define the Black Duck project and version names.

The Yocto target should be specified using for example `--target core-image-sato`, although the default value (core-image-sato) will be used if not specified.

The machine (architecture) will be extracted from the Bitbake environment automatically, but the `--machine` option can be used to specify manually.

The most recent Bitbake output manifest file (located in the `build/tmp/deploy/licenses/<image>-<target>-<datetime>/license.manifest` file) will be located automatically. Use the `--manifest` option to specify the manifest file manually.

The most recent cve\_check log file `build/tmp/deploy/images/<arch>/<image>-<target>-<datetime>.rootfs.cve` will be located automatically if it exists. Use the `--cve_check_file` option to specify the cve\_check log file location manually (for example to use an older copy).

Use the `--cve_check_only` option to skip the scanning and creation of a project, only looking for a CVE check output log file to identify and patch matched CVEs within an existing Black Duck project (which must have been created previously).

Use the `--no_cve_check` option to skip the patched CVE identification and update of CVE status in the Black Duck project if the cve_check output file exists.

### BLACK DUCK CONFIGURATION

You will need to specify the Black Duck server URL, API_TOKEN, project and version using command line options:

      --blackduck_url https://SERVER_URL
      --blackduck_api_token TOKEN
      --blackduck_trust_cert (specify if untrusted CA certificate used for BD server)
      --project PROJECT_NAME
      --version VERSION_NAME

You can also set the URL and API Token by setting environment variables:

      BLACKDUCK_URL=https://SERVER_URL
      BLACKDUCK_API_TOKEN=TOKEN

Where `SERVER_URL` is the Black Duck server URL and `TOKEN` is the Black Duck API token.

### EXAMPLE USAGE

To run the utility in wizard mode, simply use the command `import_yocto_bm` and it will ask questions to determine the scan parameters.

Use the option `--nowizard` to run in batch mode and bypass the wizard mode, noting that you will need to specify all required options on the command line correctly.

Use the following command to scan a Yocto build, create Black Duck project `myproject` and version `v1.0`, then update CVE patch status for identified CVEs (will require the OE environment to have been loaded previously):

    import_yocto_bm --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -p myproject -v v1.0

To scan a Yocto project specifying a different build manifest as opposed to the most recent one:

    import_yocto_bm --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -p myproject -v v1.0 \
      -m tmp/deploy/licenses/core-image-sato-qemux86-64-20200728105751/package.manifest

To skip the Synopsys Detect Yocto scan, Signature scan the downloaded package archives only:

    import_yocto_bm --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -p myproject -v v1.0 --skip_detect_for_bitbake

To perform a CVE check patch analysis ONLY (to update an existing Black Duck project created previously by the script with patched vulnerabilities) use the command:

    import_yocto_bm --blackduck_url https://SERVER_URL \
      --blackduck_api_token TOKEN \
      --blackduck_trust_cert \
      -p myproject -v v1.0 --cve_check_only

### CVE PATCHING

The Yocto `cve_check` class works on the Bitbake dependencies within the dev environment, and produces a list of CVEs identified from the NVD for ALL packages in the development environment.

This script can extract the packages from the build manifest (which will be a subset of those in the full Bitbake dependencies for build environment) and creates a Black Duck project.

The list of CVEs reported by `cve_check` will therefore be considerably larger than seen in the Black Duck project (which is the expected situation).

See the Prerequisites section above for details on how to configure this script to use the `cve_check` data.

# ADDITIONAL SCAN OPTIONS

For a custom C/C++ recipe, or where other languages and package managers are used to build custom recipes, other types of scan could be considered in addition to the techniques used in this script.

For C/C++ recipes, the advanced [blackduck_c_cpp](https://pypi.org/project/blackduck-c-cpp/) utility could be used as part of the build to identify the compiled sources, system includes and operating system dependencies. You would need to modify the build command for the recipe to call the `blackduck-c-cpp` utility as part of a scanning cycle after it had been configured to connect to the Black Duck server.

For recipes where a package manager is used, then a standard Synopsys Detect scan in DETECTOR mode could be utilised to analyse the project dependencies.

Multiple scans can be combined into the same Black Duck project (ensure to use the Synopsys Detect option `--detect.project.codelocation.unmap=false` to stop previous scans from being unmapped).

# OUTSTANDING ISSUES

The identification of the Linux Kernel version from the Bitbake recipes and association with the upstream component in the KB has not been completed yet. Until an automatic identification is possible, the required Linux Kernel component can be added manually to the Black Duck project.

# FAQs

1. Can this utility be used on a Yocto image without access to the build environment?

   _No - this utility needs access to the Yocto build environment including the cache of downloaded components and rpm packages to perform scans._

# UPDATE HISTORY

## V1.0
- Initial version
