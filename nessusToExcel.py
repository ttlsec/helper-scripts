#!/usr/bin/python3
import os, re, io, argparse, errno, time, textwrap, xlsxwriter
import nessus_file_reader as nfr

# CHANGELOG
# v0.1 - 26/01/2022 - Merged all modules into one file and created wrapper
# v0.2 - 27/01/2022 - Tidied up a bit, added single plugin logic and removed dir argument as xlsxwriter does not support append
# v0.3 - 15/03/2022 - Added unencrypted protocols function. Refactored columns to Hostname / IP / Info to assist with reporter import

# STANDARDS
# Columns order - Hostname / IP Address / Other (Except for .txt which will be in reporter format of IP / Hostname / OS)
# Columns width - Hostname = 40 / IP Address = 15 / Operating System = 40 / Other = variable

def extractAll(nessus_scan_file):
    extractHosts(nessus_scan_file)
    extractMSPatches(nessus_scan_file)
    extractRemediations(nessus_scan_file)
    extractWeakServicePermissions(nessus_scan_file)
    extractInstalledSoftware(nessus_scan_file)
    extractUnencryptedProtocols(nessus_scan_file)
    extractUnquotedServicePaths(nessus_scan_file)
    extractUnsupportedOperatingSystems(nessus_scan_file)

