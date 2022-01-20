from os import listdir, remove, rmdir                             # importing path to see if file exist
import json
import zipfile

json_var = list()
start = True
done = False

def get_info_from_file(location, file):
    global start
    global done
    global json_var

    if start:
        create_json_info(location, file)

    if len(json_var) > 0:
        return json_var.pop(0)
    elif done:
        return False
    else:
        create_json_info(location, file)
        return json_var.pop(0)

def create_json_info(location, file):
    global start
    global done
    global json_var

    file_name = file.pop(0)

    if len(file) == 0:
        done = True

    with zipfile.ZipFile(location + file_name, 'r') as zip_ref:
        zip_ref.extractall("usable_replay")

    file_name = listdir(r"usable_replay/")[0]

    with open(r"usable_replay/" + file_name, 'r') as curFile:
        lines = curFile.read().splitlines()
        for i in range(len(lines)):
            start = 0
            for j in range(len(lines[i])):
                if lines[i][j] == '{':
                    start = j
                    break

            lines[i] = lines[i][start:]

        for i in range(len(lines)):
            json_var.append(json.loads(lines[i]))

    remove(r"usable_replay/" + file_name)
    rmdir(r"usable_replay/")
    start = False

    return

def clear_replay():
  global start
  global json_var
  
  start = True
  json_var.clear()
  
  return

def main():
    names = [r"replay_21_09_17.echoreplay", r"replay_round_1_21_09_17.echoreplay"]
    # names.append(r"replay_21_09_17.echoreplay")
    # names.append(r"replay_round_1_21_09_17.echoreplay")
    var = get_info_from_file(r"Replays\\", names)
    while var:
        print('players' in var['teams'][1])
        var = get_info_from_file(r"Replays/", r"replay_21_09_17.echoreplay")

if __name__ == "__main__":
    main()