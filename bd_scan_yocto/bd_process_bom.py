#!/usr/bin/env python

# import argparse
# import json
import logging
import sys
# import os
import requests
import platform
import asyncio

from bd_scan_yocto.bdcomponentlist import ComponentList
from blackduck import Client
from bd_scan_yocto import global_values
# from bd_scan_yocto import config
from bd_scan_yocto import bd_asyncdata

# logging.basicConfig(level=logging.INFO)


def check_projver(bd, proj, ver):
	params = {
		'q': "name:" + proj,
		'sort': 'name',
	}

	projects = bd.get_resource('projects', params=params)
	for p in projects:
		if p['name'] == proj:
			versions = bd.get_resource('versions', parent=p, params=params)
			for v in versions:
				if v['versionName'] == ver:
					return p, v
			break
	else:
		logging.error(f"Version '{ver}' does not exist in project '{proj}'")
		sys.exit(2)

	logging.warning(f"Project '{proj}' does not exist")
	print('Available projects:')
	projects = bd.get_resource('projects')
	for proj in projects:
		print(proj['name'])
	sys.exit(2)


def get_bom_components(bd, ver_dict):
	comp_dict = {}
	res = bd.list_resources(ver_dict)

	blocksize = 1000

	projver = res['href']
	thishref = projver + f"/components?limit={blocksize}"
	headers = {
		'accept': "application/vnd.blackducksoftware.bill-of-materials-6+json",
	}
	res = bd.get_json(thishref, headers=headers)
	if 'totalCount' in res and 'items' in res:
		total_comps = res['totalCount']
	else:
		return comp_dict

	downloaded_comps = 0
	while downloaded_comps < total_comps:
		downloaded_comps += len(res['items'])

		bom_comps = res['items']

		for comp in bom_comps:
			if 'componentVersion' not in comp:
				continue
			compver = comp['componentVersion']

			comp_dict[compver] = comp

		thishref = projver + f"/components?limit={blocksize}&offset={downloaded_comps}"
		res = bd.get_json(thishref, headers=headers)
		if 'totalCount' not in res or 'items' not in res:
			break

	return comp_dict


def get_all_projects(bd):
	projs = bd.get_resource('projects', items=True)

	projlist = []
	for proj in projs:
		projlist.append(proj['name'])
	return projlist


def process_bdproject(bdproj, bdver):
	bd = Client(
		token=global_values.bd_api,
		base_url=global_values.bd_url,
		verify=(not global_values.bd_trustcert),  # TLS certificate verification
		timeout=60
	)

	proj_dict, ver_dict = check_projver(bd, bdproj, bdver)

	bom_components = get_bom_components(bd, ver_dict)

	process_bom(bd, bom_components)

	if global_values.ignore_components or global_values.detect_fix:
		ignore_components(bd, ver_dict)
	return


def process_bom(bd, bom_components):
	logging.info(f"Processing Black Duck project")
	# logging.info(f" {len(bom_components)} bom entries ...")

	# logging.info("Downloading Async data ...")

	componentlist = ComponentList()
	componentlist.process_bom(bd, bom_components)

	all_comp_count = len(bom_components)
	ignored_comps = componentlist.count_ignored_comps()

	# logging.info(f"Black Duck Server = {global_values.bd_url}")
	logging.info(f"- Total Components {all_comp_count} - Already Ignored Components {ignored_comps}")

	return


def ignore_components(bd, ver_dict):
	logging.info('----------------------------------   PHASE 6A  ----------------------------------')
	logging.info("Ignoring partially matched compoents  ...")

	# print('Getting components from project ... found ', end='')
	bom_compsdict = get_bom_components(bd, ver_dict)
	# print("{}".format(str(len(bom_compsdict))))

	logging.info('- Getting component data ... ')

	if platform.system() == "Windows":
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	pkg_ignore_dict = asyncio.run(bd_asyncdata.async_main(bom_compsdict, bd.session.auth.bearer_token))

	ignore_comps = []
	count_ignored = 0
	ignore_array = []

	logging.info("- Ignoring partial components ...")
	count = 0
	for comp in bom_compsdict.keys():
		ignored = False
		if global_values.detect_fix:
			exists_in_manifest = False
			vername = bom_compsdict[comp]['componentVersionName']
			if (len(bom_compsdict[comp]['matchTypes']) == 1 and
					bom_compsdict[comp]['matchTypes'][0] == 'FILE_DEPENDENCY_DIRECT'):
				extid = bom_compsdict[comp]['origins'][0]['externalId']
				compname = extid.split('/')[1]
				if compname in global_values.recipes_dict.keys():
					if vername == global_values.recipes_dict[compname]:
						# Exists in license_manifest
						exists_in_manifest = True
				if not exists_in_manifest:
					ignore_array.append(bom_compsdict[comp]['_meta']['href'])
					count_ignored += 1
					count += 1
					ignored = True
		if global_values.ignore_components and not ignored and pkg_ignore_dict[comp]:
			# Ignore this component
			ignore_array.append(bom_compsdict[comp]['_meta']['href'])
			count_ignored += 1
			count += 1
			ignored = True
		if ignored and count_ignored >= 99:
			ignore_comps.append(ignore_array)
			ignore_array = []
			count_ignored = 0

	ignore_comps.append(ignore_array)
	if count == 0:
		return
	for ignore_array in ignore_comps:
		if ignore_array:
			bulk_data = {
				"components": ignore_array,
				# "reviewStatus": "REVIEWED",
				"ignored": True,
				# "usage": "DYNAMICALLY_LINKED",
				# "inAttributionReport": true
			}

			try:
				url = ver_dict['_meta']['href'] + '/bulk-adjustment'
				headers = {
					"Accept": "application/vnd.blackducksoftware.bill-of-materials-6+json",
					"Content-Type": "application/vnd.blackducksoftware.bill-of-materials-6+json"
				}
				r = bd.session.patch(url, json=bulk_data, headers=headers)
				r.raise_for_status()
			except requests.HTTPError as err:
				bd.http_error_handler(err)

	logging.info(f"- Ignored {count} components")
	return