def extractHosts(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
    tic = time.perf_counter()
    
    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column widths
    hostsWorksheet = workbook.add_worksheet('Host Information')
    hostsWorksheet.set_column(0, 0, 40)
    hostsWorksheet.set_column(1, 1, 15)
    hostsWorksheet.set_column(2, 2, 60)
    hostsWorksheet.autofilter('A1:C1000000')

    hostsWorksheet.write (0, 0, 'Hostname')
    hostsWorksheet.write (0, 1, 'IP Address')
    hostsWorksheet.write (0, 2, 'Operating System')

    row, col = 1, 0
    
    with open("Host Information.txt", "a") as txt_file:

        for report_host in nfr.scan.report_hosts(root):
            report_ip = nfr.host.resolved_ip(report_host)
            report_fqdn = nfr.host.resolved_fqdn(report_host)
            report_host_os = nfr.host.detected_os(report_host)
            report_host_name = nfr.host.resolved_fqdn(report_host)

            if (report_fqdn is None and report_host_os is not None and report_host_os.count('\n') == 0 ):
                report_fqdn = "NA"

            if (report_host_os is None or report_host_os.count('\n') > 0):
                report_host_os = ""

            if (report_fqdn is None and report_host_name is None):
                report_fqdn = ""

            if (report_fqdn is None and report_fqdn is not None):
                report_fqdn = report_host_name

            # Write to txt
            print(f'{report_ip} {report_fqdn} {report_host_os}', file=txt_file)

            # Write to Excel worksheet
            hostsWorksheet.write (row, col, report_fqdn)
            hostsWorksheet.write (row, (col + 1), report_ip)
            hostsWorksheet.write (row, (col + 2), report_host_os)
            row += 1
            col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        hostsWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Host Information found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Host Information. {row} rows took {toc - tic:0.4f} seconds')

def extractMSPatches(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
    tic = time.perf_counter()

    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column widths
    MSPatchesWorksheet = workbook.add_worksheet('Missing Microsoft Patches')
    MSPatchesWorksheet.set_column(0, 0, 40)
    MSPatchesWorksheet.set_column(1, 1, 15)
    MSPatchesWorksheet.set_column(2, 2, 22)
    MSPatchesWorksheet.set_column(3, 3, 60)
    MSPatchesWorksheet.autofilter('A1:D1000000')

    MSPatchesWorksheet.write (0, 0, 'Hostname')
    MSPatchesWorksheet.write (0, 1, 'IP Address')
    MSPatchesWorksheet.write (0, 2, 'Missing Security Patch')
    MSPatchesWorksheet.write (0, 3, 'Vendor Advisory')

    row, col = 1, 0

    for report_host in nfr.scan.report_hosts(root):
        plugin_38153 = nfr.plugin.plugin_outputs(root, report_host, '38153')

        if 'Check Audit Trail' not in plugin_38153:
            report_ip = nfr.host.resolved_ip(report_host)
            report_fqdn = nfr.host.resolved_fqdn(report_host)

            if report_fqdn is None:
                report_fqdn = "N/A"

            lines = plugin_38153.splitlines()
            for line in lines:
                line.strip()

                if len(line) > 2 and 'The patches for the following bulletins' not in line:
                    patch,advisory = line.split('(',1)

                    # Write to Excel worksheet
                    MSPatchesWorksheet.write (row, col, report_fqdn)
                    MSPatchesWorksheet.write (row, (col + 1), report_ip)
                    MSPatchesWorksheet.write (row, (col + 2), patch[3:].strip())
                    MSPatchesWorksheet.write (row, (col + 3), advisory[:-3].strip())
                    row += 1
                    col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        MSPatchesWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Missing Microsoft Patches found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Microsoft Patches. {row} rows took {toc - tic:0.4f} seconds')

def extractRemediations(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)

    tic = time.perf_counter()

    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column widths
    RemediationsWorksheet = workbook.add_worksheet('Remediations')
    RemediationsWorksheet.set_column(0, 0, 40)
    RemediationsWorksheet.set_column(1, 1, 15)
    RemediationsWorksheet.set_column(2, 2, 190)
    RemediationsWorksheet.autofilter('A1:C1000000')

    RemediationsWorksheet.write (0, 0, 'Hostname')
    RemediationsWorksheet.write (0, 1, 'IP Address')
    RemediationsWorksheet.write (0, 2, 'Remediation Action')

    row, col = 1, 0

    for report_host in nfr.scan.report_hosts(root):
        plugin_66334 = nfr.plugin.plugin_outputs(root, report_host, '66334')
        report_ip = nfr.host.resolved_ip(report_host)
        report_fqdn = nfr.host.resolved_fqdn(report_host)

        if 'Check Audit Trail' not in plugin_66334:

            if report_fqdn is None:
                report_fqdn = "N/A"

            remediation = io.StringIO(plugin_66334)
            
            for fix in remediation.getvalue().split('\n'):

                if '+ Action to take :' in fix:
                    fix = fix.replace('+ Action to take : ','') 

                    if 'Microsoft has released' in fix:
                        continue
                    if 'advisory' in fix:
                        continue
                    if 'Apply the workaround' in fix:
                        continue

                    # Write to Excel worksheet
                    RemediationsWorksheet.write (row, col, report_fqdn)
                    RemediationsWorksheet.write (row, (col + 1), report_ip)
                    RemediationsWorksheet.write (row, (col + 2), fix)
                    row += 1
                    col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        RemediationsWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Remediations found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Remediations. {row} rows took {toc - tic:0.4f} seconds')

def extractWeakServicePermissions(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
    tic = time.perf_counter()
    path = services = dirGroups = writeGroups = ''

    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column width
    ServicePermissionsWorksheet = workbook.add_worksheet('Insecure Service Permissions')
    ServicePermissionsWorksheet.set_column(0, 0, 40)
    ServicePermissionsWorksheet.set_column(1, 1, 15)
    ServicePermissionsWorksheet.set_column(2, 2, 50)
    ServicePermissionsWorksheet.set_column(3, 3, 85)
    ServicePermissionsWorksheet.set_column(4, 4, 35)
    ServicePermissionsWorksheet.set_column(5, 5, 30)
    ServicePermissionsWorksheet.autofilter('A1:F1000000')

    ServicePermissionsWorksheet.write (0, 0, 'Hostname')
    ServicePermissionsWorksheet.write (0, 1, 'IP Address')
    ServicePermissionsWorksheet.write (0, 2, 'Service Name')
    ServicePermissionsWorksheet.write (0, 3, 'Service Path')
    ServicePermissionsWorksheet.write (0, 4, 'User / Group with Write permissions')
    ServicePermissionsWorksheet.write (0, 5, 'User / Group with Full Control')

    row, col = 1, 0

    for report_host in nfr.scan.report_hosts(root):
        report_ip = nfr.host.resolved_ip(report_host)
        report_fqdn = nfr.host.resolved_fqdn(report_host)
        
        plugin_65057 = nfr.plugin.plugin_outputs(root, report_host, '65057')
        if 'Check Audit Trail' not in plugin_65057:
            items = plugin_65057.split("\n\n")
            for item in items:
                lines = item.splitlines()

                for line in lines:
                    if ',' in line:
                        line=line.replace(',',' &')
                    if 'Path' in line:
                        path=line.replace('Path : ','')
                    if 'Used by services' in line:
                        services=line.replace('Used by services : ','')
                    if 'File write allowed' in line:
                        dirGroups= line.replace('File write allowed for groups : ','')
                    if 'Full control of directory' in line:
                        writeGroups= line.replace('Full control of directory allowed for groups : ','')

                # Write to Excel worksheet
                ServicePermissionsWorksheet.write (row, col, report_fqdn)
                ServicePermissionsWorksheet.write (row, (col + 1), report_ip)
                ServicePermissionsWorksheet.write (row, (col + 2), services)
                ServicePermissionsWorksheet.write (row, (col + 3), path)
                ServicePermissionsWorksheet.write (row, (col + 4), dirGroups)
                ServicePermissionsWorksheet.write (row, (col + 5), writeGroups)
                row += 1
                col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        ServicePermissionsWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Weak Service Permissions found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Weak Service Permissions. {row} rows took {toc - tic:0.4f} seconds')

def extractInstalledSoftware(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
    tic = time.perf_counter()

    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column widths
    InstalledSoftwareWorksheet = workbook.add_worksheet('Installed Third Party Software')
    InstalledSoftwareWorksheet.set_column(0, 0, 40)
    InstalledSoftwareWorksheet.set_column(1, 1, 15)
    InstalledSoftwareWorksheet.set_column(2, 2, 170)
    InstalledSoftwareWorksheet.autofilter('A1:C1000000')

    InstalledSoftwareWorksheet.write (0, 0, 'Hostname')
    InstalledSoftwareWorksheet.write (0, 1, 'IP Address')
    InstalledSoftwareWorksheet.write (0, 2, 'Installed Software')

    row, col = 1, 0

    for report_host in nfr.scan.report_hosts(root):
        report_ip = nfr.host.resolved_ip(report_host)
        report_fqdn = nfr.host.resolved_fqdn(report_host)
        plugin_20811 = nfr.plugin.plugin_output(root, report_host, '20811')
        
        if 'Check Audit Trail' not in plugin_20811:
            plugin_20811 = plugin_20811.replace('The following software are installed on the remote host :\n\n','')
            plugin_20811 = plugin_20811.replace('The following updates are installed :\n\n','')
            software = io.StringIO(plugin_20811)
            
            for installed in software.getvalue().split('\n'):
                kb_match = re.match(r"  KB\d[0-9]{5,8}", installed)

                if installed == "" or kb_match: 
                    pass
                else:
                    # Write to Excel worksheet
                    InstalledSoftwareWorksheet.write (row, col, report_fqdn)
                    InstalledSoftwareWorksheet.write (row, (col + 1), report_ip)
                    InstalledSoftwareWorksheet.write (row, (col + 2), installed)
                    row += 1
                    col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        InstalledSoftwareWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Installed Third Party Software found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Installed Third Party Software. {row} rows took {toc - tic:0.4f} seconds')

def extractUnencryptedProtocols(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
    tic = time.perf_counter()

    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column widths
    UnencryptedProtocolsWorksheet = workbook.add_worksheet('Unencrypted Protocols')
    UnencryptedProtocolsWorksheet.set_column(0, 0, 40)
    UnencryptedProtocolsWorksheet.set_column(1, 1, 15)
    UnencryptedProtocolsWorksheet.set_column(2, 2, 10)
    UnencryptedProtocolsWorksheet.set_column(3, 3, 6)
    UnencryptedProtocolsWorksheet.set_column(4, 4, 50)
    UnencryptedProtocolsWorksheet.autofilter('A1:E1000000')

    UnencryptedProtocolsWorksheet.write (0, 0, 'Hostname')
    UnencryptedProtocolsWorksheet.write (0, 1, 'IP Address')
    UnencryptedProtocolsWorksheet.write (0, 2, 'Protocol')
    UnencryptedProtocolsWorksheet.write (0, 3, 'Port')
    UnencryptedProtocolsWorksheet.write (0, 4, 'Description')

    row, col = 1, 0

    for report_host in nfr.scan.report_hosts(root):
        report_ip = nfr.host.resolved_ip(report_host)
        report_fqdn = nfr.host.resolved_fqdn(report_host)

        report_items_per_host = nfr.host.report_items(report_host)
        for report_item in report_items_per_host:
            
            plugin_id = int(nfr.plugin.report_item_value(report_item, 'pluginID'))
            if (plugin_id == 10092 or plugin_id == 10281 or plugin_id == 54582 or plugin_id == 11819 or plugin_id == 35296
            or plugin_id == 87733 or plugin_id == 10203 or plugin_id == 10205 or plugin_id == 10061 or plugin_id == 10198
            or plugin_id == 10891 or plugin_id == 65792):
                unencrypted_protocol = nfr.plugin.report_item_value(report_item, 'protocol')
                unencrypted_port = nfr.plugin.report_item_value(report_item, 'port')
                unencrypted_description = nfr.plugin.report_item_value(report_item, 'plugin_name')

                # Write to Excel worksheet
                UnencryptedProtocolsWorksheet.write (row, col, report_fqdn)
                UnencryptedProtocolsWorksheet.write (row, (col + 1), report_ip)
                UnencryptedProtocolsWorksheet.write (row, (col + 2), unencrypted_protocol)
                UnencryptedProtocolsWorksheet.write (row, (col + 3), unencrypted_port)
                UnencryptedProtocolsWorksheet.write (row, (col + 4), unencrypted_description)
                row += 1
                col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        UnencryptedProtocolsWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Unencrypted Protocols found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Unencrypted Protocols. {row} rows took {toc - tic:0.4f} seconds')

def extractUnquotedServicePaths(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
    tic = time.perf_counter()

    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column widths
    UnquotedPathsWorksheet = workbook.add_worksheet('Unquoted Service Paths')
    UnquotedPathsWorksheet.set_column(0, 0, 40)
    UnquotedPathsWorksheet.set_column(1, 1, 15)
    UnquotedPathsWorksheet.set_column(2, 2, 40)
    UnquotedPathsWorksheet.set_column(3, 3, 140)
    UnquotedPathsWorksheet.autofilter('A1:D1000000')

    UnquotedPathsWorksheet.write (0, 0, 'Hostname')
    UnquotedPathsWorksheet.write (0, 1, 'IP Address')
    UnquotedPathsWorksheet.write (0, 2, 'Service Name')
    UnquotedPathsWorksheet.write (0, 3, 'Service Path')

    row, col = 1, 0

    for report_host in nfr.scan.report_hosts(root):
                
        plugin_63155 = nfr.plugin.plugin_outputs(root, report_host, '63155')
        if 'Check Audit Trail' not in plugin_63155:
            report_ip = nfr.host.resolved_ip(report_host)
            report_fqdn = nfr.host.resolved_fqdn(report_host)

            if report_fqdn is None:
                report_fqdn = "N/A"

            lines = plugin_63155.splitlines()
            for line in lines:
                line.strip()

                if len(line) > 2 and 'Nessus found the following' not in line:
                    service,path = line.split(':',1)
                    # Write to Excel worksheet
                    UnquotedPathsWorksheet.write (row, col, report_fqdn)
                    UnquotedPathsWorksheet.write (row, (col + 1), report_ip)
                    UnquotedPathsWorksheet.write (row, (col + 2), service.strip())
                    UnquotedPathsWorksheet.write (row, (col + 3), path.strip())
                    row += 1
                    col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        UnquotedPathsWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Unquoted Service Paths found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Unquoted Service Paths. {row} rows took {toc - tic:0.4f} seconds')

def extractUnsupportedOperatingSystems(nessus_scan_file):
    root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
    tic = time.perf_counter()

    # Create worksheet with headers. Xlswriter doesn't support autofit so best guess for column widths
    UnsupportedOSWorksheet = workbook.add_worksheet('Unsupported Operating Systems')
    UnsupportedOSWorksheet.set_column(0, 0, 40)
    UnsupportedOSWorksheet.set_column(1, 1, 15)
    UnsupportedOSWorksheet.set_column(2, 2, 55)
    UnsupportedOSWorksheet.set_column(3, 3, 31)
    UnsupportedOSWorksheet.set_column(4, 4, 29)
    UnsupportedOSWorksheet.set_column(5, 5, 50)
    UnsupportedOSWorksheet.autofilter('A1:F1000000')

    UnsupportedOSWorksheet.write (0, 0, 'Hostname')
    UnsupportedOSWorksheet.write (0, 1, 'IP Address')
    UnsupportedOSWorksheet.write (0, 2, 'Operating System')
    UnsupportedOSWorksheet.write (0, 3, 'End of Mainstream Support Date')
    UnsupportedOSWorksheet.write (0, 4, 'End of Extended Support Date')
    UnsupportedOSWorksheet.write (0, 5, 'End of Extended Security Update (ESU) Program Date')

    row, col = 1, 0

    for report_host in nfr.scan.report_hosts(root):
        report_ip = nfr.host.resolved_ip(report_host)
        report_fqdn = nfr.host.resolved_fqdn(report_host)
        report_host_os = nfr.host.detected_os(report_host)

        if report_fqdn is None:
            report_fqdn = "N/A"
        if report_host_os is None or report_host_os.count('\n') > 0:
            report_host_os = ""

        # TODO - Clean this up, a lot of reused code
        # https://docs.microsoft.com/en-gb/lifecycle/products/
        if 'Microsoft Windows 2000' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "30 June 2005")
            UnsupportedOSWorksheet.write (row, (col + 4), "13 July 2010")
            row += 1
        if 'Microsoft Windows Server 2003' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "13 July 2010")
            UnsupportedOSWorksheet.write (row, (col + 4), "14 July 2015")
            row += 1
        if 'Microsoft Windows Server 2008' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "13 January 2015")
            UnsupportedOSWorksheet.write (row, (col + 4), "14 January 2020")
            UnsupportedOSWorksheet.write (row, (col + 5), "10 January 2023")
            row += 1

        if 'Microsoft Windows XP' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "14 April 2009")
            UnsupportedOSWorksheet.write (row, (col + 4), "08 April 2014")
            row += 1
        if 'Microsoft Windows Vista' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "10 April 2012")
            UnsupportedOSWorksheet.write (row, (col + 4), "11 April 2017")
            row += 1
        if 'Microsoft Windows 7' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "13 January 2015")
            UnsupportedOSWorksheet.write (row, (col + 4), "14 January 2020")
            UnsupportedOSWorksheet.write (row, (col + 5), "10 January 2023")
            row += 1

        # https://endoflife.date/
        if 'VMware ESXi 5.5' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "19 September 2015")
            UnsupportedOSWorksheet.write (row, (col + 4), "19 September 2020")
            row += 1
        if 'VMware ESXi 6.0' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "12 March 2018")
            UnsupportedOSWorksheet.write (row, (col + 4), "12 March 2022")
            row += 1

        if 'Ubuntu 14.04' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "30 September 2016")
            UnsupportedOSWorksheet.write (row, (col + 4), "02 April 2019")
            row += 1
        if 'Ubuntu 16.04' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "01 October 2018")
            UnsupportedOSWorksheet.write (row, (col + 4), "02 April 2021")
            row += 1

        if 'CentOS Linux 6' in report_host_os:
            UnsupportedOSWorksheet.write (row, col, report_fqdn)
            UnsupportedOSWorksheet.write (row, (col + 1), report_ip)
            UnsupportedOSWorksheet.write (row, (col + 2), report_host_os)
            UnsupportedOSWorksheet.write (row, (col + 3), "10 May 2017")
            UnsupportedOSWorksheet.write (row, (col + 4), "30 November 2020")
            row += 1

        col = 0

    toc = time.perf_counter()

    # If no data has been extracted, hide the worksheet (Xlsxwriter doesn't support delete)
    if row == 1:
        UnsupportedOSWorksheet.hide()
        if args.verbose:
            print('DEBUG - No Unsupported Operating Systems found, hiding workbook')
    else:
        if args.verbose:
            print (f'DEBUG - Completed Unsupported Operating Systems. {row} rows took {toc - tic:0.4f} seconds')

