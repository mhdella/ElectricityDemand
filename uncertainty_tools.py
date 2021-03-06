# Some methods for loading and analyzing pandas DataFrams 
# representing electricity demand and solar and wind availability
# info



import pandas as pd
import numpy as np
from datetime import datetime
import copy


# returns pandas df of renewable info, start_year defaults to prior to our records
# so all entries are kept, default end_year is after all records, so all entries
# are kept
def return_renewable_df(file_path, is_wind, is_solar, start_year=1900, end_year=2020):

    assert(is_wind + is_solar == 1), "Wind OR solar must be specified. You selected is_wind {} and is_solar {}".format(is_wind, is_solar)

    # Load normalizations
    if is_wind:
        energy = 'wind'
    if is_solar:
        energy = 'solar'
    dta = pd.read_csv(file_path, #index_col='time', 
                       dtype={'{} capacity'.format(energy):np.float64},
                      parse_dates=True, na_values=['MISSING', 'EMPTY'])
    
    # FIXME only have wind normalizations now, so load them for solar as well
    tmp = 'wind'
    annual = np.load('normalization_annual_{}.npy'.format(tmp))
    hour_and_weeks = np.load('normalization_24hr_x_52week_{}.npy'.format(tmp))
    

    # skip this loop if all data is to be included
    if not (start_year == 1900 and end_year == 2020):
        to_remove = []
        for index, row in dta.iterrows():
            uct_time = row['time']
            uct_time = sem_time(uct_time)
        
            date = datetime.strptime(uct_time, '%Y%m%dT%HZ')
            # Filter unwanted entries by year
            if date.year < start_year: to_remove.append(index)
            if date.year > end_year: to_remove.append(index)
        dta = dta.drop(to_remove)


    dates = []
    years = []
    weeks = []
    hours = []
    
    annual_norm = []
    weekly_norm = []
    full_norm = []
    normalized = []
    
    for index, row in dta.iterrows():
    
        uct_time = row['time']
        uct_time = sem_time(uct_time)
        
        date = datetime.strptime(uct_time, '%Y%m%dT%HZ')

        years.append(date.year)
        weeks.append(date.isocalendar()[1] - 1)
        if weeks[-1] == 52:
            weeks[-1] = 51
        hours.append(date.hour)
        dates.append(date)
        
    
        #Use filled time info arrays to access the normalization values needed
        annual_norm.append(annual.item().get(years[-1])[2])
        weekly_norm.append(hour_and_weeks[weeks[-1]][hours[-1]])
        full_norm.append(annual_norm[-1] * weekly_norm[-1])
        normalized.append( (row['{} capacity'.format(energy)] - full_norm[-1]) / full_norm[-1])
        
    dta = dta.assign(date=dates)
    dta = dta.assign(year=years)
    dta = dta.assign(week=weeks)
    dta = dta.assign(hour=hours)
    dta = dta.assign(a_normalization=annual_norm)
    dta = dta.assign(w_normalization=weekly_norm)
    dta = dta.assign(normalization=full_norm)
    dta = dta.assign(normed=normalized)

    print("Loaded {} data from {}:".format(energy, file_path))
    print(dta.head())
    print(dta.tail())
    return dta


