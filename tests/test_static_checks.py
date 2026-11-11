#!/usr/bin/env python3
"""
Phase 13A Static Validation Suite for Project 04.

Validates:
- XML syntax across package.xml, xacro, and SDF world files
- Xacro expansion into valid URDF XML
- YAML syntax across all configuration files
- Python syntax across all source and test files
- ROS 2 package discovery (all 5 packages)
- Launch file import and generate_launch_description() parsing
- Built frontend dist artifacts in both source and install share directories
"""

import os
import glob
import py_compile
import subprocess
import importlib.util
import xml.etree.ElementTree as ET
import yaml
import pytest

WS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_xml_and_package_manifests():
    xml_files = (
        glob.glob(os.path.join(WS_ROOT, 'src', '*', 'package.xml'))
        + glob.glob(os.path.join(WS_ROOT, 'src', 'four_wheel_description', 'urdf', '*.xacro'))
    )
    assert len(xml_files) >= 5
    for path in xml_files:
        ET.parse(path)


def test_sdf_worlds_valid_fortress():
    sdf_files = glob.glob(os.path.join(WS_ROOT, 'src', 'four_wheel_description', 'worlds', '*.sdf'))
    assert len(sdf_files) >= 2
    for path in sdf_files:
        root = ET.parse(path).getroot()
        assert root.tag == 'sdf', f"{path} missing <sdf> root"
        assert root.find('world') is not None, f"{path} missing <world>"
        with open(path, 'r', encoding='utf-8') as f:
            assert 'libgazebo_ros_' not in f.read(), f"{path} contains legacy Gazebo Classic plugin"


def test_yaml_configs_valid():
    yaml_files = glob.glob(os.path.join(WS_ROOT, 'src', '*', 'config', '*.yaml'))
    assert len(yaml_files) >= 5
    for path in yaml_files:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict) and len(data) > 0, f"Invalid/empty YAML: {path}"


def test_python_syntax_all_sources_and_tests():
    py_files = (
        glob.glob(os.path.join(WS_ROOT, 'src', '*', '*', '*.py'))
        + glob.glob(os.path.join(WS_ROOT, 'src', '*', 'launch', '*.py'))
        + glob.glob(os.path.join(WS_ROOT, 'tests', '*.py'))
    )
    assert len(py_files) >= 15
    for path in py_files:
        py_compile.compile(path, doraise=True)


def test_xacro_expansion_and_urdf_validity():
    xacro_path = os.path.join(WS_ROOT, 'src', 'four_wheel_description', 'urdf', 'robot.urdf.xacro')
    res = subprocess.run(
        ['xacro', xacro_path, 'controllers_yaml:=/tmp/dummy.yaml'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert res.returncode == 0, f"Xacro failed: {res.stderr}"
    root = ET.fromstring(res.stdout)
    assert root.tag == 'robot'


def test_ros2_package_discovery():
    from ament_index_python.packages import get_package_share_directory
    expected_pkgs = [
        'four_wheel_description',
        'four_wheel_control',
        'four_wheel_navigation',
        'four_wheel_exploration',
        'four_wheel_mobile_control',
    ]
    for pkg in expected_pkgs:
        share = get_package_share_directory(pkg)
        assert os.path.isdir(share), f"Missing share dir for {pkg}"


def test_launch_files_parse():
    launch_files = [
        os.path.join(WS_ROOT, 'src', 'four_wheel_description', 'launch', 'gazebo.launch.py'),
        os.path.join(WS_ROOT, 'src', 'four_wheel_navigation', 'launch', 'slam.launch.py'),
        os.path.join(WS_ROOT, 'src', 'four_wheel_navigation', 'launch', 'navigation.launch.py'),
        os.path.join(WS_ROOT, 'src', 'four_wheel_mobile_control', 'launch', 'complete_mobile_simulation.launch.py'),
    ]
    for lf in launch_files:
        spec = importlib.util.spec_from_file_location('launch_mod', lf)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ld = mod.generate_launch_description()
        assert ld is not None and len(ld.entities) > 0, f"Empty LaunchDescription in {lf}"


def test_frontend_build_artifacts_present():
    src_index = os.path.join(WS_ROOT, 'src', 'four_wheel_mobile_control', 'frontend', 'dist', 'index.html')
    assert os.path.isfile(src_index), f"Missing source dist: {src_index}"
    from ament_index_python.packages import get_package_share_directory
    share_index = os.path.join(get_package_share_directory('four_wheel_mobile_control'), 'frontend', 'index.html')
    assert os.path.isfile(share_index), f"Missing installed frontend dist: {share_index}"


if __name__ == '__main__':
    pytest.main(['-v', __file__])

