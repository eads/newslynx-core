import re
from colorama import Fore
from newslynx.lib import serialize


re_quoted_arg = re.compile(r'^[\'\"]?(.*)[\'\"]?$')

def parse_runtime_args(arg_strings):
    """
    Parses arbitrary command-line args of the format:
    --option1=value1 -option2="value" -option3 value3
    Into a dictionary of {'option1':'value1', 'option2':'value2', 'option3': 'value3'}
    """
    kwargs = {}
    for arg_string in arg_strings:
        parts = arg_string.split("=")
        key = parts[0].replace('-', '').strip()
        
        # assume this means a boolean flag
        if len(parts)==1:
            kwargs[key] = True
        # clean
        else:
            m = re_quoted_arg.search("=".join(parts[1:]))
            value = m.group(0)
            kwargs[key] = value
    return kwargs

def load_data(path_or_string):
    """
    Load data in from a filepath or a string
    """
    kwargs = {}
    if not path_or_string:
        return kwargs
    try:
        d = serialize.json_to_obj(path_or_string)
        kwargs.update(d)
        return kwargs

    except ValueError as e:
        # only deal with these formats.
        if not ( path_or_string.endswith('.yaml') or 
            path_or_string.endswith('.yml') or 
            path_or_string.endswith('.json') ):
           return kwargs

        fp = os.path.expand_user(path_or_string)
        try:
            kwargs.update(serialize.yaml_to_obj(fp.read()))
            return kwargs
        except Exception as e:
            pass
    echo_error(RuntimeError("Could not parse input data:\n'{}'".format(e.message)))
    sys.exit(1)

def echo(msg, **kwargs):
    """
    Cli logger.
    """
    if kw.get('no_interactive', False):
        color = kwargs.get('color', Fore.GREEN)
        msg = '{0}{1}{2}'.format(color, msg, Fore.RESET)
    print(msg)

def echo_error(e, tb=None):
    """
    Error message.
    """
    echo('{}: {}'.format(e.__class__.__name__, e.message), color=Fore.RED)
    if tb:
        echo(tb, color=Fore.YELLOW)

def is_valid_file(arg):
    """
    Error message when loading file.
    """
    if not os.path.exists(arg):
        RuntimeError("The file %s does not exist!" % arg)
    else:
        return open(arg, 'rU')  # return an open file handle
