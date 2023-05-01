

import pandas as pd
import urllib.request, json
import uuid 
# from utils import *

#auth
osr_key = '5b3ce3597851110001cf62487d33115ea15e483bb81a0b4cfcc899cb'
def  clamp(a, x, y): 
	return max(x, min(a, y))


def getAllStationData():
	station_info_url = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
	station_status_url = 'https://gbfs.citibikenyc.com/gbfs/en/station_status.json'

	#get station info
	with urllib.request.urlopen(station_info_url) as url:
		station_info_data = json.load(url)

	station_info_df = pd.DataFrame(station_info_data['data']['stations']).set_index('station_id')
	station_info_df['geoID'] = station_info_df['lat'] + station_info_df['lon']
	station_info_df = station_info_df[['name', 'lat', 'lon', 'capacity', 'legacy_id', 'geoID']] #extract cols of interest
	
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

def getEbikeEventsJSON(old_dataframe=None):

	changes = {}
	station_data = getAllStationData()
	station_status_url = 'https://gbfs.citibikenyc.com/gbfs/en/station_status.json'
	#get station status
	with urllib.request.urlopen(station_status_url) as url:
		station_status_data = json.load(url)

	station_status_df = station_data.set_index('name')
	station_status_df = station_data[['name','num_ebikes_available', 'last_reported']].set_index('name') #extract cols of interest, here just ebike and update timestampe 
	#TODO: we should probably screen out ebike updates due to station-level events such as activation / nonactivation, rebalancing, etc 

	updated_df = station_status_df

	if old_dataframe is None: return station_status_df.sort_index(), pd.DataFrame(changes, columns = ['name', 'num_ebikes_available', 'gain_loss', 'window_start', 'window_end']).set_index('name')
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
				d = {
					'new_bike_count':new_bike_count,
					'timestamp': window_end,
					'gain_loss': old_bike_count-new_bike_count
				}
				changes[i] = d
				# print('change!', udc.loc[i,'num_ebikes_available'], sdc.loc[i,'num_ebikes_available'], i, udc.loc[i, 'last_reported'])
		
		return udc, changes
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

def getTopTenConnections(csv):
	station_data = getAllStationData()
	trip_data = pd.read_csv(csv, low_memory=False)
	trip_data['startGeoID'] = trip_data['start_lat'] + trip_data['start_lng']
	trip_data['endGeoID'] = trip_data['end_lat'] + trip_data['end_lng']
	trips = trip_data[trip_data['start_station_name'] != trip_data['end_station_name']].value_counts(['start_station_name','end_station_name'])
	unique_stations = list(set([trips.index[i][0] for i in range(len(trips))]))
	networked_stations={}
	for station in unique_stations: 
		try:
			id = station_data.index[station_data['name']==station][0]
			id = station
			networked_stations[id] = trips[station][:10]
		except IndexError: pass 
	return networked_stations


def getRouteBetweenStations(networked_stations, station_data):
	routes = {}
	# k = 'Putnam Ave & Throop Ave'
	for k, v in networked_stations.items():
		for i in v.index: #for each station
			try:
				start = [station_data[station_data['name']==k]['lon'][0], station_data[station_data['name']==k]['lat'][0]]
				end = [station_data[station_data['name']==i]['lon'][0], station_data[station_data['name']==i]['lat'][0]]
				#setup our coords
				coordinates = [start,end]

				#get station status from local instance of ORS 
				url = 'http://localhost:8080/ors/v2/directions/driving-car?&start={},{}&end={},{}'.format(start[0],start[1],end[0],end[1])
				with urllib.request.urlopen(url) as url:
					station_status_data = json.load(url)


				#create list of loction points 
				locations=[list(reversed(coord)) 
										for coord in 
										station_status_data['features'][0]['geometry']['coordinates']]
				
				#route duration in seconds
				duration = station_status_data['features'][0]['properties']['summary']['duration']
				distance = station_status_data['features'][0]['properties']['summary']['distance']
				tempdict = {
					'points': locations,
					'duration': duration,
					'distance': distance
				}
				# print(tempdict)
				routes[k+'-'+i] = tempdict
			except: 
				pass #TODO: figure out what is going on with these stations 
	return routes


def normalizeRoutes(routes, station_data):
	#normalize location too 
	normalized_routes = routes 
	# need to filter out zeros for some data noise 
	minlat = min([i for i in station_data['lat'] if i > 0])
	maxlat  = max([i for i in station_data['lat'] if i > 0])
	minlong = min([i for i in station_data['lon'] if i  < 0])
	maxlong = max([i for i in station_data['lon'] if i < 0])


	print(minlat, maxlat, minlong, maxlong)
	#add two columns and normalize
	#hardcoding column locations to overwrite ""
	for k, v in routes.items():
		normalized_routes[k]['points'] = [[clamp((i[0] - minlat)/(maxlat-minlat),0,1),clamp((i[1] - minlong)/(maxlong-minlong),0,1)]for i in v['points']]

	return normalized_routes

# def outputRouteFilesForTextures(normalized_routes, path):
# 	id = 0
# 	cum = 0
# 	exportDict = {}
# 	unrolled_points = []
# 	for k, v in normalized_routes.items(): 
# 		d = {}
# 		d['points'] = v['points']
# 		unrolled_points += v['points']
# 		pts = len(v)
# 		d['pts'] = pts
# 		d['offset'] = cum
# 		d['duration'] = v['duration']
# 		d['distance'] = v['distance']
# 		cum += pts
# 		d['id'] = id
# 		id += 1
# 		exportDict[k] = d
# 	geoDf = pd.DataFrame(exportDict).T
# 	routeData = geoDf[['id', 'pts', 'offset', 'duration', 'distance']]
	
# 	pd.DataFrame(unrolled_points).to_csv(path + '/unrolled_points.csv')
# 	pd.DataFrame(routeData).to_csv(path+'/routeData.csv')
# 	# return routeData, unrolled_points