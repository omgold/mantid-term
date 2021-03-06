import sys
import os
import signal
import re
import yaml
import argparse

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
gi.require_version("Mantid", "1.0")
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Vte
from gi.repository import Pango
from gi.repository import Mantid as mc

from .colors import rgba_parse, default_palette, default_colors, transparent
from .keybindings import default_keybindings


def introspect(obj):
    cleaned_obj = { entry for entry in dir(obj) if not entry.startswith("__") }
    print(cleaned_obj)


def get_key_name(keyval, modifiers):
    label = Gtk.accelerator_name(keyval, modifiers)
    check_keyval, check_modifiers = Gtk.accelerator_parse(label)
    if check_keyval == keyval and check_modifiers == modifiers:
        return label


def child_exited_cb(vte, status, terminal):
    if terminal.keep_open:
        return
    app.remove_terminal(terminal, status)


def exit_with_success(window):
    Gtk.main_quit()
    sys.exit(0)


def key_press_cb(vte, key, terminal):

    command_mode = terminal.command_mode
    if command_mode:
        action = app.find_keybinding(app.keybindings_command, key,
                                     debug_print=app.print_accelerators)
    else:
        action = app.find_keybinding(app.keybindings_normal, key)

    if action is not None:
        try:
            action_name, cmd, args = action
            ret = cmd(terminal, **args)
            return ret is not False
        except Exception as e:
            if isinstance(args,dict):
                args = [ "%s=%s" % (key,arg) for key, arg in args.items() ]
            else:
                args = [ str(arg) for arg in args ]
            print("exception during invocation of action %s(%s):\n%s" % (action_name, ", ".join(args), e), file=sys.stderr)
            return True

    if command_mode:
        return True
    return False


def entry_key_press_cb():
    pass


def get_entry_position_overlay_cb(overlay, entry, allocation):

    hbox = overlay.get_child()

    width  = hbox.get_allocated_width()
    height = hbox.get_allocated_height()

    min_size, natural_size = entry.get_preferred_size()

    allocation.x = width - natural_size.width - 40
    allocation.y = 0
    allocation.width  = min(width, natural_size.width)
    allocation.height = min(height, natural_size.height)


# def button_press_cb():
#    pass

# def focus_cb():
#    pass

def set_window_title():
    terminal = app.active_terminal
    if app.title is None:
        vte_title = terminal.vte.get_window_title()
    else:
        vte_title = app.title

    terminal_count = len(app.terminals)
    if terminal_count>1:
        pos = app.terminals.index(terminal)
        title = "%s [%i/%i]" % (vte_title, pos+1, terminal_count)
    else:
        title = vte_title
    app.window.set_title(title)


def alpha_screen_changed_cb(window):
    pass


def window_state_cb(vte, event):
    app.is_fullscreen = event.new_window_state & Gdk.WindowState.FULLSCREEN
    return False


def window_title_cb(vte, terminal):
    if terminal == app.active_terminal and app.title is None:
        set_window_title()


# def spawn_child_cb(pty, task, terminal):
#     if task.had_error():
#         try:
#             task.propagate_int()
#         except GLib.Error as e:
#             print(e.message)
#         child_exited_cb(terminal.vte, 127, terminal)
#         return

#     result = pty.spawn_finish(task)
#     pid = result[0]
#     terminal.vte.watch_child(pid)


