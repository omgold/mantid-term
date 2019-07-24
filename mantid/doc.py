from . import main

template = """\
mantid(1) "mantid" ""

# NAME

mantid - a fully keyboard-controllable terminal inspired by termite

# SYNOPSIS

```
%(usage)s```

# DESCRIPTION

*Mantid* is a xterm-compatible terminal emulator based on Vte-ng,
similar to termite. Keybindings and appearance can be defined via
a configuration file in yaml format.

# OPTIONS

```
%(options)s```

# CONFIG FILE

If not specified otherwise on the command line, the configuration file in
the user's home directory at *~/.config/mantid.yml* is loaded at startup.

It contains the 3 sections *startup*, *appearance* and *keybindings*.

The section *startup* contains defaults which will be applied on startup.
Most options here will not be re-applied when the configuration file is reloaded.

The section *appearance*, e.g. allows to change fonts and colors.

The section *keybindings* has 3 subsections *global*, *normal* and *command*.
*global* bindings apply both in normal mode and command mode, while *normal* and
*command* bindings apply only the respective mode.

A keybinding entry consists of the accelerator key description (in the format
used by GDK 3.0) as the mapping key, and an action as the mapping value. The action
can either be a string (which will call the action without any arguments):

	<Ctrl><Alt>r: reload-config

or a mapping, which contains an *action* entry, giving the name of the action,
and one or multiple named arguments passed to the action:

	<Shift>Page_Up: {action: move, screen: -0.5}

*Note:* The description for a key combination can be determined
by starting *mantid* with the option --print-accelerators, which - while
in command mode - prints the accelerator description to stderr.

# ACTIONS

The following actions are known by *mantid*.

*global* actions:

%(global_actions)s

*normal* mode actions:

%(normal_actions)s

*command* mode actions:

%(command_actions)s

# EXAMPLE CONFIGURATION

A configuration file showing all options
(with everything set to the builtin defaults) would look like this:

```
%(config_example)s
```

"""

def describe_action(name, action):
    doc = action.__doc__ or ""
    return "\t*%s*: %s\n" % (name, "++\n\t".join(doc.rstrip().split("\n")))


def generate_scdoc():

    parser = main.get_arg_parser("~", None)
    raw_usage = parser.format_usage()
    usage = "\n".join([line[7:] for line in raw_usage.split('\n') ])
    options = parser.format_help()[len(raw_usage):]

    f = open("config/mantid.yml","r")
    config_example = f.read()

    actions = {}
    for section_name, section_actions in main.actions.items():
        d = [ describe_action(n, a) for n, a in sorted(section_actions.items()) ]
        actions[section_name] = "\n".join(d)
    #print(actions)

    pars = {
        "usage": usage,
        "options": options,
        "config_example": config_example,
        "global_actions": actions["global"],
        "normal_actions": actions["normal"],
        "command_actions": actions["command"],
    }

    print(template%pars)
