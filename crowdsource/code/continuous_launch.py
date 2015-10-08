import os
import time

while True:
    print("Launch job at")
    os.system("date")
    os.system("make launch")
    print("End launch job at")
    os.system('date')
    time.sleep(1800)
