#!/usr/bin/python3

import os
import sys
import time
import glob
import json
import shlex
import shutil
import plistlib
import subprocess
import pickle

from urllib.parse import urlparse, unquote

# we need a /dev/null
FNULL = open(os.devnull, 'w')

# Path of current file for options
picklePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "opts.pkl")

# Import the necessary packages and give nice errors
try:
  import eyed3
except:
  print('Error: from command prompt as admin : pip install eyeD3')
  input()
  sys.exit(1)

try:
  from cursesmenu import *
  from cursesmenu.items import *
except:
  print('Error: from command prompt as admin : pip install curses-menu')
  input()
  sys.exit(1)

try:
  import wget
except:
  print('Error: from command prompt as admin : pip3 install wget')
  input()
  sys.exit(1)

try:
  from slugify import slugify
except:
  print('Error: from command prompt as admin : pip3 install python-slugify')
  input()
  sys.exit(1)


#-----------------


#-----------------



# Functions()
def osCommand(command):
  return subprocess.run(command, stdout=subprocess.PIPE, stderr=FNULL).stdout.decode('utf-8').strip()

def path_resolver(inpath):
  if inpath.lower().startswith('desktop'):
    wdesktopPath = os.path.join(os.environ["HOMEPATH"], "Desktop")
    return (os.path.isdir(wdesktopPath), wdesktopPath)
  if inpath.startswith('/'):
    return (os.path.isfile(inpath[1:]), inpath[1:])
  else:
    return (os.path.isfile(inpath), inpath)

def path_to_windows(inpath):
  return inpath

def get_drives():
  import ctypes
  buff_size = ctypes.windll.kernel32.GetLogicalDriveStringsW(0,None)
  buff = ctypes.create_string_buffer(buff_size*2)
  x = ctypes.windll.kernel32.GetLogicalDriveStringsW(buff_size,buff)
  iterable = filter(None, buff.raw.decode('utf-16-le').split(u'\0'))
  return list(iterable)

def find_ffmpeg_locations(drive='c'):
  locations = glob.glob('%s:/**/ffmpeg.exe' % drive, recursive=True)
  approvedl = []
  for lfile in locations:
    fprobefile = os.path.join(os.path.dirname(lfile), "ffprobe.exe")
    if os.path.exists(fprobefile):
      approvedl.append(lfile)
  return approvedl

foundFFbin = False
while not foundFFbin:
  gotsome = False
  if os.path.exists(picklePath):
    try:
      ffmpegLocations = pickle.load( open(picklePath, "rb" ) )
      gotsome = True
    except:
      pass

  if gotsome == False:
    print("Looking for 'ffmpeg.exe' / 'ffprobe.exe' on your C: Drive, one moment...")
    ffmpegLocations = find_ffmpeg_locations()
    if not os.path.exists(picklePath):
      pickle.dump(ffmpegLocations, open(picklePath, "wb" ) )

  if ffmpegLocations.__len__() == 0:
    print("Please put ffmpeg.exe somewhere on your C: drive..")
    print("You can get it from there: https://ffmpeg.zeranoe.com/builds/")
    print("Install it and restart this program!, Aborting for now..\n")
    sys.exit()

  if ffmpegLocations.__len__() == 1:
    ffmpegLocation = ffmpegLocations[0]
  else:
    selection = SelectionMenu(ffmpegLocations, title='Which one do you choose?', subtitle='Please Select one:')
    selection.show()
    ffmpegLocation  = ffmpegLocations[selection.returned_value]
    ffprobeLocation = os.path.join(os.path.dirname(ffmpegLocation), "ffprobe.exe")

  if not os.path.exists(ffmpegLocation):
    print("Okay, well, seems like that ffmpeg binary is gone, try again..")
    os.remove(picklePath)
  else:
    foundFFbin = True


status , userpath = path_resolver(os.environ['USERPROFILE'])
itunesDefaultLibrary = userpath + '/Music/iTunes/iTunes Music Library.xml'
itunesDefaultLibrary = itunesDefaultLibrary.replace('/','\\')

if not os.path.isfile(itunesDefaultLibrary):
  print("\nError: Itunes Library File '%s' not found\nAborting!\n" % itunesDefaultLibrary)
  sys.exit()

plist = plistlib.readPlist(itunesDefaultLibrary)

playlists = []
for plObj in plist['Playlists']:
  playlists.append(plObj['Name'])

