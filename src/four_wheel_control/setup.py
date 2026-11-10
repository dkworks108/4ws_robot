import os
from glob import glob
from setuptools import setup, find_packages

package_name = 'four_wheel_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ROS 2 Developer',
    maintainer_email='robotics@example.com',
    description='Kinematics and control for 4WS/4WD autonomous robot',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'four_wheel_kinematics_node = four_wheel_control.four_wheel_kinematics_node:main',
            'teleop_keyboard = four_wheel_control.teleop_keyboard:main',
        ],
    },
)
