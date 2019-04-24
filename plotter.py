import matplotlib.pyplot as plt
import matplotlib
from matplotlib.pyplot import figure
import numpy as np
from collections import OrderedDict


def plot_24_hour_avg(hourly_data_set, names, x_label, y_label, title, save, do_all_seasons=False):

    matplotlib.rcParams['figure.figsize'] = (6.0, 4.0)

    seasons = OrderedDict()
    # season : min, max month
    seasons['Annual'] = [1, 12]
    if do_all_seasons:
        seasons['Winter'] = [1, 3]
        seasons['Spring'] = [4, 6]
        seasons['Summer'] = [7, 9]
        seasons['Autumn'] = [10, 12]

    hourly_demand = OrderedDict()
    hourly_demand_entries = OrderedDict()

    # Initialize to zeros
    for season in seasons.keys() :
        hourly_demand[season] = np.zeros(24)
        hourly_demand_entries[season] = np.zeros(24)  # For averaging

    # Fill and get number of entries
    for d in hourly_data_set:
        if d.missing: continue
        for season in seasons.keys() :
            if d.month >= seasons[season][0] and d.month <= seasons[season][1]:
                hourly_demand[season][d.daily_hour-1] += d.demand
                hourly_demand_entries[season][d.daily_hour-1] += 1

    # Average
    for season in seasons.keys() :
        print(season)
        for i in range(len(hourly_demand[season])):
            hourly_demand[season][i] = hourly_demand[season][i] / hourly_demand_entries[season][i]

    hours = [i for i in range(1, 25)]

    fig, ax = plt.subplots()
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    plt.title(title)
    for season in seasons.keys() :
        ax.plot(hours, hourly_demand[season], 'o', label=season)
    plt.legend()
    plt.savefig("plots/"+save+".png")


def plot_hist(x, x_label, y_label, title, save, n_bins=100, logY=False):

    matplotlib.rcParams['figure.figsize'] = (6.0, 4.0)
    x.sort() # to use for x range
    n, bins, patches = plt.hist(x, n_bins, range=[x[0], x[-1]], facecolor='g', alpha=0.75)

    plt.xlabel(x_labell)
    plt.ylabel(y_label)
    plt.title(title)
    #plt.text(bins.max()*0.35, n.max()*.95, r'ChiSq / ndof = %.2f' % (chiSq/ len(demand['hour']) ) )
    #plt.axis([-1, 2])
    plt.grid(True)
    if logY:
        plt.yscale('log', nonposy='clip')
    plt.savefig("plots/"+save+".png")
    return plt


def plot_demand(hourly_data_sets, names, x_label, y_label, title, save, ylim=[]):

    matplotlib.rcParams['figure.figsize'] = (14.0, 6.0)
    fig, ax = plt.subplots()
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    plt.title(title)

    y_max = 0.
    for hourly_data_set, name in zip(hourly_data_sets, names):
        x = [hour_data.hour for hour_data in hourly_data_set]
        y = [hour_data.demand for hour_data in hourly_data_set]
        this_max = max(y) if len(y) > 0 else 0
        if this_max > y_max:
            y_max = this_max
        ax.plot(x, y, 'o', label=name)

    if ylim != []:
        ax.set_ylim(ylim[0], ylim[1])
    else:
        old_y_min, old_y_max = ax.get_ylim()
        ax.set_ylim(old_y_min, y_max * 1.1)

    plt.legend()
    plt.grid()
    plt.savefig("plots/"+save+".png")
    return fig, ax


def plot_demand_with_daily(fig, ax, daily_x, daily_y, save):
    ax.plot(daily_x, daily_y, 'o', label='24 Hour Avg')
    plt.legend()
    plt.grid()
    plt.savefig("plots/"+save+".png")
    return fig, ax
