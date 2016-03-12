import xbmc, xbmcgui
import os, sys, urllib, datetime, time, shutil, re
if sys.version_info >= (2, 7): import json
else: import simplejson as json
from common import *

class Cleaner:
	def __init__(self):
		self.thumbnailFileList         = []    # All thumbnails
		self.texturesList              = []    # All textures (from DB)
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
			if jSon['result'].has_key('textures'): getTextures = jSon['result']['textures']
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
		log("Comparing " + str(len(sectionToDo)) + " images to exclude files")
		for s in sectionToDo:
			if showGUI:
				self.Progress.update((countList * 100) / len(sectionToDo), normalize(addonLanguage(32110)) % len(sectionToDo), textToDo, s)
				if self.Progress.iscanceled():
					self.cancelOperation = True
					break
			urlHash = getHash(s)
			extFile = s.split(".")[-1]
			try: self.thumbnailFileList.remove(urlHash + "." + extFile)
			except:
				# Workaround for the icons addon
				if "icon.png" in s:
					try: self.thumbnailFileList.remove(urlHash + ".jpg")
					except: pass
			cachedUrl = ""
			for item in self.texturesList:
				if item[0] == s.decode('utf-8'): cachedUrl = item[1]
			if cachedUrl:
				try: self.texturesList.remove((s.decode('utf-8'), cachedUrl))
				except: pass
			countList = countList + 1

	def ThumbnailCleanup(self):
		self.startedAt = datetime.datetime.now()
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2": log("Thumbnail deletion simulation started at " + self.startedAt.strftime("%Y-%m-%d %H:%M:%d"))
		else: log("Thumbnail cleanup started at " + self.startedAt.strftime("%Y-%m-%d %H:%M:%d"))
		# Get all Files in Thumbnails folder
		self.ExploreThumbnailsFolder(thumbnailsFolder)
		self.numThumbnailFiles = len(self.thumbnailFileList)
		# Get all Textures in Database
		jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Textures.GetTextures", "params": {"properties": ["url","cachedurl"]}, "id": 1}')
		jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
		jSon = json.loads(jSonQuery)
		try:
			if jSon['result'].has_key('textures'): getTextures = jSon['result']['textures']
			for item in getTextures: self.texturesList.append((urllib.unquote_plus(normalize(item.get('url'))).replace("image://", "")[:-1].decode('utf-8'), item.get('cachedurl')))
		except: pass
		self.numTextures = len(self.texturesList)
		
		# Movies
		if self.cancelOperation != True and addonSettings.getSetting("CheckMovies") == "true":
			log("*** Searching movies ***")
			log("Sending JSON query")
			dataMovie = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('movies'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " movies in the database")
					for item in jSon['result']['movies']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32111)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						for key in item.get('art'):
							valueText = urllib.unquote_plus(normalize(item.get('art')[key]))
							valueText = valueText.replace("image://", "")[:-1]
							dataMovie.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataMovie = removeDuplicate(dataMovie)
				if self.cancelOperation != True and len(dataMovie) > 0:
					self.ExcludeThumbnailHash(dataMovie, normalize(addonLanguage(32112)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# Sets
		if self.cancelOperation != True and addonSettings.getSetting("CheckSets") == "true":
			log("*** Searching collections ***")
			log("Sending JSON query")
			dataSets = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSets", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('sets'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " collections in the database")
					for item in jSon['result']['sets']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32113)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						for key in item.get('art'):
							valueText = urllib.unquote_plus(normalize(item.get('art')[key]))
							valueText = valueText.replace("image://", "")[:-1]
							dataSets.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataSets = removeDuplicate(dataSets)
				if self.cancelOperation != True and len(dataSets) > 0:
					self.ExcludeThumbnailHash(dataSets, normalize(addonLanguage(32114)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# TVShows
		if self.cancelOperation != True and addonSettings.getSetting("CheckTVShows") == "true":
			log("*** Seaching TV shows ***")
			log("Sending JSON query")
			dataTVShows = []; tvShows = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('tvshows'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " TV shows in the database")
					for item in jSon['result']['tvshows']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32115)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						tvShows.append((item.get('tvshowid'), item.get('label')))
						for key in item.get('art'):
							valueText = urllib.unquote_plus(normalize(item.get('art')[key]))
							valueText = valueText.replace("image://", "")[:-1]
							dataTVShows.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataTVShows = removeDuplicate(dataTVShows)
				if self.cancelOperation != True and len(dataTVShows) > 0:
					self.ExcludeThumbnailHash(dataTVShows, normalize(addonLanguage(32116)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass
		else: tvShows = []

		# Seasons
		if self.cancelOperation != True and addonSettings.getSetting("CheckSeasons") == "true" and len(tvShows) > 0:
			log("*** Searching seasons ***")
			dataSeasons = []; countList = 1
			for tvShow in tvShows:
				if showGUI:
					self.Progress.update((countList * 100) / len(tvShows), normalize(addonLanguage(32117)), tvShow[1], " ")
					if self.Progress.iscanceled():
						self.cancelOperation = True
						break
				jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["art"], "tvshowid": %s}, "id": 1}' % tvShow[0])
				jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
				jSon = json.loads(jSonQuery)
				try:
					if jSon['result'].has_key('seasons'):
						totalResults = jSon['result']['limits'].get('total')
						log("Found " + str(totalResults) + " seasons in " + tvShow[1])
						for item in jSon['result']['seasons']:
							for key in item.get('art'):
								if key.find("tvshow.") != 0:
									valueText = urllib.unquote_plus(normalize(item.get('art')[key]))
									valueText = valueText.replace("image://", "")[:-1]
									if item.get('label') == "Season 1": # Workaround for season all posters
										seasonAll = valueText.replace("season01", "season-all")
										dataSeasons.append(seasonAll)
									dataSeasons.append(valueText)
				except: pass
				time.sleep(0.0005)
				countList = countList + 1
			dataSeasons = removeDuplicate(dataSeasons)
			if self.cancelOperation != True and len(dataSeasons) > 0:
				self.ExcludeThumbnailHash(dataSeasons, normalize(addonLanguage(32118)))
			else: log("Found 0 images to process")

		# Episodes
		if self.cancelOperation != True and addonSettings.getSetting("CheckEpisodes") == "true" and len(tvShows) > 0:
			log("*** Searching episodes ***")
			dataEpisodes = []; countList = 1
			for tvShow in tvShows:
				if showGUI:
					self.Progress.update((countList * 100) / len(tvShows), normalize(addonLanguage(32119)), tvShow[1], " ")
					if self.Progress.iscanceled():
						self.cancelOperation = True
						break
				jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["art"], "tvshowid": %s}, "id": 1}' % tvShow[0])
				jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
				jSon = json.loads(jSonQuery)
				try:
					if jSon['result'].has_key('episodes'):
						totalResults = jSon['result']['limits'].get('total')
						log("Found " + str(totalResults) + " episodes in " + tvShow[1])
						for item in jSon['result']['episodes']:
							for key in item.get('art'):
								if key.find("tvshow.") != 0:
									valueText = urllib.unquote_plus(normalize(item.get('art')[key]))
									valueText = valueText.replace("image://", "")[:-1]
									dataEpisodes.append(valueText)
				except: pass
				time.sleep(0.0005)
				countList = countList + 1
			dataEpisodes = removeDuplicate(dataEpisodes)
			if self.cancelOperation != True and len(dataEpisodes) > 0:
				self.ExcludeThumbnailHash(dataEpisodes, normalize(addonLanguage(32120)))
			else: log("Found 0 images to process")

		# MusicVideos
		if self.cancelOperation != True and addonSettings.getSetting("CheckMusicVideos") == "true":
			log("*** Searching music videos ***")
			log("Sending JSON query")
			dataMusicVideos = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["art"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('musicvideos'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " music videos in the database")
					for item in jSon['result']['musicvideos']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32121)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						for key in item.get('art'):
							valueText = urllib.unquote_plus(normalize(item.get('art')[key]))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicVideos.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataMusicVideos = removeDuplicate(dataMusicVideos)
				if self.cancelOperation != True and len(dataMusicVideos) > 0:
					self.ExcludeThumbnailHash(dataMusicVideos, normalize(addonLanguage(32122)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# Video Genres
		if self.cancelOperation != True and addonSettings.getSetting("CheckVideoGenres") == "true":
			log("*** Searching video genres ***")
			dataVideoGenres = []
			# Movies
			countList = 1
			log("Sending JSON query")
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "label", "ignorearticle": true}, "properties": ["thumbnail"], "type": "movie"}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('genres'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " movie genres in the database")
					for item in jSon['result']['genres']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32123)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataVideoGenres.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
			except: pass
			# TV Shows
			countList = 1
			log("Sending JSON query")
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "label", "ignorearticle": true}, "properties": ["thumbnail"], "type": "tvshow"}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('genres'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " TV show genres in the database")
					for item in jSon['result']['genres']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32124)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataVideoGenres.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
			except: pass
			# Music Videos
			countList = 1
			log("Sending JSON query")
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "label", "ignorearticle": true}, "properties": ["thumbnail"], "type": "musicvideo"}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('genres'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " music video genres in the database")
					for item in jSon['result']['genres']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32125)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataVideoGenres.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
			except: pass
			dataVideoGenres = removeDuplicate(dataVideoGenres)
			if self.cancelOperation != True and len(dataVideoGenres) > 0:
				self.ExcludeThumbnailHash(dataVideoGenres, normalize(addonLanguage(32126)))
			else: log("Found 0 images to process")

		# Music Artists
		if self.cancelOperation != True and addonSettings.getSetting("CheckMusicArtists") == "true":
			log("*** Searching artists ***")
			log("Sending JSON query")
			dataMusicArtists = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["thumbnail","fanart"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('artists'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " artists in the database")
					for item in jSon['result']['artists']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32127)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicArtists.append(valueText)
						if item.get('fanart') != "":
							valueText = urllib.unquote_plus(normalize(item.get('fanart')))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicArtists.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataMusicArtists = removeDuplicate(dataMusicArtists)
				if self.cancelOperation != True and len(dataMusicArtists) > 0:
					self.ExcludeThumbnailHash(dataMusicArtists, normalize(addonLanguage(32128)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# Music Albums
		if self.cancelOperation != True and addonSettings.getSetting("CheckMusicAlbums") == "true":
			log("*** Searching albums ***")
			log("Sending JSON query")
			dataMusicAlbums = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["thumbnail","fanart"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('albums'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " albums in the database")
					for item in jSon['result']['albums']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32129)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicAlbums.append(valueText)
						if item.get('fanart') != "":
							valueText = urllib.unquote_plus(normalize(item.get('fanart')))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicAlbums.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataMusicAlbums = removeDuplicate(dataMusicAlbums)
				if self.cancelOperation != True and len(dataMusicAlbums) > 0:
					self.ExcludeThumbnailHash(dataMusicAlbums, normalize(addonLanguage(32130)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# Music Songs
		if self.cancelOperation != True and addonSettings.getSetting("CheckMusicSongs") == "true":
			log("*** Searching songs ***")
			log("Sending JSON query")
			dataMusicSongs = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["thumbnail","fanart"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('songs'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " songs in the database")
					for item in jSon['result']['songs']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32131)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicSongs.append(valueText)
						if item.get('fanart') != "":
							valueText = urllib.unquote_plus(normalize(item.get('fanart')))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicSongs.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataMusicSongs = removeDuplicate(dataMusicSongs)
				if self.cancelOperation != True and len(dataMusicSongs) > 0:
					self.ExcludeThumbnailHash(dataMusicSongs, normalize(addonLanguage(32132)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# Music Genres
		if self.cancelOperation != True and addonSettings.getSetting("CheckMusicGenres") == "true":
			log("*** Searching music genres ***")
			log("Sending JSON query")
			dataMusicGenres = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetGenres", "params": {"sort": {"order": "ascending", "method": "title", "ignorearticle": true}, "properties": ["thumbnail"]}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('genres'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " music genres in the database")
					for item in jSon['result']['genres']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32133)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataMusicGenres.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataMusicGenres = removeDuplicate(dataMusicGenres)
				if self.cancelOperation != True and len(dataMusicGenres) > 0:
					self.ExcludeThumbnailHash(dataMusicGenres, normalize(addonLanguage(32134)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# Actors
		if self.cancelOperation != True and addonSettings.getSetting("CheckActors") == "true":
			log("*** Searching actors in movies ***")
			dataCast = []
			# Movies
			countList = 1
			log("Sending JSON query")
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["cast"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('movies'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " movies in the database")
					for item in jSon['result']['movies']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32135)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						for cast in item.get('cast'):
							for key in cast:
								if key == "thumbnail":
									valueText = urllib.unquote_plus(normalize(cast[key]))
									valueText = valueText.replace("image://", "")[:-1]
									dataCast.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
			except: pass
			# TV Shows
			log("*** Searching actors in TV shows ***")
			tvShows = []; countList = 1
			log("Sending JSON query")
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["cast"], "sort": {"order": "ascending", "method": "title", "ignorearticle": true}}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('tvshows'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " TV shows in the database")
					for item in jSon['result']['tvshows']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32136)), item.get('label'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						tvShows.append((item.get('tvshowid'), item.get('label')))
						for cast in item.get('cast'):
							for key in cast:
								if key == "thumbnail":
									valueText = urllib.unquote_plus(normalize(cast[key]))
									valueText = valueText.replace("image://", "")[:-1]
									dataCast.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
			except: pass
			# Episodes
			log("*** Searching actors in episodes ***")
			countList = 1
			for tvShow in tvShows:
				if showGUI:
					self.Progress.update((countList * 100) / len(tvShows), normalize(addonLanguage(32137)), tvShow[1], " ")
					if self.Progress.iscanceled():
						self.cancelOperation = True
						break
				jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["cast"], "tvshowid": %s}, "id": 1}' % tvShow[0])
				jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
				jSon = json.loads(jSonQuery)
				try:
					if jSon['result'].has_key('episodes'):
						totalResults = jSon['result']['limits'].get('total')
						log("Found " + str(totalResults) + " episodes in " + tvShow[1])
						for item in jSon['result']['episodes']:
							for cast in item.get('cast'):
								for key in cast:
									if key == "thumbnail":
										valueText = urllib.unquote_plus(normalize(cast[key]))
										valueText = valueText.replace("image://", "")[:-1]
										dataCast.append(valueText)
				except: pass
				time.sleep(0.0005)
				countList = countList + 1
			dataCast = removeDuplicate(dataCast)
			if self.cancelOperation != True and len(dataCast) > 0:
				self.ExcludeThumbnailHash(dataCast, normalize(addonLanguage(32138)))
			else: log("Found 0 images to process")

		# Addons
		if self.cancelOperation != True and addonSettings.getSetting("CheckAddons") == "true":
			log("*** Searching addons ***")
			log("Sending JSON query")
			dataAddons = []; countList = 1
			jSonQuery = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"properties": ["thumbnail","fanart"]}, "id": 1}')
			jSonQuery = unicode(jSonQuery, 'utf-8', errors='ignore')
			jSon = json.loads(jSonQuery)
			try:
				if jSon['result'].has_key('addons'):
					totalResults = jSon['result']['limits'].get('total')
					log("Found " + str(totalResults) + " addons in the database")
					for item in jSon['result']['addons']:
						if showGUI:
							self.Progress.update((countList * 100) / totalResults, normalize(addonLanguage(32139)), item.get('addonid'), " ")
							if self.Progress.iscanceled():
								self.cancelOperation = True
								break
						if item.get('thumbnail') != "":
							valueText = urllib.unquote_plus(normalize(item.get('thumbnail')))
							valueText = valueText.replace("image://", "")[:-1]
							dataAddons.append(valueText)
						if item.get('fanart') != "":
							valueText = urllib.unquote_plus(normalize(item.get('fanart')))
							valueText = valueText.replace("image://", "")[:-1]
							dataAddons.append(valueText)
						time.sleep(0.0005)
						countList = countList + 1
				dataAddons = removeDuplicate(dataAddons)
				if self.cancelOperation != True and len(dataAddons) > 0:
					self.ExcludeThumbnailHash(dataAddons, normalize(addonLanguage(32140)))
				else: log("Found 0 images to process")
			except:
				log("Found 0 images to process"); pass

		# Process Textures Database
		if self.cancelOperation != True:
			newTextures = []
			ExtraPattern = addonSettings.getSetting("ExtraPattern").split("|")
			for t in self.texturesList:
				if not any(x in t[0] for x in ExtraPattern): newTextures.append((t[0], t[1]))
				else:
					if t[1]:
						cachedUrl = t[1].split("/")[1]
						try: self.thumbnailFileList.remove(cachedUrl)
						except: pass
			self.texturesList = newTextures
		
		# To the End
		if self.cancelOperation != True:
			self.originalNumThumbnailFiles = self.numThumbnailFiles
			self.originalThumbnailFileSize = self.thumbnailFileSize
			self.numTextures = self.numTextures - len(self.texturesList)
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
		# Move files in destination folder or copy if simulate is active
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") != "2":
			countList = 1
			log("Deleting " + len(self.texturesList) + " remaining textures from the database")
			for t in self.texturesList:
				if showGUI:
					self.Progress.update((countList * 100) / len(self.texturesList), normalize(addonLanguage(32141)) % len(self.texturesList), t[0], " ")
				url = t[0].replace("'", "''")
				RawXBMC.Execute("DELETE FROM texture WHERE url='" + url + "'")
				countList = countList + 1
		countList = 1
		for f in self.thumbnailFileList:
			files = os.path.join(thumbnailsFolder, f[:1], f)
			if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "1":
				if showGUI:
					self.Progress.update((countList * 100) / len(self.thumbnailFileList), normalize(addonLanguage(32141)) % len(self.thumbnailFileList), files, " ")
				try: os.remove(files)
				except: pass
			elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "0":
				if showGUI:
					self.Progress.update((countList * 100) / len(self.thumbnailFileList), normalize(addonLanguage(32143)) % len(self.thumbnailFileList), files, " ")
				try: os.remove(os.path.join(thumbnailBackupFolder, f))
				except: pass
				try: shutil.move(files, thumbnailBackupFolder)
				except: pass
			elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2":
				if showGUI:
					self.Progress.update((countList * 100) / len(self.thumbnailFileList), normalize(addonLanguage(32144)) % len(self.thumbnailFileList), files, " ")
				try: shutil.copy2(files, thumbnailBackupFolder)
				except: pass
			countList = countList + 1
		
		self.finishAt = datetime.datetime.now()
		self.tookTime = self.finishAt - self.startedAt
		log("Thumbnail cleanup terminated in " + str(self.tookTime).split(".")[0])
		
		# Manage Textual Response
		# Delete
		if addonSettings.getSetting("ThumbnailSelectDeleteMove") == "1":
			log(str(len(self.thumbnailFileList)) + " file(s) deleted. " + humanReadableSizeOf(self.newThumbnailFileSize) + " recovered")
			log(str(len(self.texturesList)) + " field(s) deleted from the textures database")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32145)), normalize(addonLanguage(32146)) % (str(len(self.thumbnailFileList)), humanReadableSizeOf(self.newThumbnailFileSize)), normalize(addonLanguage(32147)) % str(len(self.texturesList)))
		# Move
		elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "0":
			log(str(len(self.thumbnailFileList)) + " file(s) moved. " + humanReadableSizeOf(self.newThumbnailFileSize) + " recovered")
			log(str(len(self.texturesList)) + " field(s) deleted from the textures database")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32145)), normalize(addonLanguage(32148)) % (str(len(self.thumbnailFileList)), humanReadableSizeOf(self.newThumbnailFileSize)), normalize(addonLanguage(32147)) % str(len(self.texturesList)))
		# Simulate
		elif addonSettings.getSetting("ThumbnailSelectDeleteMove") == "2":
			log(str(len(self.thumbnailFileList)) + " file(s) copied. " + humanReadableSizeOf(self.newThumbnailFileSize) + " recoverable")
			log(str(len(self.texturesList)) + " field(s) would be deleted from the textures database")
			if showGUI:
				xbmcgui.Dialog().ok(addonName + " - " + normalize(addonLanguage(32145)), normalize(addonLanguage(32149)) % (str(len(self.thumbnailFileList)), humanReadableSizeOf(self.newThumbnailFileSize)), normalize(addonLanguage(32150)) % str(len(self.texturesList)))

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
				for key in dict.keys():
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
			selection = xbmcgui.Dialog().select(addonName, [normalize(addonLanguage(32100)), normalize(addonLanguage(32101)), normalize(addonLanguage(32102)), normalize(addonLanguage(32103)), normalize(addonLanguage(32104)), normalize(addonLanguage(32105))])
			if selection == 0: remain = True; Cleaner().PerformCleanup(1)
			elif selection == 1: remain = True; Cleaner().PerformCleanup(2)
			elif selection == 2: remain = True; Cleaner().PerformCleanup(4)
			elif selection == 3: remain = True; Cleaner().PerformCleanup(8)
			elif selection == 4: remain = True; Cleaner().ShowStats(True)
			elif selection == 5: remain = True; addonSettings.openSettings()
	# Otherwise perform both main cleanup actions in sequence
	else:
		Cleaner().PerformCleanup(9)