#!/bin/env python3

import os
import sys
import shutil
import plistlib
import subprocess

from urllib.parse import urlparse, unquote

# Import the necessary packages
try:
  from cursesmenu import *
  from cursesmenu.items import *
except:
  print('Error: please : pip install curses-menu')
  sys.exit(1)

try:
  import wget
except:
  print('Error: please : pip3 install wget')
  sys.exit(1)

try:
  from slugify import slugify
except:
  print('Error: please : pip3 install python-slugify')
  sys.exit(1)

def path_to_cygwin(inpath):
  if inpath.startswith('/'):
    INPATH = inpath[1:]
  else:
    INPATH = inpath
  if inpath.lower().startswith('desktop'):
    commd = ["cygpath.exe", "-D"]
  else:
    commd = ["cygpath.exe", "-u", INPATH ]
  thePath = subprocess.run(commd, stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
  return (os.path.isfile(thePath), thePath)

status , userpath = path_to_cygwin(os.environ['USERPROFILE'])
itunesDefaultLibrary = userpath + '/Music/iTunes/iTunes Music Library.xml'

plist = plistlib.readPlist(itunesDefaultLibrary)

playlists = []
for plObj in plist['Playlists']:
  playlists.append(plObj['Name'])
  
selection_menu = SelectionMenu(playlists, title=itunesDefaultLibrary, subtitle='Please Select a Library:')
selection_menu.show()

SelectedPlaylist = plist['Playlists'][selection_menu.returned_value]['Name']
trackList = plist['Playlists'][selection_menu.returned_value]['Playlist Items']

folderCounter = 0
exist, desktopFolder = path_to_cygwin('Desktop')
PLAYLIST_FOLDER=''
for fnum in range(1,100):
  folderCounter += 1
  PLAYLIST_FOLDER = os.path.join(desktopFolder, "%s_%02d" % ( slugify(SelectedPlaylist, separator="_"), folderCounter))
  if os.path.isdir(PLAYLIST_FOLDER): 
    if os.listdir(PLAYLIST_FOLDER):
      continue
  else:
    os.mkdir(PLAYLIST_FOLDER)
  print("\n Playlist will be saved to:\n '%s'\n" % PLAYLIST_FOLDER)
  break
  

counter = 0
for item in trackList:
  counter += 1
  try:
    TRACK       = str(item['Track ID'])
    URIlocation = plist['Tracks'][TRACK]['Location']
    trackName   = slugify(plist['Tracks'][TRACK]['Name'], separator="_", max_length=40, word_boundary=True)
    trackArtist = slugify(plist['Tracks'][TRACK]['Artist'], separator="_", max_length=20, word_boundary=True)
    trackAlbum  = slugify(plist['Tracks'][TRACK]['Album'], separator="_", max_length=20, word_boundary=True)
  except:
    continue
  url_OBJ = urlparse(plist['Tracks'][TRACK]['Location'])
  if url_OBJ.scheme.lower() == 'file':
    ifexist, LOCATION = path_to_cygwin(unquote(url_OBJ.path))
    EXTENSION = os.path.splitext(LOCATION)[1]
    if not ifexist: LOCATION = "NOT FOUND"
  elif url_OBJ.scheme.lower().startswith('http'):
    LOCATION  = plist['Tracks'][TRACK]['Location']
    EXTENSION = os.path.splitext(url_OBJ.path)[1]
  else:
    LOCATION = "NOT DETECTED"
  newFileName = "%04d__%s_%s_%s%s" % (counter, trackName, trackArtist, trackAlbum, EXTENSION)
  if LOCATION.startswith('NOT'):
    print(" Can't copy File: '%s' Not Found: '%s'" % (newFileName, LOCATION))
    continue
  print(" Working on: %s" % LOCATION)
  if LOCATION.startswith('http'):
    wget.download(LOCATION, out=os.path.join(PLAYLIST_FOLDER, newFileName))
    print()
  else:
    shutil.copy2(LOCATION, os.path.join(PLAYLIST_FOLDER, newFileName))
  