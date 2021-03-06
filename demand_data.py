from hourly_data_container import HourlyDataContainer
import csv
import numpy as np
import helpers as helpers
from collections import OrderedDict


class DemandData :
    """ A class to store the hour-by-hour info for 
    electric demand.  It will contain info and flags indicating
    relevant info for each hour of demand data """


    def __init__(self, region):

        self.region = region
        self.hourly_data = []
        self.demand_position = 2 # Position of reported demand use
        self.uct_time_position = 1 # Position of UCT time in Dan's current EIA930_BALANCE_[year]_[monts].csv data 

        self.n_hours_surrounding = 24 # Default to do 24 hrs prior and post for running avgs
        self.hourly_demand = OrderedDict() # Can be filled later with set_hourly_demand
        self.hourly_demand_avgs = OrderedDict() # Can be filled later with set_hourly_demand

        print (self.region)

        with open("data/{}.csv".format(self.region), 'r') as f:
            info = list(csv.reader(f, delimiter=","))

        # Continue the hour notation at previous entry
        # and increment by 1 unless it's the first entry
        hour = 0
        for line in info:

            # Ensure demand is listed in expected column and
            # Skip header line
            if 'series_id' in line:
                if line[self.demand_position] != 'demand (MW)':
                    print ("\n\nDemand listed in unexpected column: region {}. Break\n\n".format(self.region))
                    break
                if line[self.uct_time_position] != 'time':
                    print ("\n\nUTC Time listed in unexpected column: region {}. Break\n\n".format(self.region))
                    break
                continue


            # Initialize an HourlyDataContainer for this hour
            self.hourly_data.append( HourlyDataContainer(hour, 
                line[self.uct_time_position],
                line[self.demand_position]) )
            hour += 1

        # For all hourly data, make delta comparisons
        # Skip first and last hours
        for i in range(1, len(self.hourly_data)-1):
            self.hourly_data[i].compute_deltas(self.hourly_data[i-1], self.hourly_data[i+1])

        print ("Length of hourly data: %i" % len(self.hourly_data))


    # Currently using a modified IQR method with much broader range.
    # This currently only targets single hour outliers where the
    # delta is large compared to the previous and following hour.
    # Skip analyzing previous or following if they are 'missing'
    def find_hourly_outliers(self):

        x = [d.delta_previous for d in self.hourly_data if not d.missing]
        if len(x) > 0:
            q05 = np.percentile(x, 5)
            q95 = np.percentile(x, 95)
            iqr = q95 - q05
            
            cut_off = iqr * 1.5
            lower = q05 - cut_off
            upper = q95 + cut_off

            for d in self.hourly_data:
                if ((d.delta_previous < lower or d.delta_previous > upper) and 
                        (d.delta_following < lower or d.delta_following > upper) and
                        d.deltas_valid):
                    d.outlier = True


    # Calculate the 24 hour running average for each hour.
    # This should give insight into how large of an effect multi-day
    # weather patters are. Missing data is treated as a gap in data
    # instead of -99.99. 
    # Skip outliers.
    def compute_daily_averages(self):

        twenty_four_hours = []
        for d in self.hourly_data:
            # Add new value
            if len(twenty_four_hours) < 24:
                to_append = d.demand if not d.outlier else -99.99
                twenty_four_hours.append(to_append)
            total = 0.
            n_good_hours = 0
            if len(twenty_four_hours) == 24:
                for h in twenty_four_hours:
                    if h != -99.99:
                        total += h
                        n_good_hours += 1
                # Pop off oldest hourly value
                twenty_four_hours.pop(0)
            if n_good_hours > 0:
                d.daily_avg = total / n_good_hours
            else:
                d.daily_avg = 0.
            if len(twenty_four_hours) >= 24:
                print ("Error, len == %i" % len(twenty_four_hours))



    def compute_hour_centered_averages(self, iqr_val=25):

        n_hours = len(self.hourly_data)

        # Make list of all hours with missing as -99.99
        running_hours = []
        for d in self.hourly_data:
            if not d.missing:
                running_hours.append(d.demand)
            else:
                running_hours.append(-99.99)

        # Loop over list and compute avgs and iqr avgs
        assert(n_hours == len(running_hours))
        for i in range(len(running_hours)):
            # fill with dummy val if we don't have full range requested
            if i < self.n_hours_surrounding or i > n_hours - self.n_hours_surrounding:
                self.hourly_data[i].set_centered_average(0.)
                self.hourly_data[i].set_centered_iqr_average(0.)
                continue

            # demand for the hours surrounding the current hour giving 2 * self.n_hours_surrounding total
            # +1 extends to n past the current hour
            surrounding_vals = running_hours[i - self.n_hours_surrounding : i + self.n_hours_surrounding] 
            assert(len(surrounding_vals) == 2*self.n_hours_surrounding)

            # Remove missing values
            new_vals = []
            for val in surrounding_vals:
                if val != -99.99:
                    new_vals.append(val) 

            if len(new_vals)>0:
                avg, iqr_avg = helpers.check_avgs(new_vals, iqr_val)
                self.hourly_data[i].set_centered_average(avg)
                self.hourly_data[i].set_centered_iqr_average(iqr_avg)
            else:
                self.hourly_data[i].set_centered_average(0.)
                self.hourly_data[i].set_centered_iqr_average(0.)


    # Create average 24 hour demand curves for different time slices
    # 0 = only annual
    # 1 = seasonal
    # 2 = monthly w/ +/- 1 month for averaging
    # 3 = monthly
    def set_hourly_demand(self, time_slice_choice=0, include_outliers=False):
        assert(time_slice_choice in [0, 1, 2, 3]), "time_slice_choice=%i, 0 = only annual, 1 = seasonal, 2 = monthly w/ +/- 1 month for averaging, 3 = monthly" % time_slice_choice

        time_slices = helpers.get_time_slice_thresholds(time_slice_choice)
        hourly_demand_entries = OrderedDict()

        # Initialize to zeros
        for time_slice in time_slices.keys() :
            self.hourly_demand[time_slice] = np.zeros(24)
            hourly_demand_entries[time_slice] = np.zeros(24)  # For averaging

        # Fill and get number of entries
        for d in self.hourly_data:
            if d.missing: continue
            if d.outlier: 
                if not include_outliers:
                    continue
            for time_slice in time_slices.keys() :
                if d.month >= time_slices[time_slice][0] and d.month <= time_slices[time_slice][1]:
                    self.hourly_demand[time_slice][d.daily_hour-1] += d.demand
                    hourly_demand_entries[time_slice][d.daily_hour-1] += 1

        # Average
        for time_slice in time_slices.keys() :
            for i in range(len(self.hourly_demand[time_slice])):
                self.hourly_demand[time_slice][i] = self.hourly_demand[time_slice][i] / hourly_demand_entries[time_slice][i]

        # Set time_slice specific averages
        for time_slice in time_slices.keys() :
            self.hourly_demand_avgs[time_slice] = np.average(self.hourly_demand[time_slice])



    # Use self.hourly_demand[time_slices][24 hours] to set info for each demand hour
    # for expected usage
    def set_24_hourly_demand(self):
        assert(len(self.hourly_demand) > 0), "You must first call set_hourly_demand to build the self.hourly_demand dict"

        time_slice_map = {}
        if 'Annual' in self.hourly_demand.keys():
            for i in range(1, 13):
                time_slice_map[i] = 'Annual'
        elif 'Winter' in self.hourly_demand.keys():
            time_slice_map[1] = 'Winter'
            time_slice_map[2] = 'Winter'
            time_slice_map[3] = 'Winter'
            time_slice_map[4] = 'Spring'
            time_slice_map[5] = 'Spring'
            time_slice_map[6] = 'Spring'
            time_slice_map[7] = 'Summer'
            time_slice_map[8] = 'Summer'
            time_slice_map[9] = 'Summer'
            time_slice_map[10] = 'Fall'
            time_slice_map[11] = 'Fall'
            time_slice_map[12] = 'Fall'
        elif 'January' in self.hourly_demand.keys():
            time_slice_map[1] = 'January'
            time_slice_map[2] = 'February'
            time_slice_map[3] = 'March'
            time_slice_map[4] = 'April'
            time_slice_map[5] = 'May'
            time_slice_map[6] = 'June'
            time_slice_map[7] = 'July'
            time_slice_map[8] = 'August'
            time_slice_map[9] = 'September'
            time_slice_map[10] = 'October'
            time_slice_map[11] = 'November'
            time_slice_map[12] = 'December'
        else:
            print ("Did not align..., set_24_hourly_demand in demand_data.py")
            return

        # For each hour, map the month to the time slice name.
        # Grab the associated self.hourly_demand for that time slice and set it.
        for d in self.hourly_data:
            val = self.hourly_demand[time_slice_map[d.month]][d.daily_hour-1]
            val -= self.hourly_demand_avgs[time_slice_map[d.month]]
            val += d.centered_iqr_average
            d.set_demand_estimate(val)

            if d.hour<self.n_hours_surrounding: continue # b/c no 48 hour centered avg for the first and last day
            if d.hour>(365*24)-self.n_hours_surrounding: continue
            if ((d.demand - d.demand_estimate)/d.demand)<-0.5 or \
                    ((d.demand - d.demand_estimate)/d.demand)>0.5:
                d.set_demand_estimate_outlier(True)

    # Calculate the annaul averages for each year in our data.
    # Some means will not include a full year
    def calculate_annaul_averages(self):
        years = OrderedDict()
        # Get list of all years
        # First value in list tracks number of hours for that year
        # in the data
        for hour in self.hourly_data:
            if not hour.datetime.year in years.keys():
                years[hour.datetime.year] = [1, []]
            else:
                years[hour.datetime.year][0] += 1


        # Loop over all hours and add their demand to the appropriate year
        for hour in self.hourly_data:
            for year, vals in years.items():
                if hour.datetime.year == year:
                    vals[1].append(hour.value)

        # Add mean values
        for year, vals in years.items():
            vals.append(np.mean(vals[1]))
            if vals[0] < 8760:
                print("WARNING: you are using calculate_annaul_averages with \
                        partial data for year {}".format(year))
        
        return years

    # Adjust demand based on annual averages derived from
    # calculate_annaul_averages()
    def normalize_to_annual_averages(self, annual_info):
        for hour in self.hourly_data:
            hour.set_demand(hour.value / annual_info[hour.datetime.year][2])


    # Calculate the seasonal averages for the whole data range
    def calculate_seasonal_averages(self):
        seasons = OrderedDict()
        seasons['Winter'] = [1, 2, 3]
        seasons['Spring'] = [4, 5, 6]
        seasons['Summer'] = [7, 8, 9]
        seasons['Fall'] = [10, 11, 12]

        data_dict = helpers.get_years_in_data(self.hourly_data)
        for year in data_dict.keys():
            data_dict[year] = OrderedDict()
            for season in seasons.keys():
                data_dict[year][season] = []

        # Loop over all hours and add their demand to the appropriate year and season
        for hour in self.hourly_data:
            for season, months in seasons.items():
                if hour.month in months:
                    data_dict[hour.datetime.year][season].append(hour.value)
                    break
        
        # Replace lists with mean value before returning
        for year, seasons in data_dict.items():
            for season in seasons.keys():
                data_dict[year][season] = float(np.mean(data_dict[year][season]))
        return data_dict

    # Calculate the monthly averages for the whole data range
    def calculate_monthly_averages(self):
        months = OrderedDict()
        months[1] = 'January'
        months[2] = 'February'
        months[3] = 'March'
        months[4] = 'April'
        months[5] = 'May'
        months[6] = 'June'
        months[7] = 'July'
        months[8] = 'August'
        months[9] = 'September'
        months[10] = 'October'
        months[11] = 'November'
        months[12] = 'December'

        data_dict = helpers.get_years_in_data(self.hourly_data)
        for year in data_dict.keys():
            data_dict[year] = OrderedDict()
            for month, name in months.items():
                data_dict[year][name] = []

        # Loop over all hours and add their demand to the appropriate year and season
        for hour in self.hourly_data:
            data_dict[hour.datetime.year][months[hour.datetime.month]].append(hour.value)
        
        # Replace lists with mean value before returning
        for year, months_names in data_dict.items():
            for month in months_names.keys():
                data_dict[year][month] = float(np.mean(data_dict[year][month]))
        return data_dict
            
    # Remove partial years from data
    def remove_partial_years(self):
        years = OrderedDict()
        # Get list of all years
        # First value in list tracks number of hours for that year
        # in the data
        for hour in self.hourly_data:
            if not hour.datetime.year in years.keys():
                years[hour.datetime.year] = 1
            else:
                years[hour.datetime.year] += 1

        # Remove years with less than full hourly data
        self.hourly_data = [hour for hour in self.hourly_data if years[hour.datetime.year] >= 8760]

