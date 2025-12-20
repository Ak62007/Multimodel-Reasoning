def secs_mins(secs):
    mins = secs / 60
    if mins < 1:
        return mins*60
    else:
        sec = (mins - (secs // 60))*60
        mins = str(int((secs // 60))) + ":" + str(round(sec))
        return mins