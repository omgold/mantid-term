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

To have any keybindings available, this file needs to be created first.
Working examples (to be copied) can be found at /usr/share/mantid.

# STARTUP

The section *startup* contains defaults which will be applied on startup.
Most options here will not be re-applied when the configuration file is reloaded.

%(startup_options)s

# APPEARANCE

The section *appearance*, e.g. allows to change fonts and colors.

%(appearance_options)s

# COLORS

Most colors in the window can be customized. The format can be a name, e.g. black, red, lightblue, ..., or a RGB value in the form "#rrggbb".

%(color_options)s

# KEYBINDINGS

The section *keybindings* has 3 subsections *global*, *normal* and *command*.
*global* bindings apply both in normal mode and command mode, while *normal* and
*command* bindings apply only in the respective mode.

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


def describe_option(name, default, description):
    if default is not None:
        return """\
\t%s (default: %s):
\t\t%s
""" % (name, main.quick_yaml_translate(default), description)
    else:
        return """\
\t%s:
\t\t%s
""" % (name, description)


options_doc = {
    "startup": {
        "term": "Value of TERM environment variable",
        "role": "X11 role of the window",
        "keep-open": "Automatically close the terminal after the child process exits",
        "fullscreen": "Start in fullscreen mode",
        "shell": "Command to start as \"shell\", if not overridden on cmdline.\n\t\tCan be an array to provide arguments to the command.",
        "rows": "Number of terminal lines",
        "columns": "Number of terminal columns",
        "font-scale": "Initial zoom factor",
        "scrollback-lines": "Size of scrollback buffer, use -1 for infinite scrollback",
        "scroll-on-output": "Automatically reset scroll on new output",
        "scroll-on-keystroke": "Automatically reset scroll on keypress in normal mode",
        "audible-bell": "Bell control sequence produces sound",
    },
    "appearance": {
        "show-scrollbar": "Scrollbar position.\n\t\tCan be null, \"left\" or \"right\".",
        "cursor-blink": "Cursor is blinking.\n\t\tCan be true, false or \"system\".",
        "cursor-shape": "Cursor shape.\n\t\tCan be \"block\", \"underline\" or \"ibeam\".",
        "mouse-autohide": "Hide mouse on keypress",
        "allow-bold": "Bold escape sequence is honored",
        "bold-is-bright": "Bold text will automatically be set to bright color\n\t\t(as defined by legacy standard)",
        "cell-width-scale": "Scaling of character cell",
        "cell-height-scale": "Scaling of character cell",
        "icon": "Window icon name ",
        "font": "Terminal font",
        "cursor-aspect-ratio": "Adjust width/height of underline or ibeam cursors\n\t\t(useful in particular on HiDPI displays).",
        "padding": "thickness of padding (frame) around terminal",
        "scrollbar-padding": "thickness of padding (frame) around scrollbar",
        "scrollbar-width": "Adjust width of scrollbar \n\t\t(useful in particular on HiDPI displays).",
    },
    "colors": {
        "foreground": "foreground color of terminal",
        "foreground-bold": "foreground color of bold text",
        "background": "background color of terminal",
        "cursor": "background color of cursor (transparent when unset)",
        "cursor-foreground": "color of text under cursor (unchanged when unset)",
        "highlight": "background color of selected text (transparent when unset)",
        "highlight-foreground": "color of selected text (unchanged when unset)",
        "padding": "color of padding around terminal",
        "scrollbar": "color of scrollbar",
        "scrollbar-padding": "color of scrollbar background",
        "0-255": "palette colors of xterm-color (0-15) and xterm-256color (0-255)"
    },
}


def generate_scdoc():

    parser = main.get_arg_parser("~", None)
    raw_usage = parser.format_usage()
    usage = "\n".join([line[7:] for line in raw_usage.split('\n') ])
    options = parser.format_help()[len(raw_usage):]

    f = open("config/mantid-vi.yml","r")
    config_example = f.read()

    actions = {}
    for section_name, section_actions in main.actions.items():
        d = [ describe_action(n, a) for n, a in sorted(section_actions.items()) ]
        actions[section_name] = "\n".join(d)
    #print(actions)

    config_options = {}
    for section_name, section_doc in options_doc.items():
        section_default = main.default_config.get(section_name,{})
        d = [ describe_option(n, section_default.get(n), doc)
              for n, doc in sorted(section_doc.items()) ]
        config_options[section_name] = "\n".join(d)

    pars = {
        "usage": usage,
        "options": options,
        "config_example": config_example,
        "global_actions": actions["global"],
        "normal_actions": actions["normal"],
        "command_actions": actions["command"],
        "startup_options": config_options["startup"],
        "appearance_options": config_options["appearance"],
        "color_options": config_options["colors"],
    }

    print(template%pars)