# returns pandas df of demand info, start_year defaults to prior to our records
# so all entries are kept, default end_year is after all records, so all entries
# are kept
def return_demand_df(file_path, start_year=1900, end_year=2020):

    dta = pd.read_csv(file_path, #index_col='time', 
                       dtype={'demand (MW)':np.float64},
                      parse_dates=True, na_values=['MISSING', 'EMPTY'])
    

    # skip this loop if all data is to be included
    if not (start_year == 1900 and end_year == 2020):
        to_remove = []
        for index, row in dta.iterrows():
            uct_time = row['time']
            uct_time = sem_time(uct_time)
        
            date = datetime.strptime(uct_time, '%Y%m%dT%HZ')
            # Filter unwanted entries by year
            if date.year < start_year: to_remove.append(index)
            if date.year > end_year: to_remove.append(index)
        dta = dta.drop(to_remove)
    

    dates = []
    years = []
    weeks = []
    hours = []
    
    for index, row in dta.iterrows():
    
        uct_time = row['time']
        uct_time = sem_time(uct_time)

        date = datetime.strptime(uct_time, '%Y%m%dT%HZ')
        years.append(date.year)
        weeks.append(date.isocalendar()[1] - 1)
        if weeks[-1] == 52:
            weeks[-1] = 51
        hours.append(date.hour)
        dates.append(date)
        

    # Once all data/time stuff is handled
    rolling = np.roll(dta['demand (MW)'], -24)
    for i in range(-23, 24): # with rolling this will take -24 through +23 giving 48 hrs total
        rolling += np.roll(dta['demand (MW)'], i)
    rolling = rolling / 48.
    

    dta = dta.assign(date=dates)
    dta = dta.assign(year=years)
    dta = dta.assign(week=weeks)
    dta = dta.assign(hour=hours)
    dta = dta.assign(fourtyEight=rolling)


    print("Loaded Demand Data from {}".format(file_path))
    print(dta.head())
    print(dta.tail())
    return dta




# This takes an erroneous UCT time with hours 1 - 24
# and shiftes them to 0 - 23
def sem_time(uct_time):
    uct_time = uct_time.replace('T01Z', 'T00Z')
    uct_time = uct_time.replace('T02Z', 'T01Z')
    uct_time = uct_time.replace('T03Z', 'T02Z')
    uct_time = uct_time.replace('T04Z', 'T03Z')
    uct_time = uct_time.replace('T05Z', 'T04Z')
    uct_time = uct_time.replace('T06Z', 'T05Z')
    uct_time = uct_time.replace('T07Z', 'T06Z')
    uct_time = uct_time.replace('T08Z', 'T07Z')
    uct_time = uct_time.replace('T09Z', 'T08Z')
    uct_time = uct_time.replace('T10Z', 'T09Z')
    uct_time = uct_time.replace('T11Z', 'T10Z')
    uct_time = uct_time.replace('T12Z', 'T11Z')
    uct_time = uct_time.replace('T13Z', 'T12Z')
    uct_time = uct_time.replace('T14Z', 'T13Z')
    uct_time = uct_time.replace('T15Z', 'T14Z')
    uct_time = uct_time.replace('T16Z', 'T15Z')
    uct_time = uct_time.replace('T17Z', 'T16Z')
    uct_time = uct_time.replace('T18Z', 'T17Z')
    uct_time = uct_time.replace('T19Z', 'T18Z')
    uct_time = uct_time.replace('T20Z', 'T19Z')
    uct_time = uct_time.replace('T21Z', 'T20Z')
    uct_time = uct_time.replace('T22Z', 'T21Z')
    uct_time = uct_time.replace('T23Z', 'T22Z')
    uct_time = uct_time.replace('T24Z', 'T23Z')
    return uct_time




# Return the state number based on the value
def get_state(val, thresholds):

    rtn = 0
    for threshold in thresholds:
        if val < threshold:
            return rtn
        else:
            rtn += 1
    return rtn


# Normalize matrix rows to unity
def normalize_rows(transitions):
    normed = copy.deepcopy(transitions)
    for i in range(len(normed)):
        normed[i] = normed[i]/normed[i].sum()
    return normed


# Markov transition matrix for state system.
# Initial state is set by first time slice.
# Transitions are analyzed for n-1 time steps.
def get_markov_transitions(vals, thresholds):

    # Transitions matrix for recording each hour-to-hour transition
    transitions = np.zeros((len(thresholds)+1, len(thresholds)+1))


    prev = 0
    prev = get_state(vals[0], thresholds)
    current = 0
    for i in range(1, len(vals)):
        val = vals[i]
        current = get_state(val, thresholds)
        transitions[prev][current] += 1
        prev = current

    normed = normalize_rows(transitions)

    return transitions, normed

