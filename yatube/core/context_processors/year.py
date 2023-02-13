import datetime


def year(request):
    today = datetime.date.today()
    today_year = today.year
    return {
        'year': today_year,
    }
