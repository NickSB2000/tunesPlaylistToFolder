#!/bin/env python3

import os
import sys
import glob
import shlex
import shutil
import plistlib
import subprocess

from urllib.parse import urlparse, unquote

# we need a /dev/null
FNULL = open(os.devnull, 'w')

# Import the necessary packages and give nice errors
try:
  import eyed3
except:
  print('Error: please : pip install eyeD3')
  sys.exit(1)

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

# Functions()
def osCommand(command):
  return subprocess.run(command, stdout=subprocess.PIPE, stderr=FNULL).stdout.decode('utf-8').strip()

def path_to_cygwin(inpath):
  if inpath.startswith('/'):
    INPATH = inpath[1:]
  else:
    INPATH = inpath
  if inpath.lower().startswith('desktop'):
    commd = ["cygpath.exe", "-D"]
  else:
    commd = ["cygpath.exe", "-u", INPATH ]
  thePath = osCommand(commd)
  return (os.path.isfile(thePath), thePath)

def path_to_windows(inpath):
  INPATH = inpath
  commd = ["cygpath.exe", "-w", INPATH ]
  return osCommand(commd)

# Cygwin related dependencies
if len(osCommand(shlex.split('which ldd'))) < 2:
  print('\nError: please make sure that the ldd utility is included when installing cygwin\nAborting!\n')
  sys.exit(1) 

checkffmpeg = osCommand(shlex.split('which ffmpeg'))
if len(checkffmpeg) < 2:
  print('\nError: please make sure that ffmpeg is installed\nAborting!\n')
  sys.exit(1) 

ffmpegWinCmdOut = osCommand(shlex.split('ldd %s' % checkffmpeg))
if not ffmpegWinCmdOut.__contains__('dll'):
  print('\nError: please make sure that %s is Windows version/built\nAborting!\n' % checkffmpeg)
  sys.exit(1) 

searchresult = osCommand(shlex.split("which find"))
if len(searchresult) < 2: 
  print('\nError: please make sure that the find utility is included when installing cygwin\nAborting!\n')
  sys.exit(1)


status , userpath = path_to_cygwin(os.environ['USERPROFILE'])
itunesDefaultLibrary = userpath + '/Music/iTunes/iTunes Music Library.xml'

plist = plistlib.readPlist(itunesDefaultLibrary)

playlists = []
for plObj in plist['Playlists']:
  playlists.append(plObj['Name'])
  
selection_menu = SelectionMenu(playlists, title=itunesDefaultLibrary, subtitle='Please Select a Library:')
selection_menu.show()

try:
  SelectedPlaylist = plist['Playlists'][selection_menu.returned_value]['Name']
  trackList = plist['Playlists'][selection_menu.returned_value]['Playlist Items']
  #print(plist['Playlists'][selection_menu.returned_value])
except:
  # if you're here, means that you've hit exit at the selection menu
  sys.exit(0)

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
speculativeDrive = ''
for item in trackList:
  counter += 1
  try:
    TRACK       = str(item['Track ID'])
    URIlocation = plist['Tracks'][TRACK]['Location']
    trackName   = slugify(plist['Tracks'][TRACK]['Name'], separator="_", max_length=80, word_boundary=True)
    trackArtist = slugify(plist['Tracks'][TRACK]['Artist'], separator="_", max_length=20, word_boundary=True)
    trackAlbum  = slugify(plist['Tracks'][TRACK]['Album'], separator="_", max_length=20, word_boundary=True)
  except:
    continue
  url_OBJ = urlparse(plist['Tracks'][TRACK]['Location'])
  if url_OBJ.scheme.lower() == 'file':
    ifexist, LOCATION = path_to_cygwin(unquote(url_OBJ.path))
    EXTENSION = os.path.splitext(LOCATION)[1]
    if not ifexist:
      print(" Oups File not found: %s" % LOCATION) 
      print(" Trying to find it.. It could be on a differernt drive..")
      searchresult = ''
      if speculativeDrive != '':
        iterateOverDriveList = [speculativeDrive] + glob.glob('/cygdrive/*')
      else:
        iterateOverDriveList = glob.glob('/cygdrive/*')
      for drive in iterateOverDriveList:
        print(" Trying to find it on drive '%s', one moment.. " % drive)
        searchCommand = 'find %s -type f -name "%s" -print -quit' % (drive, os.path.basename(LOCATION))
        searchresult = osCommand(shlex.split(searchCommand)) 
        if os.path.isfile(searchresult):
          print(" ---> FOUND: %s " % searchresult)
          LOCATION = searchresult
          speculativeDrive = drive
          break
      if searchresult == '':
        LOCATION = "NOT FOUND"
  elif url_OBJ.scheme.lower().startswith('http'):
    LOCATION  = plist['Tracks'][TRACK]['Location']
    EXTENSION = os.path.splitext(url_OBJ.path)[1]
  else:
    LOCATION = "NOT DETECTED"
  newFileName = "%04d__%s_%s_%s%s" % (counter, trackName, trackArtist, trackAlbum, EXTENSION)
  if LOCATION.startswith('NOT'):
    print(" Can't create File: '%s' Reason: '%s'" % (newFileName, LOCATION))
    continue
  print(" Copying   : %s" % LOCATION)
  print(" New file  : %s" % newFileName)
  destination = os.path.join(PLAYLIST_FOLDER, newFileName)
  if LOCATION.startswith('http'):
    print('  ', end='', flush=True)
    wget.download(LOCATION, out=destination)
    print()
  else:
    shutil.copy2(LOCATION, destination)
  newFileName     = os.path.basename(destination).replace('__','___')
  newFileNamePath = os.path.join(PLAYLIST_FOLDER, newFileName)
  print(" Extracting Album Art..")
  extrCmd = 'ffmpeg -i "%s" "%s.jpg"' % (path_to_windows(destination), path_to_windows(destination))
  osCommand(shlex.split(extrCmd))
  print(" Removing All Tags..")
  ffCommand = 'ffmpeg -i "%s" -vn -codec:a copy -map_metadata -1 "%s"' % (path_to_windows(destination), path_to_windows(newFileNamePath) )
  osCommand(shlex.split(ffCommand))
  if os.path.exists(destination + '.jpg'):
    print(" Retaking Album art only..")
    os.remove(destination)
    finalInsertCmd = 'ffmpeg -i "%s" -i "%s.jpg" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" "%s"' % (path_to_windows(newFileNamePath), path_to_windows(destination), path_to_windows(destination))
    osCommand(shlex.split(finalInsertCmd))
    os.remove(destination + '.jpg')
    os.remove(newFileNamePath)
  else:
    os.remove(destination)
    os.rename(newFileNamePath, destination)
  #sys.exit()
  print('\n') 
   


  