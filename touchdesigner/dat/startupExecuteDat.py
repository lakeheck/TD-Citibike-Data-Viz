import sys 
import os 

def AddDependenciesToPath(): 
	dep_path = f'{project.folder}/Lib/' 
	norm_dep_path = os.path.normpath(dep_path) 
	if norm_dep_path not in sys.path: 
		sys.path.insert(0, norm_dep_path)
	

def onStart():
	#hacking a way to get installs right
	#op('td_pip').par.Install.pulse()
	AddDependenciesToPath()
	#add command line check for ORS running in docker 
	return

def onCreate():
	return

def onExit():
	return

def onFrameStart(frame):
	return

def onFrameEnd(frame):
	try: 
		a = parent().fetch('initialized')
		if not a: op('init_on_start_btn').click()
	except: 
		pass
	return

def onPlayStateChange(state):
	return

def onDeviceChange():
	return

def onProjectPreSave():
	return

def onProjectPostSave():
	return

	