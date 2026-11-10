#!/usr/bin/env python3
"""
Unit tests for URDF and Xacro robot model of Four-Wheel Steering Robot.
"""

import os
import subprocess
import xml.etree.ElementTree as ET
import pytest

WS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XACRO_PATH = os.path.join(WS_ROOT, 'src', 'four_wheel_description', 'urdf', 'robot.urdf.xacro')


def get_expanded_urdf():
    cmd = ['xacro', XACRO_PATH, 'controllers_yaml:=/tmp/dummy.yaml']
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0, f"Xacro failed: {res.stderr}"
    return ET.fromstring(res.stdout)


def test_xacro_expansion():
    root = get_expanded_urdf()
    assert root.tag == 'robot'
    assert root.attrib['name'] == 'four_wheel_steering_robot'


def test_single_root_and_connectivity():
    root = get_expanded_urdf()
    links = [l.attrib['name'] for l in root.findall('link')]
    joints = root.findall('joint')

    parent_map = {}
    for j in joints:
        p = j.find('parent').attrib['link']
        c = j.find('child').attrib['link']
        assert p in links, f"Parent link {p} not found in links"
        assert c in links, f"Child link {c} not found in links"
        parent_map[c] = p

    roots = [l for l in links if l not in parent_map]
    assert len(roots) == 1, f"Expected 1 root link, found {roots}"
    assert roots[0] == 'base_footprint'


def test_steering_and_wheel_joints():
    root = get_expanded_urdf()
    joints = {j.attrib['name']: j for j in root.findall('joint')}

    expected_steering = ['fl_steering_joint', 'fr_steering_joint', 'rl_steering_joint', 'rr_steering_joint']
    expected_wheel = ['fl_wheel_joint', 'fr_wheel_joint', 'rl_wheel_joint', 'rr_wheel_joint']

    for sj in expected_steering:
        assert sj in joints, f"Missing steering joint {sj}"
        assert joints[sj].attrib['type'] == 'revolute'
        axis = joints[sj].find('axis').attrib['xyz'].strip()
        assert axis == '0 0 1', f"Steering axis must be z-axis (0 0 1), got {axis}"
        lim = joints[sj].find('limit')
        assert lim is not None
        assert float(lim.attrib['lower']) < 0
        assert float(lim.attrib['upper']) > 0

    for wj in expected_wheel:
        assert wj in joints, f"Missing wheel joint {wj}"
        assert joints[wj].attrib['type'] == 'continuous'
        axis = joints[wj].find('axis').attrib['xyz'].strip()
        assert axis == '0 1 0', f"Wheel spin axis must be y-axis (0 1 0), got {axis}"


def test_sensor_frames():
    root = get_expanded_urdf()
    links = {l.attrib['name']: l for l in root.findall('link')}

    assert 'lidar_link' in links, "Missing lidar_link"
    assert 'imu_link' in links, "Missing imu_link"
    assert 'camera_link' in links, "Missing camera_link"


def test_mass_and_inertias():
    root = get_expanded_urdf()
    for link in root.findall('link'):
        name = link.attrib['name']
        if name == 'base_footprint':
            continue
        inertial = link.find('inertial')
        assert inertial is not None, f"Link {name} missing inertial"
        mass = float(inertial.find('mass').attrib['value'])
        assert mass > 0, f"Link {name} has non-positive mass: {mass}"
        inertia = inertial.find('inertia')
        assert inertia is not None
        ixx = float(inertia.attrib['ixx'])
        iyy = float(inertia.attrib['iyy'])
        izz = float(inertia.attrib['izz'])
        assert ixx > 0 and iyy > 0 and izz > 0, f"Link {name} invalid inertia: ixx={ixx}, iyy={iyy}, izz={izz}"


if __name__ == '__main__':
    pytest.main(['-v', __file__])

