import os
import re


# display off
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateLocator, AutoDateFormatter
plt.ioff()

from copy import copy
from matplotlib import colors
import matplotlib.pyplot as plt

from matplotlib.dates import AutoDateFormatter, AutoDateLocator, num2date
from mpl_toolkits.axes_grid1 import make_axes_locatable
from astropy.time import Time
import numpy as np

from suncasa.dspec import dspec
import glob

def extract_date_from_path(path):
    # Regular expression to match the date pattern in directory names
    match = re.search(r'(\d{4})(\d{2})(\d{2})', path)
    if match:
        year, month, day = match.groups()
        return year, month, day
    return None, None, None

def divide_time_in_hours(time_start, time_end, hour_length=1/24):
    # Calculate the total duration in days
    total_duration = time_end.mjd - time_start.mjd

    # Convert duration to hours
    total_hours = total_duration / hour_length
    full_hours = int(total_hours)

    # Check if the last hour is less than 0.5 hours
    if total_hours % 1 < 0.5 and full_hours > 0:
        full_hours -= 1

    # Generate time sections
    time_sections = [(time_start + i * hour_length, time_start + (i + 1) * hour_length) for i in range(full_hours)]

    # Add the remaining time to the last section if there's a remainder
    if total_hours % 1 >= 0.5 or full_hours == 0:
        time_sections.append((time_start + full_hours * hour_length, time_end))

    return time_sections


