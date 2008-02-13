import warnings
warnings.filterwarnings('ignore', 'Could not find matplotlibrc; using defaults')
warnings.filterwarnings('ignore', 'could not find rc file; returning defaults')

__import__('pkg_resources').declare_namespace(__name__)
