
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
  print('Error: from command prompt as admin : pip install windows-curses')
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

def getFormatInfo(ffprobeLocation='', inPath='', debug=True):
  winPathDestination = path_to_windows(inPath)
  ffCommand = ffprobeLocation + ' -v quiet -print_format json -show_format -show_streams "%s"' % winPathDestination
  osCmdOutputJSON   = osCommand(ffCommand)
  osCmdOutputPYTHON = json.loads(osCmdOutputJSON)
  try:
    formatName = osCmdOutputPYTHON['format']['format_name']
  except:
    formatName = 'unknown'
  if debug: print(" Format    : %s" % formatName)
  return formatName

def convertToMP3(ffprobeLocation='', inPath='', debug=True):
  winPathDestination    = path_to_windows(inPath)
  inPathNoExt, exten    = os.path.splitext(inPath)
  inPathMP3             = inPathNoExt + '.mp3'
  winPathDestinationMP3 = path_to_windows(inPathMP3)
  if debug: print(" Converting: %s" % inPathMP3)
  ffCommand = ffmpegLocation + ' -threads 0 -i "%s" "%s"' % (winPathDestination, winPathDestinationMP3 )
  subprocess.run(ffCommand)
  # removing the non-mp3 file
  os.remove(inPath)
  return inPathMP3

def extractAlbumArtJPG(ffmpegLocation='', inPath='', debug=True):
  if debug: print(" Extracting Album Art..")
  winPathDestination = path_to_windows(inPath)
  extrCmd = ffmpegLocation + ' -i "%s" "%s.jpg"' % (winPathDestination, winPathDestination)
  osCommand(extrCmd)

def insertAlbumArt(ffmpegLocation='', inPath='', outPath='', debug=True):
  if debug: print(" Retaking Album art only..")
  if os.path.exists(inPath + '.jpg'):
    finalInsertCmd = ffmpegLocation + ' -i "%s" -i "%s.jpg" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" "%s"' % (path_to_windows(inPath), path_to_windows(inPath), path_to_windows(outPath))
    osCommand(finalInsertCmd)
    # removing album art jpg, not needed anymore
    os.remove(MP3itemSavePath + '.jpg')
  else:
    if debug: print(" No Album art was available... just renaming file..")
    os.rename(inPath, outPath)    

def mp3TagRemover(ffmpegLocation='', inPath='', outPath='', debug=True):
  if debug: print(" Removing All Tags..")
  ffCommand = ffmpegLocation + ' -i "%s" -vn -codec:a copy -map_metadata -1 "%s"' % (path_to_windows(inPath), path_to_windows(outPath) )
  osCommand(ffCommand)

def findDirectoryForFinalPlaylist(outDirectory='', SelectedPlaylist=''):
  folderCounter = 0
  # taking Windows Desktop folder by default if nothing is given as outDirectory
  if outDirectory == '':
    exist, outDirectory = path_resolver('Desktop')
  PLAYLIST_FOLDER=''
  for fnum in range(1,1000):
    folderCounter += 1
    PLAYLIST_FOLDER = os.path.join(outDirectory, "%s_%03d" % ( slugify(SelectedPlaylist, separator="_"), folderCounter))
    if os.path.isdir(PLAYLIST_FOLDER):
      if os.listdir(PLAYLIST_FOLDER):
        continue
    else:
      break
  return PLAYLIST_FOLDER  

def findAllNameComponentsFromTrack(item=dict(), plist=dict(), counter=0):
  componentTest=True
  try:
    TRACK       = str(item['Track ID'])
  except:
    TRACK       = "track_%s" % counter
  try:
    URIlocation = plist['Tracks'][TRACK]['Location']
  except:
    URIlocation = ''
    componentTest=False
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
  return (componentTest, TRACK, URIlocation, trackName, trackArtist, trackAlbum)

def findTheBloodyTrack(plist=dict(), speculativeDrive='', TRACK='', debug=False):
  EXTENSION = ''
  LOCATION  = ''
  FOUND_SUCCESS = False
  url_OBJ = urlparse(plist['Tracks'][TRACK]['Location'])
  if url_OBJ.scheme.lower() == 'file':
    ifexist, LOCATION = path_resolver(unquote(url_OBJ.path))
    EXTENSION = os.path.splitext(LOCATION)[1]
    if ifexist == False:
      print(" Oups File not found: %s" % LOCATION)
      print(" Trying to find it now.. It could be on a differernt drive..")
      searchresult = ''
      # if a speculative drive exist, it will start with it first
      if speculativeDrive != '':
        iterateOverDriveList = [speculativeDrive] + get_drives()
      else:
        iterateOverDriveList = get_drives()
      for drive in iterateOverDriveList:
        print(" Trying to find it on drive '%s', one moment.. " % drive)
        search = glob.glob('%s/**/%s' % (drive, os.path.basename(LOCATION)), recursive=True)
        try:
          # actually taking the first found
          searchresult = search[0]
        except:
          searchresult = ''
        if os.path.isfile(searchresult):
          print(" ---> FOUND: %s " % searchresult)
          LOCATION = searchresult
          speculativeDrive = drive
          FOUND_SUCCESS = True
          break
      if searchresult == '':  
        LOCATION = "NOT FOUND"
        #sys.exit()
    else:
      FOUND_SUCCESS = True
  elif url_OBJ.scheme.lower().startswith('http'):
    LOCATION  = plist['Tracks'][TRACK]['Location']
    EXTENSION = os.path.splitext(url_OBJ.path)[1]
  else:
    LOCATION = "NOT DETECTED"        
  if debug:
    print("FOUND_SUCCESS %s | speculativeDrive %s | LOCATION %s | EXTENSION %s" % (FOUND_SUCCESS, speculativeDrive, LOCATION, EXTENSION))
  return (FOUND_SUCCESS, speculativeDrive, LOCATION, EXTENSION) 

