"""
Extension classes enhance TouchDesigner components with python. An
extension is accessed via ext.ExtensionClassName from any operator
within the extended component. If the extension is promoted via its
Promote Extension parameter, all its attributes with capitalized names
can be accessed externally, e.g. op('yourComp').PromotedFunction().

Help: search "Extensions" in wiki
"""

from TDStoreTools import StorageManager
import TDFunctions as TDF

# from utils import *
from citibikeAPI import *
from matplotlib import pyplot as plt


class citibikeDataExt:
	"""
	citibikeDataExt description
	"""
	def __init__(self, ownerComp):
		# The component to which this extension is attached
		self.ownerComp = ownerComp
		self.edgesDat = op('edges')
		self.pointsDat = op('points')
		self.old_df = None
		self.eventCHOP = op('event2')
		self.eventRouteID_LUT = op('EVENT_TO_ROUTE_MAPPING/id_lookup')
		self.routeData_LUT = op('EVENT_TO_ROUTE_MAPPING/routeData')
		self.data_path =  'data'
		self.trip_data_csv = self.data_path + '/202303-citibike-tripdata.csv'
		self.networked_stations = None
		self.normalized_routes = None
		self.offsets = None 
		self.scriptOp = op('script1')
		self.controller = op('CONTROLLER')


	#function intended to be called inside a script SOP operator to create geometry 
	def BikeDatatoSOP(self, scriptOp):
		scriptOp.clear()
		for r in range(1,self.pointsDat.numRows):
			p = scriptOp.appendPoint()
			p.x = self.pointsDat[r, 1]
			p.y = self.pointsDat[r, 2]
			p.z = self.pointsDat[r, 3]
			#edges are still wip but this worked for dummy data
			# edges = [int(r) for r in edgesDat[r,0].val.split()]
			# for e in edges: 
			# 	if e == 0: 
			# 		pass 
			# 	else:
			# 		poly = scriptOp.appendPoly(2, closed=False)
			# 		poly[0].point = p 
			# 		p1 = poly[1].point
			# 		debug(p1)
			# 		p1.x = self.pointsDat[e,1]
			# 		p1.y = self.pointsDat[e,2]
			# 		p1.z = self.pointsDat[e,3]
		return
	
	def TestImports(self):
		return 1
	
	#TODO - cache data
	def InitializeData(self):
		#TODO - insert something to ensure ORS local server is running
		station_data = getAllStationData() #returns dataframe with station info
		print('gathered station data')
		self.ownerComp.store('station_data', station_data)
		print('stored station data')
		self.networked_stations = getTopTenConnections(self.trip_data_csv) #use most recent trip csv to create a dictionary with the 10 stations any given station is most connected to
		print('found connections')
		self.ownerComp.store('networked_stations', self.networked_stations)
		print('stored connections')
		routes = getRouteBetweenStations(self.networked_stations, station_data)
		print('routes found')
		self.normalized_routes = normalizeRoutes(routes, station_data) 
		print('routes normalized')
		self.ownerComp.store('normalized_routes', self.normalized_routes)
		print('normalized routes stored')
		self.OutputRouteFilesForTextures(self.normalized_routes, self.data_path)
		print('output file saved')
		print('Initalized Route Data to Memory')
		self.ownerComp.store('initialized', True)
		return
	
	def GetDataPath(self):
		return self.data_path
	
	def GetNetworkedStations(self):
		return  self.ownerComp.fetch('networked_stations')
	
	def InitRealTime(self):
		self.ownerComp.storeStartupValue('realtime_data', None)
		self.ownerComp.store('realtime_data', None)
		print('Initalized Realtime Data Pipeline')
		return
		
	def GetRideStarts(self):

		old_dataframe = self.ownerComp.fetch('realtime_data')
		starts = []
		station_status_url = 'https://gbfs.citibikenyc.com/gbfs/en/station_status.json'
		#get station status
		with urllib.request.urlopen(station_status_url) as url:
			station_status_data = json.load(url)
		station_status_df = pd.DataFrame(station_status_data['data']['stations']).set_index('station_id')
		station_status_df = station_status_df[['num_ebikes_available', 'num_bikes_available', 'last_reported']] #extract cols of interest, here just ebike and update timestampe 
		#TODO: we should probably screen out ebike updates due to station-level events such as activation / nonactivation, rebalancing, etc 
		updated_df = station_status_df
		
		station_data = self.ownerComp.fetch('station_data')
		if old_dataframe is None: 
			self.ownerComp.store('realtime_data', station_status_df.sort_index())
		else: 
			udc = updated_df.sort_index()
			sdc = old_dataframe.sort_index()
			for i in sdc.index:
				if self.controller.par.Displaymode.eval() == 'AllBikes': #if display mode is all bikes
					if (udc.loc[i,'num_ebikes_available'] == sdc.loc[i,'num_ebikes_available']
						and udc.loc[i,'num_bikes_available'] == sdc.loc[i,'num_bikes_available']): pass 
					else: 
						p = station_data.loc[i, 'name']
						starts += [[p]]
				elif self.controller.par.Displaymode.eval() == 'EbikesOnly': #if display mode is ebike only
					if (udc.loc[i,'num_ebikes_available'] == sdc.loc[i,'num_ebikes_available']): pass 
					else: 
						p = station_data.loc[i, 'name']
						starts += [[p]]
				elif self.controller.par.Displaymode.eval() == 'RegularBikesOnly': #if display mode is reg bike only
					if (udc.loc[i,'num_bikes_available'] == sdc.loc[i,'num_bikes_available']): pass 
					else: 
						p = station_data.loc[i, 'name']
						starts += [[p]]
				else: pass 
		self.ownerComp.store('realtime_data', updated_df)
		print('{} rides started since last call'.format(len(starts)))
		return starts
	
	def CreateEventsFromStarts(self, starts): 
		connections = self.ownerComp.fetch('networked_stations')
		routes = self.ownerComp.fetch('normalized_routes')
		offsets = self.ownerComp.fetch('offsets')
		# debug(starts)
		if(len(starts) < 1): return
		else: 
			try:
				for start in starts:
					s = start[0]
					# debug('s = ', s)
					topten = connections[s]
					# debug('topten: ', topten)

					i = 0
					for t in topten.index: 
						routeID = '-'.join([s,t])
						#for now, going to set the time to the avg, ~7min, with an approx uniform band 2min in either way
						#not precise, but dont need that yet
						dur = routes[routeID]['duration']
						dist = routes[routeID]['distance']
						eventID = self.eventCHOP.createEvent(attackTime  = dur)
						weight = 1  - i / 10
						r = [eventID, routeID, offsets.loc[routeID, 'pts'], offsets.loc[routeID, 'offset'], dur, dist, weight]
						# r += routes[routeID]
						self.eventRouteID_LUT.appendRow(r)
						# routeData = geoDf[['id', 'pts', 'offset', 'duration']] 
						# route_info = [eventID, offsets.loc[routeID, 'pts'], offsets.loc[routeID, 'offset'], dur]
						# self.routeData_LUT.appendRow(route_info)
						i += 1
						# debug(routes[routeID])
			except KeyError: 
				print('missing station: ' , s)
		return 

	def ResetEventRouteLUT(self):
		self.eventRouteID_LUT.clear()
		return

	def RemoveLUTRow(self, row):
		self.eventRouteID_LUT.deleteRow(row)
		# self.routeData_LUT.deleteRow(row)
		return

	def OutputRouteFilesForTextures(self, normalized_routes, path):
		id = 0
		cum = 0
		exportDict = {}
		unrolled_points = []
		for k, v in normalized_routes.items(): 
			d = {}
			d['points'] = v['points']
			unrolled_points += v['points']
			pts = len(v['points'])
			d['pts'] = pts
			d['offset'] = cum
			d['duration'] = v['duration']
			d['distance'] = v['distance']
			cum += pts
			d['id'] = k
			id += 1
			exportDict[k] = d
		geoDf = pd.DataFrame(exportDict).T
		# geoDf.to_csv(path+'/debug.csv')
		routeData = geoDf[['id', 'pts', 'offset', 'duration', 'distance']] 
		self.ownerComp.store('offsets', routeData)
		self.ownerComp.storeStartupValue('offsets', routeData)
		print('route data stored successfully')
		self.ownerComp.store('unrolled_points', unrolled_points)
		self.ownerComp.storeStartupValue('unrolled_points', unrolled_points)
		print('stored unrolled points successfully')
		pd.DataFrame(unrolled_points).to_csv(path + '/unrolled_points.csv')
		# plt.imsave(path+'unrolled_points.jpeg', unrolled_points)
		# pd.DataFrame(routeData).to_csv(path+'/routeData.csv')

		
		self.ownerComp.storeStartupValue('realtime_data', None)
		return
	
	def StartupRoutine(self):
		self.ownerComp.storeStartupValue('realtime_data', None)
		return 

#Pacific St & Thomas S. Boyland St-Somers St & Rockaway Ave
#Liberty St & Broadway-Murray St & Greenwich St