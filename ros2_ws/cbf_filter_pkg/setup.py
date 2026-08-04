from setuptools import find_packages, setup

package_name = 'cbf_filter_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tusaslab7',
    maintainer_email='ibakpinar43@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': ['safety_filter_node = cbf_filter_pkg.safety_filter_node:main', 'obstacle_chaser_node = cbf_filter_pkg.obstacle_chaser_node:main', 'scenario_node = cbf_filter_pkg.scenario_node:main', 'metrics_extractor = cbf_filter_pkg.metrics_extractor:main', 'sweep_runner = cbf_filter_pkg.sweep_runner:main',
        ],
    },
)
