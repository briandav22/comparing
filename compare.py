from scrut_api import ReportAPI, Requester
import json
import csv




scrutinizer_requester = Requester(
    authToken="your_auth_token",
    hostname="example.scrutinizer.com"
)

report_filters = {
     "sdfDips_0": "in_GROUP_ALL",
     "sdfIPGroups_0": "in_16900046_Both"
}

report_params = ReportAPI()
#find all available groups with their ID's and create object with id's and group name
def get_groups():
    print("Getting All Groups")
    report_params.get_groups()
    group_data = scrutinizer_requester.make_request(report_params)
    group_object = {}
    for group in group_data['rows']:
        group_object[group[1]['name']]= group[1]['id']
    print("{} Groups found".format(len(group_object)))
    return group_object

#find all available groups with their ID's and store just IDs to a list.
def get_group_id_list():
    print("Getting All Group IDs")
    report_params.get_groups()
    group_data = scrutinizer_requester.make_request(report_params)
    group_list = []
    for group in group_data['rows']:
        group_list.append(group[1]['id'])
    print("{} Groups found".format(len(group_list)))
    return group_list



# iterate through group list and pull all exporters for each.

def get_exporters_for_groups(group_list):
    number_of_groups = len(group_list)
    print("Creating a Group Hash comprised of all exporters in {} groups".format(number_of_groups))
    exporter_group_hash = {}
    group_count = 0
    for group_id in group_list:
        report_params.get_exporters(group_id)
        exporters_in_groups = scrutinizer_requester.make_request(report_params)
        for exporter in exporters_in_groups['results']:
            exporter_ip = exporter['exporter_ip']
            #maybe use lable later on.
            exporter_lbl = exporter['lbl']
            parent_gname = exporter['parent_gname']
            exporter_group_hash[exporter_ip] = parent_gname
        group_count += 1
        print("{} of {} completed".format(group_count,number_of_groups ), end='\r', flush=True)

    return exporter_group_hash

#get interfaces unfiltered
def top_interfaces_report(
        exporter_hash, 
        report_filters= {"sdfDips_0":"in_GROUP_ALL"}):
    if len(report_filters) == 1:
        print("Gathering Interface Data for All Devices")
    else:
        print("Gathering Interface Data for All Devices with Filters Applied")
    report_params.report_options(
            reportTypeLang="interfaces",
            rateTotal={"selected": "total"},
            orderBy=  "custom_interfacepercent",
            filters = report_filters
    )
    report_params.report_direction(
            max_rows=1000
    )
    report_params.make_object()
    interface_report = scrutinizer_requester.make_request(report_params)
    interface_report_data = interface_report['report']['table']['inbound']['rows']
    exporter_details = organize_interface_data(interface_report_data, exporter_hash)

    return exporter_details



def organize_interface_data(interface_data, exporter_hash):
    length_of_interfaces= len(interface_data)
    print("organizing results, there were {} items passed in".format(length_of_interfaces))
    exporter_details_list = []
    exporter_count = 0
    for exporter in interface_data:
        ip = exporter[1]['rawValue']
        hostname = exporter[1]['label']
        interface = exporter[2]['label']
        interface_speed = exporter[3]['label']
        interface_bits = exporter[6]['rawValue']
        interface_utilization = exporter[7]['label']
        try:
            export_group = exporter_hash[ip]
        except:
            export_group = "No Group"

        exporter_details = {
            "ip":ip,
            "exporter_group":export_group,
            "hostname":hostname,
            "interface":interface,
            "interface_speed":interface_speed,
            "interface_bits":interface_bits,
            "interface_utilization":interface_utilization
        }

        exporter_details_list.append(exporter_details)
        exporter_count += 0
        print("{} of {} completed".format(exporter_count,length_of_interfaces ), end='\r', flush=True)

    return exporter_details_list

def compare_interface_reports(unfiltered_report, filtered_report):
    print("comparing results from unfilted list to filtered list")
    merged_list = []
    for exporters in unfiltered_report:
        exporter_ip = exporters['ip']
        exporter_interface =exporters['interface']    
        for filtered_exporter in filtered_report:
            try:
                if filtered_exporter['ip'] == exporter_ip and filtered_exporter['interface'] == exporter_interface:
                    filtered_exporter.update({
                        "interface_utilization_total":exporters['interface_utilization'],
                        "interface_bits_total": exporters['interface_bits']
                        })
                    merged_list.append(filtered_exporter)

            except:
                pass  
    return merged_list

def write_csv(merged_list):
    print("writing data to a CSV file")
    keys = merged_list[0].keys()
    with open('merged_results.csv', 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(merged_list)
#get groups
group_list = get_group_id_list()

#get exporters for each group.
exporter_hash = get_exporters_for_groups(group_list)

#run all interfaces report without a filter. Apply group name as part of results. 
top_interfaces_unfiltered = top_interfaces_report(exporter_hash)
# print(top_interfaces_unfiltered)

top_interfaces_filtered = top_interfaces_report(exporter_hash,report_filters)

merged_data = compare_interface_reports(top_interfaces_unfiltered, top_interfaces_filtered)

write_csv(merged_data)


