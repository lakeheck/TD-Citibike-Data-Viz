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

class citibikeDataExt:
	"""
	citibikeDataExt description
	"""
	def __init__(self, ownerComp):
		# The component to which this extension is attached
		self.ownerComp = ownerComp
		self.edgesDat = op('edges')
		self.pointsDat = op('points')

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