# Argparser to handle the usage / argument handling
parser = argparse.ArgumentParser(description='''Extract useful information out of .nessus files into Excel

nessusToExcel.py --verbose --file report.nessus --module unsupported,hosts,software --out companyName
nessusToExcel.py --file report.nessus''', formatter_class=argparse.RawTextHelpFormatter)

# Arguments
parser.add_argument('--file', '-f', required=True, help='.nessus file to extract from')
parser.add_argument('--verbose', '-v', action='store_true', help='Increase output verbosity')
parser.add_argument('--out', '-o', default='ExtractedData.xlsx', help='Name of resulting Excel workbook. (Does not need extention, default ExtractedData.xlsx)')
parser.add_argument('--module', '-m', type=str, default='all', 
help=textwrap.dedent('''Comma seperated list of what data you want to extract:
all          = Default
hosts        = Host information (also comes in .txt file for reporter import)
patches      = Missing Microsoft security patches
remediations = All suggested fixes
services     = Insecure Services and their weak permissions
software     = Installed third party software (warning: can be heavy!)
unencrypted  = Unencrypted protocols in use. FTP, Telnet etc.
unquoted     = Unquoted service paths and their weak permissions
unsupported  = Unsupported operating systems
'''))

# Keep a timer to keep an eye on performance
tic = time.perf_counter()

