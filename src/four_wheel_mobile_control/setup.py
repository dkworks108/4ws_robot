from setuptools import setup
import os
from glob import glob

package_name = 'four_wheel_mobile_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.*')),
        (os.path.join('share', package_name, 'frontend'), glob('frontend/dist/*.html') + glob('frontend/dist/*.svg')),
        (os.path.join('share', package_name, 'frontend', 'assets'), glob('frontend/dist/assets/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bumble',
    maintainer_email='bumble@robotics.local',
    description='Mobile Web Control, Monitoring Dashboard, and Command Arbitration for 4WS/4WD Autonomous Mobile Robot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'command_arbiter_node = four_wheel_mobile_control.command_arbiter_node:main',
            'web_server = four_wheel_mobile_control.web_server:main',
            'system_readiness_node = four_wheel_mobile_control.system_readiness_node:main',
            'launch_gate = four_wheel_mobile_control.launch_gate:main',
        ],
    },
)

