import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/tusaslab7/tez_cbf/ros2_ws/install/cbf_filter_pkg'
