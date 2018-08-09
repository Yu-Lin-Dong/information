import time

from datetime import datetime

print(time.localtime())
t = time.localtime()
mon_begin = "%d-%02d-01"%(t.tm_year,t.tm_mon)
mon_begin_date = datetime.strptime(mon_begin,'%Y-%m-%d')
print(mon_begin_date)