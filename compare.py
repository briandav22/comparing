from scrut_api import ReportAPI, Requester
import json
import csv



#Update with your Scrutinizer Information
scrutinizer_requester = Requester(
    authToken="yourAuthToken",
    hostname="example.yourscrut.local"
)

#Update with your IPGROUP filter 
report_filters = {
     "sdfDips_0": "in_GROUP_ALL",
     "sdfIPGroups_0": "in_16900092_both"
}

#Update with time range and granuliarity you want.
time_range = "Last24Hours"
granularity = "5"

#this variable is for later use, for now we will use it if we pass a filter we aren't looking for specifically
group_name = "filtered"


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

def get_ipgroup_name(report_filters):
    report_params.get_ipgroup_name()
    group_data = scrutinizer_requester.make_request(report_params)

    for ip_group in group_data:
        try:
            if ip_group['id'] == report_filters:
                ip_group_name = ip_group['name']
                return ip_group_name
        except:
            pass         
    
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
        report_filters= {"sdfDips_0":"in_GROUP_ALL"},
        filter_name = '',
         ):
    if len(report_filters) == 1:
        filter_name = "interface"
        print("Gathering Interface Data for All Devices for {} in data source {} ".format(time_range, granularity))
    else:
        filter_name = filter_name
        print("Gathering Interface Data for All Devices with Filters Applied for {} in data source {} ".format(time_range, granularity))
    report_params.report_options(
            reportTypeLang="interfaces",
            rateTotal={"selected": "total"},
            orderBy=  "custom_interfacepercent",
            filters = report_filters,
            times = {"dateRange":time_range},
            dataGranularity= granularity

    )
    report_params.report_direction(
            max_rows=1000
    )
    report_params.make_object()
    interface_report = scrutinizer_requester.make_request(report_params)
    interface_report_data = interface_report['report']['table']['inbound']['rows']
    exporter_details = organize_interface_data(interface_report_data, exporter_hash, filter_name)

    return exporter_details



def organize_interface_data(interface_data, exporter_hash, filter_name):
    length_of_interfaces= len(interface_data)
    print("organizing results, there were {} items passed in".format(length_of_interfaces))
    exporter_details_list = []
    exporter_count = 0
    for exporter in interface_data:
        ip = exporter[1]['rawValue']
        interface = exporter[2]['label']
        interface_peak = exporter[4]['label']
        interface_95th = exporter[5]['label']
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
            "interface":interface,
            "interface_speed":interface_speed,
            "{}_bits".format(filter_name):interface_bits,
            "{}_peak".format(filter_name):interface_peak,
            "{}_95th".format(filter_name):interface_95th,
            "{}_utilization".format(filter_name):interface_utilization
        }

        exporter_details_list.append(exporter_details)
        exporter_count += 0
        print("{} of {} completed".format(exporter_count,length_of_interfaces ), end='\r', flush=True)

    return exporter_details_list

def compare_interface_reports(unfiltered_report, filtered_report):
    print("comparing results from unfilted list to filtered list")
    if len(filtered_report) == 0:
        print("There were no results in the filtered report. Nothing to return")
        return
    merged_list = []
    for exporters in unfiltered_report:
        exporter_ip = exporters['ip']
        exporter_interface =exporters['interface']    
        for filtered_exporter in filtered_report:
            # print(filtered_exporter)
            try:
                if filtered_exporter['ip'] == exporter_ip and filtered_exporter['interface'] == exporter_interface:
                    filtered_exporter.update({
                        
                        "interface_bits_total": exporters['interface_bits'],
                        "interface_peak_total": exporters['interface_peak'],
                        "interface_95th_total":exporters['interface_95th'],
                        "interface_utilization_total":exporters['interface_utilization']
                        })
                    merged_list.append(filtered_exporter)

            except:
                pass  
    return merged_list

def write_csv(merged_list):
    print("writing data to a CSV file")
    keys = merged_list[0].keys()
    with open('merged_results_{}.csv'.format(time_range), 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(merged_list)

try:
    if report_filters['sdfIPGroups_0']:
        ip_group_id = report_filters['sdfIPGroups_0'].split('_')[1]
        group_name = get_ipgroup_name(ip_group_id)
except:
    pass


group_list = get_group_id_list()

#get exporters for each group.
exporter_hash = get_exporters_for_groups(group_list)


#run all interfaces report without a filter. Apply group name as part of results. 
top_interfaces_unfiltered = top_interfaces_report(exporter_hash)
# print(top_interfaces_unfiltered)

top_interfaces_filtered = top_interfaces_report(exporter_hash,report_filters, group_name)

merged_data = compare_interface_reports(top_interfaces_unfiltered, top_interfaces_filtered)

write_csv(merged_data)


