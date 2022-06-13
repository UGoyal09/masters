# from os import walk

# CONFIG_DIR = "configmaps"


# def parse_config(config_name):
#     """ returns dict with [configfile]: content """

#     config = {}

#     path = "{:s}/{:s}".format(CONFIG_DIR, config_name)
#     _, _, filenames = next(walk(path))
#     for file in filenames:
#         f = open("{:s}/{:s}".format(path, file), "r")
#         value = f.read().rstrip("\n ")
#         config[file] = value

#     return config
