
def strtime_secs(tm):
    for prefix,factor in [['n',1e9],
                          ['mc', 1e6],
                          ['m', 1e3],
                          ['', 1]][::-1]:
        if tm * factor >= 0.3:
            break
    return '%.1f %ss' % (tm*factor, prefix)

def strtime(tm):
    minutes, secs = divmod(tm, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365)
    if years:
        return '%.1f years' % (tm / 365.0 / 24.0 / 60.0 / 60.0,)
    if days:
        return '%.1f days' % (tm / 24.0 / 60.0 / 60.0,)
    if hours:
        return '%.1f hours' % (tm / 60.0 / 60.0,)
    if minutes:
        return '%.1f minutes' % (tm / 60.0)
    return strtime_secs(tm)