def rebin1d(arr, new_len):
    shape = (new_len, len(arr) // new_len)
    return arr.reshape(shape).mean(1)


def rebin2d(arr, new_shape):
    shape = (new_shape[0], arr.shape[0] // new_shape[0],
             new_shape[1], arr.shape[1] // new_shape[1])
    return arr.reshape(shape).mean(-1).mean(1)


def get_cal_factor(cal_factor_file):
    import csv
    with open(cal_factor_file, 'r') as f:
        reader = csv.reader(f)
        cal_factors = list(reader)
    freq_num = [ a[0] for a in cal_factors[1:]]
    cal_num = [ a[1] for a in cal_factors[1:]]
    freq_num = np.array(freq_num, dtype=float)
    cal_num = np.array(cal_num, dtype=float)
    return freq_num, cal_num

def traverse_and_print_dates(directory):
    for root, dirs, _ in os.walk(directory):
        for name in dirs:
            full_path = os.path.join(root, name)
            data_directory = full_path
            year, month, day = extract_date_from_path(full_path)
            if year and month and day:
                print("Processing {}".format(full_path))
                #if True:
                try:
                    files = glob.glob(data_directory + '/*')
                    files.sort()
                    d = dspec.Dspec()
                    d.read(files, source='lwa', timebin=32, freqbin=5, freqrange=[29,84], stokes='IV')

                    time_range_all =[ d.time_axis[0] , d.time_axis[-1]]
                    hourly_ranges = divide_time_in_hours(time_range_all[0],time_range_all[1], hour_length=1/24)

                    fig = d.plot( pol='I', plot_fast=True,minmaxpercentile=True,vmax2=0.5,vmin2=-0.5)

                    ax = fig.get_axes()[0]
                    locator = AutoDateLocator(minticks=2)
                    ax.xaxis.set_major_locator(locator)
                                    # ax1.xaxis.set_major_formatter(AutoDateFormatter(locator))
                    formatter = AutoDateFormatter(locator)
                    formatter.scaled[1 / 24] = '%H:%M'
                    formatter.scaled[1 / (24 * 60)] = '%H:%M'
                    ax.xaxis.set_major_formatter(formatter)
                    ax.set_title(d.time_axis[0].strftime('%Y-%m-%d %H:%M:%S') + ' - ' + d.time_axis[-1].strftime('%Y-%m-%d %H:%M:%S'))

                    fig.savefig('/common/lwa/spec/daily/{}{}{}.png'.format(year,month,day))
                    d.tofits('/common/lwa/spec/fits/{}{}{}.fits'.format(year,month,day))
                    for i in range(len(hourly_ranges)):
                        thishour = [ hourly_ranges[i][0].datetime.strftime('%Y-%m-%dT%H:%M:%S'),
                                    hourly_ranges[i][1].datetime.strftime('%Y-%m-%dT%H:%M:%S') ]
                        fig = d.plot(pol='IP',timerange=thishour,plot_fast=True,minmaxpercentile=True,vmax2=0.5,vmin2=-0.5)
                        os.makedirs('/common/lwa/spec/hourly/{}{}'.format(year,month), exist_ok=True)
                        fig.savefig('/common/lwa/spec/hourly/{}{}/{}_{}.png'.format(year,month,day,i))
                        plt.close(fig)
                except:
                    print("Error with {}".format(full_path))
                    pass

import sys

def one_day_proc(full_path, freq_bin=4, cal_dirs = []):
    if True:
        year, month, day = extract_date_from_path(full_path)
        if year and month and day:
            print("[", Time.now().datetime ,"], Processing {}".format(full_path))
            try:
            #if True:
                files = glob.glob(full_path + '/*')
                files.sort()
                d = dspec.Dspec()

                d.read(files, source='lwa', timebin=32, freqbin=freq_bin, stokes='IV')
                print(cal_dirs)
                do_calib = False
                if len(cal_dirs)>0: # do calibration
                    do_calib=True
                    cal_files = []
                    for cal_dir in cal_dirs:
                        cal_files += glob.glob(cal_dir + '/*.csv')
                    cal_files.sort(key=lambda x: x.split('/')[-1].split('_')[0])
                # get filename from full path
                    date_cal_lst = [ cal_factor_csv_f.split('/')[-1].split('_')[0]
                            for cal_factor_csv_f in cal_files]

                    time_of_firstslot = d.time_axis[0]
                    str_this_day = time_of_firstslot.to_datetime().strftime('%Y%m%d')

                    idx_cal = 0
                    for date_cal in date_cal_lst:
                        if date_cal <= str_this_day:
                            cal_fname = date_cal
                            idx_cal += 1
                        else:
                            break
                    print("Using calibration factor from {}".format(cal_files[idx_cal-1]))
                    freq_num, cal_num = get_cal_factor(cal_files[idx_cal-1])


                if do_calib:
                    cal_num_downsp = cal_num[::freq_bin]
                    d.data = d.data / cal_num_downsp[None,None,:,None]
                time_range_all =[ d.time_axis[0] , d.time_axis[-1]]
                hourly_ranges = divide_time_in_hours(time_range_all[0],time_range_all[1], hour_length=1/24)

                fig = d.plot( pol='I', plot_fast=True,minmaxpercentile=True,vmax2=0.5,vmin2=-0.5)
                ax = fig.get_axes()[0]
                locator = AutoDateLocator(minticks=2)
                ax.xaxis.set_major_locator(locator)
                                # ax1.xaxis.set_major_formatter(AutoDateFormatter(locator))
                formatter = AutoDateFormatter(locator)
                formatter.scaled[1 / 24] = '%H:%M'
                formatter.scaled[1 / (24 * 60)] = '%H:%M'
                ax.xaxis.set_major_formatter(formatter)
                ax.set_title(d.time_axis[0].strftime('%Y-%m-%d %H:%M:%S') + ' - ' + d.time_axis[-1].strftime('%Y-%m-%d %H:%M:%S'))

                fig.savefig('/common/lwa/spec/daily/{}{}{}.png'.format(year,month,day))
                d.tofits('/common/lwa/spec/fits/{}{}{}.fits'.format(year,month,day))
                for i in range(len(hourly_ranges)):
                    thishour = [ hourly_ranges[i][0].datetime.strftime('%Y-%m-%dT%H:%M:%S'),
                                hourly_ranges[i][1].datetime.strftime('%Y-%m-%dT%H:%M:%S') ]
                    fig = d.plot(pol='IP',timerange=thishour,plot_fast=True,minmaxpercentile=True,vmax2=0.5,vmin2=-0.5)
                    os.makedirs('/common/lwa/spec/hourly/{}{}'.format(year,month), exist_ok=True)
                    fig.savefig('/common/lwa/spec/hourly/{}{}/{}_{}.png'.format(year,month,day,i))
                    plt.close(fig)
            except:
                print("Error with {}".format(full_path))
                # print error msg
                print( "Error: ", sys.exc_info()[0] )
#    except:
#        print("Error with {}".format(full_path))

if __name__ == "__main__":
    """
    This script is used to generate all the spectra for the LWA data

    Example usage:
    python generate_all_spectra.py --oneday /nas5/ovro-lwa-data/beam/beam-data/202106/beam20210601
    python generate_all_spectra.py --lasttwoday
    """

    # parse the arg directory path as input
    import argparse
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('datahome', metavar='D', type=str, help='an integer for the accumulator', nargs='?',
                         default='/nas5/ovro-lwa-data/beam/beam-data/')
    parser.add_argument('--oneday', action='store_true', help='Process one day')
    parser.add_argument('--lasttwoday', action='store_true', help='Process the last two days data')
    parser.add_argument('--onedaypath', type=str, help='The data path for one day processing')
    parser.add_argument('--lastnday', type=int, help='Process the last n days data',default=-1)
    parser.add_argument('--runall', action='store_true', help='Process all historical data')
    parser.add_argument('--dir_cal', type=str, help='The directory for calibration factor',
                        default='')

    pre_defined_cal_dir = [
        '/lustre/bin.chen/realtime_pipeline/caltables_beam/',
        '/nas6/ovro-lwa-data/calibrations/caltables_beam/'
    ]


    args = parser.parse_args()
    directory_path = args.datahome
    print(pre_defined_cal_dir)
    print(args.dir_cal)
    pre_defined_cal_dir.append(args.dir_cal)
    print(pre_defined_cal_dir)
    if args.oneday:
        one_day_proc(args.onedaypath)
    elif args.runall:
        traverse_and_print_dates(directory_path)
    elif args.lasttwoday:
        # get yyyy, mm, dd of today and yesterday
        import datetime
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        yyyy_today, mm_today, dd_today = today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
        yyyy_yesterday, mm_yesterday, dd_yesterday = yesterday.strftime("%Y"), yesterday.strftime("%m"), yesterday.strftime("%d")

        one_day_proc(os.path.join(directory_path, yyyy_yesterday+mm_yesterday, 'beam'+yyyy_yesterday+mm_yesterday+dd_yesterday), cal_dirs = pre_defined_cal_dir)
        one_day_proc(os.path.join(directory_path, yyyy_today+mm_today, 'beam'+yyyy_today+mm_today+dd_today), cal_dirs = pre_defined_cal_dir)
    elif args.lastnday>0:
        import datetime
        today = datetime.date.today()
        for i in range(args.lastnday):
            today = today - datetime.timedelta(days=1)
            yyyy, mm, dd = today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
            one_day_proc(os.path.join(directory_path, yyyy+mm, 'beam'+yyyy+mm+dd), cal_dirs = pre_defined_cal_dir)
