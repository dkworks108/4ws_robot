import os
import sys
import xml.etree.ElementTree as ET

# find urdf file
urdf_file = os.path.join(os.path.dirname(__file__), 'urdf', 'robot.urdf')

if not os.path.exists(urdf_file):
    print(f"FAIL: File not found: {urdf_file}")
    sys.exit(1)

try:
    tree = ET.parse(urdf_file)
    root = tree.getroot()
except Exception as e:
    print(f"FAIL: XML parse error: {e}")
    sys.exit(1)

# get links and joints
links = {link.attrib['name']: link for link in root.findall('link')}
joints = {joint.attrib['name']: joint for joint in root.findall('joint')}

print(f"Total links: {len(links)}")
print(f"Total joints: {len(joints)}")

steering_joints = []
wheel_joints = []
all_joints_valid = True

for name, j in joints.items():
    jtype = j.attrib.get('type')
    parent = j.find('parent').attrib.get('link') if j.find('parent') is not None else None
    child = j.find('child').attrib.get('link') if j.find('child') is not None else None

    print(f" - Joint: {name} | Type: {jtype} | Parent: {parent} -> Child: {child}")

    if parent not in links or child not in links:
        print(f"   ERROR: Joint {name} links missing: parent={parent}, child={child}")
        all_joints_valid = False

    if jtype == 'revolute' and 'steering' in name:
        steering_joints.append(name)
    elif jtype == 'continuous' and 'wheel' in name:
        wheel_joints.append(name)

print(f"Steering joints ({len(steering_joints)}): {steering_joints}")
print(f"Wheel joints ({len(wheel_joints)}): {wheel_joints}")

# check symmetry of steering joints origins
positions = {}
for s_name in ['fl_steering_joint', 'fr_steering_joint', 'rl_steering_joint', 'rr_steering_joint']:
    j = joints.get(s_name)
    if j is not None and j.find('origin') is not None:
        coords = [float(val) for val in j.find('origin').attrib.get('xyz', '0 0 0').split()]
        positions[s_name] = coords
        print(f"   Position of {s_name}: {coords}")

symmetric = False
if len(positions) == 4:
    fl = positions['fl_steering_joint']
    fr = positions['fr_steering_joint']
    rl = positions['rl_steering_joint']
    rr = positions['rr_steering_joint']

    x_sym = abs(fl[0] - fr[0]) < 1e-4 and abs(rl[0] - rr[0]) < 1e-4 and abs(abs(fl[0]) - abs(rl[0])) < 1e-4
    y_sym = abs(fl[1] + fr[1]) < 1e-4 and abs(rl[1] + rr[1]) < 1e-4 and abs(fl[1] - rl[1]) < 1e-4
    z_sym = abs(fl[2] - fr[2]) < 1e-4 and abs(rl[2] - rr[2]) < 1e-4
    symmetric = x_sym and y_sym and z_sym
    print(f"Symmetry check: x_sym={x_sym}, y_sym={y_sym}, z_sym={z_sym} -> overall symmetric={symmetric}")

if all_joints_valid and len(steering_joints) == 4 and len(wheel_joints) == 4 and symmetric:
    print("PASS: 4WS Robot verification passed! 4 steering + 4 continuous wheel joints with symmetric geometry.")
    sys.exit(0)
else:
    print("FAIL: Verification failed!")
    sys.exit(1)
