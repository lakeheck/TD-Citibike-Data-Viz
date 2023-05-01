from mongo import get_database
from citibikeAPI import *
import time

delay = 5 #in seconds

#setup mongo
dbname = get_database()
collection_name = dbname["ebike_ride_events"]

#initialize with an empty funtion call 
nDF, chgs = getEbikeData()
oDF = nDF #set our old dataframe to our baseline from initialization 
print('sucessfully initialized')
time.sleep(delay) #wait after we setup
#this should run each minute 
starttime = time.time()
iter = 0
while True: #infinite loop
	nDF , chgs = getEbikeData(oDF)
	oDF = nDF

	for i in chgs.index:
		s = formatSeries(chgs.loc[i])
		collection_name.insert_one(s)

	print("running, ", str(iter), " iterations elapsed\n", "chg count: ", str(chgs.shape[0]))
	iter = iter + 1
	time.sleep(delay - ((time.time() - starttime) % delay))
	
