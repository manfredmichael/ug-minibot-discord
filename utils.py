import datetime
import os
from math import ceil

def week_of_month(dt):
    """ Returns the week of the month for the specified date.
    """

    first_day = dt.replace(day=1)

    dom = dt.day
    adjusted_dom = dom + first_day.weekday()

    return int(ceil(adjusted_dom/7.0))

def get_month_code():
    return int(os.environ.get('MONTH_CODE'))

def get_current_week():
    return week_of_month(datetime.datetime.now()) 

def bot_is_running():
    """ Returns whether or not the bot is supposed to run in boolean
    
    There are 2 dynos, one will run at first half of the month, and the other for the rest of the month
    """
    month_code = get_month_code()
    current_week = get_current_week()
    return (month_code == 0 and current_week <= 2) or (month_code == 1 and current_week > 2)