while True:  
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
  exist, desktopFolder = path_resolver('Desktop')
  PLAYLIST_FOLDER=''
  for fnum in range(1,100):
    folderCounter += 1
    PLAYLIST_FOLDER = os.path.join(desktopFolder, "%s_%02d" % ( slugify(SelectedPlaylist, separator="_"), folderCounter))
    if os.path.isdir(PLAYLIST_FOLDER): 
      if os.listdir(PLAYLIST_FOLDER):
        continue
    else:
      pass
      os.mkdir(PLAYLIST_FOLDER)
      print("\n Playlist will be saved to:\n '%s'\n" % PLAYLIST_FOLDER)
      break
    
  counter = 0
  speculativeDrive = ''
  for item in trackList:
    counter += 1
    
    try:
      TRACK       = str(item['Track ID'])
    except:
      TRACK       = "track_%s" % counter

    try:
      URIlocation = plist['Tracks'][TRACK]['Location']
    except:
      # If no URI location is found, the carrots are cooked
      continue 

    try:
      trackName   = slugify(plist['Tracks'][TRACK]['Name'], separator="_", max_length=80, word_boundary=True)
    except:
      trackName   = "_"

    try:
      trackArtist = slugify(plist['Tracks'][TRACK]['Artist'], separator="_", max_length=20, word_boundary=True)
    except:
      trackArtist = "_"

    try:
      trackAlbum  = slugify(plist['Tracks'][TRACK]['Album'], separator="_", max_length=20, word_boundary=True)
    except:
      trackAlbum  = "_"


    #print(plist['Tracks'][TRACK]['Location'])
    url_OBJ = urlparse(plist['Tracks'][TRACK]['Location'])
    if url_OBJ.scheme.lower() == 'file':
      ifexist, LOCATION = path_resolver(unquote(url_OBJ.path))
      EXTENSION = os.path.splitext(LOCATION)[1]
      if not ifexist:
        print(" Oups File not found: %s" % LOCATION) 
        print(" Trying to find it.. It could be on a differernt drive..")
        searchresult = ''
        if speculativeDrive != '':
          iterateOverDriveList = [speculativeDrive] + get_drives()
        else:
          iterateOverDriveList = get_drives()
        for drive in iterateOverDriveList:
          print(" Trying to find it on drive '%s', one moment.. " % drive)
          search = glob.glob('%s/**/%s' % (drive, os.path.basename(LOCATION)), recursive=True)
          try:
            searchresult = search[0]
          except:
            searchresult = ''
          if os.path.isfile(searchresult):
            print(" ---> FOUND: %s " % searchresult)
            LOCATION = searchresult
            speculativeDrive = drive
            break
        if searchresult == '':
          LOCATION = "NOT FOUND"
          sys.exit()
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

    winPathDestination      = path_to_windows(destination)
    destinationNoExt, exten = os.path.splitext(destination)
    destinationMP3          = destinationNoExt + '.mp3'
    winPathDestinationMP3   = path_to_windows(destinationMP3)
    newFileName             = os.path.basename(destinationMP3).replace('__','___')
    newFileNamePath         = os.path.join(PLAYLIST_FOLDER, newFileName)

    ffCommand = ffprobeLocation + ' -v quiet -print_format json -show_format -show_streams "%s"' % winPathDestination
    osCmdOutputJSON   = osCommand(ffCommand)
    osCmdOutputPYTHON = json.loads(osCmdOutputJSON)
    try:
      formatName = osCmdOutputPYTHON['format']['format_name']
    except:
      formatName = 'unknown'
    print(" Format    : %s" % formatName)

    if formatName.lower() != 'mp3':
      print(" Converting: %s" % destinationMP3)
      #ffCommand = ffmpegLocation + ' -i "%s" -acodec libmp3lame "%s"' % (winPathDestination, path_to_windows(destinationMP3) )
      ffCommand = ffmpegLocation + ' -threads 0 -i "%s" "%s"' % (winPathDestination, winPathDestinationMP3 )
      subprocess.run(ffCommand)
      os.remove(destination)
      destination = destinationMP3

    print(" Extracting Album Art..")
    winPathDestination = path_to_windows(destination)
    extrCmd = ffmpegLocation + ' -i "%s" "%s.jpg"' % (winPathDestination, winPathDestination)
    osCommand(extrCmd)
    print(" Removing All Tags..")
    ffCommand = ffmpegLocation + ' -i "%s" -vn -codec:a copy -map_metadata -1 "%s"' % (winPathDestination, path_to_windows(newFileNamePath) )
    osCommand(ffCommand)
    if os.path.exists(destination + '.jpg'):
      print(" Retaking Album art only..")
      os.remove(destination)
      finalInsertCmd = ffmpegLocation + ' -i "%s" -i "%s.jpg" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" "%s"' % (path_to_windows(newFileNamePath), path_to_windows(destination), path_to_windows(destination))
      osCommand(finalInsertCmd)
      os.remove(destination + '.jpg')
      os.remove(newFileNamePath)
    else:
      os.remove(destination)
      os.rename(newFileNamePath, destination)
    print('\n') 
   

  