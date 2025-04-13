import vfd
from time import sleep, ctime

d = vfd.BA63("/dev/ttySC0")

d.reset()
d.write("marloth automation \r\n", 1, 2)

d.scroll("", line=2, step_delay=0.2)

while 1:
    sleep(0.1)
    d.scroll_update(2, ctime()[0:-4])


