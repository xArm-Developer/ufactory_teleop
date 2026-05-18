import os
import sys
import time
import pysurvive

argv = sys.argv.copy()
if '--force-calibrate' not in argv:
    argv.append('--force-calibrate')
if '--v' not in argv:
    argv.append('--v')
    argv.append('100')

config_path = os.path.join(os.path.expanduser('~'), '.config', 'libsurvive', 'config.json')
if os.path.exists(config_path):
    print('Remove config: {}'.format(config_path))
    os.remove(config_path)
ctx = pysurvive.SimpleContext(argv)

for obj in ctx.Objects():
    print("*device:", obj.Name())

next_print_time = time.monotonic()
while ctx.Running():
    updated = ctx.NextUpdated()
    if updated:
        pose, ts = updated.Pose()
        name = updated.Name().decode("utf-8")
        serial_number = None
        if hasattr(pysurvive, "simple_serial_number"):
            serial_number = pysurvive.simple_serial_number(updated.ptr).decode("utf-8")
        pos = [pose.Pos[0], pose.Pos[1], pose.Pos[2]]
        rot = [pose.Rot[0], pose.Rot[1], pose.Rot[2], pose.Rot[3]]
        print('[{}][{}] POS: {}, ROT: {}'.format(name, serial_number, pos, rot))