args = parser.parse_args()
if args.verbose:
    print (f'DEBUG - Arguments provided: {args}')

# If a valid .nessus file has been provided, create our Excel workbook
if not '.xlsx' in args.out:
    args.out = args.out + '.xlsx'
    print(f'DEBUG - Output file does not contain extension, new value: {args.out}')

# Ensure provided file or directory exists before we carry on
if not os.path.isfile(args.file):
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), args.file)
else:
    # Create our Excel workbook
    excelPath = os.getcwd() + os.sep + args.out
    workbook = xlsxwriter.Workbook(excelPath)
    if args.verbose:
        print(f'DEBUG - Using Excel output file: {excelPath}')

    # Then check which modules have been requested
    if "all" in args.module:
        if args.verbose:
            print(f'DEBUG - Running all modules')
        extractAll(args.file)
    else:
        # Split out comma separated modules
        argvars = vars(parser.parse_args())
        argvars['module'] = [mod.strip() for mod in argvars['module'].split(",")]
        if args.verbose:
            print(f'DEBUG - Modules selected: {(argvars["module"])} ')
        if 'hosts' in argvars['module']:
            extractHosts(args.file)
        if 'patches' in argvars['module']:
            extractMSPatches(args.file)
        if 'remediations' in argvars['module']:
            extractRemediations(args.file)
        if 'services' in argvars['module']:
            extractWeakServicePermissions(args.file)
        if 'software' in argvars['module']:
            extractInstalledSoftware(args.file)
        if 'unencrypted' in argvars['module']:
            extractUnencryptedProtocols(args.file)
        if 'unquoted' in argvars['module']:
            extractUnquotedServicePaths(args.file)
        if 'unsupported' in argvars['module']:
            extractUnsupportedOperatingSystems(args.file)
        else:
            print('Invalid module provided. Omitting')

toc = time.perf_counter()
print (f'COMPLETED! Output can be found in {excelPath}. Total time taken: {toc - tic:0.4f} seconds')
workbook.close()
exit()