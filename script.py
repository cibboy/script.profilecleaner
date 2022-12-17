import traceback
import xbmc
import lib.kodi18to19_xbmcgui as xbmcgui
import os, sys, urllib.request, urllib.parse, urllib.error, datetime, time, shutil, re
if sys.version_info >= (2, 7): import json
else: import simplejson as json
from common import *

class Cleaner:
	def __init__(self):
		self.thumbnailFileList         = []    # All thumbnails
		self.texturesDict              = {}    # All textures (from DB)
		self.thumbnailFileSize         = 0     # Initial thumbnail file size
		self.cancelOperation           = False # Init cancelOperation Flag

	def ExploreThumbnailsFolder(self, thumbnailsFolder):
		basedir = thumbnailsFolder; subdirlist = []
		for item in os.listdir(thumbnailsFolder):
			if os.path.isfile(os.path.join(basedir, item)):
				last = os.path.split(os.path.dirname(basedir))[1]
				itemWithDir = basedir + "/" + item
				self.thumbnailFileList.append((item))
				self.thumbnailFileSize = self.thumbnailFileSize + os.stat(os.path.join(basedir, item)).st_size
			else: subdirlist.append(os.path.join(basedir, item))
		for subdir in subdirlist:
			self.ExploreThumbnailsFolder(subdir)

	def ShowStats(self, showAddons = False):
		# Get all Files in Thumbnails folder and all Textures in Database
		self.ExploreThumbnailsFolder(thumbnailsFolder)
		jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Textures.GetTextures", "id": 1}')
		jSon = json.loads(jSonQuery)
		try:
			if 'textures' in jSon['result']: getTextures = jSon['result']['textures']
		except: getTextures = []

		statsT = normalize(addonLanguage(32108)) + ": " + humanReadableSizeOf(self.thumbnailFileSize) + ", " + str(len(self.thumbnailFileList)) + " " + normalize(addonLanguage(32107)) + ", " + str(len(getTextures)) + " " + normalize(addonLanguage(32108))
		statsA = ""

		if showAddons:
			# Compute addon size and number of files.
			totalAddonSize = 0
			totalAddonFiles = 0
			addonData = os.path.join(userdataFolder, "addon_data")
			for item in os.listdir(addonData):
				totalAddonSize = totalAddonSize + self.GetFolderSize(os.path.join(addonData, item))
				totalAddonFiles = totalAddonFiles + 1
			addonRollback = os.path.join(homeFolder, "addons", "packages")
			for item in os.listdir(addonRollback):
				totalAddonSize = totalAddonSize + os.stat(os.path.join(addonRollback, item)).st_size
				totalAddonFiles = totalAddonFiles + 1

			statsA = normalize(addonLanguage(32109)) + ": " + humanReadableSizeOf(totalAddonSize) + ", " + str(totalAddonFiles) + " " + normalize(addonLanguage(32107))

		# Show stats
		xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32106)), statsT, statsA)

	def ExcludeThumbnailHash(self, sectionToDo, textToDo):
		countList = 1
		excludedTextureCount = 0
		tnHashFileList = []

		log("Comparing " + str(len(sectionToDo)) + " images to exclude texture entries")
		for s in sectionToDo:
			if showGUI:
				self.Progress.update((countList * 100) / len(sectionToDo), normalize(addonLanguage(32110)) % len(sectionToDo), textToDo, s)
				if self.Progress.iscanceled():
					self.cancelOperation = True
					break
			#calcualte hash filenames
			ts = s.rstrip('/')
			urlHash = getHash(ts)
			extFile = ts.split(".")[-1]
			tnHashFileList.append(urlHash + "." + extFile)
			if "icon.png" in s:		# Workaround for the icons addon
				tnHashFileList.append(urlHash + ".jpg")

			# remove from texturelist and add to hashfilelist
			matchingTextuture = next((item for key,item in self.texturesDict.items() if item['url'] == s), None)
			if matchingTextuture:
				tnHashFileList.append(matchingTextuture['cachedurl'])
				del self.texturesDict[matchingTextuture['textureid']]
				excludedTextureCount = excludedTextureCount + 1
			countList = countList + 1  

		# remove from filelist
		tnHashFileList = removeDuplicate(tnHashFileList)		#remove duplicates
		log("Comparing " + str(len(tnHashFileList)) + " updated images to exclude files")
		excludedThumbFileCount = 0
		for s in tnHashFileList:
			if showGUI:
				self.Progress.update((excludedThumbFileCount * 100) / len(tnHashFileList), normalize(addonLanguage(32110)) % len(tnHashFileList), textToDo)
				if self.Progress.iscanceled():
					self.cancelOperation = True
					break
			try:
				self.thumbnailFileList.remove(s)
				excludedThumbFileCount += 1
			except:
				pass
		xbmc.log(str(excludedThumbFileCount) + " image files excluded")
		xbmc.log(str(excludedTextureCount) + " texture image entry excluded")

	def _processMediaThumbnails(self, mediaType: str, jsonrpccommand: str, languageId: int, excludeHashLanguageId: int, dialogExtension: str = '') -> None:
		if self.cancelOperation != True:
			thumbnailsList = []; countList = 1
			log("*** Searching %s %s ***" %(dialogExtension, mediaType))
			try:
				# Get all Textures in Database
				jSonQuery = xbmc.executeJSONRPC(jsonrpccommand)
				jSon = json.loads(jSonQuery)

				if jSon['result'].get(mediaType):
					totalResults = jSon['result']['limits'].get('total')
					log("Found %d %s in the database" % (totalResults, mediaType))
					for item in jSon['result'][mediaType]:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults,
								normalize(addonLanguage(languageId)), dialogExtension, item.get('label'))
							if self.Progress.iscanceled():
									self.cancelOperation = True
									break
							#time.sleep(0.0005)
						#collections
						if item.get('art'):
							for artKey, artValue in item['art'].items():		#for json art dictionary objects in movies/tvshows/episodes
								if artKey.startswith('tvshow.') or 'DefaultVideo.png' in artValue: continue	# check for bad season/episode entries *performance 
								cleanandAppendUrl(artValue, thumbnailsList)
								if item['label'] == "Season 1": # Workaround for tv show seasons all posters
									cleanandAppendUrl(artValue.replace("season01", "season-all"), thumbnailsList)
						if item.get('cast'):
							for cast in  item['cast']:	#for actors in movies/tvshows/episodes	
								if cast.get('thumbnail'):
									cleanandAppendUrl(cast['thumbnail'], thumbnailsList)
						#individuals
						if item.get('thumbnail'):		#for json thumbnail objects // conditional fails on missing key or emtpy string or None value
							cleanandAppendUrl(item['thumbnail'], thumbnailsList)
						if item.get('fanart'):			#for json thumbnail objects // conditional fails on missing key or emtpy string or None value
							cleanandAppendUrl(item['fanart'], thumbnailsList)
						countList = countList + 1
				if not self.cancelOperation and len(thumbnailsList):
					thumbnailsList = removeDuplicate(thumbnailsList)
					self.ExcludeThumbnailHash(thumbnailsList, normalize(
						addonLanguage(excludeHashLanguageId)))
				else:
					log("Found 0 images to process")
			except Exception as e:
				logError(mediaType + " check exception: " + traceback.format_exc())

	def ThumbnailCleanup(self):
		self.startedAt = datetime.datetime.now()
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2": log("Thumbnail deletion simulation started at " + self.startedAt.strftime("%Y-%m-%d %H:%M:%d"))
		else: log("Thumbnail cleanup started at " + self.startedAt.strftime("%Y-%m-%d %H:%M:%d"))
		# Get all Files in Thumbnails folder
		self.ExploreThumbnailsFolder(thumbnailsFolder)
		self.numThumbnailFiles = len(self.thumbnailFileList)
		# Get all Textures in Database
		jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Textures.GetTextures", "params": {"properties": ["url","cachedurl"]}, "id": 1}')
		jSon = json.loads(jSonQuery)
		try:
			if 'textures' in jSon['result']: getTextures = jSon['result']['textures']
			for item in getTextures:
				#if  item['url'] and item['cachedurl']:  clean list?
				item['url'] = urllib.parse.unquote_plus(normalize(item.get('url'))).replace("image://", "")
				item['cachedurl'] = item.get('cachedurl').split("/")[1]
				self.texturesDict[item['textureid'] ] = item
		except Exception as e:
			logError('Failed to load textures from database' + traceback.format_exc())
		self.numTextures = len(self.texturesDict)
		
		# Movies
		if addonSettings.getSetting("CheckMovies") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('movies', jsonrpccommand, 32111, 32112)

		# Sets
		if addonSettings.getSetting("CheckSets") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSets", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('sets', jsonrpccommand, 32113, 32114)

		# TVShows
		if addonSettings.getSetting("CheckTVShows") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('tvshows', jsonrpccommand, 32115, 32116)
			#get tv show list
			tvShows = []
			jSonQuery = xbmc.executeJSONRPC(jsonrpccommand)
			jSon = json.loads(jSonQuery)
			for tvshow in jSon['result']['tvshows']:
				tvShows.append((tvshow['tvshowid'], tvshow['label']))

		# Seasons
		if addonSettings.getSetting("CheckSeasons") == "true":
			for tvShow in tvShows:
				jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["art"], "tvshowid": %s}, "id": 1}' % tvShow[0]
				self._processMediaThumbnails('seasons', jsonrpccommand, 32117, 32118, tvShow[1])

		# Episodes
		if addonSettings.getSetting("CheckEpisodes") == "true":
			for tvShow in tvShows:
				jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["art"], "tvshowid": %s}, "id": 1}' % tvShow[0]
				self._processMediaThumbnails('episodes', jsonrpccommand, 32119, 32120, tvShow[1])

		# MusicVideos
		if addonSettings.getSetting("CheckMusicVideos") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('musicvideos', jsonrpccommand, 32121, 32122)

		# Video Genres
		if addonSettings.getSetting("CheckVideoGenres") == "true":
			log("*** Searching video/music genres ***")
			# Movies
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "label", "ignorearticle": true}, "properties": ["thumbnail"], "type": "movie"}, "id": 1}'
			self._processMediaThumbnails('genres', jsonrpccommand, 32123, 32126)
			# TV Shows
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "label", "ignorearticle": true}, "properties": ["thumbnail"], "type": "tvshow"}, "id": 1}'
			self._processMediaThumbnails('genres', jsonrpccommand, 32124, 32126)
			# Music Videos
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "label", "ignorearticle": true}, "properties": ["thumbnail"], "type": "musicvideo"}, "id": 1}'
			self._processMediaThumbnails('genres', jsonrpccommand, 32125, 32126)

		# Music Artists
		if addonSettings.getSetting("CheckMusicArtists") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["thumbnail","fanart"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('artists', jsonrpccommand, 32127, 32128)

		# Music Albums
		if addonSettings.getSetting("CheckMusicAlbums") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["thumbnail","fanart"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('albums', jsonrpccommand, 32129, 32130)

		# Music Songs
		if addonSettings.getSetting("CheckMusicSongs") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["thumbnail","fanart"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('songs', jsonrpccommand, 32131, 32132)

		# Music Genres
		if addonSettings.getSetting("CheckMusicGenres") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "title", "ignorearticle": true}, "properties": ["thumbnail"]}, "id": 1}'
			self._processMediaThumbnails('genres', jsonrpccommand, 32133, 32134)

		# Actors
		if addonSettings.getSetting("CheckActors") == "true":
			log("*** Searching Actors ***")
			# Movies
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["cast"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('movies', jsonrpccommand, 32135, 32138)
			# TV Shows
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["cast"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}'
			self._processMediaThumbnails('tvshows', jsonrpccommand, 32136, 32138)
			# Episodes
			for tvShow in tvShows:
				jsonrpccommand = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["cast"], "tvshowid": %s}, "id": 1}' % tvShow[0]
				self._processMediaThumbnails('episodes', jsonrpccommand, 32137, 32138, tvShow[1])

		# Addons
		if addonSettings.getSetting("CheckAddons") == "true":
			jsonrpccommand = '{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"properties": ["thumbnail","fanart"]}, "id": 1}'
			self._processMediaThumbnails('addons', jsonrpccommand, 32139, 32140)			#note: item.get('addonid')

		 # Favorites
		if addonSettings.getSetting("CheckFavorites") == "true":
			jsonrpccommand = '{"jsonrpc":"2.0","method":"Favourites.GetFavourites","params":{"properties":["thumbnail"]},"id":1}'
			self._processMediaThumbnails('favourites', jsonrpccommand, 32166, 32167)			#note: item.get('title')

		# Process Textures Database
		if self.cancelOperation != True:
			newTexturesDict = {}
			ExtraPattern = addonSettings.getSetting("ExtraPattern").split("|")
			ExtraPattern.extend(['DefaultVideo.png', 'DefaultFolder.png'])						#add default values
			for key, t in self.texturesDict.items():
				if not any(x in t['url'] for x in ExtraPattern): newTexturesDict[key] = t		#dectect entries not matching ExtraPatterns
				else:		 																	#remove matching entries from TN filelist
					try: 
						self.thumbnailFileList.remove(t['cachedurl'])
					except: pass
			self.texturesDict = newTexturesDict   

		# To the End
		if self.cancelOperation != True:
			self.originalNumThumbnailFiles = self.numThumbnailFiles
			self.originalThumbnailFileSize = self.thumbnailFileSize
			self.numTextures = self.numTextures - len(self.texturesDict)
			# Re-Calculate Total Files and Sizes
			self.numThumbnailFiles = self.numThumbnailFiles - len(self.thumbnailFileList)
			self.newThumbnailFileSize = 0
			for f in self.thumbnailFileList:
				files = os.path.join(thumbnailsFolder, f[:1], f)
				try: self.newThumbnailFileSize = self.newThumbnailFileSize + os.stat(files).st_size
				except: pass
			self.thumbnailFileSize = self.thumbnailFileSize - self.newThumbnailFileSize
			# Finalize Clean
			self.FinalizeThumbnailCleanup()
		else:
			log("The operation was aborted by the user")

	def FinalizeThumbnailCleanup(self):
		texturesLength = len(self.texturesDict)
		thumbnailFilesLength = len(self.thumbnailFileList)
		# Move files in destination folder or copy if simulate is active
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") != "2":
			countList = 1
			log("Deleting " + str(texturesLength) + " remaining textures from the database")
			for tKey,t in self.texturesDict.items():
				if showGUI:
					self.Progress.update((countList * 100) / texturesLength, normalize(addonLanguage(32141)) % texturesLength, t['url'])
				RawXBMC.Execute("DELETE FROM texture WHERE id=" + str(tKey)) 
				countList = countList + 1
		countList = 1
		for f in self.thumbnailFileList:
			files = os.path.join(thumbnailsFolder, f[:1], f)
			progress = int((countList * 100) / thumbnailFilesLength)
			if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "1":
				if showGUI:
					self.Progress.update(progress, normalize(addonLanguage(32141)) % thumbnailFilesLength, files)
				try: os.remove(files)
				#except: pass
				except Exception as e:
					logError("Deleting  File exception: " +str(files)+" " + traceback.format_exc())
			elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "0":
				if showGUI:
					self.Progress.update(progress, normalize(addonLanguage(32143)) % thumbnailFilesLength, files)
				try: os.remove(os.path.join(thumbnailBackupFolder, f))
				except: pass
				try: shutil.move(files, thumbnailBackupFolder)
				#except: pass
				except Exception as e:
					logError("Moving File exception: "+ str(files)+" " + traceback.format_exc())
			elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2":
				if showGUI:
					self.Progress.update(progress, normalize(addonLanguage(32144)) % thumbnailFilesLength, files)
				try: shutil.copy2(files, thumbnailBackupFolder)
				#except: pass
				except Exception as e:
					logError("Copying File exception: "+str(files)+" " + traceback.format_exc())
			countList = countList + 1

		self.finishAt = datetime.datetime.now()
		self.tookTime = self.finishAt - self.startedAt
		log("Thumbnail cleanup terminated in " + str(self.tookTime).split(".")[0])

		# Manage Textual Response
		# Delete
		dialogHeading = addonName + " - " + normalize(addonLanguage(32145))
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "1":
			log(str(thumbnailFilesLength) + " file(s) deleted. " + humanReadableSizeOf(self.newThumbnailFileSize) + " recovered")
			log(str(texturesLength) + " field(s) deleted from the textures database")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32145)), normalize(addonLanguage(32146)) % (str(thumbnailFilesLength), humanReadableSizeOf(self.newThumbnailFileSize)), normalize(addonLanguage(32147)) % str(texturesLength))
		# Move
		elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "0":
			log(str(thumbnailFilesLength) + " file(s) moved. " + humanReadableSizeOf(self.newThumbnailFileSize) + " recovered")
			log(str(texturesLength) + " field(s) deleted from the textures database")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32145)), normalize(addonLanguage(32148)) % (str(thumbnailFilesLength), humanReadableSizeOf(self.newThumbnailFileSize)), normalize(addonLanguage(32147)) % str(texturesLength))
		# Simulate
		elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2":
			log(str(thumbnailFilesLength) + " file(s) copied. " + humanReadableSizeOf(self.newThumbnailFileSize) + " recoverable")
			log(str(texturesLength) + " field(s) would be deleted from the textures database")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32145)), normalize(addonLanguage(32149)) % (str(thumbnailFilesLength), humanReadableSizeOf(self.newThumbnailFileSize)), normalize(addonLanguage(32150)) % str(texturesLength))

	def SearchAndDeleteThumbnail(self):
		keyboard = xbmc.Keyboard()
		keyboard.doModal()
		query = keyboard.getText()
		if query:
			lists = []; query = query.replace("'", "''")
			match = RawXBMC.Execute("SELECT url FROM texture WHERE url LIKE '%" + query + "%'")
			for base in match: lists.append(base[0])
			if len(lists) > 0:
				selected = xbmcgui.Dialog().multiselect(normalize(addonLanguage(32151)), lists)
				for sel in selected:
					url = str(lists[sel])
					url = url.replace("'", "''")
					cachedUrl = RawXBMC.Execute("SELECT cachedurl FROM texture WHERE url='" + url + "'")
					cachedUrlPath = os.path.join(thumbnailsFolder, cachedUrl[0][0])
					try: shutil.move(cachedUrlPath, thumbnailBackupFolder)
					except: pass
					RawXBMC.Execute("DELETE FROM texture WHERE url='" + url + "'")
				if showGUI:
					self.ShowStats()
			elif (addonSettings.getSetting("ShowNotifications") == "true"):
				xbmc.executebuiltin("Notification(%s,%s,2000,%s)" % (addonName, normalize(addonLanguage(32152)), addonIcon))

	def EmptyThumbnailTable(self):
		self.Erase = xbmcgui.Dialog().yesno("%s" % addonName, "%s" % normalize(addonLanguage(32153)), "%s" % normalize(addonLanguage(32154)), " ", "%s" % "No", "%s" % "Yes")
		if self.Erase != 0:
			shutil.copy2(databaseFolder + "/Textures" + addonSettings.getSetting("TexturesDB") + ".db", databaseFolder + "/Textures" + addonSettings.getSetting("TexturesDB") + ".db.bak")
			RawXBMC.Execute("DELETE FROM texture")
			log("A copy of the textures database has been created")
			log("Textures database has been emptied")
			if showGUI:
				xbmcgui.Dialog().ok("%s - %s" % (addonName, normalize("Info")), "%s" % normalize(addonLanguage(32155)), normalize(addonLanguage(32156)))
				self.ShowStats()

	def GetFolderSize(self, start_path = '.'):
		total_size = 0
		for dirpath, dirnames, filenames in os.walk(start_path):
			for f in filenames:
				fp = os.path.join(dirpath, f)
				total_size += os.path.getsize(fp)
		return total_size

	def AddonCleanup(self):
		self.startedAt = datetime.datetime.now()
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2": log("Addon deletion simulation started at " + self.startedAt.strftime("%Y-%m-%d %H:%M:%d"))
		else: log("Addon cleanup started at " + self.startedAt.strftime("%Y-%m-%d %H:%M:%d"))
		
		jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"properties": ["name","path"]}, "id": 1}')
		jSon = json.loads(jSonQuery)
		installedAddons = []
		if jSon['result']:
			for addon in jSon['result']['addons']:
				rest, realname = os.path.split(addon["path"])
				installedAddons.append(addon["addonid"])
				installedAddons.append(realname)

		self.totalAddonSize = 0
		self.deletedAddonSize = 0
		self.deletedAddonNumber = 0
		# Compute total size.
		addonData = os.path.join(userdataFolder, "addon_data")
		for item in os.listdir(addonData):
			self.totalAddonSize = self.totalAddonSize + self.GetFolderSize(os.path.join(addonData, item))
		addonRollback = os.path.join(homeFolder, "addons", "packages")
		for item in os.listdir(addonRollback):
			self.totalAddonSize = self.totalAddonSize + os.stat(os.path.join(addonRollback, item)).st_size
		
		if self.cancelOperation != True:
			if (addonSettings.getSetting("DelAddonsSettings") == "true"):
				log("Deleting addon settings for uninstalled addons")
				addonData = os.path.join(userdataFolder, "addon_data")
				toDelete = []
				for item in os.listdir(addonData):
					if (item not in installedAddons):
						toDelete.append(os.path.join(addonData, item))
				countList = 1
				for item in toDelete:
					self.deletedAddonSize = self.deletedAddonSize + self.GetFolderSize(item)
					self.deletedAddonNumber = self.deletedAddonNumber + 1
					rest, realname = os.path.split(item)
					# Delete
					if addonSettings.getSetting("AddonSelectDeleteMove") == "1":
						log("Deleting settings for " + realname + " from " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32157)) + realname)
						try: shutil.rmtree(item)
						except: pass
					# Move
					elif addonSettings.getSetting("AddonSelectDeleteMove") == "0":
						log("Moving settings for " + realname + " from " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32158)) + realname)
						try: shutil.rmtree(os.path.join(addonBackupFolder, realname))
						except: pass
						try: shutil.move(item, addonBackupFolder)
						except: pass
					# Simulate
					elif addonSettings.getSetting("AddonSelectDeleteMove") == "2":
						log("Copying settings for " + realname + " from " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32159)) + realname)
						try: shutil.rmtree(os.path.join(addonBackupFolder, realname))
						except: pass
						try: shutil.copytree(item, os.path.join(addonBackupFolder, realname))
						except: pass
						
					if showGUI:
						if self.Progress.iscanceled():
							self.cancelOperation = True
							break
					countList = countList + 1

		if self.cancelOperation != True:
			if (addonSettings.getSetting("DelAddonsPackages") == "true"):
				log("Deleting addon packages for uninstalled addons")
				addonRollback = os.path.join(homeFolder, "addons", "packages")
				toDelete = []
				for item in os.listdir(addonRollback):
					splits = item.split('-')
					if (splits[0] not in installedAddons):
						toDelete.append(os.path.join(addonRollback, item))
				countList = 1
				for item in toDelete:
					self.deletedAddonSize = self.deletedAddonSize + os.stat(item).st_size
					self.deletedAddonNumber = self.deletedAddonNumber + 1
					rest, realname = os.path.split(item)
					# Delete
					if addonSettings.getSetting("AddonSelectDeleteMove") == "1":
						log("Deleting package " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32160)) + item)
						try: os.remove(item)
						except: pass
					# Move
					elif addonSettings.getSetting("AddonSelectDeleteMove") == "0":
						log("Moving package " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32161)) + item)
						try: os.remove(os.path.join(addonBackupFolder, realname))
						except: pass
						try: shutil.move(item, addonBackupFolder)
						except: pass
					# Simulate
					elif addonSettings.getSetting("AddonSelectDeleteMove") == "2":
						log("Copying package " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32162)) + item)
						try: shutil.copy2(item, addonBackupFolder)
						except: pass
					
					if showGUI:
						if self.Progress.iscanceled():
							self.cancelOperation = True
							break
					countList = countList + 1 

		if self.cancelOperation != True:
			if (addonSettings.getSetting("LimitAddonsPackages") == "true"):
				log("Trimming history of addon packages")
				historyKeep = int(addonSettings.getSetting("NumAddonsPackages"))
				addonRollback = os.path.join(homeFolder, "addons", "packages")
				files = os.listdir(addonRollback)
				# Sort list of files to make sure versions are ordered correctly
				convert = lambda text: int(text) if text.isdigit() else text
				alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
				files.sort(key=alphanum_key)
				dict = {}
				for item in files:
					splits = item.split('-')
					if dict.get(splits[0]) == None:
						dict[splits[0]] = []
					dict[splits[0]].append(item)
				toDelete = []
				for key in dict:
					delNum = len(dict.get(key)) - historyKeep
					while delNum > 0:
						toDelete.append(os.path.join(addonRollback, dict.get(key)[len(dict.get(key)) - (delNum + historyKeep)]))
						delNum = delNum - 1
				countList = 1
				for item in toDelete:
					self.deletedAddonSize = self.deletedAddonSize + os.stat(item).st_size
					self.deletedAddonNumber = self.deletedAddonNumber + 1
					rest, realname = os.path.split(item)
					# Delete
					if addonSettings.getSetting("AddonSelectDeleteMove") == "1":
						log("Deleting package " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32160)) + item)
						try: os.remove(item)
						except: pass
					# Move
					elif addonSettings.getSetting("AddonSelectDeleteMove") == "0":
						log("Moving package " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32161)) + item)
						try: os.remove(os.path.join(addonBackupFolder, realname))
						except: pass
						try: shutil.move(item, addonBackupFolder)
						except: pass
					# Simulate
					elif addonSettings.getSetting("AddonSelectDeleteMove") == "2":
						log("Copying package " + item)
						if showGUI:
							self.Progress.update((countList * 100) / len(toDelete), normalize(addonLanguage(32162)) + item)
						try: shutil.copy2(item, addonBackupFolder)
						except: pass
					
					if showGUI:
						if self.Progress.iscanceled():
							self.cancelOperation = True
							break
					countList = countList + 1 

		self.finishAt = datetime.datetime.now()
		self.tookTime = self.finishAt - self.startedAt
		log("Addon cleanup terminated in " + str(self.tookTime).split(".")[0])
		log("Total addon size = " + str(humanReadableSizeOf(self.totalAddonSize)))

		# Manage Textual Response
		# Delete
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "1":
			log(str(self.deletedAddonNumber) + " file(s) deleted. " + humanReadableSizeOf(self.deletedAddonSize) + " recovered")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32163)), normalize(addonLanguage(32146)) % (str(self.deletedAddonNumber), humanReadableSizeOf(self.deletedAddonSize)))
		# Move
		elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "0":
			log(str(self.deletedAddonNumber) + " file(s) moved. " + humanReadableSizeOf(self.deletedAddonSize) + " recovered")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32163)), normalize(addonLanguage(32148)) % (str(self.deletedAddonNumber), humanReadableSizeOf(self.deletedAddonSize)))
		# Simulate
		elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2":
			log(str(self.deletedAddonNumber) + " file(s) copied. " + humanReadableSizeOf(self.deletedAddonSize) + " recoverable")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32163)), normalize(addonLanguage(32149)) % (str(self.deletedAddonNumber), humanReadableSizeOf(self.deletedAddonSize)))

	def PerformCleanup(self, bitmask):
		if addonSettings.getSetting("ShowNotifications") == "true" and not showGUI:
			xbmc.executebuiltin("Notification(%s,%s,2000,%s)" % (addonName, normalize(addonLanguage(32164)), addonIcon))
			
		if (bitmask > 0 and showGUI):
			self.Progress = xbmcgui.DialogProgress()
			self.Progress.create(addonName)
		
		if ((bitmask & 1) == 1):
			self.ThumbnailCleanup()
		if ((bitmask & 2) == 2):
			self.SearchAndDeleteThumbnail()
		if ((bitmask & 4) == 4):
			self.EmptyThumbnailTable()
		if ((bitmask & 8) == 8):
			self.AddonCleanup()
			
		if (bitmask > 0 and showGUI):
			self.Progress.close()
		
		if addonSettings.getSetting("ShowNotifications") == "true" and not showGUI:
			xbmc.executebuiltin("Notification(%s,%s,2000,%s)" % (addonName, normalize(addonLanguage(32165)), addonIcon))

if (__name__ == "__main__"):
	# If show main manu option is enabled, show main menu in a loop
	if addonSettings.getSetting("ShowMainMenu") == "true":
		remain = True
		while remain == True:
			remain = False
			selection = xbmcgui.Dialog().select(addonName, [normalize(addonLanguage(32100)), 
												normalize(addonLanguage(32101)), normalize(addonLanguage(32102)), 
												normalize(addonLanguage(32103)), normalize(addonLanguage(32104)), 
												normalize(addonLanguage(32105))])
			if selection == 0: remain = True; Cleaner().PerformCleanup(1)
			elif selection == 1: remain = True; Cleaner().PerformCleanup(2)
			elif selection == 2: remain = True; Cleaner().PerformCleanup(4)
			elif selection == 3: remain = True; Cleaner().PerformCleanup(8)
			elif selection == 4: remain = True; Cleaner().ShowStats(True)
			elif selection == 5: remain = True; addonSettings.openSettings()
	# Otherwise perform both main cleanup actions in sequence
	else:
		Cleaner().PerformCleanup(9)	
	del addonSettings