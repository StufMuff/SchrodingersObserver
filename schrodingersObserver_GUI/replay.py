from requests.exceptions import ConnectionError # used for connecting to HTTP server
import echovr_api                               # importing echovr api information and functions
from os import path, remove, environ, makedirs              # importing path to see if file exist
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"              # removes banner that pygame always prints
import zipfile, pygame
from datetime import date, datetime                           # importing to set time stamps
import json                                         # importing functions for json manipulation
import traceback

# import zipfile
#
# jungle_zip = zipfile.ZipFile('C:\\Stories\\Fantasy\\jungle.zip', 'w')
# jungle_zip.write('C:\\Stories\\Fantasy\\jungle.pdf', compress_type=zipfile.ZIP_DEFLATED)
#
# jungle_zip.close()

file_info = {                               # putting all file info into dictionary
        'file_name': 'replay',
        'file_ext': '.echoreplay',
        'round': 1,
        'directory': r"Replays/",
        'today': date.today(),
        'today_date': date.today().strftime('_%y_%m_%d'),
        'file_index': 0,
        'first_write': True,                     # flag used to tell if file has info
        'wrote_file': False,                     # flag used to only write the file once
        'new_file_needed': True,                 # flag to control file creation
        'error_occured' : False                  # flag to see if there is a connection error
        }

# setting IP and port to grab echoVR API data
echovr_api = echovr_api.api.API(base_url="http://127.0.0.1:6721")

fps = 30
pass_read = True

def setup_file_info(file_info):
    file_info['file_open'] = file_info['file_name'] + file_info['today_date'] + "_round_" + str(file_info['round']) + file_info['file_ext']
    return

# creating a new file
def create_new_file():

    # while loop used create a file name that doesn't exist yet
    while path.exists(file_info['directory'] + file_info['file_open']):
        file_info['file_index'] += 1
        file_info['file_open'] = \
            file_info['file_name'] + file_info['today_date'] + "_" + str(file_info['file_index']) + "_round_" + str(file_info['round']) + file_info['file_ext']


    return

def end_round():
    # if directoy doesn't exist
    if not path.exists(file_info['directory']):
        makedirs(file_info['directory'])
    # compressing replay file
    if path.exists(file_info['file_open']):
        jungle_zip = zipfile.ZipFile(file_info['directory'] + file_info['file_open'], 'w')
        jungle_zip.write(file_info['file_open'], compress_type=zipfile.ZIP_DEFLATED)
        remove(file_info['file_open'])

        file_info['round'] += 1
        if file_info['file_index'] != 0:
            file_info['file_open'] = \
                file_info['file_name'] + "_" + file_info['today_date'] + "_" + str(file_info['file_index']) + "_round_" + str(file_info['round']) + file_info['file_ext']
        else:
            file_info['file_open'] = \
                file_info['file_name'] + file_info['today_date'] + "_round_" + str(file_info['round']) + file_info['file_ext']


    return

def save_replay(fps):
    global clock
    global pass_read
    
    try:
        # retrieve data from server and run task
        current_status = echovr_api.fetch_state_data()

        if pass_read:
          if current_status['game_status'] == "round_over" or current_status['game_status'] == "pre_match":
              if not file_info['first_write']:
                pass_read = False
                write_replay_info(current_status)
          elif current_status['game_status'] == "post_match":
              pass_read = False
              #I don't think I need to write post match? Is it right after round over?
#              write_replay_info(current_status)
          else:
              if file_info['first_write']:
                  file_info['first_write'] = False
              write_replay_info(current_status)
        else:
          if current_status['game_status'] == "round_over" or current_status['game_status'] == "pre_match":
              if not file_info['first_write']:
                  end_round()
                  file_info['first_write'] = True
                  pass_read = True
          elif current_status['game_status'] == "post_match":
              pass
          else:
              if file_info['first_write']:
                  file_info['first_write'] = False

              write_replay_info(current_status)

        clock.tick(fps)
        return True
    except (ConnectionError, json.decoder.JSONDecodeError):
        print("Replay Finished_ Hi Cosmic")
        end_round()
        file_info['first_write'] = True
        return False

def write_replay_info(status):
  
  now = datetime.now()
  time_stamp = now.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
  # print(json.dumps(current_status))
  with open(file_info['file_open'], 'a+') as file:
      file.write(time_stamp + "\t" + json.dumps(status) + "\n")
  
  return

def main():
    global fps

    create_new_file()

    while save_replay(fps):
        pass

    return

clock = pygame.time.Clock()
setup_file_info(file_info)

if __name__ == '__main__':
    main()