class Terminal:
    def __init__(self, keep_open):

        self.keep_open = keep_open
        self.command_mode = False
        self.select_mode = None
        self.selection_start = None
        self.normal_cursor_position = None

        self.vte = Vte.Terminal()
        vte_style = self.vte.get_style_context()
        Gtk.StyleContext.add_class(vte_style,"mantid")
        vte_style.add_provider(app.style, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox_style = self.hbox.get_style_context()
        Gtk.StyleContext.add_class(hbox_style,"mantid")
        hbox_style.add_provider(app.style, Gtk.STYLE_PROVIDER_PRIORITY_USER)


        self.hint_overlay = Gtk.Overlay()
        self.hint_overlay.override_background_color(Gtk.StateFlags.NORMAL,transparent)

        self.scrollbar = Gtk.Scrollbar.new(Gtk.Orientation.VERTICAL,
                                           self.vte.get_vadjustment())
        scrollbar_style = self.scrollbar.get_style_context()
        Gtk.StyleContext.add_class(scrollbar_style,"mantid")
        scrollbar_style.add_provider(app.style, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.da = Gtk.DrawingArea()
        self.da.override_background_color(Gtk.StateFlags.NORMAL,transparent)
        self.da.set_halign(Gtk.Align.FILL)
        self.da.set_valign(Gtk.Align.FILL)

        self.panel_overlay = Gtk.Overlay()

        self.panel_entry = Gtk.Entry()
        self.panel_entry.set_margin_start(5)
        self.panel_entry.set_margin_end(5)
        self.panel_entry.set_margin_top(5)
        self.panel_entry.set_margin_bottom(5)
        self.panel_entry.set_halign(Gtk.Align.START)
        self.panel_entry.set_valign(Gtk.Align.END)
        self.panel_entry.connect("key-press-event", entry_key_press_cb, self)
        self.panel_overlay.connect("get-child-position", get_entry_position_overlay_cb)

        self.vte.connect("child-exited", child_exited_cb, self)
        self.vte.connect("key-press-event", key_press_cb, self)
        #self.vte.connect("button-press-event", button_press_cb, self)
        self.vte.connect("window-title-changed", window_title_cb, self)

        self.hint_overlay.add_overlay(self.da)
        self.hint_overlay.add(self.vte)
        self.hbox.pack_start(self.hint_overlay, True, True, 0)
        self.hbox.pack_start(self.scrollbar, False, False, 0)
        self.panel_overlay.add(self.hbox)
        # self.panel_overlay.add_overlay(self.panel_entry)

        self.panel_overlay.show_all()

        self.apply_config()

        self.panel_entry.hide()
        self.da.hide()


    def apply_config(self):

        vte = self.vte

        startup = app.config["startup"]
        appearance = app.config["appearance"]

        scrollbar_pos = appearance["show-scrollbar"]
        if scrollbar_pos == True or scrollbar_pos == "right":
            self.hbox.reorder_child(self.scrollbar, -1);
            self.scrollbar.show()
        elif scrollbar_pos == "left":
            self.hbox.reorder_child(self.scrollbar, 0);
            self.scrollbar.show()
        else:
            self.scrollbar.hide()

        vte.set_scrollback_lines(startup["scrollback-lines"])
        vte.set_scroll_on_output(startup["scroll-on-output"])
        vte.set_scroll_on_keystroke(startup["scroll-on-keystroke"])
        vte.set_audible_bell(startup["audible-bell"])
        vte.set_mouse_autohide(appearance["mouse-autohide"])
        vte.set_allow_bold(appearance["allow-bold"])
        vte.set_bold_is_bright(appearance["bold-is-bright"])
        # vte_terminal_search_set_wrap_around(vte, cfg_bool("search_wrap", TRUE));
        # vte_terminal_set_allow_hyperlink(vte, cfg_bool("hyperlinks", FALSE));

        font = Pango.font_description_from_string(appearance["font"])
        vte.set_font(font)

        vte.set_colors(None, None, app.palette)
        vte.set_color_background(app.colors["background"])
        foreground = app.colors["foreground"]
        vte.set_color_foreground(foreground)
        vte.set_color_bold(app.colors.get("foreground-bold",foreground))
        vte.set_color_cursor(app.colors.get("cursor"))
        vte.set_color_cursor_foreground(app.colors.get("cursor-foreground"))
        vte.set_color_highlight(app.colors.get("highlight"))
        vte.set_color_highlight_foreground(app.colors.get("highlight-foreground"))

        blink = appearance["cursor-blink"]
        if blink == True:
            blink_mode = Vte.CursorBlinkMode.ON
        elif blink == False:
            blink_mode = Vte.CursorBlinkMode.OFF
        else:
            blink_mode = Vte.CursorBlinkMode.SYSTEM
        vte.set_cursor_blink_mode(blink_mode)

        shape = appearance["cursor-shape"]
        if shape == "ibeam":
            shape_mode = Vte.CursorShape.IBEAM
        elif shape == "underline":
            shape_mode = Vte.CursorShape.UNDERLINE
        else:
            shape_mode = Vte.CursorShape.BLOCK
        vte.set_cursor_shape(shape_mode)

        scale_x = appearance["cell-width-scale"]
        scale_y = appearance["cell-height-scale"]
        vte.set_cell_width_scale(scale_x)
        vte.set_cell_height_scale(scale_x)


    def run(self, cmd):
        env = os.environ.copy()

        gdk_window = app.window.get_window()
        if isinstance(gdk_window,gi.repository.GdkX11.X11Window):
            env["WINDOWID"] = gdk_window.get_xid()

        startup = app.config["startup"]

        env["TERM"] = startup["term"]

        #draw_cb_info draw_cb_info{vte, &info.panel, &info.config.hints, info.config.filter_unmatched_urls};
        #g_signal_connect_swapped(info.panel.da, "draw", G_CALLBACK(draw_cb), &draw_cb_info);

        # pty = self.vte.pty_new_sync(Vte.PtyFlags.DEFAULT, None)

        # pty.spawn_async(None, # pwd
        #                 cmd, # cmd
        #                 None, # env
        #                 GLib.SpawnFlags.SEARCH_PATH|GLib.SpawnFlags.DO_NOT_REAP_CHILD, # spawn_flags
        #                 None, # child_setup_data,
        #                 None, # child_setup_data_destroy,
        #                 -1, # timeout,
        #                 None, # cancellable
        #                 spawn_child_cb, # callback
        #                 self, # user_data
        # )

        # self.vte.set_pty(pty)

        _, self.pid = \
        self.vte.spawn_sync(Vte.PtyFlags.DEFAULT,
                            app.work_dir, # pwd
                            cmd, # cmd
                            [ "%s=%s" % entry for entry in env.items()], # env
                            GLib.SpawnFlags.SEARCH_PATH, # spawn_flags
                            None, # child_setup_data,
                            None, # child_setup_data_destroy,
                            None, # cancellable
        )


    def update_scroll(self):

        vte = self.vte

        adjustment = vte.get_vadjustment()
        scroll_row = adjustment.get_value()
        row_count = vte.get_row_count()
        _, cursor_row = vte.get_cursor_position()

        if cursor_row < scroll_row:
            adjustment.set_value(cursor_row)
        elif cursor_row - row_count >= scroll_row:
            adjustment.set_value(cursor_row-row_count+1)


    def update_selection(self):

        vte = self.vte

        col_count = vte.get_column_count()
        cursor_col, cursor_row = vte.get_cursor_position()

        mode = self.select_mode
        if mode is None:
            return

        start_col, start_row = self.selection_start

        vte.set_selection_block_mode(self.select_mode == "block")

        if mode == "standard":
            start = start_row * col_count + start_col;
            end = cursor_row * col_count + cursor_col;
            if start < end:
                vte.select_text(start_col, start_row,
                                cursor_col, cursor_row)
            else:
                vte.select_text(cursor_col, cursor_row,
                                start_col, start_row)
        elif mode == "line":
            vte.select_text(0, min(start_row, cursor_row),
                            col_count-1, max(start_row, cursor_row))
        elif mode == "block":
            vte.select_text(min(start_col, cursor_col), min(start_row, cursor_row),
                            max(start_col, cursor_col), max(start_row, cursor_row))


    def start_select(self, mode):
        self.selection_start = self.vte.get_cursor_position()
        self.select_mode = mode
        self.update_selection()


    def stop_select(self):
        self.selection_start = None
        self.select_mode = None
        self.vte.unselect_all()


    def yank_selection(self, dest):
        if dest == "primary":
            self.select_mode = None
            self.stop_select()
        elif dest == "clipboard":
            self.select_mode = None
            self.stop_select()


    def paste_selection(self, dest):
        if dest == "primary":
            self.vte.paste_primary()
        elif dest == "clipboard":
            self.vte.paste_clipboard()


def action_inject_keys(terminal, chars):
    """sends characters to the terminal

chars (string): characters to send
"""

    if isinstance(chars, str):
        chars = chars.encode("utf-8")
    terminal.vte.feed_child_binary(chars)


def action_move(terminal, x=0, y=0, screen=0, column=None):
    """moves cursor

x (int): number of rows to move
y (int): number of columns to move
screen (float): multiples of screen height to move
column (float): multiples of screen width to move
"""

    vte = terminal.vte

    col_count = vte.get_column_count()
    cursor_col, cursor_row = vte.get_cursor_position()
    adjustment = vte.get_vadjustment()
    mode = vte.get_cursor_blink_mode()
    vte.set_cursor_blink_mode(Vte.CursorBlinkMode.OFF)

    if column is not None:
        base_x = vte.get_column_count() * column
    else:
        base_x = cursor_col

    diff_y, dest_x = divmod(base_x+x, col_count)
    dest_y = cursor_row + y + diff_y

    if screen != 0:
        dest_y += vte.get_row_count() * screen
    if dest_y < cursor_row:
        first_row = adjustment.get_lower()
        if dest_y < first_row:
            dest_y = first_row
            dest_x = 0
    elif dest_y > cursor_row:
        row_count = adjustment.get_upper()
        if dest_y >= row_count:
            dest_y = row_count-1
            dest_x = col_count-1

    vte.set_cursor_position(dest_x, dest_y)

    terminal.update_scroll()
    terminal.update_selection()
    vte.set_cursor_blink_mode(mode)


def action_move_regexp(terminal, regexp, backward=False, after=False):
    """move within line of cursor to the next matching regexp
(uses GLib regex)

regexp (string): regexp to match
backward (bool): whether to search backward from cursor
after (bool): whether to move to start or end of matched text
"""

    vte = terminal.vte
    cursor_col, cursor_row = vte.get_cursor_position()
    success, row, col = mc.match_regexp(vte,regexp, cursor_row, cursor_col, backward, after)

    if not success:
        return

    adjustment = vte.get_vadjustment()
    mode = vte.get_cursor_blink_mode()
    vte.set_cursor_blink_mode(Vte.CursorBlinkMode.OFF)
    vte.set_cursor_position(col, row)
    terminal.update_scroll()
    terminal.update_selection()
    vte.set_cursor_blink_mode(mode)


def action_scroll(terminal, y=0, screen=0):
    """scroll terminal

y (int): number of rows to scroll (negative values to scroll up)
screen (float): multiples of screen height to scroll
"""

    vte = terminal.vte

    adjustment = vte.get_vadjustment()
    dest = adjustment.get_value()
    if screen != 0:
        dest += vte.get_row_count() * screen
    dest += y
    adjustment.set_value(dest);


def action_enter_command_mode(terminal):
    """switches to command mode"""

    vte = terminal.vte
    vte.disconnect_pty_read()

    adjustment = vte.get_vadjustment()
    scroll_row = adjustment.get_value()
    row_count = vte.get_row_count()
    cursor_col, cursor_row = vte.get_cursor_position()
    terminal.normal_cursor_position = cursor_col, cursor_row

    if cursor_row < scroll_row:
        terminal.vte.set_cursor_position(cursor_col,
                                         scroll_row)
    elif cursor_row - row_count >= scroll_row:
        terminal.vte.set_cursor_position(cursor_col,
                                         scroll_row+row_count-1)

    terminal.command_mode = True


def action_leave_command_mode(terminal):
    """switches to normal mode"""

    vte = terminal.vte
    vte.set_cursor_position(*terminal.normal_cursor_position)
    terminal.command_mode = False
    if terminal.select_mode is not None:
        terminal.stop_select()
    terminal.update_scroll()
    vte.connect_pty_read()


def action_enter_select_mode(terminal, mode="standard"):
    """enter one of the selection modes

mode (string): selection mode (can be "standard", "line" or "block")
"""

    if mode not in ("standard", "line", "block"):
        return
    terminal.start_select(mode)


def action_leave_select_mode(terminal):
    """stop selecting text but stay in command mode"""

    if terminal.select_mode is not None:
        terminal.stop_select()


def action_yank_selection(terminal, dest="clipboard", leave_command_mode=False):
    """copy selected text to X selection

dest (string): destination to copy to (can be "primary" or "clipboard")
leave_command_mode (bool): if in command mode, switch back to normal mode
"""

    terminal.yank_selection(dest)
    if leave_command_mode:
        action_leave_command_mode(terminal)


def action_paste_selection(terminal, src="clipboard"):
    """send X selection to terminal

src (string): selection to copy from (can be "primary" or "clipboard")
"""
    terminal.paste_selection(src)


def action_zoom(terminal, set=None, change=0):
    """change text zoom level

set (float): set scaling factor to this value
change (float): relative amount to change current scaling factor
                (example: -0.5 reduces scale to half, 1.0 doubles scale)
"""

    scale = app.font_scale
    if set is not None:
        scale = set
    scale *= (1+change)
    if scale < 0.1 or scale > 10:
        return
    app.set_font_scale(scale)


def action_fullscreen(terminal, set=None, toggle=False):
    """switch between normal and fullscreen mode

set (bool): enable/disable fullscreen mode
toggle (bool): if true, toggle fullscreen mode
"""

    if set is not None:
        if set:
            app.is_fullscreen = True
        else:
            app.is_fullscreen = False
    if toggle:
        app.is_fullscreen = not app.is_fullscreen
    if app.is_fullscreen:
        app.window.fullscreen()
    else:
        app.window.unfullscreen()


def action_reset_terminal(terminal, clear_scrollback=False):
    """resets all state of the terminal

clear_scrollback (bool): also clear the scrollback buffer
"""

    vte = terminal.vte
    terminal.stop_select()
    vte.reset(True, clear_scrollback)
    terminal.normal_cursor_position = vte.get_cursor_position()


def action_reload_config(terminal):
    """reload configuration file"""

    app.load_config()
    app.apply_config()


def action_new_tab(terminal, position=None, select=True, keep_open=False, command=None):
    """opens a new terminal

position (string): where to place the new tab in the order
(can be "start", "end", "before", "after")
"""

    if position == "start":
        index = 0
    elif position == "before":
        index = app.terminals.index(terminal)
    elif position == "after":
        index = app.terminals.index(terminal)+1
    else:
        index = len(app.terminals)

    new_terminal = app.add_terminal(keep_open, index)
    if command is None:
        command = app.shell
    new_terminal.run(command)
    if select:
        app.set_active_terminal(new_terminal)
    else:
        set_window_title()


def action_close_tab(terminal):
    """closes the current tab and kill the attached process"""

    os.kill(terminal.pid, signal.SIGHUP)
    app.remove_terminal(terminal, 0)


def action_select_tab(terminal, position=None):
    """switches to another tab

position (string): position of the tab to select
(can be "first", "last", "previous", "next")
"""

    terminal_count = len(app.terminals)
    if position == "first":
        index = 0
    elif position == "previous":
        index = app.terminals.index(terminal) - 1
        if index == -1:
            index = terminal_count - 1
    elif position == "next":
        index = app.terminals.index(terminal) + 1
        if index == terminal_count:
            index = 0
    elif position == "last":
        index = terminal_count - 1
    else:
        return
    app.set_active_terminal(app.terminals[index])


def action_move_tab(terminal, position=None):
    """moves the active tab within the tab order

position (string): where to place the tab in the order
(can be "start", "end", "before", "after")
"""

    terminal_count = len(app.terminals)
    if position == "start":
        index = 0
    elif position == "before":
        index = app.terminals.index(terminal) - 1
        if index == -1:
            return
    elif position == "after":
        index = app.terminals.index(terminal) + 1
        if index == terminal_count:
            return
    elif position == "end":
        index = len(app.terminals) - 1
    else:
        return
    app.terminals.remove(terminal)
    app.terminals.insert(index, terminal)
    set_window_title()


regexp_compile_flags_none = GLib.RegexCompileFlags(0)
regexp_match_flags_none = GLib.RegexMatchFlags(0)


actions = {
    "global": {
        "new-tab": action_new_tab,
        "close-tab": action_close_tab,
        "select-tab": action_select_tab,
        "move-tab": action_move_tab,
        "yank-selection": action_yank_selection,
        "zoom": action_zoom,
        "scroll": action_scroll,
        "fullscreen": action_fullscreen,
        "reset-terminal": action_reset_terminal,
        "reload-config": action_reload_config,
    },
    "normal": {
        "enter-command-mode": action_enter_command_mode,
        "inject-keys": action_inject_keys,
        "paste-selection": action_paste_selection,
    },
    "command": {
        "leave-command-mode": action_leave_command_mode,
        "move": action_move,
        "move-regexp": action_move_regexp,
        "start-select": action_enter_select_mode,
        "end-select": action_leave_select_mode,
    },
}

css_appearance = {
    "cursor-aspect-ratio": (("vte-terminal", "-GtkWidget-cursor-aspect-ratio"),),
    "padding": (("box", "padding"),),
    "scrollbar-padding": (
        ("scrollbar.mantid>contents>trough>slider", "border-width"),
        ("scrollbar.mantid>contents>trough>slider:backdrop", "border-width"),
    ),
    "scrollbar-width": (
        ("scrollbar.mantid>contents>trough>slider", "min-width"),
        ("scrollbar.mantid>contents>trough>slider:backdrop", "min-width"),
    ),
}

css_colors = {
    "padding": (("box", "background-color"),),
    "scrollbar": (
        ("scrollbar.mantid>contents>trough>slider", "background-color"),
        ("scrollbar.mantid>contents>trough>slider:backdrop", "background-color"),
    ),
    "scrollbar-background": (
        ("scrollbar.mantid>contents", "background-color"),
        ("scrollbar.mantid>contents:backdrop", "background-color"),
    ),
}


default_config = {
    "startup": {
        "term": "xterm-256color",
        "role": None,
        "keep-open": False,
        "fullscreen": False,
        "shell": os.environ.get("SHELL","/bin/sh"),
        "rows": 25,
        "columns": 80,
        "font-scale": 1.,
        "scrollback-lines": 1000,
        "scroll-on-output": False,
        "scroll-on-keystroke": True,
        "audible-bell": False,
    },
    "appearance": {
        "window-title": None,
        "show-scrollbar": True,
        "cursor-blink": "system",
        "cursor-shape": "block",
        "mouse-autohide": False,
        "allow-bold": True,
        "bold-is-bright": False,
        "cell-width-scale": 1.,
        "cell-height-scale": 1.,
        "icon": "terminal",
        "font": "Monospace",
    },
}


def get_arg_parser(home_dir,
                   description="fully keyboard-controllable terminal inspired by termite"):

    parser = argparse.ArgumentParser(prog="mantid", description=description)
    parser.add_argument('COMMAND', help='command to execute (instead of shell)', nargs='?')
    parser.add_argument('ARG', help='arguments to command', nargs='*')
    parser.add_argument('-v', '--version', help='version info', action="store_true")
    parser.add_argument('-d', '--pwd', help='working directory', default='.')
    parser.add_argument('-r', '--role', help='window role')
    parser.add_argument('-t', '--title', help='window title')
    parser.add_argument('-k', '--keep-open', help='keep window open after child exits',
                        action="store_true")
    parser.add_argument('-f', '--fullscreen', help='start in fullscreen mode',
                        action="store_true")
    parser.add_argument('-c', '--config', help='config file',
                        default=home_dir+"/.config/mantid.yml")
    parser.add_argument('-i', '--icon', help='window icon')
    parser.add_argument('-a', '--print-accelerators',
                        help='print key accelerator names in command mode',
                        action="store_true")

    return parser


re_css_validate = re.compile("[:;{}>\"']")

def css_validate(val):
    if isinstance(val,(int,float)):
        return True
    if not isinstance(val, str):
        return False
    if re_css_validate.search(val):
        return False
    return True


def quick_yaml_translate(value):
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif value is None:
        return "null"
    return value


def format_action(name,args):
    res = "%s(%s)" % \
    (name, ", ".join([ "%s=%s" % quick_yaml_translate(arg) for arg in args.items()]))
    return res


class App:

    def __init__(self):

        self.args = get_arg_parser(os.environ.get("HOME",".")).parse_args()

        p = os.environ["__MANTID__LD_LIBRARY_PATH"]
        if p != "":
            os.environ["LD_LIBRARY_PATH"] = p
        else:
            del os.environ["LD_LIBRARY_PATH"]
        p = os.environ["__MANTID__GI_TYPELIB_PATH"]
        if p != "":
            os.environ["GI_TYPELIB_PATH"] = p
        else:
            del os.environ["GI_TYPELIB_PATH"]
        del os.environ["__MANTID__LD_LIBRARY_PATH"]
        del os.environ["__MANTID__GI_TYPELIB_PATH"]

        self.load_config()

        self.terminals = []
        self.active_terminal = None
        self.is_fullscreen = False

        self.style = Gtk.CssProvider()

        self.work_dir = self.args.pwd


    def setup(self):
        self.hint_overlay = Gtk.Overlay()

        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.connect("destroy", exit_with_success)

        # self.window.connect("focus-in-event", focus_cb)
        # self.window.connect("focus-out-event", focus_cb)
        self.window.connect("screen-changed", alpha_screen_changed_cb)
        self.window.connect("window-state-event", window_state_cb)

        alpha_screen_changed_cb(self.window)

        self.print_accelerators = self.args.print_accelerators

        startup = self.config["startup"]

        keep_open = self.args.keep_open or startup["keep-open"]

        fullscreen = self.args.fullscreen or startup["fullscreen"]
        if fullscreen:
            action_fullscreen(None, set=fullscreen)

        self.apply_config()

        if self.args.COMMAND is not None:
            cmd = [self.args.COMMAND] + self.args.ARG
        else:
            cmd = self.shell

        self.add_terminal(keep_open, 0)
        self.set_active_terminal(self.terminals[0])

        self.active_terminal.vte.set_size(startup["columns"], startup["rows"])
        self.set_font_scale( self.config["startup"]["font-scale"] )

        self.window.show()

        self.active_terminal.run(cmd)


    def load_config(self):

        self.config = {
            "keybindings": {}
        }
        for key, section in default_config.items():
            self.config[key] = section.copy()
        self.config["appearance"]["colors"] = {}

        if os.path.exists(self.args.config):
            try:
                config_file = yaml.safe_load( open( self.args.config, "r" ) )
            except yaml.YAMLError as e:
                print("yaml:",e, file=sys.stderr)
                config_file = {}
            except IOError as e:
                print("config:",e, file=sys.stderr)
                config_file = {}
        else:
            print("""\
warning: Config file could not be loaded.
         You won't have any keybindings available.
advice: Copy one of the examples in /usr/share/mantid to ~/.config/mantid.yml
        and tweak it to your needs.""")
            config_file = {}

        for section_name, section in self.config.items():
            file_section = config_file.get(section_name, {})
            if isinstance(file_section, dict):
                self.config[section_name].update(file_section)
            else:
                print("config: section", section_name, "needs to be a mapping. Will be ignored.", file=sys.stderr)

        self.colors = default_colors.copy()
        self.colors.update( { key: None if value is None else rgba_parse(value)
                              for key, value in self.config["appearance"]["colors"].items() } )

        self.palette = default_palette.copy()

        for i in range(256):
            color = self.colors.get(i)
            if color is not None:
                self.palette[i] = color

        self.keybindings = {}
        for s in ("global","normal","command"):
            b = default_keybindings[s].copy()
            b.update(self.config["keybindings"].get(s,{}))
            a = {}

            for key, action in b.items():
                acc = Gtk.accelerator_parse(key)
                if acc.accelerator_key == 0:
                    print("keybindings:", "accelerator ", key, "failed to parse. Will be ignored.", file=sys.stderr)
                    continue
                binding = acc.accelerator_key, acc.accelerator_mods
                if action is None:
                    continue
                if isinstance(action, str):
                    action_name = action
                    args = {}
                else:
                    action_name = action.get("action","undefined")
                    args = action.copy()
                    try:
                        del args["action"]
                    except KeyError:
                        pass
                    if action_name == "move-regexp":
                        regexp = args.get("regexp","\\w+")
                        try:
                            gre = GLib.Regex.new(regexp,
                                                 regexp_compile_flags_none,
                                                 regexp_match_flags_none)
                        except gi.repository.GLib.Error:
                            print("keybindings:",
                                  "in action %s bound to %s regexp is invalid." %
                                  (format_action(action_name, args), key), file=sys.stderr)
                            continue
                        args["regexp"] = gre
                cmd = actions[s].get(action_name) or actions["global"].get(action_name)
                if cmd is None:
                    print("keybindings: action %s bound to %s is not defined." %
                          (format_action(action_name, args), key),
                          "Will be ignored.", file=sys.stderr)
                    continue
                action = action_name, cmd, args

                a[binding] = action

            self.keybindings[s] = a

        self.keybindings_normal = self.keybindings["global"].copy()
        self.keybindings_normal.update(self.keybindings["normal"])
        self.keybindings_command = self.keybindings["global"].copy()
        self.keybindings_command.update(self.keybindings["command"])


    def apply_config(self):

        startup = self.config["startup"]
        appearance = self.config["appearance"]

        if self.args.role is not None:
            role = self.args.role
        else:
            role = startup["role"]

        if role is not None:
            self.window.set_role(self.args.role)

        shell = startup["shell"]
        if isinstance(shell, str):
            shell = [ shell ]
        self.shell = shell

        if self.args.title is not None:
            self.title = self.args.title
        else:
            self.title = appearance["window-title"]

        if self.args.icon is not None:
            icon = self.args.icon
        else:
            icon = appearance["icon"]

        self.window.set_icon_name(icon)

        for terminal in self.terminals:
            terminal.apply_config()


        css = []

        for name, dests in css_appearance.items():
            for dest in dests:
                value = appearance.get(name)
                if value is None:
                    continue
                if not css_validate(value):
                    print("appearance: %s value %s is not in valid format, skipping." %
                          (name, value), file=sys.stderr)
                    continue
                sel, attr = dest
                entry = "%s { %s: %s; }" % (sel, attr, value)
                css.append(entry)

        colors = self.colors
        for name, dests in css_colors.items():
            for dest in dests:
                value = colors.get(name)
                if value is None:
                    continue
                value = "#%02x%02x%02x" % (int(value.red*255), int(value.green*255), int(value.blue*255))
                sel, attr = dest
                entry = "%s { %s: %s; }" % (sel, attr, value)
                css.append(entry)

        self.style.load_from_data("\n".join(css).encode("utf-8"))

        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual != None and screen.is_composited():
            self.window.set_visual(visual)

        self.window.set_app_paintable(True)


    def set_font_scale(self, scale):
        for term in self.terminals:
            term.vte.set_font_scale(scale)
        self.font_scale = scale


    def add_terminal(self, keep_open, pos=None):
        terminal = Terminal(keep_open)
        self.terminals.insert(pos, terminal)
        return terminal


    def remove_terminal(self, terminal, status):
        try:
            pos = self.terminals.index(terminal)
        except ValueError:
            return
        self.terminals.remove(terminal)
        terminal_count = len(app.terminals)
        if terminal_count == 0:
            Gtk.main_quit()
            sys.exit(status//256)
        if pos == terminal_count:
            pos -= 1
        self.set_active_terminal(self.terminals[pos])


    def set_active_terminal(self, terminal):
        if self.active_terminal is not None:
            self.window.remove(self.active_terminal.panel_overlay)
        self.active_terminal = terminal
        self.window.add(terminal.panel_overlay)
        terminal.vte.grab_focus()
        set_window_title()


    def find_keybinding(self, binding_map, event, debug_print=False):
        display = app.window.get_window().get_display()
        keymap = Gdk.Keymap.get_for_display(display)
        intent_default_mod_mask = keymap.get_modifier_mask(Gdk.ModifierIntent.DEFAULT_MOD_MASK)

        # 'direct' match
        modifiers = event.state

        t = keymap.translate_keyboard_state(event.hardware_keycode, modifiers, event.group)
        consumed_modifiers = t.consumed_modifiers
        result_keyval = t.keyval
        result_modifiers = modifiers & intent_default_mod_mask
        result_modifiers &= Gdk.ModifierType(~consumed_modifiers)

        if debug_print:
            label1 = get_key_name(result_keyval, result_modifiers)

        action = binding_map.get((result_keyval, result_modifiers))
        if action is not None:
            if debug_print:
                if label1 is not None:
                    print( "key '%s' pressed" % label1, file=sys.stderr)
            return action
        #print("n",result_keyval, result_modifiers)

        # match keyval converted without modifiers
        if (modifiers & intent_default_mod_mask):
            #print("c",modifiers & Gdk.ModifierType(~intent_default_mod_mask))
            t = keymap.translate_keyboard_state(event.hardware_keycode,
                                                modifiers & Gdk.ModifierType(~intent_default_mod_mask), event.group)
            result_keyval = t.keyval
            result_modifiers = modifiers & intent_default_mod_mask
            #result_modifiers = modifiers
            #result_modifiers &= intent_default_mod_mask | Gdk.ModifierType(~consumed_modifiers)
            #print("e",result_keyval, result_modifiers)

            if debug_print:
                label2 = get_key_name(result_keyval, result_modifiers)
                if label1 == label2:
                    label2 = None
                if label1 is None:
                    label1 = label2
                    label2 = None
                if label1 is not None:
                    if label2 is None:
                        print( "key '%s' pressed" % label1, file=sys.stderr)
                    else:
                        print( "key '%s' aka '%s' pressed" % (label1,label2), file=sys.stderr)
            action = binding_map.get((result_keyval, result_modifiers))
            if action is not None:
                return action

        else:
            if debug_print:
                print( "key '%s' pressed" % label1, file=sys.stderr)


def main():
#if __name__ == "__main__":

    try:
        import prctl
        if len(sys.argv) == 1:
            prctl.set_proctitle("mantid")
        else:
            prctl.set_proctitle("mantid "+" ".join(sys.argv[1:]))
    except:
        pass

    global app
    Gtk.init()
    app = App()
    app.setup()
    Gtk.main()
