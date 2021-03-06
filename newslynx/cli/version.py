import pkg_resources

from colorama import Fore

from newslynx.cli.common import echo

def setup(parser):
    api_parser = parser.add_parser("version", help="Report the version.")
    return 'version', run

def run(opts, **kwargs):
    """
    Report the version.
    """
    echo(pkg_resources.get_distribution("newslynx").version, 
        color=Fore.BLUE, no_color=opts.no_color)