def ffmpegUtilsFinder():
  foundFFbin = False
  ffmpegLocation = ''
  ffprobeLocation = ''
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
      print(" Okay, well, seems like that ffmpeg binary is gone, try again..")
      os.remove(picklePath)
    else:
      foundFFbin = True
  return (foundFFbin, ffmpegLocation, ffprobeLocation)


# -----------------------------------------------------------------------------------------------------------------------

def main():
  # need to have windows version of ffmpeg utils installed
  foundFFbin, ffmpegLocation, ffprobeLocation = ffmpegUtilsFinder()

  # Default location of Itunes library, for now I assume it's there
  status , userpath = path_resolver(os.environ['USERPROFILE'])
  itunesDefaultLibrary = userpath + '/Music/iTunes/iTunes Music Library.xml'
  itunesDefaultLibrary = itunesDefaultLibrary.replace('/','\\')

  # this program can't continue if I do not find the itunes xml library
  if not os.path.isfile(itunesDefaultLibrary):
    print("\nError: Itunes Library File '%s' not found\nAborting!\n" % itunesDefaultLibrary)
    sys.exit()

  # Loading the XML into a parser for python
  plist = plistlib.readPlist(itunesDefaultLibrary)

  # Getting the playlists names 
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

    # Finding a perfect directory name for the re-worked playlist
    PLAYLIST_FOLDER = findDirectoryForFinalPlaylist(SelectedPlaylist=SelectedPlaylist)
    os.mkdir(PLAYLIST_FOLDER)
    print("\n Playlist will be saved to:\n '%s'\n" % PLAYLIST_FOLDER)
    
    # an other for loop for every track found to be renamed, copied, checked and prepared  
    counter = 0
    speculativeDrive = ''
    for item in trackList:
      counter += 1
      componentTest, TRACK, URIlocation, trackName, trackArtist, trackAlbum = findAllNameComponentsFromTrack(item=item, plist=plist, counter=counter)
      if componentTest == False:
        print(" Warning: Track '%s' for playlist '%s' has an issue, can't find URL location" % (trackName, SelectedPlaylist))
        time.sleep(5)
        continue
      
      FOUND_SUCCESS, speculativeDrive, LOCATION, EXTENSION = findTheBloodyTrack(plist=plist, speculativeDrive=speculativeDrive, TRACK=TRACK, debug=True)
      
      newFileName = "%04d__%s_%s_%s%s" % (counter, trackName, trackArtist, trackAlbum, EXTENSION)
      
      if LOCATION.startswith('NOT') or FOUND_SUCCESS == False:
        print(" Can't create File: '%s' Location: '%s' ..skipping.." % (newFileName, LOCATION))
        time.sleep(5)
        continue
      
      print(" Copying   : %s" % LOCATION)
      print(" New file  : %s" % newFileName)
      
      MP3itemSavePath             = os.path.join(PLAYLIST_FOLDER, newFileName)
      MP3itemSavePathNoExt, exten = os.path.splitext(MP3itemSavePath)
      MP3itemSavePathMP3          = MP3itemSavePathNoExt + '.mp3'
      newFileName                 = os.path.basename(MP3itemSavePathMP3).replace('__','___')
      newFileNamePath             = os.path.join(PLAYLIST_FOLDER, newFileName)

      # If playlist item is actually a real online URL, just download it
      if LOCATION.startswith('http'):
        print('  ', end='', flush=True)
        #FIXME: Need to adress the case when it's unreacheable
        wget.download(LOCATION, out=MP3itemSavePath)
        print()
      else:
        shutil.copy2(LOCATION, MP3itemSavePath)
      # Need to know if this is actually a MP3 file or not.
      formatName = getFormatInfo(ffprobeLocation=ffprobeLocation, inPath=MP3itemSavePath, debug=True)
      # If this is nor a MP3 file, well, let's convert it
      if formatName.lower() != 'mp3':
        MP3itemSavePath = convertToMP3(ffprobeLocation=ffmpegLocation, inPath=MP3itemSavePath, debug=True)
      # Attempt to extract the album art as a JPG file if one is present
      extractAlbumArtJPG(ffmpegLocation=ffmpegLocation, inPath=MP3itemSavePath, debug=True)
      # While removing tag we are now saving to a new file name called : newFileNamePath
      mp3TagRemover(ffmpegLocation=ffmpegLocation, inPath=MP3itemSavePath, outPath=newFileNamePath, debug=True)
      # removing the original tagged MP3 file
      os.remove(MP3itemSavePath)
      # Attempt at re-inserting album art if it's available and save it to MP3itemSavePath
      insertAlbumArt(ffmpegLocation=ffmpegLocation, inPath=newFileNamePath, outPath=MP3itemSavePath, debug=True)
      print('\n') 
   
if __name__ == "__main__":
    # execute only if run as a script
    main()
  