import json, os, re, pprint
import pandas as pd
import getpass

def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)    

def output_csv(run_number, thr):
    # hvscan_path = "/var/webdcs/HVSCAN"
    hvscan_path = f"/Users/dayron/GIF/test_beam_Oct2021/efficiency_scans"
    # file_path = f'{hvscan_path}/{run_number:06}/Digitizer_efficiency/analysing_qmax_stcdrip_limited_by_clustersize_20ns/Th_{thr:01}'
    file_path = f'{hvscan_path}/{run_number:06}/Digitizer_efficiency/analyzing_all_strip_over_thr/Th_{thr:01}'
    save_path = f'{hvscan_path}/analysis'

    hv_values = [4800., 5200., 5400., 5600., 5800., 6000., 6200., 6400., 6600., 6800., 7000., 7200., 7400., 7600., 7800., 8000.]

    HV_points = []
    for entry_name in os.listdir(file_path):
        entry_path = os.path.join(file_path, entry_name)
        if os.path.isdir(entry_path):
            HV_points.append(entry_name)
    HV_points = natural_sort(HV_points)

    data = []
    for idx, HV_point in enumerate(HV_points):
        with open(file_path + '/' + HV_point + '/output.json') as json_file:
            output = json.load(json_file)
        if idx == 0:
            '''hveff = [i for i in output[HV_point] if i.startswith('hveff')]
            imons = [i for i in output[HV_point] if (i.startswith('imon') and not i.startswith('imon_err'))]
            eff = [i for i in output[HV_point] if i.startswith('efficiencyMuon')]
            columns = hveff + imons + eff'''
            columns = [i for i in output["output_parameters"]]
            
        line = [output["output_parameters"][column] for column in columns]
        data.append(line)
    df = pd.DataFrame(data, columns=columns)
    df.insert(loc=0, column='hveff', value=hv_values)
    df.to_csv(f"{save_path}/run_{run_number:06}_thr_{thr}.csv", index=False)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Output csv data')
    parser.add_argument('run_number', metavar='run_number', type=int, nargs=1, help='run number')
    parser.add_argument('thr', metavar='thr', type=int, nargs=1, help='threshold value')

    args = parser.parse_args()
    run_number = args.run_number[0]
    thr = args.thr[0]
    
    output_csv(run_number, thr)
