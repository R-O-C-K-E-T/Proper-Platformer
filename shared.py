import numpy as np

def get_objects():
    return level['objects']

level = {'objects': [], 'constraints': [], 'spawn': [0,0], 'gravity': [0, 0.3]}
level_modified = False
selection = []
joint_selection = []
selected_colour = [0, 0, 0]

history = []
history_index = -1

root = None
colour_button = None
god = None
colour_picker = None
