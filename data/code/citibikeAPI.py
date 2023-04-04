import pandas as pd
import urllib.request, json, jmespath
import uuid 

#auth
osr_key = '5b3ce3597851110001cf62487d33115ea15e483bb81a0b4cfcc899cb'

def getAllStationData():
	station_info_url = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
	station_status_url = 'https://gbfs.citibikenyc.com/gbfs/en/station_status.json'

	#get station info
	with urllib.request.urlopen(station_info_url) as url:
		station_info_data = json.load(url)

	station_info_df = pd.DataFrame(station_info_data['data']['stations']).set_index('station_id')
	station_info_df = station_info_df[['name', 'lat', 'lon', 'capacity', 'legacy_id']] #extract cols of interest
	station_info_df.head()
	
	#get station status
	with urllib.request.urlopen(station_status_url) as url:
		station_status_data = json.load(url)

	station_status_df = pd.DataFrame(station_status_data['data']['stations']).set_index('station_id')
	station_status_df = station_status_df[['num_docks_available', 'num_bikes_disabled', 'num_ebikes_available', 'num_bikes_available', 'num_docks_disabled', 'station_status', 'is_renting', 'is_returning', 'last_reported', 'is_installed']] #extract cols of interest
	
	return station_info_df.merge(station_status_df, left_index=True, right_index=True)

def getEbikeData(old_dataframe=None):

	changes = []

	station_status_url = 'https://gbfs.citibikenyc.com/gbfs/en/station_status.json'
	#get station status
	with urllib.request.urlopen(station_status_url) as url:
		station_status_data = json.load(url)

	station_status_df = pd.DataFrame(station_status_data['data']['stations']).set_index('station_id')
	station_status_df = station_status_df[['num_ebikes_available', 'last_reported']] #extract cols of interest, here just ebike and update timestampe 
	#TODO: we should probably screen out ebike updates due to station-level events such as activation / nonactivation, rebalancing, etc 

	updated_df = station_status_df

	if old_dataframe is None: return station_status_df.sort_index(), pd.DataFrame(changes, columns = ['station_id', 'num_ebikes_available', 'gain_loss', 'window_start', 'window_end']).set_index('station_id')
	else: 
		udc = updated_df.sort_index()
		sdc = old_dataframe.sort_index()

		for i in sdc.index:
			if udc.loc[i,'num_ebikes_available'] == sdc.loc[i,'num_ebikes_available']: pass 
			else: 
				new_bike_count = udc.loc[i].to_list()[0]
				window_end = udc.loc[i].to_list()[1]
				old_bike_count = sdc.loc[i].to_list()[0]
				window_start = sdc.loc[i].to_list()[1]
				changes += [[i, new_bike_count, old_bike_count-new_bike_count, window_start, window_end]]
				# print('change!', udc.loc[i,'num_ebikes_available'], sdc.loc[i,'num_ebikes_available'], i, udc.loc[i, 'last_reported'])
		
		return udc, pd.DataFrame(changes, columns = ['station_id', 'num_ebikes_available', 'gain_loss', 'window_start', 'window_end']).set_index('station_id')
		# return new df, changes

#helper function to format our changed dataframe for mongo
def formatSeries(s):
	return {
		"event_id": str(uuid.uuid4()),
		"station_id": s.name,
		"num_ebikes_available": str(s.num_ebikes_available),
		"gain_loss": str(s.gain_loss),
		"window_start": str(s.window_start), 
		"window_end":str(s.window_end),
		"time_updated": pd.Timestamp.now() 
	}

def findMostCommonRoutesByStation(trip_data):
	station_data = getAllStationData()
	#we only want trips that dont start and end at the same station
	trips = trip_data[trip_data['start station id'] != trip_data['end station id']].value_counts(['start station name','end station name'])
	#find unique starting stations
	unique_start_stations = list(set([trips.index[i][0] for i in range(len(trips))]))
	adjacencyDict = {}
	for station in unique_start_stations: 
		try: 
			id = station_data.index[station_data['name']==station][0]
			top_ten_routes = trips[station][:10]
			edges = []
			for route in top_ten_routes.index: 
				edges.append(station_data.index[station_data['name']==route][0])
			adjacencyDict[id] = edges
		#sometimes we get an index error if a station went online / offline since the last data pull 
		except IndexError: 
			pass 
	return adjacencyDict
