import json

def read_json_from_file(filename):
    file = open(filename, "r")
    raw_content = file.read()
    file.close()
    return json.loads( raw_content )